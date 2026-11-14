import { useId, type ReactNode } from 'react';

import { PeriodSelector } from '@/components/ui/period-selector/period-selector';

import type { AccountOption, FlowOption } from '../api/get-history-options';
import type { HistorySearch } from '../utils/history-search';

const FIELD = 'rounded border border-slate-300 bg-white px-2 py-1 disabled:bg-slate-100';
const EVERY = '';

type Choice = { readonly value: string; readonly label: string };

type FilterProps = {
  readonly label: string;
  readonly value: string;
  readonly every: string;
  readonly choices: readonly Choice[];
  readonly choose: (value: string) => void;
  readonly disabled?: boolean;
};

const Filter = ({ label, value, every, choices, choose, disabled = false }: FilterProps) => {
  const id = useId();
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        className={FIELD}
        value={value}
        disabled={disabled}
        onChange={(event) => choose(event.target.value)}
      >
        <option value={EVERY}>{every}</option>
        {choices.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    </>
  );
};

const Row = ({ children }: { children: ReactNode }) => (
  <div className="flex flex-wrap items-center gap-3">{children}</div>
);

// The versions of a flow go from 1 to the one in force; without a flow a version names nothing (ADR 0139).
const versionsOf = (flow: FlowOption | undefined): Choice[] =>
  Array.from({ length: flow?.version ?? 0 }, (_, index) => ({
    value: String(index + 1),
    label: `Versione ${index + 1}`,
  }));

const assetsOf = (flows: readonly FlowOption[]): Choice[] =>
  [...new Set(flows.flatMap((flow) => flow.assets))]
    .sort()
    .map((asset) => ({ value: asset, label: asset }));

type HistoryFiltersProps = {
  readonly search: HistorySearch;
  readonly change: (values: Partial<HistorySearch>) => void;
  readonly flows: readonly FlowOption[];
  readonly accounts: readonly AccountOption[];
};

/** The filters of the histories, in any combination: each choice is a new search of the API. */
export const HistoryFilters = ({ search, change, flows, accounts }: HistoryFiltersProps) => {
  const flow = flows.find((candidate) => candidate.id === search.flow);
  return (
    <fieldset className="mb-4 space-y-2 rounded border border-slate-200 bg-white p-3">
      <legend className="px-1 font-semibold">Filtri</legend>
      <Row>
        <Filter
          label="Flusso"
          value={search.flow}
          every="Tutti i flussi"
          choices={flows.map(({ id, name }) => ({ value: id, label: name }))}
          choose={(value) => change({ flow: value })}
        />
        <Filter
          label="Versione"
          value={search.version}
          every="Tutte le versioni"
          choices={versionsOf(flow)}
          choose={(value) => change({ version: value })}
          disabled={flow === undefined}
        />
        <Filter
          label="Conto"
          value={search.account}
          every="Tutti i conti"
          choices={accounts.map(({ id, name }) => ({ value: id, label: name }))}
          choose={(value) => change({ account: value })}
        />
        <Filter
          label="Asset"
          value={search.asset}
          every="Tutti gli asset"
          choices={assetsOf(flows)}
          choose={(value) => change({ asset: value })}
        />
      </Row>
      <PeriodSelector />
    </fieldset>
  );
};
