import type { ReactNode } from 'react';
import { Link, useInRouterContext, useLocation } from 'react-router';

import { EnvironmentBadge } from '@/components/ui/environment-badge';
import { paths } from '@/config/paths';
import { useRuntimeConfig } from '@/config/runtime-config';

import { BackButton } from './back-button';
import { UserMenu } from './user-menu';

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
 * way back on the pages of the dashboard (ADR 0145), and on the right the area of the signed-in user (ADR
 * area-utente-in-alto-a-destra). Outside the router, before the dashboard opens, the name links nowhere.
 */
export const AppHeader = ({ children }: { children?: ReactNode }) => {
  const { environment } = useRuntimeConfig();
  const inDashboard = useInRouterContext();
  return (
    // On a narrow phone the area of the user goes on a line of its own rather than pushing the page wider.
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 md:px-6">
      <div className="flex items-center gap-3">
        {children}
        {inDashboard ? <Navigation /> : <span className="font-semibold">{PLATFORM_NAME}</span>}
      </div>
      <div className="ml-auto flex min-w-0 items-center gap-2">
        <EnvironmentBadge environment={environment} />
        <UserMenu />
      </div>
    </header>
  );
};
