import { Link } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { paths } from '@/config/paths';
import { FlowsList } from '@/features/flows/components/flows-list';
import { ImportStrategyForm } from '@/features/flows/components/import-strategy-form';

export const HomeRoute = () => (
  <PageLayout title="I tuoi flussi">
    <nav aria-label="Pagine" className="mb-4">
      <Link to={paths.accounts.getHref()} className="text-blue-800 hover:underline">
        I tuoi conti
      </Link>
    </nav>
    <Link
      to={paths.newFlow.getHref()}
      className="mb-4 inline-block rounded bg-blue-700 px-3 py-1.5 text-white"
    >
      Nuovo flusso
    </Link>
    <FlowsList />
    <ImportStrategyForm />
    <nav aria-label="Consultazione" className="mt-6">
      <Link to={paths.history.getHref()} className="text-blue-800 hover:underline">
        Storico
      </Link>
    </nav>
    <nav aria-label="Confronto" className="mt-6">
      <Link to={paths.ranking.getHref()} className="text-blue-800 hover:underline">
        Classifica dei flussi
      </Link>
    </nav>
    <nav aria-label="Impostazioni" className="mt-6 flex gap-4">
      <Link to={paths.providerKeys.getHref()} className="text-blue-800 hover:underline">
        Chiavi dei fornitori IA
      </Link>
      <Link to={paths.notifications.getHref()} className="text-blue-800 hover:underline">
        Notifiche Telegram
      </Link>
    </nav>
  </PageLayout>
);
