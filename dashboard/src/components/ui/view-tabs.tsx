import { useRef, type KeyboardEvent } from 'react';
import { Link, useLocation } from 'react-router';

/** A view with an address of its own. */
export type View = { readonly name: string; readonly to: string };

/** A view of the same page, chosen by its key. */
export type Tab<Key extends string> = { readonly key: Key; readonly name: string };

type PageViewsProps = { readonly label: string; readonly views: readonly View[] };

type SamePageViewsProps<Key extends string> = {
  readonly label: string;
  readonly tabs: readonly Tab<Key>[];
  readonly current: Key;
  readonly choose: (key: Key) => void;
};

// The look of every tab of the dashboard (ADR schede-con-aspetto-e-ruolo-di-schede): the tabs on a light bar of their
// own, one row that scrolls inside itself on a narrow screen, the chosen tab white with dark text and a blue mark, the
// others as commands not chosen. The tabs stay large enough to touch (ADR viste-e-comandi-della-pagina-del-flusso).
const SCROLLER = 'mb-4 w-fit max-w-full overflow-x-auto';
const BAR = 'flex flex-nowrap gap-1 rounded-lg bg-slate-100 p-1';
const TAB =
  'inline-flex min-h-11 shrink-0 items-center whitespace-nowrap rounded-md border-b-2 px-3 font-medium focus-visible:outline-2 focus-visible:outline-blue-700';
const CHOSEN = `${TAB} border-blue-700 bg-white text-slate-900 shadow-sm`;
const NOT_CHOSEN = `${TAB} border-transparent text-slate-600 hover:bg-white/60 hover:text-slate-900`;

const lookOf = (chosen: boolean): string => (chosen ? CHOSEN : NOT_CHOSEN);

const PageViews = ({ label, views }: PageViewsProps) => {
  const { pathname } = useLocation();
  return (
    <nav aria-label={label} className={SCROLLER}>
      <ul className={BAR}>
        {views.map((view) => {
          const current = view.to === pathname;
          return (
            <li key={view.to} className="flex">
              <Link
                to={view.to}
                aria-current={current ? 'page' : undefined}
                className={lookOf(current)}
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

/** The tab the key moves to from the tab at position, round the ends; undefined for a key the tabs leave to the page. */
const tabAfter = <Item,>(
  key: string,
  items: readonly Item[],
  position: number,
): Item | undefined => {
  const last = items.length - 1;
  const moves: Record<string, number> = {
    ArrowRight: position === last ? 0 : position + 1,
    ArrowLeft: position === 0 ? last : position - 1,
    Home: 0,
    End: last,
  };
  const next = moves[key];
  return next === undefined ? undefined : items[next];
};

const SamePageViews = <Key extends string>({
  label,
  tabs,
  current,
  choose,
}: SamePageViewsProps<Key>) => {
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  // The arrows move among the tabs and choose the one reached, as a group of tabs does (WAI-ARIA tabs pattern).
  const move = (event: KeyboardEvent<HTMLButtonElement>) => {
    const position = tabs.findIndex((tab) => tab.key === current);
    const reached = tabAfter(event.key, tabs, position);
    if (reached === undefined) {
      return;
    }
    event.preventDefault();
    buttons.current[tabs.indexOf(reached)]?.focus();
    choose(reached.key);
  };
  return (
    <div className={SCROLLER}>
      <div role="tablist" aria-label={label} className={BAR}>
        {tabs.map((tab, position) => {
          const selected = tab.key === current;
          return (
            <button
              key={tab.key}
              ref={(button) => {
                buttons.current[position] = button;
              }}
              type="button"
              role="tab"
              aria-selected={selected}
              tabIndex={selected ? 0 : -1}
              onClick={() => choose(tab.key)}
              onKeyDown={move}
              className={lookOf(selected)}
            >
              {tab.name}
            </button>
          );
        })}
      </div>
    </div>
  );
};

/**
 * The views of one area as tabs, the same look on every page (ADR schede-con-aspetto-e-ruolo-di-schede): views with an
 * address of their own are links, the view of the current page marked (ADR 0161); views of the same page are tabs of a
 * group of tabs, chosen also with the arrows.
 */
export const ViewTabs = <Key extends string>(props: PageViewsProps | SamePageViewsProps<Key>) =>
  'views' in props ? <PageViews {...props} /> : <SamePageViews {...props} />;
