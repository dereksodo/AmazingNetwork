import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Comment, Post, Reason } from '../api/types';
import { ErrorNote, Field, ReasonSelect, UserLink, when } from '../components/basics';
import { PostCard } from '../components/PostCard';
import { ReportForm } from '../components/ReportForm';
import { useAction, useResource } from '../hooks';
import { useLive } from '../live/LiveProvider';
import { useSession } from '../session';

/** One post with its comments, updated live. */
export function PostPage() {
  const { id } = useParams();
  const post = useResource<Post>(`/posts/${id}`);
  const comments = useResource<Comment[]>(`/posts/${id}/comments`);
  const reload = () => {
    void post.reload();
    void comments.reload();
  };
  useLive(`post:${id}`, reload);
  if (post.error) return <ErrorNote message={post.error.message} />;
  if (!post.data) return <p>Loading…</p>;
  const list = comments.data ?? [];
  const open = post.data.comments_enabled && !post.data.locked && post.data.status === 'visible';
  return (
    <>
      <PostCard post={post.data} onChange={reload} />
      <section className="card">
        <h2>Comments</h2>
        {!open && <p className="meta">Comments are closed.</p>}
        {list
          .filter((c) => c.parent_id === null)
          .map((comment) => (
            <div key={comment.id}>
              <CommentItem comment={comment} post={post.data!} onChange={reload} />
              <div className="replies">
                {list
                  .filter((reply) => reply.parent_id === comment.id)
                  .map((reply) => (
                    <CommentItem
                      key={reply.id}
                      comment={reply}
                      post={post.data!}
                      onChange={reload}
                    />
                  ))}
                {open && <CommentForm postId={post.data!.id} parentId={comment.id} />}
              </div>
            </div>
          ))}
        {open && <CommentForm postId={post.data.id} />}
      </section>
    </>
  );
}

function CommentForm({ postId, parentId }: { postId: number; parentId?: number }) {
  const [open, setOpen] = useState(parentId === undefined);
  const [body, setBody] = useState('');
  const { run, error, busy } = useAction();
  if (!open) {
    return (
      <button type="button" className="quiet" onClick={() => setOpen(true)}>
        Reply
      </button>
    );
  }
  const send = async () => {
    await api.post(`/posts/${postId}/comments`, { body, parent_id: parentId ?? null });
    setBody('');
    setOpen(parentId === undefined);
  };
  return (
    <form
      className="inline-form"
      onSubmit={(e) => {
        e.preventDefault();
        void run(send);
      }}
    >
      <Field label={parentId ? 'Reply' : 'Comment'}>
        <input required maxLength={1000} value={body} onChange={(e) => setBody(e.target.value)} />
      </Field>
      <button disabled={busy}>Send</button>
      <ErrorNote message={error} />
    </form>
  );
}

interface ItemProps {
  comment: Comment;
  post: Post;
  onChange: () => void;
}

function CommentItem({ comment, post, onChange }: ItemProps) {
  const { me } = useSession();
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(comment.body);
  const { run, error } = useAction();
  const mine = comment.author.id === me.id;
  const officer = me.memberships.some(
    (m) => m.community_id === post.community_id && m.role !== 'member',
  );
  return (
    <div className="comment" id={`comment-${comment.id}`}>
      <UserLink user={comment.author} />{' '}
      <span className="meta">
        {when(comment.created_at)}
        {comment.edited_at && ' · edited'}
        {comment.status !== 'visible' && ` · ${comment.status}`}
      </span>
      {editing ? (
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            void run(async () => {
              await api.patch(`/comments/${comment.id}`, { body });
              setEditing(false);
              onChange();
            });
          }}
        >
          <Field label="Edit comment">
            <input value={body} maxLength={1000} onChange={(e) => setBody(e.target.value)} />
          </Field>
          <button>Save</button>
        </form>
      ) : (
        <p>{comment.body}</p>
      )}
      <div className="row">
        {mine && (
          <>
            <button type="button" className="quiet" onClick={() => setEditing(!editing)}>
              Edit
            </button>
            <button
              type="button"
              className="quiet"
              onClick={() => run(() => api.delete(`/comments/${comment.id}`).then(onChange))}
            >
              Delete
            </button>
          </>
        )}
        {!mine && <ReportForm targetType="comment" targetId={comment.id} />}
        {!mine && officer && comment.status === 'visible' && (
          <OfficerHide id={comment.id} onDone={onChange} />
        )}
      </div>
      <ErrorNote message={error} />
    </div>
  );
}

function OfficerHide({ id, onDone }: { id: number; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<Reason>('harassment');
  const [explanation, setExplanation] = useState('');
  const [escalate, setEscalate] = useState(false);
  const { run, error } = useAction();
  if (!open) {
    return (
      <button type="button" className="quiet" onClick={() => setOpen(true)}>
        Hide as officer
      </button>
    );
  }
  const body = { reason, explanation, escalate };
  return (
    <form
      className="inline-form"
      onSubmit={(e) => {
        e.preventDefault();
        void run(() => api.post(`/comments/${id}/officer-hide`, body).then(onDone));
      }}
    >
      <ReasonSelect value={reason} onChange={setReason} />
      <Field label="Explanation">
        <input required value={explanation} onChange={(e) => setExplanation(e.target.value)} />
      </Field>
      <label>
        <input type="checkbox" checked={escalate} onChange={(e) => setEscalate(e.target.checked)} />{' '}
        Escalate to moderators
      </label>
      <button>Hide</button>
      <ErrorNote message={error} />
    </form>
  );
}
