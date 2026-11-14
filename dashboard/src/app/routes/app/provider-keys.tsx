import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { ProviderKeysList } from '@/features/provider-keys/components/provider-keys-list';
import { RegisterProviderKeyForm } from '@/features/provider-keys/components/register-provider-key-form';

const SECTION_HEADING_ID = 'provider-keys-heading';

export const ProviderKeysRoute = () => (
  <DashboardLayout title="Chiavi">
    <section aria-labelledby={SECTION_HEADING_ID} className="space-y-4">
      <h2 id={SECTION_HEADING_ID} className="text-lg font-semibold">
        Chiavi dei fornitori IA
      </h2>
      <ProviderKeysList />
      <RegisterProviderKeyForm />
    </section>
  </DashboardLayout>
);
