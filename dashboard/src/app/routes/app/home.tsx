import { PageLayout } from '@/components/layouts/page-layout';
import { FlowsList } from '@/features/flows/components/flows-list';

export const HomeRoute = () => (
  <PageLayout title="I tuoi flussi">
    <FlowsList />
  </PageLayout>
);
