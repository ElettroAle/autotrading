import { usePeriodSearch } from '@/components/ui/period-selector/use-period';
import { ViewTabs } from '@/components/ui/view-tabs';
import { paths } from '@/config/paths';

/**
 * The tabs of the page of the flow, each with an address of its own and the period of the page, which holds for all of
 * them (R6.4.3, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune).
 */
export const FlowTabs = ({ flowId }: { flowId: string }) => {
  const periodSearch = usePeriodSearch();
  const views = [
    { name: 'Panoramica', to: `${paths.flow.getHref(flowId)}${periodSearch}` },
    { name: 'Posizioni chiuse', to: `${paths.flowClosedPositions.getHref(flowId)}${periodSearch}` },
    { name: 'Cicli', to: `${paths.flowCycles.getHref(flowId)}${periodSearch}` },
    { name: 'Capitale', to: `${paths.flowCapital.getHref(flowId)}${periodSearch}` },
  ];
  return <ViewTabs label="Dati del flusso" views={views} />;
};
