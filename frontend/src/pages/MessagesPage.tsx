import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Conversation, Message } from '../api/types';
import { ErrorNote, Field, when } from '../components/basics';
import { ReportForm } from '../components/ReportForm';
import { useAction, useResource } from '../hooks';
import { useLive } from '../live/LiveProvider';
import { useSession } from '../session';

export function MessagesPage() {
  const { id } = useParams();
  const { me } = useSession();
  const { data = [], reload } = useResource<Conversation[]>('/conversations');
  useLive(`user:${me.id}`, () => void reload());
  return (
    <>
      <h1>Messages</h1>
      <nav className="row" aria-label="Conversations">
        {data.map((conversation) => (
          <Link
            key={conversation.id}
            to={`/messages/${conversation.id}`}
            aria-current={String(conversation.id) === id ? 'page' : undefined}
          >
            {conversation.other.display_name}
          </Link>
        ))}
      </nav>
      {id ? <Thread key={id} id={Number(id)} /> : <p>Open a conversation from a profile.</p>}
    </>
  );
}

function Thread({ id }: { id: number }) {
  const { me } = useSession();
  const { data = [], error, reload } = useResource<Message[]>(`/conversations/${id}/messages`);
  const [body, setBody] = useState('');
  const [selected, setSelected] = useState<number[]>([]);
  const action = useAction();
  useLive(`user:${me.id}`, ({ event, data: { conversation_id } }) => {
    if (event === 'resync' || conversation_id === id) void reload();
  });
  if (error) return <ErrorNote message={error.message} />;
  const select = (messageId: number, on: boolean) =>
    setSelected(on ? [...selected, messageId] : selected.filter((m) => m !== messageId));
  return (
    <section className="card">
      <ol className="plain thread" aria-live="polite">
        {data.map((message) => (
          <li key={message.id} className={message.sender_id === me.id ? 'mine' : ''}>
            <p>{message.body}</p>
            <span className="meta">{when(message.created_at)}</span>
            {message.sender_id !== me.id && (
              <label className="meta">
                <input
                  type="checkbox"
                  checked={selected.includes(message.id)}
                  onChange={(e) => select(message.id, e.target.checked)}
                />{' '}
                attach to report
              </label>
            )}
          </li>
        ))}
      </ol>
      <form
        className="inline-form"
        onSubmit={(e) => {
          e.preventDefault();
          void action.run(async () => {
            await api.post(`/conversations/${id}/messages`, { body });
            setBody('');
          });
        }}
      >
        <Field label="Message">
          <input required maxLength={2000} value={body} onChange={(e) => setBody(e.target.value)} />
        </Field>
        <button disabled={action.busy}>Send</button>
      </form>
      <ErrorNote message={action.error} />
      {selected.length > 0 && (
        <ReportForm targetType="message" targetId={id} messageIds={selected} />
      )}
    </section>
  );
}
