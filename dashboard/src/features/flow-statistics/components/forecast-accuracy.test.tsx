import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform, type FakeForecast } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

// The error of the forecasts in the Panoramica of the flow (R3.6.1, ADR errore-della-previsione-nella-pagina-del-flusso).

const HOUR_MS = 60 * 60 * 1000;
const DAY_MS = 24 * HOUR_MS;
const ago = (milliseconds: number) => new Date(Date.now() - milliseconds);

const forecast = (
  predictedPrice: number,
  actualPrice: number | null,
  changes: Partial<FakeForecast> = {},
): FakeForecast => ({
  asset: 'BTC',
  horizonMinutes: 60,
  expiresAt: ago(2 * HOUR_MS),
  predictedPrice,
  actualPrice,
  ...changes,
});

const panel = () => screen.findByRole('region', { name: 'Errore della previsione' });

const errorOf = async (label: string) =>
  within(await panel()).findByLabelText(label, { exact: true });

const shownNow = (label: string) =>
  within(screen.getByRole('region', { name: 'Errore della previsione' })).getByLabelText(label, {
    exact: true,
  });

describe('ForecastAccuracy', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('shows the mean error of each asset and horizon formatted in Italian', async () => {
    fakePlatform.addFlow('anna', 'alfa', {
      forecasts: [
        forecast(60500, 60000),
        forecast(61000, 61400),
        forecast(60900, 60000, { horizonMinutes: 15 }),
      ],
    });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await errorOf('BTC · 1 ora')).toHaveTextContent(
      'errore medio 450 · 0,74% · 2 previsioni valutate',
    );
    expect(await errorOf('BTC · 15 minuti')).toHaveTextContent(
      'errore medio 900 · 1,50% · 1 previsione valutata',
    );
  });

  it('says how many forecasts could not be evaluated', async () => {
    fakePlatform.addFlow('anna', 'alfa', {
      forecasts: [forecast(60500, 60000), forecast(60000, null), forecast(60000, null)],
    });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await errorOf('BTC · 1 ora')).toHaveTextContent(
      'errore medio 500 · 0,83% · 1 previsione valutata · 2 non valutabili',
    );
  });

  it('says the error is not available without evaluated forecasts in the period', async () => {
    fakePlatform.addFlow('anna', 'alfa', { forecasts: [forecast(60000, null)] });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await errorOf('BTC · 1 ora')).toHaveTextContent(
      'non disponibile nel periodo · 1 non valutabile',
    );
  });

  it('reads the error of the period of the page', async () => {
    fakePlatform.addFlow('anna', 'alfa', {
      forecasts: [forecast(60900, 60000, { expiresAt: ago(20 * DAY_MS) }), forecast(60300, 60000)],
    });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    expect(await errorOf('BTC · 1 ora')).toHaveTextContent('errore medio 600');

    await userEvent.selectOptions(screen.getByLabelText('Periodo'), '7 giorni');

    await waitFor(() => expect(shownNow('BTC · 1 ora')).toHaveTextContent('errore medio 300'));
  });

  it('names a horizon of hours in hours', async () => {
    fakePlatform.addFlow('anna', 'alfa', {
      forecasts: [forecast(60500, 60000, { horizonMinutes: 240, expiresAt: ago(DAY_MS) })],
    });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await errorOf('BTC · 4 ore')).toHaveTextContent('errore medio 500');
  });

  it('does not show the panel for a flow without forecasts', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await screen.findByRole('region', { name: 'Statistiche' });
    await within(await screen.findByRole('region', { name: 'Statistiche' })).findByLabelText(
      'Numero di operazioni',
    );

    expect(screen.queryByRole('region', { name: 'Errore della previsione' })).toBeNull();
  });

  it('tells why the error could not be read', async () => {
    fakePlatform.addFlow('anna', 'alfa', { forecasts: [forecast(60500, 60000)] });
    await renderApp({
      account: 'anna',
      url: '/flows/flow-alfa?period=range&from=2026-11-03T10%3A00Z&to=2026-11-03T09%3A59Z',
    });

    expect(await within(await panel()).findByRole('alert')).toHaveTextContent(
      "periodo non valido: l'inizio è successivo alla fine",
    );
  });
});
