import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { DataTable } from './data-table';

type Fruit = { readonly name: string; readonly colour: string };

const FRUITS: Fruit[] = [
  { name: 'mela', colour: 'rossa' },
  { name: 'banana', colour: 'gialla' },
];

const COLUMNS = [
  { header: 'Nome', cell: (fruit: Fruit) => fruit.name },
  { header: 'Colore', cell: (fruit: Fruit) => <em>{fruit.colour}</em> },
];

describe('DataTable', () => {
  it('shows a row for each item, a cell for each column, under the headers', () => {
    render(
      <DataTable label="Frutti" columns={COLUMNS} rows={FRUITS} rowKey={(fruit) => fruit.name} />,
    );

    const table = screen.getByRole('table', { name: 'Frutti' });
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((header) => header.textContent),
    ).toEqual(['Nome', 'Colore']);
    const [, first, second] = within(table).getAllByRole('row');
    expect(within(first as HTMLElement).getAllByRole('cell')[1]).toHaveTextContent('rossa');
    expect(second).toHaveTextContent('banana');
  });

  it('labels every cell with its header for the stacked cards of a narrow screen, hidden from readers', () => {
    render(
      <DataTable label="Frutti" columns={COLUMNS} rows={FRUITS} rowKey={(fruit) => fruit.name} />,
    );

    const [cell] = screen.getAllByRole('cell');
    const label = within(cell as HTMLElement).getByText('Nome');
    expect(label).toHaveAttribute('aria-hidden', 'true');
    expect(label).toHaveClass('md:hidden');
  });

  it('says there is nothing to show', () => {
    render(
      <DataTable
        label="Frutti"
        columns={COLUMNS}
        rows={[]}
        rowKey={(fruit) => fruit.name}
        empty="Nessun frutto."
      />,
    );

    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.getByText('Nessun frutto.')).toBeInTheDocument();
  });

  describe('with sortable headers', () => {
    const SORTABLE = [
      { header: 'Nome', cell: (fruit: Fruit) => fruit.name, sortKey: 'name' },
      { header: 'Colore', cell: (fruit: Fruit) => fruit.colour, sortKey: 'colour' },
      { header: 'Nota', cell: () => '' },
    ];

    const renderSorted = (onSort: (key: string) => void = () => undefined) => {
      render(
        <DataTable
          label="Frutti"
          columns={SORTABLE}
          rows={FRUITS}
          rowKey={(fruit) => fruit.name}
          sort={{ key: 'colour', direction: 'descending' }}
          onSort={onSort}
        />,
      );
    };

    it('declares the order on the sorted header only, and none on the other sortable ones', () => {
      renderSorted();

      expect(screen.getByRole('columnheader', { name: 'Colore' })).toHaveAttribute(
        'aria-sort',
        'descending',
      );
      expect(screen.getByRole('columnheader', { name: 'Nome' })).toHaveAttribute(
        'aria-sort',
        'none',
      );
      expect(screen.getByRole('columnheader', { name: 'Nota' })).not.toHaveAttribute('aria-sort');
    });

    it('asks to sort by the column whose header is pressed', async () => {
      const onSort = vi.fn();
      renderSorted(onSort);

      await userEvent.click(screen.getByRole('button', { name: 'Nome' }));

      expect(onSort).toHaveBeenCalledWith('name');
    });

    it('offers no button on a header that does not sort', () => {
      renderSorted();

      expect(screen.queryByRole('button', { name: 'Nota' })).not.toBeInTheDocument();
    });

    it('shows plain headers without a way to sort', () => {
      render(
        <DataTable
          label="Frutti"
          columns={SORTABLE}
          rows={FRUITS}
          rowKey={(fruit) => fruit.name}
        />,
      );

      expect(screen.queryByRole('button')).not.toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: 'Nome' })).not.toHaveAttribute('aria-sort');
    });
  });
});
