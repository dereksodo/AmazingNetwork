import { useState } from 'react';
import { api } from '../api/client';
import type { Community, UserRef } from '../api/types';
import { ErrorNote, Field } from '../components/basics';
import { useAction, useResource } from '../hooks';

export function AdminPage() {
  return (
    <>
      <h1>Administration</h1>
      <PendingCommunities />
      <Moderators />
      <AuditExport />
      <Agreement />
    </>
  );
}

function PendingCommunities() {
  const { data = [], reload } = useResource<Community[]>('/communities');
  const [reason, setReason] = useState('');
  const { run, error } = useAction();
  const pending = data.filter((c) => c.status === 'pending');
  const decide = (id: number, accept: boolean) =>
    run(() => api.post(`/admin/communities/${id}/decision`, { accept, reason }).then(reload));
  return (
    <section className="card">
      <h2>Requested communities</h2>
      {pending.length === 0 && <p>None.</p>}
      {pending.length > 0 && (
        <Field label="Reason for your decision">
          <input value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
      )}
      {pending.map((community) => (
        <div key={community.id} className="row">
          <strong>{community.name}</strong> {community.description}
          <button type="button" disabled={!reason} onClick={() => decide(community.id, true)}>
            Approve
          </button>
          <button
            type="button"
            className="quiet"
            disabled={!reason}
            onClick={() => decide(community.id, false)}
          >
            Reject
          </button>
        </div>
      ))}
      <ErrorNote message={error} />
    </section>
  );
}

function Moderators() {
  const { data = [] } = useResource<UserRef[]>('/users');
  const [user, setUser] = useState('');
  const [role, setRole] = useState('moderator');
  const [reason, setReason] = useState('');
  const [done, setDone] = useState('');
  const { run, error } = useAction();
  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        void run(async () => {
          await api.put(`/admin/users/${user}/role`, { role, reason });
          setDone('Role saved.');
        });
      }}
    >
      <h2>Moderators</h2>
      <Field label="User">
        <select required value={user} onChange={(e) => setUser(e.target.value)}>
          <option value="">Choose…</option>
          {data.map((u) => (
            <option key={u.id} value={u.id}>
              {u.display_name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Role">
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option>moderator</option>
          <option>user</option>
        </select>
      </Field>
      <Field label="Reason">
        <input required value={reason} onChange={(e) => setReason(e.target.value)} />
      </Field>
      <button>Save role</button>
      <p role="status">{done}</p>
      <ErrorNote message={error} />
    </form>
  );
}

function AuditExport() {
  const today = new Date().toISOString().slice(0, 10);
  const [start, setStart] = useState(`${today.slice(0, 8)}01`);
  const [end, setEnd] = useState(today);
  const { run, error } = useAction();
  const download = async () => {
    const blob = await api.blob(`/admin/audit-log?start=${start}&end=${end}`);
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `audit-${start}-${end}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  };
  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        void run(download);
      }}
    >
      <h2>Audit log</h2>
      <Field label="From">
        <input type="date" required value={start} onChange={(e) => setStart(e.target.value)} />
      </Field>
      <Field label="To">
        <input type="date" required value={end} onChange={(e) => setEnd(e.target.value)} />
      </Field>
      <button>Export CSV</button>
      <ErrorNote message={error} />
    </form>
  );
}

function Agreement() {
  const { data } = useResource<{ decided: number; agreed: number }>('/admin/ai-agreement');
  return (
    <section className="card">
      <h2>AI agreement</h2>
      <p>
        Moderators agreed with {data?.agreed} of {data?.decided} suggestions.
      </p>
    </section>
  );
}
