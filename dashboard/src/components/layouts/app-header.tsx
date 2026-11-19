import type { ReactNode } from 'react';
import { Link, useInRouterContext, useLocation } from 'react-router';

import { EnvironmentBadge } from '@/components/ui/environment-badge';
import { paths } from '@/config/paths';
import { useRuntimeConfig } from '@/config/runtime-config';

import { BackButton } from './back-button';
import { NotificationBell } from './notification-bell';
import { UserMenu } from './user-menu';

const PLATFORM_NAME = 'AutoTrading';

type BackProps = {
  /** Where «Indietro» leads from the page the dashboard was opened on: the main page when not given. */
  readonly backTo?: string;
};

type HeaderProps = BackProps & {
  children?: ReactNode;
  /**
   * The bell of the notifications, on the pages of the data of the user only: before the API admits the user the bar
   * reads nothing (ADR campanello-delle-notifiche-nella-dashboard).
   */
  readonly withNotifications?: boolean;
};

/** The way back from a page of the dashboard: the name leads to the main page, «Indietro» to the previous one. */
const Navigation = ({ backTo }: BackProps) => {
  const { pathname } = useLocation();
  return (
    <>
      {pathname === paths.home.path ? null : <BackButton fallback={backTo} />}
      <Link to={paths.home.getHref()} className="min-w-0 truncate font-semibold">
        {PLATFORM_NAME}
      </Link>
    </>
  );
};

/**
 * The bar on top of every page: the name of the platform and the environment of the installation (R0.1.4), with the
 * way back on the pages of the dashboard (ADR 0145), and on the right the area of the signed-in user (ADR
 * area-utente-in-alto-a-destra), with the bell of the notifications beside the name (ADR
 * campanello-delle-notifiche-nella-dashboard). Outside the router, before the dashboard opens, the name links nowhere.
 * On one line at every width (ADR intestazione-su-una-riga).
 */
export const AppHeader = ({ children, backTo, withNotifications = false }: HeaderProps) => {
  const { environment } = useRuntimeConfig();
  const inDashboard = useInRouterContext();
  return (
    // The bar never wraps, or it would grow over the page: where the room ends, the name of the platform gives way
    // (ADR intestazione-su-una-riga).
    // Relative: the panel of the bell opens under the whole bar, aligned to its right side.
    <header className="relative flex flex-nowrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        {children}
        {inDashboard ? (
          <Navigation backTo={backTo} />
        ) : (
          <span className="min-w-0 truncate font-semibold">{PLATFORM_NAME}</span>
        )}
      </div>
      <div className="ml-auto flex shrink-0 items-center gap-2">
        <EnvironmentBadge environment={environment} />
        {withNotifications && inDashboard ? <NotificationBell /> : null}
        <UserMenu />
      </div>
    </header>
  );
};
