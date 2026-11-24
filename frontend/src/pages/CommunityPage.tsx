import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Community, Member, Post } from '../api/types';
import { ErrorNote, UserLink } from '../components/basics';
import { Composer } from '../components/Composer';
import { PostCard } from '../components/PostCard';
import { PostList } from '../components/PostList';
import { useAction, useResource } from '../hooks';
import { useLive } from '../live/LiveProvider';
import { useSession } from '../session';

export function CommunityPage() {
  const { id } = useParams();
  const { reload: reloadMe } = useSession();
  const { data: community, error, reload } = useResource<Community>(`/communities/${id}`);
  const pinned = useResource<Post[]>(`/posts/pinned?community_id=${id}`);
  const { run, error: actionError } = useAction();
  useLive('feed', () => void pinned.reload());
  if (error) return <ErrorNote message={error.message} />;
  if (!community) return <p>Loading…</p>;
  const act = (action: Promise<unknown>) =>
    run(async () => {
      await action;
      await Promise.all([reload(), reloadMe()]);
    });
  const toggle = (on: boolean, what: 'follow' | 'mute') =>
    act(on ? api.delete(`/communities/${id}/${what}`) : api.put(`/communities/${id}/${what}`));
  const member = community.my_status === 'active';
  return (
    <>
      <h1>{community.name}</h1>
      <p>{community.description}</p>
      {community.status !== 'approved' ? (
        <p className="banner warning">This community is {community.status}.</p>
      ) : (
        <div className="row">
          {community.my_status === null && (
            <button type="button" onClick={() => act(api.post(`/communities/${id}/join`))}>
              Join
            </button>
          )}
          {community.my_status === 'pending' && <span>Waiting for an officer</span>}
          {community.my_status !== null && community.my_role !== 'owner' && (
            <button
              type="button"
              className="quiet"
              onClick={() => act(api.delete(`/communities/${id}/members/me`))}
            >
              Leave
            </button>
          )}
          <button
            type="button"
            className="quiet"
            aria-pressed={community.following}
            onClick={() => toggle(community.following, 'follow')}
          >
            Follow
          </button>
          <button
            type="button"
            className="quiet"
            aria-pressed={community.muted}
            onClick={() => toggle(community.muted, 'mute')}
          >
            Mute notifications
          </button>
        </div>
      )}
      <ErrorNote message={actionError} />
      {member && <Members community={community} onChange={() => void reload()} />}
      {member && community.status === 'approved' && <Composer community={community} />}
      {pinned.data?.map((post) => (
        <PostCard key={post.id} post={post} onChange={() => void pinned.reload()} />
      ))}
      <PostList query={`community_id=${id}`} />
    </>
  );
}

function Members({ community, onChange }: { community: Community; onChange: () => void }) {
  const base = `/communities/${community.id}`;
  const { data = [], reload } = useResource<Member[]>(`${base}/members`);
  const { me, reload: reloadMe } = useSession();
  const { run, error } = useAction();
  useLive(`community:${community.id}`, () => {
    void reload();
    void reloadMe();
    onChange();
  });
  const owner = community.my_role === 'owner';
  return (
    <details className="card">
      <summary>{community.member_count} members</summary>
      <ul className="plain">
        {data.map(({ user, role, status }) => {
          const path = `${base}/members/${user.id}`;
          return (
            <li key={user.id} className="row">
              <UserLink user={user} /> <span className="tag">{role}</span>
              {status === 'pending' && (
                <>
                  <span className="tag">wants to join</span>
                  {[true, false].map((accept) => (
                    <button
                      key={String(accept)}
                      type="button"
                      onClick={() => run(() => api.post(`${base}/requests/${user.id}`, { accept }))}
                    >
                      {accept ? 'Accept' : 'Decline'}
                    </button>
                  ))}
                </>
              )}
              {owner && status === 'active' && user.id !== me.id && (
                <>
                  <button
                    type="button"
                    className="quiet"
                    onClick={() =>
                      run(() => api.patch(path, { role: role === 'member' ? 'officer' : 'member' }))
                    }
                  >
                    {role === 'member' ? 'Make officer' : 'Make member'}
                  </button>
                  <button
                    type="button"
                    className="quiet"
                    onClick={() => run(() => api.delete(path))}
                  >
                    Remove
                  </button>
                </>
              )}
            </li>
          );
        })}
      </ul>
      <ErrorNote message={error} />
    </details>
  );
}
