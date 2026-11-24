import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Conversation, Profile } from '../api/types';
import { ErrorNote } from '../components/basics';
import { PostList } from '../components/PostList';
import { ReportForm } from '../components/ReportForm';
import { useAction, useResource } from '../hooks';
import { useSession } from '../session';

const FOLLOW_LABEL = { none: 'Follow', pending: 'Requested', active: 'Following' };

export function ProfilePage() {
  const { id } = useParams();
  const { me } = useSession();
  const navigate = useNavigate();
  const { data: user, error, reload } = useResource<Profile>(`/users/${id}`);
  const { run, error: actionError } = useAction();
  if (error) return <ErrorNote message={error.message} />;
  if (!user) return <p>Loading…</p>;
  const follow = `/users/${id}/follow`;
  const message = async () => {
    const opened = await api.post<Conversation>('/conversations', { user_id: user.id });
    navigate(`/messages/${opened.id}`);
  };
  return (
    <>
      <h1>{user.display_name}</h1>
      <p className="meta">
        @{user.handle} · {user.programme?.name ?? user.role} · {user.follower_count} followers
      </p>
      <p>{user.bio}</p>
      {user.id !== me.id && (
        <div className="row">
          <button
            type="button"
            aria-pressed={user.follow_status !== 'none'}
            onClick={() =>
              run(() =>
                (user.follow_status === 'none' ? api.put(follow) : api.delete(follow)).then(reload),
              )
            }
          >
            {FOLLOW_LABEL[user.follow_status]}
          </button>
          {me.role === 'user' && user.role === 'user' && (
            <button type="button" onClick={() => run(message)}>
              Message
            </button>
          )}
          <button
            type="button"
            className="quiet"
            onClick={() =>
              run(() => api.put(`/users/${id}/block`).then(() => navigate('/settings')))
            }
          >
            Block
          </button>
          <ReportForm targetType="user" targetId={user.id} />
        </div>
      )}
      <ErrorNote message={actionError} />
      <PostList query={`author_id=${id}`} />
    </>
  );
}
