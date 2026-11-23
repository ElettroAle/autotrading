import {
  isComplete,
  useListInterval,
  usePeriod,
  type ListInterval,
} from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';

import { useAccountCapitalChanges } from '../api/get-capital-changes';

import { CapitalChangesTable } from './capital-changes-table';

type AccountCapitalChangesProps = { readonly accountId: string; readonly page: number };

const ChangesInInterval = ({
  accountId,
  page,
  interval,
}: AccountCapitalChangesProps & { readonly interval: ListInterval }) => (
  <CapitalChangesTable
    reading={useAccountCapitalChanges(accountId, page, interval)}
    interval={interval}
    path={paths.accountCapital.getHref(accountId)}
    withFlow
  />
);

/**
 * The changes of the capital of every flow of the account and the deposits and withdrawals of its exchange in the
 * period of the page, from the most recent, in the pages of the API (R3.4.2, ADR storico-delle-variazioni-di-capitale).
 */
export const AccountCapitalChanges = ({ accountId, page }: AccountCapitalChangesProps) => {
  const [period] = usePeriod();
  const interval = useListInterval(period);
  if (!isComplete(period)) {
    return <p className="text-slate-600">Scegli l&apos;inizio e la fine dell&apos;intervallo.</p>;
  }
  return <ChangesInInterval accountId={accountId} page={page} interval={interval} />;
};
