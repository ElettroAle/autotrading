import { ViewTabs } from '@/components/ui/view-tabs';

import { HISTORY_TABS, type HistoryKind } from '../utils/history-search';

type HistoryTabsProps = {
  readonly current: HistoryKind;
  readonly choose: (kind: HistoryKind) => void;
};

const TABS = HISTORY_TABS.map(({ kind, label }) => ({ key: kind, name: label }));

/** The three histories of the page: one shows at a time, the others keep their place in the query string. */
export const HistoryTabs = ({ current, choose }: HistoryTabsProps) => (
  <ViewTabs label="Storici" tabs={TABS} current={current} choose={choose} />
);
