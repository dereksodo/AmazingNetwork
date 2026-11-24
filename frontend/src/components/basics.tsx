import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Reason, UserRef } from '../api/types';

export const REASONS: Reason[] = [
  'harassment',
  'hate',
  'spam',
  'sexual',
  'violence',
  'misinformation',
  'other',
];

export const when = (iso: string) =>
  new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });

export function ErrorNote({ message }: { message?: string }) {
  return message ? (
    <p className="error" role="alert">
      {message}
    </p>
  ) : null;
}

export function UserLink({ user }: { user: UserRef }) {
  return <Link to={`/users/${user.id}`}>{user.display_name}</Link>;
}

/** Rich text. The HTML was cleaned by the server's allow-list before it was stored. */
export function RichText({ html }: { html: string }) {
  return <div className="rich-text" dangerouslySetInnerHTML={{ __html: html }} />;
}

/** An image that needs the bearer token. */
export function AuthImage({ id, alt }: { id: number; alt: string }) {
  const [url, setUrl] = useState('');
  useEffect(() => {
    let objectUrl = '';
    void api.blob(`/images/${id}`).then((blob) => {
      objectUrl = URL.createObjectURL(blob);
      setUrl(objectUrl);
    });
    return () => URL.revokeObjectURL(objectUrl);
  }, [id]);
  return url ? <img src={url} alt={alt} /> : null;
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

/** Reason and explanation, used for reports and moderation. */
export function ReasonSelect({
  value,
  onChange,
}: {
  value: Reason;
  onChange: (reason: Reason) => void;
}) {
  return (
    <Field label="Reason">
      <select value={value} onChange={(e) => onChange(e.target.value as Reason)}>
        {REASONS.map((reason) => (
          <option key={reason}>{reason}</option>
        ))}
      </select>
    </Field>
  );
}
