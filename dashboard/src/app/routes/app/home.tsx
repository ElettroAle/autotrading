import { Link } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { paths } from '@/config/paths';
import { FlowsList } from '@/features/flows/components/flows-list';

export const HomeRoute = () => (
  <PageLayout title="I tuoi flussi">
    <FlowsList />
    <nav aria-label="Impostazioni" className="mt-6">
      <Link to={paths.notifications.getHref()} className="text-blue-800 hover:underline">
        Notifiche Telegram
      </Link>
    </nav>
  </PageLayout>
);
