import { Link } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { paths } from '@/config/paths';
import { FlowsList } from '@/features/flows/components/flows-list';

export const HomeRoute = () => (
  <PageLayout title="I tuoi flussi">
    <nav aria-label="Pagine" className="mb-4">
      <Link to={paths.accounts.getHref()} className="text-blue-800 hover:underline">
        I tuoi conti
      </Link>
    </nav>
    <FlowsList />
    <nav aria-label="Consultazione" className="mt-6">
      <Link to={paths.history.getHref()} className="text-blue-800 hover:underline">
        Storico
      </Link>
    </nav>
    <nav aria-label="Impostazioni" className="mt-6">
      <Link to={paths.notifications.getHref()} className="text-blue-800 hover:underline">
        Notifiche Telegram
      </Link>
    </nav>
  </PageLayout>
);
