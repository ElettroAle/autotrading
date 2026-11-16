import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { aCapitalChange } from '@/testing/mocks/capital-changes';
import { fakePlatform, type FakeFlow } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const AT = new Date('2026-11-15T09:07:00Z');
const HOUR = 3_600_000;

const rowsOf = async () => {
  const table = await screen.findByRole('table', { name: 'Variazioni di capitale' });
  return within(table).getAllByRole('row').slice(1);
};

// A missing row has no cells, so the comparison with the expected ones fails with both in sight.
const cellsOf = (row: HTMLElement | undefined) =>
  row === undefined
    ? []
    : within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent);

const changed = (flow: FakeFlow, previous: number, next: number, at: Date) => {
  fakePlatform.recordCapitalChange(aCapitalChange(flow, previous, next, at));
};

// R3.4.2, ADR storico-delle-variazioni-di-capitale: the shared table and pages of the history of the capital.
describe('FlowCapitalChanges', () => {
  let flow: FakeFlow;

  beforeEach(() => {
    flow = fakePlatform.giveFlowTo('anna', 'alfa');
  });

  it('shows date and time, reason, amount, capital before and after of each change, from the most recent', async () => {
    changed(flow, 500, 700, new Date(AT.getTime() - HOUR));
    changed(flow, 700, 400, AT);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/capital' });

    const [first, second] = await rowsOf();
    expect(cellsOf(first)).toEqual([
      'Data e ora15/11/2026, 10:07:00',
      'Motivoriduzione',
      'Importo300 USDC',
      'Capitale prima700 USDC',
      'Capitale dopo400 USDC',
    ]);
    expect(cellsOf(second)).toEqual([
      'Data e ora15/11/2026, 09:07:00',
      'Motivoaumento',
      'Importo200 USDC',
      'Capitale prima500 USDC',
      'Capitale dopo700 USDC',
    ]);
  });

  it('is the tab Capitale of the page of the flow', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/capital' });

    expect(await screen.findByRole('link', { name: 'Capitale' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('shows only the changes of the minutes of the period', async () => {
    changed(flow, 500, 600, new Date('2026-11-10T09:00:00Z'));
    changed(flow, 600, 700, new Date('2026-11-15T09:00:00Z'));
    await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa/capital?period=range&from=2026-11-14T00%3A00Z&to=2026-11-16T23%3A59Z',
    });

    const rows = await rowsOf();
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent('15/11/2026');
  });

  it('asks the start and the end of a range before reading', async () => {
    await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa/capital?period=range&from=2026-11-14T00%3A00Z',
    });

    expect(
      await screen.findByText("Scegli l'inizio e la fine dell'intervallo."),
    ).toBeInTheDocument();
    expect(screen.queryByRole('table', { name: 'Variazioni di capitale' })).not.toBeInTheDocument();
  });

  it('shows 50 changes a page, with the next page and back', async () => {
    Array.from({ length: 60 }, (_, index) =>
      changed(flow, 500, 501 + index, new Date(AT.getTime() - index * HOUR)),
    );
    const user = userEvent.setup();
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/capital' });

    expect(await rowsOf()).toHaveLength(50);
    await user.click(screen.getByRole('link', { name: 'Pagina successiva' }));

    await screen.findByText('Pagina 2');
    expect(await rowsOf()).toHaveLength(10);
    expect(screen.getByRole('link', { name: 'Pagina precedente' })).toHaveAttribute(
      'href',
      '/flows/flow-alfa/capital',
    );
  });

  it('says the flow has no change of capital', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/capital' });

    expect(await screen.findByText('Nessuna variazione di capitale.')).toBeInTheDocument();
  });

  it('says no change falls in the period chosen', async () => {
    changed(flow, 500, 600, AT);
    await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa/capital?period=range&from=2026-10-01T00%3A00Z&to=2026-10-02T23%3A59Z',
    });

    expect(await screen.findByText('Nessuna variazione nel periodo scelto.')).toBeInTheDocument();
  });

  it('tells why the history could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/capital-changes', () =>
        HttpResponse.json({ detail: 'flusso non trovato' }, { status: 404 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/capital' });

    expect(await screen.findByRole('alert')).toHaveTextContent('flusso non trovato');
  });
});
