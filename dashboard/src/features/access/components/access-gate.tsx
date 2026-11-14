import type { ReactNode } from 'react';

import { PageLayout } from '@/components/layouts/page-layout';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { ApiError } from '@/lib/api-client';

import { useIdentity } from '../api/get-identity';

const FORBIDDEN = 403;

/**
 * Shows the pages only once the API admits the user: the authorization stays on the API, the dashboard only tells
 * its answer (ADR 0118), and no data appears before it.
 */
export const AccessGate = ({ children }: { children: ReactNode }) => {
  const identity = useIdentity();
  if (identity.isPending) {
    return (
      <PageLayout title="AutoTrading">
        <Loading />
      </PageLayout>
    );
  }
  if (identity.error instanceof ApiError && identity.error.status === FORBIDDEN) {
    return (
      <PageLayout title="Accesso non consentito">
        <p role="alert">Accesso non consentito: manca il ruolo Utente</p>
      </PageLayout>
    );
  }
  if (identity.isError) {
    return (
      <PageLayout title="AutoTrading">
        <ErrorMessage error={identity.error} />
      </PageLayout>
    );
  }
  return children;
};
