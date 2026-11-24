import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Community } from '../api/types';
import { ErrorNote, Field } from '../components/basics';
import { useAction, useResource } from '../hooks';
import { useSession } from '../session';

export function CommunitiesPage() {
  const { reload: reloadMe } = useSession();
  const { data = [], reload } = useResource<Community[]>('/communities');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [policy, setPolicy] = useState('open');
  const { run, error } = useAction();
  const request = async () => {
    await api.post('/communities', { name, description, join_policy: policy });
    setName('');
    setDescription('');
    await Promise.all([reload(), reloadMe()]);
  };
  return (
    <>
      <h1>Communities</h1>
      {data.map((community) => (
        <article className="card" key={community.id}>
          <h2>
            <Link to={`/communities/${community.id}`}>{community.name}</Link>
          </h2>
          <p>{community.description}</p>
          <p className="meta">
            {community.member_count} members · {community.join_policy}
            {community.status !== 'approved' && ` · ${community.status}`}
            {community.my_role && ` · you: ${community.my_role}`}
          </p>
        </article>
      ))}
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          void run(request);
        }}
      >
        <h2>Request a community</h2>
        <Field label="Name">
          <input
            required
            minLength={3}
            maxLength={80}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label="Description">
          <input
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Field>
        <Field label="Joining">
          <select value={policy} onChange={(e) => setPolicy(e.target.value)}>
            <option value="open">Open: anyone joins at once</option>
            <option value="closed">Closed: officers accept requests</option>
          </select>
        </Field>
        <button>Request</button>
        <p className="meta">A school admin approves new communities.</p>
        <ErrorNote message={error} />
      </form>
    </>
  );
}
