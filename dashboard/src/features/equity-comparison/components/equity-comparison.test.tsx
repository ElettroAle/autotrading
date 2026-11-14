import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const DAY = 24 * 60 * 60 * 1000;
const daysAgo = (days: number) => new Date(Date.now() - days * DAY);

const chart = async () => screen.findByRole('figure', { name: 'Equity curve sovrapposte' });

const recordEquities = (flow: string, equities: ReadonlyArray<readonly [number, number]>) => {
  equities.forEach(([days, equity]) => fakePlatform.recordEquity(flow, daysAgo(days), equity));
};

describe('EquityComparison', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa', { allocatedCapital: 300 });
    fakePlatform.addFlow('anna', 'beta', { allocatedCapital: 200 });
  });

  it('draws the curves of the chosen flows from 0% at the first point of the period', async () => {
    recordEquities('alfa', [
      [40, 100],
      [20, 300],
      [10, 330],
    ]);
    recordEquities('beta', [
      [15, 200],
      [5, 190],
    ]);

    await renderApp({
      account: 'anna',
      url: '/comparison?period=30d&flow=flow-alfa&flow=flow-beta',
    });

    const curves = await chart();
    expect(within(curves).getAllByRole('img', { name: /^alfa / })).toHaveLength(2);
    expect(within(curves).getAllByRole('img', { name: /^alfa / })[0]).toHaveAccessibleName(
      /^alfa 0,00% del /,
    );
    expect(within(curves).getByRole('img', { name: /^alfa \+10,00% del / })).toBeInTheDocument();
    expect(within(curves).getAllByRole('img', { name: /^beta / })[0]).toHaveAccessibleName(
      /^beta 0,00% del /,
    );
    expect(within(curves).getByRole('img', { name: /^beta -5,00% del / })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Periodo' })).toHaveValue('30d');
  });

  it('names the chosen flows in the legend', async () => {
    recordEquities('alfa', [[1, 300]]);
    recordEquities('beta', [[1, 200]]);

    await renderApp({ account: 'anna', url: '/comparison?flow=flow-alfa&flow=flow-beta' });

    const legend = within(await chart()).getByRole('list', { name: 'Legenda' });
    expect(
      within(legend)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['alfa', 'beta']);
  });

  it('compares at most five flows, the first five chosen', async () => {
    for (const name of ['gamma', 'delta', 'epsilon', 'zeta']) {
      fakePlatform.addFlow('anna', name);
    }
    const names = ['alfa', 'beta', 'gamma', 'delta', 'epsilon', 'zeta'];
    names.forEach((name) => recordEquities(name, [[1, 100]]));
    const flows = names.map((name) => `flow=flow-${name}`).join('&');

    await renderApp({ account: 'anna', url: `/comparison?${flows}` });

    const legend = within(await chart()).getByRole('list', { name: 'Legenda' });
    expect(
      within(legend)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(names.slice(0, 5));
  });

  it('reads the period again when the user chooses another one', async () => {
    recordEquities('alfa', [
      [20, 300],
      [3, 330],
      [1, 363],
    ]);
    await renderApp({ account: 'anna', url: '/comparison?flow=flow-alfa' });
    await chart();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Periodo' }), '7 giorni');

    expect(await screen.findByRole('img', { name: /^alfa \+10,00% del / })).toBeInTheDocument();
    expect(screen.getAllByRole('img', { name: /^alfa / })).toHaveLength(2);
  });

  it('ignores a flow the user does not have', async () => {
    recordEquities('alfa', [[1, 300]]);

    await renderApp({ account: 'anna', url: '/comparison?flow=flow-alfa&flow=flow-omega' });

    const legend = within(await chart()).getByRole('list', { name: 'Legenda' });
    expect(
      within(legend)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['alfa']);
  });

  it('draws no point where the change is not defined', async () => {
    recordEquities('alfa', [
      [2, 0],
      [1, 30],
    ]);
    recordEquities('beta', [[1, 200]]);

    await renderApp({ account: 'anna', url: '/comparison?flow=flow-alfa&flow=flow-beta' });

    const curves = await chart();
    expect(within(curves).queryAllByRole('img', { name: /^alfa / })).toHaveLength(0);
    expect(within(curves).getAllByRole('img', { name: /^beta / })).toHaveLength(1);
  });

  it('asks to choose the flows when none is chosen', async () => {
    await renderApp({ account: 'anna', url: '/comparison' });

    expect(
      await screen.findByText('Scegli da 1 a 5 flussi dalla classifica da confrontare.'),
    ).toBeInTheDocument();
  });

  it('tells when the chosen flows have no cycle in the period', async () => {
    recordEquities('alfa', [[40, 300]]);

    await renderApp({ account: 'anna', url: '/comparison?period=7d&flow=flow-alfa' });

    expect(await screen.findByText('Nessun ciclo nel periodo scelto')).toBeInTheDocument();
    expect(screen.queryByRole('figure')).not.toBeInTheDocument();
  });

  it('waits for both days of a range', async () => {
    await renderApp({ account: 'anna', url: '/comparison?period=range&flow=flow-alfa' });

    expect(
      await screen.findByText("Scegli il primo e l'ultimo giorno dell'intervallo."),
    ).toBeInTheDocument();
  });

  it('tells why a curve cannot be read', async () => {
    server.use(
      http.get('*/flows/:flowId/equity', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Bad Request', status: 400, detail: 'periodo non valido' },
          { status: 400, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );

    await renderApp({ account: 'anna', url: '/comparison?flow=flow-alfa' });

    expect(await screen.findByRole('alert')).toHaveTextContent('periodo non valido');
  });

  it('tells why the flows cannot be read', async () => {
    server.use(
      http.get('*/flows', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Error', status: 503, detail: 'servizio non disponibile' },
          { status: 503, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );

    await renderApp({ account: 'anna', url: '/comparison?flow=flow-alfa' });

    expect(await screen.findByRole('alert')).toHaveTextContent('servizio non disponibile');
  });
});
