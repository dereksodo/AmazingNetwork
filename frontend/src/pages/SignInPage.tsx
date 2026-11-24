import { useState } from 'react';
import { api, session } from '../api/client';
import type { Programme, SignedIn } from '../api/types';
import { ErrorNote, Field } from '../components/basics';
import { useAction, useResource } from '../hooks';

/** Sign in or create an account. */
export function SignInPage({ onSignedIn }: { onSignedIn: (answer: SignedIn) => void }) {
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', handle: '', display_name: '' });
  const [programme, setProgramme] = useState('');
  const { data: programmes = [] } = useResource<Programme[]>('/programmes');
  const { run, error, busy } = useAction();
  const text = (name: keyof typeof form, label: string, type = 'text') => (
    <Field label={label}>
      <input
        required
        type={type}
        autoComplete={type === 'password' ? 'current-password' : undefined}
        value={form[name]}
        onChange={(e) => setForm({ ...form, [name]: e.target.value })}
      />
    </Field>
  );
  const submit = async () => {
    const answer = creating
      ? await api.post<SignedIn>('/auth/register', {
          ...form,
          programme_id: programme ? Number(programme) : null,
        })
      : await api.post<SignedIn>('/auth/login', { email: form.email, password: form.password });
    session.start(answer.token);
    onSignedIn(answer);
  };
  return (
    <main className="narrow">
      <h1>Connect</h1>
      <p>The social network of your campus.</p>
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          void run(submit);
        }}
      >
        <h2>{creating ? 'Create an account' : 'Sign in'}</h2>
        {text('email', 'University email', 'email')}
        {text('password', 'Password', 'password')}
        {creating && (
          <>
            {text('handle', 'Handle (a-z, 0-9, _)')}
            {text('display_name', 'Name')}
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
          </>
        )}
        <button disabled={busy}>{creating ? 'Create account' : 'Sign in'}</button>
        <button type="button" className="quiet" onClick={() => setCreating(!creating)}>
          {creating ? 'I have an account' : 'I am new here'}
        </button>
        <ErrorNote message={error} />
      </form>
    </main>
  );
}
