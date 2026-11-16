import { Fragment, type Key, type MouseEvent, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router';

import { TableFilters, type TableFiltering } from './table-filters';

export type DataTableColumn<T> = {
  readonly header: string;
  readonly cell: (row: T) => ReactNode;
  /** The key the table asks to sort by when the header is pressed; without it the column does not sort. */
  readonly sortKey?: string;
};

export type SortDirection = 'ascending' | 'descending';

export type DataTableSort = { readonly key: string; readonly direction: SortDirection };

type DataTableProps<T> = {
  readonly label: string;
  readonly columns: readonly DataTableColumn<T>[];
  readonly rows: readonly T[];
  readonly rowKey: (row: T) => Key;
  readonly empty?: string;
  /** The order of the rows, which the caller applies: the table only declares it and asks to change it. */
  readonly sort?: DataTableSort;
  readonly onSort?: (key: string) => void;
  /** The detail a row leads to: the whole row opens it, and its first cell links it. */
  readonly rowHref?: (row: T) => string;
  /** The filters of the table, shown above it with the count of the results. */
  readonly filtering?: TableFiltering;
  /** What a row adds under it across every column, as a text that wraps; nothing for a row without it. */
  readonly rowDetail?: (row: T) => ReactNode;
};

const ARROWS: Record<SortDirection, string> = { ascending: '▲', descending: '▼' };

// The first column stays in view while the others scroll under it on a wide screen (R6.4.4).
const FIXED = 'md:sticky md:left-0 md:z-10 md:bg-white';

const fixedIf = (first: boolean): string => (first ? FIXED : '');

type HeaderProps<T> = {
  readonly column: DataTableColumn<T>;
  readonly first: boolean;
  readonly sort?: DataTableSort;
  readonly onSort?: (key: string) => void;
};

// A sortable header is a button inside the header cell, which declares the order with aria-sort (ADR 0136).
const Header = <T,>({ column, first, sort, onSort }: HeaderProps<T>) => {
  const { header, sortKey } = column;
  const className = `px-3 py-2 font-semibold ${fixedIf(first)}`;
  if (sortKey === undefined || onSort === undefined) {
    return (
      <th scope="col" className={className}>
        {header}
      </th>
    );
  }
  const direction = sort?.key === sortKey ? sort.direction : undefined;
  return (
    <th scope="col" aria-sort={direction ?? 'none'} className={className}>
      <button
        type="button"
        className="inline-flex items-center gap-1 hover:underline"
        onClick={() => onSort(sortKey)}
      >
        {header}
        {direction !== undefined && <span aria-hidden="true">{ARROWS[direction]}</span>}
      </button>
    </th>
  );
};

// A control or a link inside the row does its own work: only a press elsewhere opens the detail.
const CONTROLS = 'a, button, input, select, textarea, label';

const isOnAControl = (event: MouseEvent): boolean =>
  event.target instanceof Element && event.target.closest(CONTROLS) !== null;

const ROW =
  'block rounded border border-slate-200 bg-white p-2 md:table-row md:rounded-none md:border-0 md:border-b md:p-0';

type CellsProps<T> = {
  readonly row: T;
  readonly columns: readonly DataTableColumn<T>[];
  readonly href?: string;
};

const Cells = <T,>({ row, columns, href }: CellsProps<T>) =>
  columns.map((column, index) => (
    <td
      key={column.header}
      className={`flex gap-2 px-1 py-1 max-md:wrap-anywhere md:table-cell md:px-3 md:py-2 ${fixedIf(index === 0)}`}
    >
      <span aria-hidden="true" className="font-medium text-slate-600 md:hidden">
        {column.header}
      </span>
      {index === 0 && href !== undefined ? (
        <Link to={href} className="font-medium text-blue-800 hover:underline">
          {column.cell(row)}
        </Link>
      ) : (
        column.cell(row)
      )}
    </td>
  ));

const LinkedRow = <T,>({ row, columns, href }: CellsProps<T> & { readonly href: string }) => {
  const navigate = useNavigate();
  // The link of the first cell is the way of keyboards and readers; the press on the row is a shortcut for a pointer.
  const open = (event: MouseEvent) => {
    if (!isOnAControl(event)) {
      void navigate(href);
    }
  };
  return (
    <tr onClick={open} className={`${ROW} cursor-pointer hover:bg-slate-50`}>
      <Cells row={row} columns={columns} href={href} />
    </tr>
  );
};

// On a phone the detail ends the card of its row; on a wide screen it is a line under the row, as wide as the table.
const DETAIL_ROW = 'block px-2 pb-2 md:table-row md:border-b md:px-0';

const DetailRow = ({ detail, width }: { readonly detail: ReactNode; readonly width: number }) =>
  detail === undefined || detail === null ? null : (
    <tr className={DETAIL_ROW}>
      <td colSpan={width} className="block wrap-anywhere md:table-cell md:px-3 md:pb-2">
        {detail}
      </td>
    </tr>
  );

type TableProps<T> = Omit<DataTableProps<T>, 'empty' | 'filtering'>;

const Table = <T,>({
  label,
  columns,
  rows,
  rowKey,
  sort,
  onSort,
  rowHref,
  rowDetail,
}: TableProps<T>) => (
  // Wider than its box, the table scrolls inside it: the page never scrolls (R6.4.4).
  <div role="region" aria-label={label} className="md:overflow-x-auto">
    <table aria-label={label} className="block w-full text-sm md:table">
      <thead className="hidden border-b border-slate-200 text-left md:table-header-group">
        <tr>
          {columns.map((column, index) => (
            <Header
              key={column.header}
              column={column}
              first={index === 0}
              sort={sort}
              onSort={onSort}
            />
          ))}
        </tr>
      </thead>
      <tbody className="block space-y-2 md:table-row-group md:space-y-0">
        {rows.map((row) => (
          <Fragment key={rowKey(row)}>
            {rowHref === undefined ? (
              <tr className={ROW}>
                <Cells row={row} columns={columns} />
              </tr>
            ) : (
              <LinkedRow row={row} columns={columns} href={rowHref(row)} />
            )}
            <DetailRow detail={rowDetail?.(row)} width={columns.length} />
          </Fragment>
        ))}
      </tbody>
    </table>
  </div>
);

/**
 * A table on a wide screen, stacked cards under 768 pixels (ADR 0128): one table in the page, whose rows become cards,
 * each cell labelled with its header for the eye only, as readers already announce the header of the column. It never
 * widens the page, a row that leads to a detail opens it from any point, and the filters it declares sit above it
 * (ADR tabella-condivisa-senza-sforamento-e-con-filtri).
 */
export const DataTable = <T,>({
  empty = 'Nessun dato.',
  filtering,
  ...table
}: DataTableProps<T>) => (
  <>
    {filtering !== undefined && <TableFilters label={table.label} {...filtering} />}
    {table.rows.length === 0 ? <p className="text-slate-600">{empty}</p> : <Table {...table} />}
  </>
);
