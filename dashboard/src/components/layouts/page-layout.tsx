import type { ReactNode } from 'react';

import { AppHeader } from './app-header';

/** A page outside the data of the user: sign-in, refusals, missing pages. */
export const PageLayout = ({ title, children }: { title: string; children: ReactNode }) => (
  <div className="min-h-screen bg-slate-50 text-slate-900">
    <AppHeader />
    <main className="mx-auto max-w-4xl p-4 md:p-6">
      <h1 className="mb-4 text-2xl font-semibold">{title}</h1>
      {children}
    </main>
  </div>
);
