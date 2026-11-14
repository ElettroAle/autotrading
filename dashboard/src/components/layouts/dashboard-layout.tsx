import { useId, useState, type ReactNode } from 'react';
import { Link } from 'react-router';

import { RefreshBar } from '@/components/ui/refresh-bar';
import { paths } from '@/config/paths';
import { usePageData } from '@/hooks/use-page-data';

import { AppHeader } from './app-header';

const NAVIGATION = [{ name: 'Flussi', to: paths.home.getHref() }] as const;

/**
 * A page of the data of the user: navigation at the side on a wide screen, folded into a menu under 768 pixels, and
 * the data of the page reread on request or by itself (ADR 0119).
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
          className={`${menuOpen ? 'block' : 'hidden'} border-b border-slate-200 bg-white md:block md:min-h-screen md:w-48 md:shrink-0 md:border-r md:border-b-0`}
        >
          <ul className="p-2">
            {NAVIGATION.map((entry) => (
              <li key={entry.to}>
                <Link
                  to={entry.to}
                  className="block rounded px-3 py-2 font-medium text-blue-800 hover:bg-slate-100"
                >
                  {entry.name}
                </Link>
              </li>
            ))}
          </ul>
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
