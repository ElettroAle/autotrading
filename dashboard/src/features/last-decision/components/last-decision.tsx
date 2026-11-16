import { useId, type ReactNode } from 'react';
import { Link } from 'react-router';

import { DETAIL_VALUE, DETAILS_GRID } from '@/components/ui/details-list';
import { ErrorMessage } from '@/components/ui/error-message';
import { paths } from '@/config/paths';
import { formatInstant } from '@/utils/format-instant';
import { shortenText } from '@/utils/shorten-text';

import { useLastDecision, type Decision } from '../api/get-last-decision';

const NOT_AVAILABLE = 'non disponibile';

const Entry = ({ label, children }: { label: string; children: ReactNode }) => {
  const id = useId();
  return (
    <div className="contents">
      <dt id={id} className="text-slate-600">
        {label}
      </dt>
      <dd aria-labelledby={id} className={`${DETAIL_VALUE} font-medium`}>
        {children}
      </dd>
    </div>
  );
};

// The values are the API's: the panel only shortens the reasoning, the detail of the cycle shows it whole.
const DecisionEntry = ({ decision }: { decision: Decision }) => (
  <section aria-label={decision.asset}>
    <dl className={DETAILS_GRID}>
      <Entry label="Asset">{decision.asset}</Entry>
      <Entry label="Azione">{decision.action}</Entry>
      {decision.direction === null ? null : <Entry label="Direzione">{decision.direction}</Entry>}
      <Entry label="Confidenza">
        {decision.confidence === null ? NOT_AVAILABLE : String(decision.confidence)}
      </Entry>
      <Entry label="Ragionamento">{shortenText(decision.reasoning)}</Entry>
    </dl>
  </section>
);

const DecisionPanel = ({ children }: { children: ReactNode }) => {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="mt-4 rounded border border-slate-200 bg-white p-4"
    >
      <h3 id={titleId} className="text-lg font-semibold">
        Ultima decisione
      </h3>
      <p className="mb-2 text-sm text-slate-600">indipendente dal periodo</p>
      {children}
    </section>
  );
};

/**
 * The last decision of the agent in the flow, whatever the period chosen on the page, with the link to the detail of
 * its cycle (R6.5.4).
 */
export const LastDecision = ({ flowId }: { flowId: string }) => {
  const lastDecision = useLastDecision(flowId);
  if (lastDecision.isPending) {
    return null;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (lastDecision.data === undefined) {
    return (
      <DecisionPanel>
        <ErrorMessage error={lastDecision.error} />
      </DecisionPanel>
    );
  }
  if (lastDecision.data === null) {
    return (
      <DecisionPanel>
        <p>nessuna decisione ancora</p>
      </DecisionPanel>
    );
  }
  const { planned_at: plannedAt, decisions } = lastDecision.data;
  return (
    <DecisionPanel>
      <p className="mb-2">
        <Link to={paths.cycle.getHref(flowId, plannedAt)} className="text-blue-800 hover:underline">
          {formatInstant(plannedAt)}
        </Link>
      </p>
      <div className="space-y-3">
        {decisions.map((decision) => (
          <DecisionEntry key={decision.asset} decision={decision} />
        ))}
      </div>
    </DecisionPanel>
  );
};
