import { PageLayout } from '@/components/layouts/page-layout';
import { CreateFlow } from '@/features/flow-editor/components/create-flow';

export const NewFlowRoute = () => (
  <PageLayout title="Nuovo flusso">
    <CreateFlow />
  </PageLayout>
);
