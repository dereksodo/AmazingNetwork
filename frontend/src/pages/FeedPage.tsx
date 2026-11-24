import { useState } from 'react';
import { PostCard } from '../components/PostCard';
import { PostList } from '../components/PostList';
import { Composer } from '../components/Composer';
import type { Post } from '../api/types';
import { useResource } from '../hooks';
import { useSession } from '../session';

export function FeedPage() {
  const { me } = useSession();
  const [scope, setScope] = useState('feed');
  const pinned = useResource<Post[]>('/posts/pinned');
  return (
    <>
      <h1>Home</h1>
      {me.role !== 'admin' && <Composer />}
      {pinned.data?.map((post) => (
        <PostCard key={post.id} post={post} onChange={() => void pinned.reload()} />
      ))}
      <div className="row" role="group" aria-label="Choose a list">
        {[
          ['feed', 'My feed'],
          ['campus', 'All campus'],
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={scope === value}
            onClick={() => setScope(value)}
          >
            {label}
          </button>
        ))}
      </div>
      <PostList query={`scope=${scope}`} />
    </>
  );
}
