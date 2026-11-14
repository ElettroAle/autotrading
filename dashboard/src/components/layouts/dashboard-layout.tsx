import { useId, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'react-router';

import { RefreshBar } from '@/components/ui/refresh-bar';
import { paths } from '@/config/paths';
import { usePageData } from '@/hooks/use-page-data';

import { AppHeader } from './app-header';

type NavigationEntry = {
  readonly name: string;
  readonly to: string;
  /** The beginnings of the paths of the area of the entry: its sub-pages light it up too. */
  readonly area: readonly string[];
};

type NavigationGroup = { readonly heading?: string; readonly entries: readonly NavigationEntry[] };

// The pages of a flow have no path of their own to start from: they all live under /flows.
const FLOW_PAGES = '/flows';

const NAVIGATION: readonly NavigationGroup[] = [
  {
    entries: [
      {
        name: 'Flussi',
        to: paths.home.getHref(),
        area: [paths.home.path, FLOW_PAGES, paths.ranking.path, paths.comparison.path],
      },
      { name: 'Conti', to: paths.accounts.getHref(), area: [paths.accounts.path] },
      { name: 'Storico', to: paths.history.getHref(), area: [paths.history.path] },
    ],
  },
  {
    heading: 'Impostazioni',
    entries: [
      { name: 'Chiavi', to: paths.providerKeys.getHref(), area: [paths.providerKeys.path] },
      { name: 'Notifiche', to: paths.notifications.getHref(), area: [paths.notifications.path] },
    ],
  },
];

// The main page is the beginning of every path: it belongs to its area only as itself.
const isWithin = (pathname: string, start: string): boolean =>
  pathname === start || (start !== paths.home.path && pathname.startsWith(`${start}/`));

const isCurrentArea = (entry: NavigationEntry, pathname: string): boolean =>
  entry.area.some((start) => isWithin(pathname, start));

const NavigationLinks = ({
  entries,
  labelledBy,
}: {
  entries: readonly NavigationEntry[];
  labelledBy?: string;
}) => {
  const { pathname } = useLocation();
  return (
    <ul aria-labelledby={labelledBy}>
      {entries.map((entry) => {
        const current = isCurrentArea(entry, pathname);
        return (
          <li key={entry.to}>
            <Link
              to={entry.to}
              aria-current={current ? 'page' : undefined}
              className={`block rounded px-3 py-2 font-medium ${
                current ? 'bg-blue-100 text-blue-900' : 'text-blue-800 hover:bg-slate-100'
              }`}
            >
              {entry.name}
            </Link>
          </li>
        );
      })}
    </ul>
  );
};

const NavigationGroupLinks = ({ group }: { group: NavigationGroup }) => {
  const headingId = useId();
  if (group.heading === undefined) {
    return <NavigationLinks entries={group.entries} />;
  }
  return (
    <div className="mt-4">
      <p
        id={headingId}
        className="px-3 pb-1 text-xs font-semibold tracking-wide text-slate-500 uppercase"
      >
        {group.heading}
      </p>
      <NavigationLinks entries={group.entries} labelledBy={headingId} />
    </div>
  );
};

/**
 * A page of the data of the user: navigation at the side on a wide screen, folded into a menu under 768 pixels, and
 * the data of the page reread on request or by itself (ADR 0119). The menu gathers the areas in groups and marks the
 * area of the page, its sub-pages included (ADR 0158).
 */
export const DashboardLayout = ({ title, children }: { title: string; children: ReactNode }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const navigationId = useId();
  const pageData = usePageData();
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <AppHeader>
        <button
          type="button"
          aria-expanded={menuOpen}
          aria-controls={navigationId}
          onClick={() => setMenuOpen((open) => !open)}
          className="rounded border border-slate-300 px-2 py-1 text-sm md:hidden"
        >
          Menu
        </button>
      </AppHeader>
      <div className="md:flex">
        <nav
          id={navigationId}
          aria-label="Navigazione"
          className={`${menuOpen ? 'block' : 'hidden'} border-b border-slate-200 bg-white p-2 md:block md:min-h-screen md:w-48 md:shrink-0 md:border-r md:border-b-0`}
        >
          {NAVIGATION.map((group) => (
            <NavigationGroupLinks key={group.heading ?? ''} group={group} />
          ))}
        </nav>
        <main className="mx-auto w-full max-w-4xl min-w-0 p-4 md:p-6">
          <h1 className="mb-4 text-2xl font-semibold">{title}</h1>
          <RefreshBar pageData={pageData} />
          {children}
        </main>
      </div>
    </div>
  );
};
