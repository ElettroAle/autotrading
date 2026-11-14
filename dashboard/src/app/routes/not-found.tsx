import { Link } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { paths } from '@/config/paths';

export const NotFoundRoute = () => (
  <PageLayout title="Pagina non trovata">
    <Link to={paths.home.getHref()} className="text-blue-800 hover:underline">
      Torna ai tuoi flussi
    </Link>
  </PageLayout>
);
