import { useState } from 'react';
import { api } from '../api/client';
import type { Post } from '../api/types';
import { useAction } from '../hooks';
import { useSession } from '../session';
import { ErrorNote, when } from './basics';
import { EventFields, fromEvent, toEvent } from './EventFields';

interface Props {
  post: Post;
  event: NonNullable<Post['event']>;
  onChange: () => void;
}

/** Time, place, RSVP and, for officers, changing the event. */
export function EventDetails({ post, event, onChange }: Props) {
  const { me } = useSession();
  const [form, setForm] = useState(fromEvent(event));
  const [editing, setEditing] = useState(false);
  const { run, error } = useAction();
  const manager =
    post.community_id === null
      ? me.role === 'admin'
      : me.memberships.some((m) => m.community_id === post.community_id && m.role !== 'member');
  const rsvp = (status: 'going' | 'interested' | null) =>
    run(() => api.put(`/events/${post.id}/rsvp`, { status }).then(onChange));
  const save = (cancelled: boolean) =>
    run(async () => {
      await api.put(`/events/${post.id}`, { ...toEvent(form), cancelled });
      setEditing(false);
      onChange();
    });
  return (
    <section className="event">
      {event.cancelled && <p className="banner warning">This event is cancelled.</p>}
      <p>
        <strong>{when(event.starts_at)}</strong> to {when(event.ends_at)} · {event.location}
      </p>
      <p className="meta">
        {event.going} of {event.capacity} places taken · {event.waitlisted} waiting · RSVP by{' '}
        {when(event.rsvp_deadline)}
      </p>
      <div className="row">
        <button
          type="button"
          aria-pressed={event.my_rsvp === 'going'}
          onClick={() => rsvp('going')}
        >
          {event.my_rsvp === 'waitlisted' ? 'On the waitlist' : 'Going'}
        </button>
        <button
          type="button"
          aria-pressed={event.my_rsvp === 'interested'}
          onClick={() => rsvp('interested')}
        >
          Interested
        </button>
        {event.my_rsvp && (
          <button type="button" className="quiet" onClick={() => rsvp(null)}>
            Withdraw
          </button>
        )}
        {manager && (
          <button type="button" className="quiet" onClick={() => setEditing(!editing)}>
            Change event
          </button>
        )}
      </div>
      {editing && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void save(false);
          }}
        >
          <EventFields value={form} onChange={setForm} />
          <button>Save changes</button>
          <button type="button" className="quiet" onClick={() => save(true)}>
            Cancel event
          </button>
        </form>
      )}
      <ErrorNote message={error} />
    </section>
  );
}
