import { useState } from 'react';
import type { UserRef } from '../api/types';
import { Field, UserLink } from '../components/basics';
import { useResource } from '../hooks';

export function PeoplePage() {
  const [query, setQuery] = useState('');
  const { data = [] } = useResource<UserRef[]>(`/users?q=${encodeURIComponent(query)}`);
  return (
    <>
      <h1>People</h1>
      <Field label="Search by name or handle">
        <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} />
      </Field>
      <ul className="plain">
        {data.map((user) => (
          <li key={user.id}>
            <UserLink user={user} /> <span className="meta">@{user.handle}</span>
          </li>
        ))}
      </ul>
    </>
  );
}
