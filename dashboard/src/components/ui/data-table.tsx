import type { Key, ReactNode } from 'react';

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
};

const ARROWS: Record<SortDirection, string> = { ascending: '▲', descending: '▼' };

type HeaderProps<T> = {
  readonly column: DataTableColumn<T>;
  readonly sort?: DataTableSort;
  readonly onSort?: (key: string) => void;
};

// A sortable header is a button inside the header cell, which declares the order with aria-sort (ADR 0136).
const Header = <T,>({ column, sort, onSort }: HeaderProps<T>) => {
  const { header, sortKey } = column;
  if (sortKey === undefined || onSort === undefined) {
    return (
      <th scope="col" className="px-3 py-2 font-semibold">
        {header}
      </th>
    );
  }
  const direction = sort?.key === sortKey ? sort.direction : undefined;
  return (
    <th scope="col" aria-sort={direction ?? 'none'} className="px-3 py-2 font-semibold">
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

/**
 * A table on a wide screen, stacked cards under 768 pixels (ADR 0128): one table in the page, whose rows become cards,
 * each cell labelled with its header for the eye only, as readers already announce the header of the column.
 */
export const DataTable = <T,>({
  label,
  columns,
  rows,
  rowKey,
  empty = 'Nessun dato.',
  sort,
  onSort,
}: DataTableProps<T>) => {
  if (rows.length === 0) {
    return <p className="text-slate-600">{empty}</p>;
  }
  return (
    <table aria-label={label} className="block w-full text-sm md:table">
      <thead className="hidden border-b border-slate-200 text-left md:table-header-group">
        <tr>
          {columns.map((column) => (
            <Header key={column.header} column={column} sort={sort} onSort={onSort} />
          ))}
        </tr>
      </thead>
      <tbody className="block space-y-2 md:table-row-group md:space-y-0">
        {rows.map((row) => (
          <tr
            key={rowKey(row)}
            className="block rounded border border-slate-200 bg-white p-2 md:table-row md:rounded-none md:border-0 md:border-b md:p-0"
          >
            {columns.map((column) => (
              <td
                key={column.header}
                className="flex gap-2 px-1 py-1 md:table-cell md:px-3 md:py-2"
              >
                <span aria-hidden="true" className="font-medium text-slate-600 md:hidden">
                  {column.header}
                </span>
                {column.cell(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};
