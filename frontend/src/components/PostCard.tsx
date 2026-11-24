import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Post, PostVersion, ReactionKind, Visibility } from '../api/types';
import { RichTextEditor } from '../editor/RichTextEditor';
import { useAction, useResource } from '../hooks';
import { useSession } from '../session';
import { AuthImage, ErrorNote, Field, RichText, UserLink, when } from './basics';
import { EventDetails } from './EventDetails';
import { ReportForm } from './ReportForm';

const REACTIONS: Record<ReactionKind, string> = {
  like: '👍',
  love: '❤️',
  celebrate: '🎉',
  think: '🤔',
};

interface Props {
  post: Post;
  onChange: () => void;
}

/** A post with every action the reader may take. */
export function PostCard({ post, onChange }: Props) {
  const { me } = useSession();
  const [mode, setMode] = useState<'read' | 'edit' | 'versions' | 'reshare'>('read');
  const { run, error } = useAction();
  const mine = post.author.id === me.id;
  const officer = me.memberships.some(
    (m) => m.community_id === post.community_id && ['officer', 'owner'].includes(m.role),
  );
  const campusAdmin =
    me.role === 'admin' &&
    post.community_id === null &&
    ['announcement', 'event'].includes(post.type);
  const act = (action: Promise<unknown>) => run(() => action.then(onChange));

  return (
    <article className="card">
      <header>
        <UserLink user={post.author} />
        {post.community_id && (
          <>
            {' in '}
            <Link to={`/communities/${post.community_id}`}>{post.community_name}</Link>
          </>
        )}
        <span className="meta">
          {' · '}
          <Link to={`/posts/${post.id}`}>{when(post.created_at)}</Link>
          {post.edited_at && ' · edited'}
        </span>
        <span className="tags">
          <span className="tag">{post.type}</span>
          <span className="tag">{post.visibility}</span>
          {post.pinned && <span className="tag">pinned</span>}
          {post.locked && <span className="tag">locked</span>}
        </span>
      </header>
      {post.status !== 'visible' && (
        <p className="banner warning">
          This post is {post.status} by the moderators. Nobody can interact with it.{' '}
          {mine && <Link to="/settings">See the reason or appeal</Link>}
        </p>
      )}
      {mode === 'edit' ? (
        <EditPost
          post={post}
          onDone={() => {
            setMode('read');
            onChange();
          }}
        />
      ) : (
        <>
          {post.title && <h2>{post.title}</h2>}
          <RichText html={post.body_html} />
        </>
      )}
      {post.reshare_of && (
        <blockquote className="reshare">
          <UserLink user={post.reshare_of.author} />{' '}
          <Link className="meta" to={`/posts/${post.reshare_of.id}`}>
            {when(post.reshare_of.created_at)}
          </Link>
          {post.reshare_of.title && <h3>{post.reshare_of.title}</h3>}
          <RichText html={post.reshare_of.body_html} />
        </blockquote>
      )}
      <div className="images">
        {post.images.map((image) => (
          <AuthImage key={image.id} id={image.id} alt={image.alt_text} />
        ))}
      </div>
      {post.event && <EventDetails post={post} event={post.event} onChange={onChange} />}
      <footer className="row">
        {(Object.keys(REACTIONS) as ReactionKind[]).map((kind) => {
          const on = post.my_reactions.includes(kind);
          const path = `/posts/${post.id}/reactions/${kind}`;
          return (
            <button
              key={kind}
              type="button"
              className="quiet"
              aria-pressed={on}
              aria-label={`${REACTIONS[kind]} ${post.reactions[kind] ?? 0} ${kind}`}
              onClick={() => act(on ? api.delete(path) : api.put(path))}
            >
              {REACTIONS[kind]} {post.reactions[kind] ?? 0}
            </button>
          );
        })}
        <Link to={`/posts/${post.id}`}>{post.comment_count} comments</Link>
        {post.visibility === 'campus' && me.role !== 'admin' && (
          <button type="button" className="quiet" onClick={() => setMode('reshare')}>
            Reshare
          </button>
        )}
        {mine && (
          <>
            <button type="button" className="quiet" onClick={() => setMode('edit')}>
              Edit
            </button>
            <button
              type="button"
              className="quiet"
              onClick={() => act(api.delete(`/posts/${post.id}`))}
            >
              Delete
            </button>
          </>
        )}
        {(mine || me.role === 'moderator') && post.edited_at && (
          <button type="button" className="quiet" onClick={() => setMode('versions')}>
            Versions
          </button>
        )}
        {(officer || campusAdmin) &&
          (['pinned', 'locked'] as const).map((flag) => (
            <button
              key={flag}
              type="button"
              className="quiet"
              aria-pressed={post[flag]}
              onClick={() =>
                act(
                  api.put(`/posts/${post.id}/officer-controls`, {
                    pinned: post.pinned,
                    locked: post.locked,
                    [flag]: !post[flag],
                  }),
                )
              }
            >
              {{ pinned: 'Pin', locked: 'Lock' }[flag]}
            </button>
          ))}
        {!mine && <ReportForm targetType="post" targetId={post.id} />}
      </footer>
      {mode === 'versions' && <Versions post={post} />}
      {mode === 'reshare' && (
        <Reshare
          post={post}
          onDone={() => {
            setMode('read');
            onChange();
          }}
        />
      )}
      <ErrorNote message={error} />
    </article>
  );
}

function EditPost({ post, onDone }: { post: Post; onDone: () => void }) {
  const [html, setHtml] = useState(post.body_html);
  const [title, setTitle] = useState(post.title ?? '');
  const [visibility, setVisibility] = useState(post.visibility);
  const [version] = useState(post.version);
  const { run, error } = useAction();
  const choices: Visibility[] = post.reshare_of
    ? ['campus']
    : ['campus', post.community_id ? 'community' : 'followers'];
  const save = () =>
    api.patch(
      `/posts/${post.id}`,
      {
        title: title || null,
        body_html: html,
        visibility,
        comments_enabled: post.comments_enabled,
      },
      { 'If-Match': String(version) },
    );
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void run(() => save().then(onDone));
      }}
    >
      {post.type !== 'post' && (
        <Field label="Title">
          <input required value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
      )}
      <RichTextEditor label="Post text" initial={post.body_html} onChange={setHtml} />
      <div className="row">
        <Field label="Who can see it">
          <select value={visibility} onChange={(e) => setVisibility(e.target.value as Visibility)}>
            {choices.map((choice) => (
              <option key={choice}>{choice}</option>
            ))}
          </select>
        </Field>
        <button>Save</button>
        <button type="button" className="quiet" onClick={onDone}>
          Cancel
        </button>
      </div>
      <ErrorNote message={error} />
    </form>
  );
}

function Versions({ post }: { post: Post }) {
  const { data = [] } = useResource<PostVersion[]>(`/posts/${post.id}/versions`);
  return (
    <section>
      <h3>Earlier versions</h3>
      {data.map((version) => (
        <blockquote key={version.version}>
          <span className="meta">
            Version {version.version}, replaced {when(version.replaced_at)}
          </span>
          <RichText html={version.body_html} />
        </blockquote>
      ))}
    </section>
  );
}

function Reshare({ post, onDone }: { post: Post; onDone: () => void }) {
  const [html, setHtml] = useState('');
  const { run, error } = useAction();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void run(() => api.post(`/posts/${post.id}/reshare`, { body_html: html }).then(onDone));
      }}
    >
      <RichTextEditor label="Your comment on the reshared post" onChange={setHtml} />
      <button>Reshare with campus</button>
      <ErrorNote message={error} />
    </form>
  );
}
