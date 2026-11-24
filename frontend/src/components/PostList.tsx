import { useState } from 'react';
import { api } from '../api/client';
import type { Post, PostPage } from '../api/types';
import { useResource } from '../hooks';
import { useLive } from '../live/LiveProvider';
import { ErrorNote } from './basics';
import { PostCard } from './PostCard';

/** A live list of posts. `query` selects the list, e.g. "scope=feed". */
export function PostList({ query }: { query: string }) {
  const { data, error, reload } = useResource<PostPage>(`/posts?${query}`);
  // Pages loaded after the first one are kept until the first page is reloaded.
  const [older, setOlder] = useState<{ first?: PostPage; items: Post[]; next: number | null }>();
  useLive('feed', () => void reload());
  if (error) return <ErrorNote message={error.message} />;
  if (!data) return <p>Loading…</p>;
  const current = older?.first === data ? older : { items: [], next: data.next_before };
  const more = async () => {
    const page = await api.get<PostPage>(`/posts?${query}&before=${current.next}`);
    setOlder({ first: data, items: [...current.items, ...page.items], next: page.next_before });
  };
  const posts = [...data.items, ...current.items];
  return (
    <>
      {posts.length === 0 && <p>Nothing here yet.</p>}
      {posts.map((post) => (
        <PostCard key={post.id} post={post} onChange={() => void reload()} />
      ))}
      {current.next && (
        <button type="button" onClick={more}>
          Show older posts
        </button>
      )}
    </>
  );
}
