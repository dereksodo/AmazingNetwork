import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Notification } from '../api/types';
import { when } from '../components/basics';
import { useResource } from '../hooks';
import { useLive } from '../live/LiveProvider';
import { useSession } from '../session';

export function NotificationsPage() {
  const { me } = useSession();
  const { data = [], reload } = useResource<Notification[]>('/notifications');
  useLive(`user:${me.id}`, () => void reload());
  useEffect(() => {
    if (data.some((n) => n.read_at === null)) void api.post('/notifications/read');
  }, [data]);
  return (
    <>
      <h1>Notifications</h1>
      {data.length === 0 && <p>Nothing new.</p>}
      <ul className="plain">
        {data.map((item) => (
          <li key={item.id} className="card">
            {item.type === 'system_notice' && <strong>Connect Moderation: </strong>}
            {item.post_id ? <Link to={`/posts/${item.post_id}`}>{item.text}</Link> : item.text}
            <p className="meta">
              {when(item.created_at)}
              {item.type === 'system_notice' && (
                <>
                  {' · cannot be answered · '}
                  <Link to="/settings">details and appeal</Link>
                </>
              )}
            </p>
          </li>
        ))}
      </ul>
    </>
  );
}
