import { Link } from 'react-router';

type PaginationProps = {
  readonly page: number;
  readonly hasNext: boolean;
  readonly hrefOf: (page: number) => string;
};

/** The pages the API divides a list into: the API alone says whether a next page exists. */
export const Pagination = ({ page, hasNext, hrefOf }: PaginationProps) => (
  <nav aria-label="Pagine" className="mt-4 flex items-center justify-between text-sm">
    {page > 1 ? (
      <Link to={hrefOf(page - 1)} className="text-blue-800 hover:underline">
        Pagina precedente
      </Link>
    ) : (
      <span />
    )}
    <span className="text-slate-600">Pagina {page}</span>
    {hasNext ? (
      <Link to={hrefOf(page + 1)} className="text-blue-800 hover:underline">
        Pagina successiva
      </Link>
    ) : (
      <span />
    )}
  </nav>
);
