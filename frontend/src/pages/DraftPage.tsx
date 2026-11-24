import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { Draft, Member, Post } from '../api/types';
import { ErrorNote, Field } from '../components/basics';
import { emptyEvent, EventFields, toEvent } from '../components/EventFields';
import { CollaborativeEditor } from '../editor/CollaborativeEditor';
import { DraftConnection, type DraftState } from '../editor/DraftConnection';
import { useAction, useResource } from '../hooks';

const MESSAGES: Record<DraftState['status'], string> = {
  connecting: 'Connecting…',
  online: 'Online',
  offline: 'Offline. Your changes are kept and will be merged when the connection returns.',
  refused: 'You can no longer edit this draft.',
  published: 'This draft is published and read-only.',
};

export function DraftPage() {
  const { id } = useParams();
  const { data: draft, error } = useResource<Draft>(`/drafts/${id}`);
  if (error) return <ErrorNote message={error.message} />;
  if (!draft) return <p>Loading…</p>;
  if (draft.status === 'published') {
    return (
      <p>
        This draft is published. <Link to={`/posts/${draft.published_post_id}`}>Open the post</Link>
      </p>
    );
  }
  return <DraftEditor key={draft.id} draft={draft} />;
}

function DraftEditor({ draft }: { draft: Draft }) {
  const [state, setState] = useState<DraftState>({
    status: 'connecting',
    version: 0,
    saved: true,
    people: [],
  });
  const [connection] = useState(() => new DraftConnection(draft.id, setState));
  useEffect(() => {
    connection.start();
    return connection.stop;
  }, [connection]);
  return (
    <>
      <h1>{draft.title}</h1>
      <p role="status" className={`banner ${state.status === 'online' ? '' : 'warning'}`}>
        {MESSAGES[state.status]}
        {state.status === 'online' && (state.saved ? ' · saved' : ' · saving…')}
        {state.postId && <Link to={`/posts/${state.postId}`}> Open the post</Link>}
      </p>
      <p className="meta">
        Editing now: {state.people.map((p) => p.display_name).join(', ')} · version {state.version}
      </p>
      <CollaborativeEditor
        connection={connection}
        editable={state.status === 'online' || state.status === 'offline'}
      />
      <Publish draft={draft} state={state} />
      {draft.community_id && <Invite draft={draft} communityId={draft.community_id} />}
    </>
  );
}

function Publish({ draft, state }: { draft: Draft; state: DraftState }) {
  const navigate = useNavigate();
  const [title, setTitle] = useState(draft.title);
  const [visibility, setVisibility] = useState('campus');
  const [pinned, setPinned] = useState(false);
  const [event, setEvent] = useState(emptyEvent);
  const [published, setPublished] = useState<number>();
  const { run, error, busy } = useAction();
  const publish = async () => {
    try {
      const post = await api.post<Post>(`/drafts/${draft.id}/publish`, {
        expected_version: state.version,
        title,
        visibility,
        pinned,
        event: draft.kind === 'event' ? toEvent(event) : null,
      });
      navigate(`/posts/${post.id}`);
    } catch (problem) {
      const { code, details } = problem as ApiError;
      if (code === 'ALREADY_PUBLISHED') setPublished(details!.post_id);
      throw problem;
    }
  };
  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        void run(publish);
      }}
    >
      <h2>Publish</h2>
      <Field label="Title">
        <input required maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} />
      </Field>
      <Field label="Who can see it">
        <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
          <option value="campus">Campus</option>
          {draft.community_id && <option value="community">Members</option>}
        </select>
      </Field>
      {draft.kind === 'event' && <EventFields value={event} onChange={setEvent} />}
      <label>
        <input type="checkbox" checked={pinned} onChange={(e) => setPinned(e.target.checked)} /> Pin
      </label>
      <button disabled={busy || state.status !== 'online' || !state.saved}>Publish</button>
      <ErrorNote message={error} />
      {published && <Link to={`/posts/${published}`}>Open the published post</Link>}
    </form>
  );
}

function Invite({ draft, communityId }: { draft: Draft; communityId: number }) {
  const { data: members = [] } = useResource<Member[]>(`/communities/${communityId}/members`);
  const [names, setNames] = useState(draft.collaborators.map((c) => c.display_name));
  const { run, error } = useAction();
  const officers = members.filter(
    (m) => m.role !== 'member' && !names.includes(m.user.display_name),
  );
  return (
    <section className="card">
      <h2>Collaborators</h2>
      <p>{names.join(', ')}</p>
      {officers.map(({ user }) => (
        <button
          key={user.id}
          type="button"
          onClick={() =>
            run(async () => {
              await api.post(`/drafts/${draft.id}/collaborators`, { user_id: user.id });
              setNames([...names, user.display_name]);
            })
          }
        >
          Invite {user.display_name}
        </button>
      ))}
      <ErrorNote message={error} />
    </section>
  );
}
