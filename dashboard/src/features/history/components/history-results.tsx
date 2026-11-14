import type { InfiniteData, UseInfiniteQueryResult } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { ApiError } from '@/lib/api-client';

import { LoadMore } from './load-more';

const REJECTED = 400;

type HistoryResultsProps<T> = {
  readonly pages: UseInfiniteQueryResult<InfiniteData<T>>;
  readonly waiting: boolean;
  readonly children: (pages: readonly T[]) => ReactNode;
};

// A search the API refuses says why, as the API says it; any other failure is a read that did not succeed.
const prefixOf = (error: Error): string | undefined =>
  error instanceof ApiError && error.status === REJECTED ? 'Interrogazione rifiutata' : undefined;

/** The pages of a history as they arrive, with the next one on request; a range waits for both its days. */
export const HistoryResults = <T,>({ pages, waiting, children }: HistoryResultsProps<T>) => {
  if (waiting) {
    return (
      <p className="text-slate-600">
        Scegli il giorno iniziale e il giorno finale dell&apos;intervallo.
      </p>
    );
  }
  if (pages.isPending) {
    return <Loading />;
  }
  if (pages.isError) {
    return <ErrorMessage error={pages.error} prefix={prefixOf(pages.error)} />;
  }
  return (
    <>
      {children(pages.data.pages)}
      <LoadMore
        hasMore={pages.hasNextPage}
        loading={pages.isFetchingNextPage}
        load={() => void pages.fetchNextPage()}
      />
    </>
  );
};
