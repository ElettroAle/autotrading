import { Link } from 'react-router';

import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { paths } from '@/config/paths';

import type { Flow } from '../api/get-flows';

// What a draft lacks to start, in the order and with the words the refusal of the start uses (ADR 0124).
const missingOf = (flow: Flow): string[] =>
  [
    flow.account_id === null ? 'conto' : '',
    flow.allocated_capital === null ? 'capitale allocato' : '',
    flow.assets.length === 0 ? 'asset' : '',
  ].filter((part) => part !== '');

const listed = (parts: string[]): string => {
  const last = parts.at(-1) ?? '';
  return parts.length === 1 ? last : `${parts.slice(0, -1).join(', ')} e ${last}`;
};

const readinessOf = (missing: string[]): string => {
  if (missing.length === 0) {
    return 'Pronta per essere avviata';
  }
  return `Prima dell'avvio ${missing.length === 1 ? 'manca' : 'mancano'}: ${listed(missing)}`;
};

/**
 * The overview of a draft: what it lacks to start and the way to its configuration, where account, capital and assets
 * are set (ADR assegnazione-della-bozza-nel-form-di-configurazione).
 */
export const DraftReadiness = ({ flow }: { flow: Flow }) => (
  <div
    role="note"
    aria-label="Da configurare"
    className="mt-4 flex flex-wrap items-center gap-2 rounded border border-slate-200 p-3"
  >
    <p>{readinessOf(missingOf(flow))}</p>
    <Link to={paths.editFlow.getHref(flow.id)} className={SECONDARY_COMMAND}>
      Configura
    </Link>
  </div>
);
