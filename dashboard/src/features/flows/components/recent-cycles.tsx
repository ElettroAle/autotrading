import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { formatInstant } from '@/utils/format-instant';

import { useRecentCycles } from '../api/get-recent-cycles';

export const RecentCycles = ({ flowId }: { flowId: string }) => {
  const cycles = useRecentCycles(flowId);
  if (cycles.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the cycles already read on the page: the warning is the page's (ADR 0119).
  if (cycles.data === undefined) {
    return <ErrorMessage error={cycles.error} />;
  }
  return (
    <section aria-labelledby="recent-cycles" className="mt-4">
      <h3 id="recent-cycles" className="mb-2 text-lg font-semibold">
        Cicli recenti
      </h3>
      {cycles.data.length === 0 ? (
        <p>Nessun ciclo ancora eseguito.</p>
      ) : (
        <ul
          aria-label="Cicli recenti"
          className="divide-y divide-slate-200 rounded border border-slate-200 bg-white"
        >
          {cycles.data.map((cycle) => (
            <li
              key={cycle.planned_at}
              className="flex flex-wrap items-center justify-between gap-2 px-4 py-2"
            >
              <time dateTime={cycle.planned_at}>{formatInstant(cycle.planned_at)}</time>
              <span className="text-sm text-slate-600">{cycle.outcome}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};
