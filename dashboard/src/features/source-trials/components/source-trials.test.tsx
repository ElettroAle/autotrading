import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakeClock } from '@/testing/mocks/clock';
import { fakePlatform } from '@/testing/mocks/platform';
import { problem } from '@/testing/mocks/responses';
import { server } from '@/testing/mocks/server';
import {
  FAKE_TRIAL_MILLISECONDS,
  fakeSourceTrials,
  unreachableReason,
} from '@/testing/mocks/source-trials';
import { renderApp } from '@/testing/test-utils';
import { formatInstant } from '@/utils/format-instant';

const SOURCES_PAGE = '/fonti';
const NOW = new Date('2026-11-19T09:00:00Z');
const DATA_AT = new Date(NOW.getTime() - 5 * 60_000).toISOString();

const card = (source: string) => screen.findByRole('article', { name: source });

const trialForm = async (source: string) =>
  within(await card(source)).findByRole('form', { name: `Prova di ${source}` });

const outcome = async (source: string) =>
  within(await card(source)).getByRole('region', { name: `Esito della prova di ${source}` });

const tryIt = async (source: string) => {
  const form = await trialForm(source);
  await userEvent.click(within(form).getByRole('button', { name: 'Prova' }));
};

describe('the page Fonti with the trial of each adapter (R6.3.1, ADR pagina-fonti-con-la-prova)', () => {
  beforeEach(() => {
    fakeClock.fix(NOW);
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('shows a card for each source of the catalog, with its description', async () => {
    await renderApp({ account: 'anna', url: SOURCES_PAGE });

    expect(await screen.findByRole('heading', { level: 1, name: 'Fonti' })).toBeVisible();
    expect(await card('indicatori')).toHaveTextContent('Prezzo e indicatori tecnici');
    expect(await card('sentiment')).toBeVisible();
    expect(await card('notizie')).toBeVisible();
  });

  it('names the only adapter, preselects the first asset and fills the defaults', async () => {
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('indicatori');

    expect(form).toHaveTextContent('Adapter: Hyperliquid');
    expect(within(form).queryByLabelText('Adapter')).not.toBeInTheDocument();
    await waitFor(() => expect(within(form).getByLabelText('Asset')).toHaveValue('BTC'));
    const series = within(form).getByLabelText('lunghezza serie');
    expect(series).toHaveValue(10);
    expect(series).toHaveAttribute('min', '1');
    expect(series).toHaveAttribute('max', '50');
  });

  it('shows the values read, the instant of the data and the time of response of a trial that succeeds', async () => {
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('indicatori');
    await waitFor(() => expect(within(form).getByLabelText('Asset')).toHaveValue('BTC'));
    await userEvent.selectOptions(within(form).getByLabelText('Asset'), 'ETH');

    await tryIt('indicatori');

    const result = await outcome('indicatori');
    await waitFor(() => expect(result).toHaveTextContent('riuscita'));
    expect(result).toHaveAttribute('aria-live', 'polite');
    expect(result).toHaveTextContent('assetETH');
    expect(result).toHaveTextContent('lunghezza_serie10');
    expect(result).toHaveTextContent('valore42');
    expect(result).toHaveTextContent(formatInstant(DATA_AT));
    expect(result).toHaveTextContent(`${String(FAKE_TRIAL_MILLISECONDS)} ms`);
    expect(fakeSourceTrials.requests()).toEqual([
      {
        account: 'anna',
        source: 'indicatori',
        adapter: 'Hyperliquid',
        asset: 'ETH',
        parameters: { lunghezza_serie: 10 },
      },
    ]);
  });

  it('shows the reason and that the error is transient for a source that does not answer', async () => {
    fakeSourceTrials.silence('notizie');
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('notizie');
    await waitFor(() => expect(within(form).getByLabelText('Asset')).toHaveValue('BTC'));

    await tryIt('notizie');

    const result = await outcome('notizie');
    await waitFor(() => expect(result).toHaveTextContent('errore'));
    expect(result).toHaveTextContent(unreachableReason('notizie'));
    expect(result).toHaveTextContent('transitorio');
    expect(result).not.toHaveTextContent('permanente');
  });

  it('says permanent an error the source will repeat', async () => {
    server.use(
      http.post('*/sources/:name/adapters/:adapter/trials', () =>
        HttpResponse.json({
          outcome: 'failed',
          values: [],
          data_at: null,
          response_milliseconds: 12,
          reason: 'credenziali rifiutate',
          permanent: true,
        }),
      ),
    );
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('notizie');
    await waitFor(() => expect(within(form).getByLabelText('Asset')).toHaveValue('BTC'));

    await tryIt('notizie');

    const result = await outcome('notizie');
    await waitFor(() => expect(result).toHaveTextContent('permanente'));
    expect(result).toHaveTextContent('credenziali rifiutate');
  });

  it('says no data when a trial succeeds without values', async () => {
    server.use(
      http.post('*/sources/:name/adapters/:adapter/trials', () =>
        HttpResponse.json({
          outcome: 'succeeded',
          values: [],
          data_at: null,
          response_milliseconds: 7,
          reason: null,
          permanent: false,
        }),
      ),
    );
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    await card('sentiment');
    await userEvent.selectOptions(
      within(await trialForm('sentiment')).getByLabelText('Adapter'),
      'alternative.me',
    );

    await tryIt('sentiment');

    const result = await outcome('sentiment');
    await waitFor(() => expect(result).toHaveTextContent('nessun dato'));
    expect(result).toHaveTextContent('7 ms');
  });

  it('does not start a trial with a parameter outside its limits and says the admitted range', async () => {
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('indicatori');
    const series = within(form).getByLabelText('lunghezza serie');
    await userEvent.clear(series);
    await userEvent.type(series, '51');

    await tryIt('indicatori');

    expect(await within(form).findByText('ammesso da 1 a 50')).toBeVisible();
    expect(series).toHaveAttribute('aria-invalid', 'true');
    expect(fakeSourceTrials.requests()).toEqual([]);
  });

  it('asks the adapter of a source that has more than one, then asks no asset of a market source', async () => {
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('sentiment');
    expect(within(form).queryByLabelText('Asset')).not.toBeInTheDocument();

    await tryIt('sentiment');
    expect(await within(form).findByText("scegli l'adapter")).toBeVisible();

    await userEvent.selectOptions(within(form).getByLabelText('Adapter'), 'CoinMarketCap');
    await tryIt('sentiment');

    await waitFor(() => expect(fakeSourceTrials.requests()).toHaveLength(1));
    expect(fakeSourceTrials.requests()[0]).toMatchObject({
      source: 'sentiment',
      adapter: 'CoinMarketCap',
      asset: null,
      parameters: {},
    });
  });

  it('shows on its field a refusal of the API about a parameter', async () => {
    server.use(
      http.post('*/sources/:name/adapters/:adapter/trials', () =>
        problem(422, 'Unprocessable Content', 'parametro fuori dai valori ammessi', {
          field: 'lunghezza_serie',
          minimum: 1,
          maximum: 50,
        }),
      ),
    );
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('indicatori');
    await waitFor(() => expect(within(form).getByLabelText('Asset')).toHaveValue('BTC'));

    await tryIt('indicatori');

    expect(await within(form).findByText('parametro fuori dai valori ammessi')).toBeVisible();
    expect(within(form).getByLabelText('lunghezza serie')).toHaveAttribute('aria-invalid', 'true');
  });

  it('shows on the asset a refusal of the API about the asset', async () => {
    server.use(
      http.post('*/sources/:name/adapters/:adapter/trials', () =>
        problem(422, 'Unprocessable Content', "scegli l'asset su cui provare la fonte indicatori", {
          field: 'asset',
        }),
      ),
    );
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('indicatori');
    await waitFor(() => expect(within(form).getByLabelText('Asset')).toHaveValue('BTC'));

    await tryIt('indicatori');

    expect(
      await within(form).findByText("scegli l'asset su cui provare la fonte indicatori"),
    ).toBeVisible();
  });

  it('shows at the head of the form a refusal that concerns no field', async () => {
    server.use(
      http.post('*/sources/:name/adapters/:adapter/trials', () =>
        problem(503, 'Service Unavailable', 'servizio di esecuzione non raggiungibile, riprovare'),
      ),
    );
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('indicatori');
    await waitFor(() => expect(within(form).getByLabelText('Asset')).toHaveValue('BTC'));

    await tryIt('indicatori');

    expect(await within(form).findByRole('alert')).toHaveTextContent(
      'servizio di esecuzione non raggiungibile, riprovare',
    );
  });

  it('places on no field a refusal about a parameter the adapter does not declare', async () => {
    server.use(
      http.post('*/sources/:name/adapters/:adapter/trials', () =>
        problem(422, 'Unprocessable Content', 'parametro sconosciuto', { field: 'altro' }),
      ),
    );
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('indicatori');
    await waitFor(() => expect(within(form).getByLabelText('Asset')).toHaveValue('BTC'));

    await tryIt('indicatori');

    expect(await within(form).findByRole('alert')).toHaveTextContent('parametro sconosciuto');
  });

  it('says why the assets cannot be read', async () => {
    server.use(
      http.get('*/assets', () => problem(503, 'Service Unavailable', 'exchange non raggiungibile')),
    );
    await renderApp({ account: 'anna', url: SOURCES_PAGE });
    const form = await trialForm('indicatori');

    expect(await within(form).findByText(/Impossibile leggere gli asset/)).toBeVisible();
    expect(within(form).getByLabelText('Asset')).toBeDisabled();
  });

  it('says why the catalog cannot be read', async () => {
    server.use(
      http.get('*/sources', () => problem(503, 'Service Unavailable', 'catalogo non disponibile')),
    );
    await renderApp({ account: 'anna', url: SOURCES_PAGE });

    expect(await screen.findByRole('alert')).toHaveTextContent('catalogo non disponibile');
  });

  it('says the catalog has no sources', async () => {
    server.use(http.get('*/sources', () => HttpResponse.json([])));
    await renderApp({ account: 'anna', url: SOURCES_PAGE });

    expect(await screen.findByText('Nessuna fonte nel catalogo.')).toBeVisible();
  });
});
