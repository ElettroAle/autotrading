import { formatInstant, formatTimeOfDay } from '@/utils/format-instant';

import type { CycleOutcome } from '../api/get-flow-overviews';

const ICON_BY_OUTCOME: Readonly<Record<string, { icon: string; style: string }>> = {
  concluso: { icon: '✓', style: 'bg-green-100 text-green-800' },
  fallito: { icon: '✗', style: 'bg-red-100 text-red-800' },
};
const OTHER_OUTCOME = { icon: '–', style: 'bg-slate-100 text-slate-700' };

/** The outcome of the last cycles of a flow from the most recent, as icons with a text for every reader (R2.2.2). */
export const RecentOutcomes = ({ outcomes }: { outcomes: CycleOutcome[] }) => {
  if (outcomes.length === 0) {
    return <p className="text-sm text-slate-600">Nessun ciclo registrato.</p>;
  }
  return (
    <ol aria-label="Esito degli ultimi cicli" className="flex flex-wrap gap-1">
      {outcomes.map((cycle) => {
        const { icon, style } = ICON_BY_OUTCOME[cycle.outcome] ?? OTHER_OUTCOME;
        return (
          <li
            key={cycle.planned_at}
            title={`${cycle.outcome}, ${formatInstant(cycle.planned_at)}`}
            className={`flex h-6 w-6 items-center justify-center rounded text-sm font-bold ${style}`}
          >
            <span aria-hidden="true">{icon}</span>
            <span className="sr-only">{`${cycle.outcome}, ${formatTimeOfDay(cycle.planned_at)}`}</span>
          </li>
        );
      })}
    </ol>
  );
};
