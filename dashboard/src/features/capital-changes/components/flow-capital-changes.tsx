import {
  isComplete,
  listDaysOf,
  usePeriod,
  type ListDays,
} from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';

import { useFlowCapitalChanges } from '../api/get-capital-changes';

import { CapitalChangesTable } from './capital-changes-table';

type FlowCapitalChangesProps = { readonly flowId: string; readonly page: number };

const ChangesInDays = ({
  flowId,
  page,
  days,
}: FlowCapitalChangesProps & { readonly days: ListDays }) => (
  <CapitalChangesTable
    reading={useFlowCapitalChanges(flowId, page, days)}
    days={days}
    path={paths.flowCapital.getHref(flowId)}
  />
);

/**
 * The changes of the capital of the flow in the period of the page, from the most recent, in the pages of the API: the
 * tab Capitale of the page of the flow (R3.4.2, ADR storico-delle-variazioni-di-capitale).
 */
export const FlowCapitalChanges = ({ flowId, page }: FlowCapitalChangesProps) => {
  const [period] = usePeriod();
  if (!isComplete(period)) {
    return (
      <p className="text-slate-600">Scegli il primo e l&apos;ultimo giorno dell&apos;intervallo.</p>
    );
  }
  return <ChangesInDays flowId={flowId} page={page} days={listDaysOf(period, new Date())} />;
};
