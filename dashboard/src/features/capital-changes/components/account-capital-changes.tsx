import {
  isComplete,
  listDaysOf,
  usePeriod,
  type ListDays,
} from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';

import { useAccountCapitalChanges } from '../api/get-capital-changes';

import { CapitalChangesTable } from './capital-changes-table';

type AccountCapitalChangesProps = { readonly accountId: string; readonly page: number };

const ChangesInDays = ({
  accountId,
  page,
  days,
}: AccountCapitalChangesProps & { readonly days: ListDays }) => (
  <CapitalChangesTable
    reading={useAccountCapitalChanges(accountId, page, days)}
    days={days}
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
  if (!isComplete(period)) {
    return (
      <p className="text-slate-600">Scegli il primo e l&apos;ultimo giorno dell&apos;intervallo.</p>
    );
  }
  return <ChangesInDays accountId={accountId} page={page} days={listDaysOf(period, new Date())} />;
};
