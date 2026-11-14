import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { ProviderKeysList } from '@/features/provider-keys/components/provider-keys-list';
import { RegisterProviderKeyForm } from '@/features/provider-keys/components/register-provider-key-form';

export const ProviderKeysRoute = () => (
  <DashboardLayout title="Chiavi dei fornitori IA">
    <div className="space-y-4">
      <ProviderKeysList />
      <RegisterProviderKeyForm />
    </div>
  </DashboardLayout>
);
