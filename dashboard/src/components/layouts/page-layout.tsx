import type { ReactNode } from 'react';

import { EnvironmentBadge } from '@/components/ui/environment-badge';
import { useRuntimeConfig } from '@/config/runtime-config';

export const PageLayout = ({ title, children }: { title: string; children: ReactNode }) => {
  const { environment } = useRuntimeConfig();
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <span className="font-semibold">AutoTrading</span>
        <EnvironmentBadge environment={environment} />
      </header>
      <main className="mx-auto max-w-4xl p-6">
        <h1 className="mb-4 text-2xl font-semibold">{title}</h1>
        {children}
      </main>
    </div>
  );
};
