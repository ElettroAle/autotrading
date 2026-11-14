import { HISTORY_TABS, type HistoryKind } from '../utils/history-search';

type HistoryTabsProps = {
  readonly current: HistoryKind;
  readonly choose: (kind: HistoryKind) => void;
};

/** The three histories of the page: one shows at a time, the others keep their place in the query string. */
export const HistoryTabs = ({ current, choose }: HistoryTabsProps) => (
  <div role="tablist" aria-label="Storici" className="mb-4 flex gap-2 border-b border-slate-200">
    {HISTORY_TABS.map(({ kind, label }) => (
      <button
        key={kind}
        type="button"
        role="tab"
        aria-selected={kind === current}
        onClick={() => choose(kind)}
        className={
          kind === current
            ? 'border-b-2 border-blue-800 px-3 py-2 font-semibold text-blue-800'
            : 'px-3 py-2 text-slate-600 hover:text-slate-900'
        }
      >
        {label}
      </button>
    ))}
  </div>
);
