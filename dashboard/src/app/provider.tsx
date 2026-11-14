import type { IPublicClientApplication } from '@azure/msal-browser';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';

import { RuntimeConfigProvider, type RuntimeConfig } from '@/config/runtime-config';
import { AuthProvider } from '@/lib/auth';
import { queryConfig } from '@/lib/react-query';

type AppProviderProps = {
  config: RuntimeConfig;
  authClient: IPublicClientApplication;
  children: ReactNode;
};

export const AppProvider = ({ config, authClient, children }: AppProviderProps) => {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: queryConfig }));
  return (
    <RuntimeConfigProvider config={config}>
      <AuthProvider client={authClient} scope={config.scope}>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </AuthProvider>
    </RuntimeConfigProvider>
  );
};
