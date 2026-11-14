import { Link, useLocation } from 'react-router';

export type View = { readonly name: string; readonly to: string };

/** The views of one area, each a link with its own address, the view of the current page marked (ADR 0156). */
export const ViewTabs = ({ label, views }: { label: string; views: readonly View[] }) => {
  const { pathname } = useLocation();
  return (
    <nav aria-label={label} className="mb-4 border-b border-slate-200">
      <ul className="flex gap-1">
        {views.map((view) => {
          const current = view.to === pathname;
          return (
            <li key={view.to}>
              <Link
                to={view.to}
                aria-current={current ? 'page' : undefined}
                className={`-mb-px inline-flex min-h-11 items-center border-b-2 px-3 font-medium ${
                  current
                    ? 'border-blue-700 text-blue-800'
                    : 'border-transparent text-slate-600 hover:text-slate-900'
                }`}
              >
                {view.name}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
};
