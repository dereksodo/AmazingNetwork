import type { Post } from '../api/types';
import { Field } from './basics';

export interface EventForm {
  starts_at: string;
  ends_at: string;
  location: string;
  capacity: string;
  rsvp_deadline: string;
}

export const emptyEvent: EventForm = {
  starts_at: '',
  ends_at: '',
  location: '',
  capacity: '30',
  rsvp_deadline: '',
};

/** Value for a datetime-local input, in the browser's time zone. */
const local = (iso: string) => {
  const date = new Date(iso);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};

export const fromEvent = (event: NonNullable<Post['event']>): EventForm => ({
  starts_at: local(event.starts_at),
  ends_at: local(event.ends_at),
  location: event.location,
  capacity: String(event.capacity),
  rsvp_deadline: local(event.rsvp_deadline),
});

export const toEvent = (form: EventForm) => ({
  starts_at: new Date(form.starts_at).toISOString(),
  ends_at: new Date(form.ends_at).toISOString(),
  location: form.location,
  capacity: Number(form.capacity),
  rsvp_deadline: new Date(form.rsvp_deadline).toISOString(),
});

const FIELDS: [keyof EventForm, string, string][] = [
  ['starts_at', 'Starts', 'datetime-local'],
  ['ends_at', 'Ends', 'datetime-local'],
  ['location', 'Location', 'text'],
  ['capacity', 'Capacity', 'number'],
  ['rsvp_deadline', 'RSVP deadline', 'datetime-local'],
];

export function EventFields({
  value,
  onChange,
}: {
  value: EventForm;
  onChange: (form: EventForm) => void;
}) {
  return (
    <div className="row">
      {FIELDS.map(([name, label, type]) => (
        <Field key={name} label={label}>
          <input
            required
            type={type}
            min={type === 'number' ? 1 : undefined}
            value={value[name]}
            onChange={(e) => onChange({ ...value, [name]: e.target.value })}
          />
        </Field>
      ))}
    </div>
  );
}
