const FIRST_PAGE = 1;

/**
 * The page a list shows, from the query string, so a page has a link of its own; anything else is the first page.
 * Whether the page exists is for the API to say.
 */
export const pageOf = (value: string | null): number => {
  const page = Number(value);
  return Number.isInteger(page) && page >= FIRST_PAGE ? page : FIRST_PAGE;
};

/** The query string of another page of the same list: the filters stay, the first page leaves no trace. */
export const searchWithPage = (current: URLSearchParams, page: number): string => {
  const next = new URLSearchParams(current);
  next.delete('page');
  if (page !== FIRST_PAGE) {
    next.set('page', String(page));
  }
  const search = next.toString();
  return search === '' ? '' : `?${search}`;
};
