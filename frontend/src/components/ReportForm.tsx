import { useState } from 'react';
import { api } from '../api/client';
import type { Reason } from '../api/types';
import { useAction } from '../hooks';
import { ErrorNote, Field, ReasonSelect } from './basics';

interface Props {
  targetType: 'post' | 'comment' | 'user' | 'message';
  targetId: number;
  messageIds?: number[];
}

/** Report something to the moderators. */
export function ReportForm({ targetType, targetId, messageIds = [] }: Props) {
  const [open, setOpen] = useState(false);
  const [sent, setSent] = useState(false);
  const [reason, setReason] = useState<Reason>('harassment');
  const [note, setNote] = useState('');
  const { run, error, busy } = useAction();
  if (sent) return <p role="status">Thank you. The moderators received your report.</p>;
  if (!open) {
    return (
      <button type="button" className="quiet" onClick={() => setOpen(true)}>
        Report
      </button>
    );
  }
  const body = {
    target_type: targetType,
    target_id: targetId,
    message_ids: messageIds,
    reason,
    note,
  };
  return (
    <form
      className="inline-form"
      onSubmit={(e) => {
        e.preventDefault();
        void run(() => api.post('/reports', body).then(() => setSent(true)));
      }}
    >
      <ReasonSelect value={reason} onChange={setReason} />
      <Field label="Note (optional)">
        <input value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} />
      </Field>
      <button disabled={busy}>Send report</button>
      <button type="button" className="quiet" onClick={() => setOpen(false)}>
        Cancel
      </button>
      <ErrorNote message={error} />
    </form>
  );
}
