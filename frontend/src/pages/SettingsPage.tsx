import { useState } from 'react';
import { api } from '../api/client';
import type { Action, Programme, UserRef } from '../api/types';
import { ErrorNote, Field, UserLink, when } from '../components/basics';
import { useAction, useResource } from '../hooks';
import { useSession } from '../session';

export function SettingsPage() {
  return (
    <>
      <h1>Settings</h1>
      <ProfileForm />
      <FollowRequests />
      <Blocks />
      <ModerationActions />
      <DeleteAccount />
    </>
  );
}

function ProfileForm() {
  const { me, reload } = useSession();
  const { data: programmes = [] } = useResource<Programme[]>('/programmes');
  const [name, setName] = useState(me.display_name);
  const [bio, setBio] = useState(me.bio);
  const [programme, setProgramme] = useState(String(me.programme?.id ?? ''));
  const [approve, setApprove] = useState(me.approve_followers);
  const { run, error } = useAction();
  const body = {
    display_name: name,
    bio,
    programme_id: programme ? Number(programme) : null,
    approve_followers: approve,
  };
  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        void run(() => api.patch('/me', body).then(reload));
      }}
    >
      <h2>Profile</h2>
      <Field label="Display name">
        <input required maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Field label="About me">
        <input maxLength={300} value={bio} onChange={(e) => setBio(e.target.value)} />
      </Field>
      <Field label="Study programme">
        <select value={programme} onChange={(e) => setProgramme(e.target.value)}>
          <option value="">None</option>
          {programmes.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </Field>
      <label>
        <input type="checkbox" checked={approve} onChange={(e) => setApprove(e.target.checked)} />{' '}
        Approve new followers
      </label>
      <button>Save</button>
      <ErrorNote message={error} />
    </form>
  );
}

function FollowRequests() {
  const { data = [], reload } = useResource<UserRef[]>('/follow-requests');
  const { run, error } = useAction();
  const decide = (id: number, accept: boolean) =>
    run(() => api.post(`/follow-requests/${id}`, { accept }).then(reload));
  return (
    <section className="card">
      <h2>Follow requests</h2>
      {data.length === 0 && <p>None.</p>}
      {data.map((user) => (
        <div key={user.id} className="row">
          <UserLink user={user} />
          <button type="button" onClick={() => decide(user.id, true)}>
            Accept
          </button>
          <button type="button" className="quiet" onClick={() => decide(user.id, false)}>
            Decline
          </button>
        </div>
      ))}
      <ErrorNote message={error} />
    </section>
  );
}

function Blocks() {
  const { data = [], reload } = useResource<UserRef[]>('/blocks');
  return (
    <section className="card">
      <h2>Blocked people</h2>
      {data.length === 0 && <p>None.</p>}
      {data.map((user) => (
        <div key={user.id} className="row">
          {user.display_name}
          <button type="button" onClick={() => api.delete(`/users/${user.id}/block`).then(reload)}>
            Unblock
          </button>
        </div>
      ))}
    </section>
  );
}

const APPEAL_WINDOW_MS = 7 * 24 * 3600 * 1000;

function ModerationActions() {
  const { data = [], reload } = useResource<Action[]>('/me/moderation-actions');
  return (
    <section className="card">
      <h2>Decisions about my content</h2>
      {data.length === 0 && <p>None.</p>}
      {data.map((action) => (
        <ActionItem key={action.id} action={action} onChange={() => void reload()} />
      ))}
    </section>
  );
}

function ActionItem({ action, onChange }: { action: Action; onChange: () => void }) {
  const [statement, setStatement] = useState('');
  const [loadedAt] = useState(() => Date.now());
  const { run, error } = useAction();
  const open =
    action.appeal_status === 'none' &&
    loadedAt - new Date(action.created_at).getTime() < APPEAL_WINDOW_MS;
  return (
    <div className="comment">
      <p>
        <strong>{action.action}</strong> ({action.target_type}, {action.reason}):{' '}
        {action.explanation}
      </p>
      <p className="meta">
        {when(action.created_at)} · appeal: {action.appeal_status}
      </p>
      {open && (
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            void run(() =>
              api.post('/appeals', { action_id: action.id, statement }).then(onChange),
            );
          }}
        >
          <Field label="Why is this decision wrong?">
            <input
              required
              maxLength={1000}
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
            />
          </Field>
          <button>Appeal</button>
          <ErrorNote message={error} />
        </form>
      )}
    </div>
  );
}

function DeleteAccount() {
  const { signOut } = useSession();
  const { run, error } = useAction();
  const remove = () => {
    if (confirm('Delete your account? It becomes invisible now and is erased within 30 days.')) {
      void run(() => api.delete('/me').then(signOut));
    }
  };
  return (
    <section className="card">
      <h2>Delete account</h2>
      <button type="button" className="danger" onClick={remove}>
        Delete my account
      </button>
      <ErrorNote message={error} />
    </section>
  );
}
