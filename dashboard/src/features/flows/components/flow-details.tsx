import { DETAIL_VALUE, DETAILS_GRID } from '@/components/ui/details-list';

import type { Account } from '../api/get-accounts';
import type { Flow } from '../api/get-flows';

const TO_ASSIGN = 'da assegnare';

const accountName = (flow: Flow, accounts: Account[]): string => {
  if (flow.account_id === null) {
    return TO_ASSIGN;
  }
  return accounts.find((account) => account.id === flow.account_id)?.name ?? flow.account_id;
};

// Every adapter chosen of every source, «fonte · adapter (peso N)» (R4.1.1).
const sourcesText = (flow: Flow): string =>
  flow.sources
    .flatMap((source) =>
      source.adapters.map((adapter) => `${source.name} · ${adapter.name} (peso ${adapter.weight})`),
    )
    .join(', ');

/** The configuration in force; a draft shows what it still lacks before it can start (ADR 0125). */
export const FlowDetails = ({ flow, accounts }: { flow: Flow; accounts: Account[] }) => {
  const details: [string, string][] = [
    ['Versione', String(flow.version)],
    ['Modello', flow.model.name],
    ['Fonti', sourcesText(flow)],
    ['Conto', accountName(flow, accounts)],
    [
      'Capitale allocato',
      flow.allocated_capital === null ? TO_ASSIGN : `${flow.allocated_capital} USDC`,
    ],
    ['Asset', flow.assets.length === 0 ? TO_ASSIGN : flow.assets.join(', ')],
  ];
  return (
    <dl aria-label="Configurazione" className={`mt-3 ${DETAILS_GRID}`}>
      {details.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-slate-600">{label}</dt>
          <dd className={DETAIL_VALUE}>{value}</dd>
        </div>
      ))}
    </dl>
  );
};
