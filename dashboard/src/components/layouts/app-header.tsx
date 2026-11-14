import type { ReactNode } from 'react';
import { Link, useInRouterContext, useLocation } from 'react-router';

import { EnvironmentBadge } from '@/components/ui/environment-badge';
import { paths } from '@/config/paths';
import { useRuntimeConfig } from '@/config/runtime-config';

import { BackButton } from './back-button';

const PLATFORM_NAME = 'AutoTrading';

/** The way back from a page of the dashboard: the name leads to the main page, «Indietro» to the previous one. */
const Navigation = () => {
  const { pathname } = useLocation();
  return (
    <>
      {pathname === paths.home.path ? null : <BackButton />}
      <Link to={paths.home.getHref()} className="font-semibold">
        {PLATFORM_NAME}
      </Link>
    </>
  );
};

/**
 * The bar on top of every page: the name of the platform and the environment of the installation (R0.1.4), with the
 * way back on the pages of the dashboard (ADR 0145). Outside the router, before the dashboard opens, the name links
 * nowhere.
 */
export const AppHeader = ({ children }: { children?: ReactNode }) => {
  const { environment } = useRuntimeConfig();
  const inDashboard = useInRouterContext();
  return (
    <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 md:px-6">
      <div className="flex items-center gap-3">
        {children}
        {inDashboard ? <Navigation /> : <span className="font-semibold">{PLATFORM_NAME}</span>}
      </div>
      <EnvironmentBadge environment={environment} />
    </header>
  );
};
