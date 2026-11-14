import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const DAY = 24 * 60 * 60 * 1000;
const daysAgo = (days: number) => new Date(Date.now() - days * DAY);

const curve = async () => screen.findByRole('figure', { name: 'Equity curve' });

describe('EquityCurve', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa', { allocatedCapital: 300 });
  });

  it('draws a point for each cycle of the whole life of the flow by default', async () => {
    for (const [days, equity] of [
      [45, 310],
      [20, 295],
      [1, 305],
    ] as const) {
      fakePlatform.recordEquity('alfa', daysAgo(days), equity);
    }
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(within(await curve()).getAllByRole('img', { name: /^Equity / })).toHaveLength(3);
    expect(screen.getByRole('combobox', { name: 'Periodo' })).toHaveValue('all');
  });

  it('colours the points against the initial capital of the flow', async () => {
    fakePlatform.recordEquity('alfa', daysAgo(2), 310);
    fakePlatform.recordEquity('alfa', daysAgo(1), 295);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    const chart = await curve();
    expect(within(chart).getByRole('img', { name: /^Equity 310 .*verde$/ })).toBeInTheDocument();
    expect(within(chart).getByRole('img', { name: /^Equity 295 .*rossa$/ })).toBeInTheDocument();
    expect(within(chart).getByText('Capitale iniziale 300')).toBeInTheDocument();
  });

  it('shows only the cycles of the period the user chooses', async () => {
    fakePlatform.recordEquity('alfa', daysAgo(40), 310);
    fakePlatform.recordEquity('alfa', daysAgo(10), 295);
    fakePlatform.recordEquity('alfa', daysAgo(3), 305);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await curve();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Periodo' }), '7 giorni');

    await expect.poll(() => screen.getAllByRole('img', { name: /^Equity / })).toHaveLength(1);
    expect(screen.getByRole('img', { name: /^Equity 305 / })).toBeInTheDocument();
  });

  it('shows the cycles of a range from its first to its last day', async () => {
    fakePlatform.recordEquity('alfa', daysAgo(10), 310);
    fakePlatform.recordEquity('alfa', daysAgo(5), 295);
    fakePlatform.recordEquity('alfa', daysAgo(1), 305);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await curve();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Periodo' }), 'Intervallo');
    expect(
      within(screen.getByRole('region', { name: 'Equity curve' })).getByText(
        "Scegli il primo e l'ultimo giorno dell'intervallo.",
      ),
    ).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Dal'), dayOf(daysAgo(6)));
    await userEvent.type(screen.getByLabelText('Al'), dayOf(daysAgo(4)));

    await expect.poll(() => screen.queryAllByRole('img', { name: /^Equity / })).toHaveLength(1);
    expect(screen.getByRole('img', { name: /^Equity 295 / })).toBeInTheDocument();
  });

  it('tells why a range that ends before it starts is refused', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await screen.findByText('Nessun ciclo ancora eseguito');

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Periodo' }), 'Intervallo');
    await userEvent.type(screen.getByLabelText('Dal'), dayOf(daysAgo(1)));
    await userEvent.type(screen.getByLabelText('Al'), dayOf(daysAgo(3)));

    const panel = screen.getByRole('region', { name: 'Equity curve' });
    expect(
      await within(panel).findByText(/il giorno iniziale è successivo al giorno finale/),
    ).toBeInTheDocument();
  });

  it('says when the flow has not run a cycle yet', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByText('Nessun ciclo ancora eseguito')).toBeInTheDocument();
    expect(screen.queryByRole('figure', { name: 'Equity curve' })).not.toBeInTheDocument();
  });

  it('shows no curve for a draft, which has no capital and no cycle yet', async () => {
    fakePlatform.addFlow('anna', 'bozza', { status: 'bozza', allocatedCapital: null });
    await renderApp({ account: 'anna', url: '/flows/flow-bozza' });

    expect(await screen.findByText('Nessun ciclo ancora eseguito')).toBeInTheDocument();
  });

  it('says when no cycle falls in the period', async () => {
    fakePlatform.recordEquity('alfa', daysAgo(40), 310);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await curve();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Periodo' }), '30 giorni');

    expect(await screen.findByText('Nessun ciclo nel periodo scelto')).toBeInTheDocument();
  });

  it('tells why the curve could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/equity', () =>
        HttpResponse.json({ detail: 'errore interno' }, { status: 500 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('alert')).toHaveTextContent('errore interno');
  });
});

const dayOf = (instant: Date): string => {
  const month = String(instant.getMonth() + 1).padStart(2, '0');
  const day = String(instant.getDate()).padStart(2, '0');
  return `${instant.getFullYear()}-${month}-${day}`;
};
