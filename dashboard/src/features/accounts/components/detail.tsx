import type { ReactNode } from 'react';

import { DETAIL_VALUE } from '@/components/ui/details-list';

/** One term and its value in a list of labels and values of an account, the value named by its term. */
export const Detail = ({
  term,
  children,
}: {
  readonly term: string;
  readonly children: ReactNode;
}) => (
  <>
    <dt className="font-medium text-slate-600">{term}</dt>
    <dd aria-label={term} className={DETAIL_VALUE}>
      {children}
    </dd>
  </>
);
