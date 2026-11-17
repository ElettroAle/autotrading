import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';

import { DataTable } from './data-table';

const Address = () => <output aria-label="indirizzo">{useLocation().pathname}</output>;

const inRouter = (ui: ReactNode) => {
  const router = createMemoryRouter([
    {
      path: '*',
      element: (
        <>
          {ui}
          <Address />
        </>
      ),
    },
  ]);
  render(<RouterProvider router={router} />);
};

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

  it('shows the detail of a row under it, across every column, and no detail where the row has none', () => {
    render(
      <DataTable
        label="Frutti"
        columns={COLUMNS}
        rows={FRUITS}
        rowKey={(fruit) => fruit.name}
        rowDetail={(fruit) => (fruit.name === 'mela' ? `dettaglio di ${fruit.name}` : undefined)}
      />,
    );

    const rows = within(screen.getByRole('table', { name: 'Frutti' })).getAllByRole('row');
    expect(rows.map((row) => row.textContent)).toEqual([
      'NomeColore',
      'NomemelaColorerossa',
      'dettaglio di mela',
      'NomebananaColoregialla',
    ]);
    expect(within(rows[2] as HTMLElement).getByRole('cell')).toHaveAttribute('colspan', '2');
  });

  it('shows the detail of a row that leads to a detail too', () => {
    inRouter(
      <DataTable
        label="Frutti"
        columns={COLUMNS}
        rows={FRUITS}
        rowKey={(fruit) => fruit.name}
        rowHref={(fruit) => `/frutti/${fruit.name}`}
        rowDetail={(fruit) => `dettaglio di ${fruit.name}`}
      />,
    );

    expect(screen.getByText('dettaglio di banana')).toBeInTheDocument();
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

  it('breaks a long word of a cell on a phone, where the cell is a line of a card', () => {
    render(
      <DataTable label="Frutti" columns={COLUMNS} rows={FRUITS} rowKey={(fruit) => fruit.name} />,
    );

    for (const cell of screen.getAllByRole('cell')) {
      expect(cell).toHaveClass('max-md:wrap-anywhere');
    }
  });

  it('keeps the table within its box on a wide screen, scrolling inside it with the first column fixed', () => {
    render(
      <DataTable label="Frutti" columns={COLUMNS} rows={FRUITS} rowKey={(fruit) => fruit.name} />,
    );

    const box = screen.getByRole('region', { name: 'Frutti' });
    expect(box).toHaveClass('md:overflow-x-auto');
    expect(within(box).getByRole('table', { name: 'Frutti' })).toBeInTheDocument();
    const [firstHeader, secondHeader] = screen.getAllByRole('columnheader');
    expect(firstHeader).toHaveClass('md:sticky', 'md:left-0');
    expect(secondHeader).not.toHaveClass('md:sticky');
    const [firstCell, secondCell] = screen.getAllByRole('cell');
    expect(firstCell).toHaveClass('md:sticky', 'md:left-0');
    expect(secondCell).not.toHaveClass('md:sticky');
  });

  describe('with rows that lead to a detail', () => {
    const renderLinked = () =>
      inRouter(
        <DataTable
          label="Frutti"
          columns={[
            ...COLUMNS,
            { header: 'Scelta', cell: () => <input type="checkbox" aria-label="Scegli" /> },
          ]}
          rows={FRUITS}
          rowKey={(fruit) => fruit.name}
          rowHref={(fruit) => `/frutti/${fruit.name}`}
        />,
      );

    it('links the first cell of each row to its detail, for keyboards and readers', () => {
      renderLinked();

      expect(screen.getByRole('link', { name: 'banana' })).toHaveAttribute(
        'href',
        '/frutti/banana',
      );
    });

    it('opens the detail from any point of the row', async () => {
      renderLinked();

      await userEvent.click(screen.getByText('gialla'));

      expect(screen.getByRole('status', { name: 'indirizzo' })).toHaveTextContent('/frutti/banana');
    });

    it('leaves a control of the row to do its own work', async () => {
      renderLinked();

      const [box] = screen.getAllByRole('checkbox', { name: 'Scegli' });
      await userEvent.click(box as HTMLElement);

      expect(box).toBeChecked();
      expect(screen.getByRole('status', { name: 'indirizzo' })).toHaveTextContent(/^\/$/);
    });
  });

  describe('with filters', () => {
    const FILTERS = [
      {
        name: 'colour',
        label: 'Colore',
        all: 'Tutti',
        options: [{ value: 'rossa', label: 'Rossi' }],
      },
    ];
    const countOf = (total: number) => `${total} frutti`;

    it('shows the filters above the table, with the count of the results', () => {
      inRouter(
        <DataTable
          label="Frutti"
          columns={COLUMNS}
          rows={FRUITS}
          rowKey={(fruit) => fruit.name}
          filtering={{ filters: FILTERS, total: 12, countOf }}
        />,
      );

      const bar = screen.getByRole('group', { name: 'Filtri di Frutti' });
      expect(within(bar).getByRole('button', { name: 'Rossi' })).toBeInTheDocument();
      expect(within(bar).getByText('12 frutti')).toBeInTheDocument();
      expect(
        bar.compareDocumentPosition(screen.getByRole('table')) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
    });

    it('keeps the filters when nothing matches, so they can be changed', () => {
      inRouter(
        <DataTable
          label="Frutti"
          columns={COLUMNS}
          rows={[]}
          rowKey={(fruit) => fruit.name}
          empty="Nessun frutto."
          filtering={{ filters: FILTERS, total: 0, countOf }}
        />,
      );

      expect(screen.getByRole('group', { name: 'Filtri di Frutti' })).toBeInTheDocument();
      expect(screen.getByText('Nessun frutto.')).toBeInTheDocument();
    });
  });
  // ADR posizione-evidenziata-dall-indirizzo: the row an address points at stands out by colour and by text.
  it('marks the highlighted row as current, with a text besides the colour, and brings it into focus', () => {
    render(
      <DataTable
        label="Frutti"
        columns={COLUMNS}
        rows={FRUITS}
        rowKey={(fruit) => fruit.name}
        highlightedRow={(fruit) => fruit.name === 'banana'}
      />,
    );

    const [, apple, banana] = screen.getAllByRole('row');
    expect(banana).toHaveAttribute('aria-current', 'true');
    expect(banana).toHaveClass('bg-amber-50');
    expect(within(banana as HTMLElement).getByText('Dalla notifica')).toBeInTheDocument();
    expect(banana).toHaveFocus();
    expect(apple).not.toHaveAttribute('aria-current');
    expect(within(apple as HTMLElement).queryByText('Dalla notifica')).not.toBeInTheDocument();
  });

  it('scrolls the highlighted row into view', () => {
    const scrolled: Element[] = [];
    // jsdom lays nothing out and has no scrollIntoView: the test lends one that records the element.
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = function (this: Element) {
      scrolled.push(this);
    };

    render(
      <DataTable
        label="Frutti"
        columns={COLUMNS}
        rows={FRUITS}
        rowKey={(fruit) => fruit.name}
        highlightedRow={(fruit) => fruit.name === 'mela'}
      />,
    );

    Element.prototype.scrollIntoView = original;
    expect(scrolled).toEqual([screen.getAllByRole('row')[1]]);
  });

  it('highlights a row that leads to a detail too', () => {
    inRouter(
      <DataTable
        label="Frutti"
        columns={COLUMNS}
        rows={FRUITS}
        rowKey={(fruit) => fruit.name}
        rowHref={(fruit) => `/frutti/${fruit.name}`}
        highlightedRow={(fruit) => fruit.name === 'mela'}
      />,
    );

    const [, apple] = screen.getAllByRole('row');
    expect(apple).toHaveAttribute('aria-current', 'true');
    expect(apple).toHaveFocus();
  });

  it('highlights no row without the prop', () => {
    render(
      <DataTable label="Frutti" columns={COLUMNS} rows={FRUITS} rowKey={(fruit) => fruit.name} />,
    );

    expect(screen.getAllByRole('row').filter((row) => row.hasAttribute('aria-current'))).toEqual(
      [],
    );
    expect(screen.queryByText('Dalla notifica')).not.toBeInTheDocument();
  });
});
