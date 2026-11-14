import { ViewTabs } from '@/components/ui/view-tabs';
import { paths } from '@/config/paths';

const FLOW_VIEWS = [
  { name: 'Elenco', to: paths.home.getHref() },
  { name: 'Classifica', to: paths.ranking.getHref() },
] as const;

/** The views of the flows, the list and the ranking, each with its own address (ADR 0156). */
export const FlowViewTabs = () => <ViewTabs label="Viste dei flussi" views={FLOW_VIEWS} />;
