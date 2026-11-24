import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { Draft } from '../api/types';
import { ErrorNote, Field } from '../components/basics';
import { useAction, useResource } from '../hooks';
import { useSession } from '../session';

export function DraftsPage() {
  const { me } = useSession();
  const navigate = useNavigate();
  const { data = [] } = useResource<Draft[]>('/drafts');
  const places = [
    ...me.memberships
      .filter((m) => m.role !== 'member')
      .map((m) => [String(m.community_id), m.community_name]),
    ...(me.role === 'admin' ? [['', 'Whole campus']] : []),
  ];
  const [place, setPlace] = useState(places[0]?.[0] ?? '');
  const [kind, setKind] = useState('announcement');
  const [title, setTitle] = useState('');
  const { run, error } = useAction();
  const create = async () => {
    const draft = await api.post<Draft>('/drafts', {
      community_id: place ? Number(place) : null,
      kind,
      title,
    });
    navigate(`/drafts/${draft.id}`);
  };
  return (
    <>
      <h1>Drafts</h1>
      {data.length === 0 && <p>You have no drafts.</p>}
      {data.map((draft) => (
        <article className="card" key={draft.id}>
          <h2>
            <Link to={`/drafts/${draft.id}`}>{draft.title}</Link>
          </h2>
          <p className="meta">
            {draft.kind} · {draft.community_name ?? 'Whole campus'} · {draft.status} ·{' '}
            {draft.collaborators.map((c) => c.display_name).join(', ')}
          </p>
        </article>
      ))}
      {places.length > 0 && (
        <form
          className="card"
          onSubmit={(e) => {
            e.preventDefault();
            void run(create);
          }}
        >
          <h2>New draft</h2>
          <Field label="For">
            <select value={place} onChange={(e) => setPlace(e.target.value)}>
              {places.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Kind">
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="announcement">Announcement</option>
              <option value="event">Event</option>
            </select>
          </Field>
          <Field label="Title">
            <input
              required
              maxLength={120}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </Field>
          <button>Start writing</button>
          <ErrorNote message={error} />
        </form>
      )}
    </>
  );
}
