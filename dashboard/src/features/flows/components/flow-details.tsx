import type { Account } from '../api/get-accounts';
import type { Flow } from '../api/get-flows';

const TO_ASSIGN = 'da assegnare';

const accountName = (flow: Flow, accounts: Account[]): string => {
  if (flow.account_id === null) {
    return TO_ASSIGN;
  }
  return accounts.find((account) => account.id === flow.account_id)?.name ?? flow.account_id;
};

/** The configuration in force; a draft shows what it still lacks before it can start (ADR 0125). */
export const FlowDetails = ({ flow, accounts }: { flow: Flow; accounts: Account[] }) => {
  const details: [string, string][] = [
    ['Versione', String(flow.version)],
    ['Modello', flow.model.name],
    ['Fonti', flow.sources.map((source) => `${source.name} (peso ${source.weight})`).join(', ')],
    ['Conto', accountName(flow, accounts)],
    [
      'Capitale allocato',
      flow.allocated_capital === null ? TO_ASSIGN : `${flow.allocated_capital} USDC`,
    ],
    ['Asset', flow.assets.length === 0 ? TO_ASSIGN : flow.assets.join(', ')],
  ];
  return (
    <dl
      aria-label="Configurazione"
      className="mt-3 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1"
    >
      {details.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-slate-600">{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
};
