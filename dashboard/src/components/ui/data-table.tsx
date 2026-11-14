import type { Key, ReactNode } from 'react';

export type DataTableColumn<T> = {
  readonly header: string;
  readonly cell: (row: T) => ReactNode;
};

type DataTableProps<T> = {
  readonly label: string;
  readonly columns: readonly DataTableColumn<T>[];
  readonly rows: readonly T[];
  readonly rowKey: (row: T) => Key;
  readonly empty?: string;
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
}: DataTableProps<T>) => {
  if (rows.length === 0) {
    return <p className="text-slate-600">{empty}</p>;
  }
  return (
    <table aria-label={label} className="block w-full text-sm md:table">
      <thead className="hidden border-b border-slate-200 text-left md:table-header-group">
        <tr>
          {columns.map((column) => (
            <th key={column.header} scope="col" className="px-3 py-2 font-semibold">
              {column.header}
            </th>
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
