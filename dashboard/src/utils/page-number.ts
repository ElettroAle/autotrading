const FIRST_PAGE = 1;

/**
 * The page a list shows, from the query string, so a page has a link of its own; anything else is the first page.
 * Whether the page exists is for the API to say.
 */
export const pageOf = (value: string | null): number => {
  const page = Number(value);
  return Number.isInteger(page) && page >= FIRST_PAGE ? page : FIRST_PAGE;
};
