import {
  isComplete,
  listIntervalOf,
  usePeriod,
  type ListInterval,
} from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';

import { useFlowCapitalChanges } from '../api/get-capital-changes';

import { CapitalChangesTable } from './capital-changes-table';

type FlowCapitalChangesProps = { readonly flowId: string; readonly page: number };

const ChangesInInterval = ({
  flowId,
  page,
  interval,
}: FlowCapitalChangesProps & { readonly interval: ListInterval }) => (
  <CapitalChangesTable
    reading={useFlowCapitalChanges(flowId, page, interval)}
    interval={interval}
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
    return <p className="text-slate-600">Scegli l&apos;inizio e la fine dell&apos;intervallo.</p>;
  }
  return (
    <ChangesInInterval flowId={flowId} page={page} interval={listIntervalOf(period, new Date())} />
  );
};
