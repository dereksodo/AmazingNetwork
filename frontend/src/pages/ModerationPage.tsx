import { useState } from 'react';
import { api } from '../api/client';
import type { Appeal, Reason, Report } from '../api/types';
import { ErrorNote, Field, ReasonSelect, UserLink, when } from '../components/basics';
import { useAction, useResource } from '../hooks';
import { useLive } from '../live/LiveProvider';

export function ModerationPage() {
  const queue = useResource<Report[]>('/moderation/queue');
  const appeals = useResource<Appeal[]>('/moderation/appeals');
  const reload = () => {
    void queue.reload();
    void appeals.reload();
  };
  useLive('moderation', reload);
  return (
    <>
      <h1>Moderation</h1>
      <ErrorNote message={queue.error?.message} />
      <h2>Reports</h2>
      {queue.data?.length === 0 && <p>No open reports.</p>}
      {queue.data?.map((report) => (
        <ReportItem key={report.id} report={report} onChange={reload} />
      ))}
      <h2>Appeals</h2>
      {appeals.data?.length === 0 && <p>No open appeals.</p>}
      {appeals.data?.map((appeal) => (
        <AppealItem key={appeal.id} appeal={appeal} onChange={reload} />
      ))}
    </>
  );
}

type ActionName = 'dismiss' | 'hide' | 'remove' | 'notice' | 'mute';

function ReportItem({ report, onChange }: { report: Report; onChange: () => void }) {
  const [action, setAction] = useState<ActionName>('dismiss');
  const [reason, setReason] = useState<Reason>(report.reason);
  const [explanation, setExplanation] = useState('');
  const [hours, setHours] = useState('24');
  const [agreed, setAgreed] = useState('yes');
  const { run, error } = useAction();
  const { suggestion } = report;
  const actions: ActionName[] = ['post', 'comment'].includes(report.target_type)
    ? ['dismiss', 'hide', 'remove', 'notice', 'mute']
    : ['dismiss', 'notice', 'mute'];
  const body = {
    action,
    reason,
    explanation,
    mute_hours: action === 'mute' ? Number(hours) : null,
    ai_agreed: suggestion ? agreed === 'yes' : null,
  };
  return (
    <article className="card">
      <header>
        <strong>{report.reason}</strong> · {report.target_type} by{' '}
        <UserLink user={report.target_user} />{' '}
        <span className="meta">
          {when(report.created_at)} · {report.report_count} report(s)
        </span>
      </header>
      <blockquote className="reported">{report.target_text}</blockquote>
      {report.note && <p>Reporter’s note: {report.note}</p>}
      {report.triage === 'pending' && <p className="tag">AI suggestion pending…</p>}
      {report.triage === 'unscored' && (
        <p>
          <span className="tag">unscored</span> No AI suggestion is available.{' '}
          <button
            type="button"
            className="quiet"
            onClick={() =>
              run(() => api.post(`/moderation/reports/${report.id}/triage`).then(onChange))
            }
          >
            Ask the AI again
          </button>
        </p>
      )}
      {suggestion && (
        <p className="banner">
          <strong>AI suggestion:</strong> {suggestion.severity} severity, {suggestion.category}.{' '}
          {suggestion.rationale} <span className="meta">({suggestion.model})</span>
        </p>
      )}
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          void run(() => api.post(`/moderation/reports/${report.id}/actions`, body).then(onChange));
        }}
      >
        <Field label="Action">
          <select value={action} onChange={(e) => setAction(e.target.value as ActionName)}>
            {actions.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </Field>
        {action === 'mute' && (
          <Field label="For">
            <select value={hours} onChange={(e) => setHours(e.target.value)}>
              <option value="24">24 hours</option>
              <option value="168">7 days</option>
              <option value="720">30 days</option>
            </select>
          </Field>
        )}
        <ReasonSelect value={reason} onChange={setReason} />
        <Field label="Explanation for the user">
          <input required value={explanation} onChange={(e) => setExplanation(e.target.value)} />
        </Field>
        {suggestion && (
          <Field label="AI was right">
            <select value={agreed} onChange={(e) => setAgreed(e.target.value)}>
              <option>yes</option>
              <option>no</option>
            </select>
          </Field>
        )}
        <button>Decide</button>
      </form>
      <ErrorNote message={error} />
    </article>
  );
}

function AppealItem({ appeal, onChange }: { appeal: Appeal; onChange: () => void }) {
  const [reason, setReason] = useState('');
  const { run, error } = useAction();
  const decide = (outcome: 'upheld' | 'overturned') =>
    run(() =>
      api.post(`/moderation/appeals/${appeal.id}/decision`, { outcome, reason }).then(onChange),
    );
  return (
    <article className="card">
      <header>
        <UserLink user={appeal.appellant} /> appeals: {appeal.action.action} ({appeal.action.reason}
        : {appeal.action.explanation})
      </header>
      <blockquote className="reported">{appeal.target_text}</blockquote>
      <blockquote>{appeal.statement}</blockquote>
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          void decide('upheld');
        }}
      >
        <Field label="Reason for your decision">
          <input required value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
        <button>Uphold</button>
        <button type="button" disabled={!reason} onClick={() => decide('overturned')}>
          Overturn
        </button>
      </form>
      <ErrorNote message={error} />
    </article>
  );
}
