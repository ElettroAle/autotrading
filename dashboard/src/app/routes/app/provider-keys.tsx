import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { ProviderKeysList } from '@/features/provider-keys/components/provider-keys-list';
import { RegisterProviderKeyForm } from '@/features/provider-keys/components/register-provider-key-form';
import { SourceCredentialsSection } from '@/features/source-credentials/components/source-credentials-section';

const SECTION_HEADING_ID = 'provider-keys-heading';
const SOURCES_HEADING_ID = 'source-credentials-heading';

// Under the keys of the AI providers, the credentials of the adapters of the sources (ADR
// sezione-fonti-nella-pagina-chiavi).
export const ProviderKeysRoute = () => (
  <DashboardLayout title="Chiavi">
    <section aria-labelledby={SECTION_HEADING_ID} className="space-y-4">
      <h2 id={SECTION_HEADING_ID} className="text-lg font-semibold">
        Chiavi dei fornitori IA
      </h2>
      <ProviderKeysList />
      <RegisterProviderKeyForm />
    </section>
    <section aria-labelledby={SOURCES_HEADING_ID} className="mt-8 space-y-4">
      <h2 id={SOURCES_HEADING_ID} className="text-lg font-semibold">
        Fonti
      </h2>
      <SourceCredentialsSection />
    </section>
  </DashboardLayout>
);
