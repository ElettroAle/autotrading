import type { IPublicClientApplication } from '@azure/msal-browser';
import type { ReactNode } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import {
  isAccessConfigured,
  loadRuntimeConfig,
  RuntimeConfigProvider,
  type RuntimeConfig,
} from '@/config/runtime-config';
import { completeSignIn, createAuthClient } from '@/lib/auth';

import { AppProvider } from './provider';
import { BASE_NAME, routes } from './router';

type Router = ReturnType<typeof createBrowserRouter>;

export const App = ({
  config,
  authClient,
  router,
}: {
  config: RuntimeConfig;
  authClient: IPublicClientApplication;
  router: Router;
}) => (
  <AppProvider config={config} authClient={authClient}>
    <RouterProvider router={router} />
  </AppProvider>
);

const ConfigurationUnavailable = () => (
  <main className="p-6">
    <p role="alert">La configurazione della dashboard non è disponibile: riprova più tardi.</p>
  </main>
);

const AccessNotConfigured = ({ config }: { config: RuntimeConfig }) => (
  <RuntimeConfigProvider config={config}>
    <PageLayout title="Accesso non configurato">
      <p role="alert">L'accesso a questa installazione non è ancora configurato.</p>
    </PageLayout>
  </RuntimeConfigProvider>
);

/**
 * Reads the configuration of the installation, completes a sign-in coming back from the identity provider and
 * opens the page the user was asking for.
 */
export const startApp = async (): Promise<ReactNode> => {
  const config = await loadRuntimeConfig().catch(() => null);
  if (config === null) {
    return <ConfigurationUnavailable />;
  }
  if (!isAccessConfigured(config)) {
    return <AccessNotConfigured config={config} />;
  }
  const authClient = createAuthClient(config, `${window.location.origin}${BASE_NAME}/`);
  const returnTo = await completeSignIn(authClient);
  if (returnTo !== null) {
    window.history.replaceState(null, '', `${BASE_NAME}${returnTo}`);
  }
  const router = createBrowserRouter(routes, { basename: BASE_NAME });
  return <App config={config} authClient={authClient} router={router} />;
};
