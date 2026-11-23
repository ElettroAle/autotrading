import { Link } from 'react-router';

import { Card } from '@/components/ui/card';
import { SECONDARY_COMMAND } from '@/components/ui/commands';
import { paths } from '@/config/paths';

import type { Flow } from '../api/get-flows';
import { listed } from '../utils/listed';

const readinessOf = (missing: readonly string[]): string => {
  if (missing.length === 0) {
    return 'Pronta per essere avviata';
  }
  return `Prima dell'avvio ${missing.length === 1 ? 'manca' : 'mancano'}: ${listed(missing)}`;
};

/**
 * The overview of a draft: what it lacks to start, as the API declares it (ADR mancanze-della-bozza-dichiarate-dall-api),
 * and the way to its configuration, where account, capital and assets are set (ADR
 * assegnazione-della-bozza-nel-form-di-configurazione).
 */
export const DraftReadiness = ({ flow }: { flow: Flow }) => (
  <Card role="note" aria-label="Da configurare" className="mt-4 flex flex-wrap items-center gap-2">
    <p>{readinessOf(flow.missing)}</p>
    <Link to={paths.editFlow.getHref(flow.id)} className={SECONDARY_COMMAND}>
      Configura
    </Link>
  </Card>
);
