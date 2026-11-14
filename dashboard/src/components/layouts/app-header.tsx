import type { ReactNode } from 'react';

import { EnvironmentBadge } from '@/components/ui/environment-badge';
import { useRuntimeConfig } from '@/config/runtime-config';

/** The bar on top of every page: the name of the platform and the environment of the installation (R0.1.4). */
export const AppHeader = ({ children }: { children?: ReactNode }) => {
  const { environment } = useRuntimeConfig();
  return (
    <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 md:px-6">
      <div className="flex items-center gap-3">
        {children}
        <span className="font-semibold">AutoTrading</span>
      </div>
      <EnvironmentBadge environment={environment} />
    </header>
  );
};
