import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { configurationOf, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const NEW_FLOW = '/flows/new';
const MODEL = 'openrouter/deepseek-chat';

const field = (label: string) => screen.getByLabelText(label, { exact: true });

const fillValidFlow = async ({ capital = '300' }: { capital?: string } = {}) => {
  await userEvent.type(await screen.findByLabelText('Nome'), 'alfa');
  await userEvent.selectOptions(field('Conto'), 'principale');
  await userEvent.type(field('Asset'), 'BTC, eth');
  await userEvent.clear(field('Intervallo del ciclo in minuti'));
  await userEvent.type(field('Intervallo del ciclo in minuti'), '30');
  await userEvent.click(screen.getByRole('checkbox', { name: 'indicatori' }));
  await userEvent.type(field('Peso di indicatori'), '2');
  await userEvent.type(await screen.findByLabelText('lunghezza serie di indicatori'), '20');
  await userEvent.click(screen.getByRole('checkbox', { name: 'sentiment' }));
  await userEvent.selectOptions(field('Modello'), MODEL);
  await userEvent.type(field('temperatura'), '0,5');
  await userEvent.selectOptions(field('livello di ragionamento'), 'high');
  await userEvent.type(field('Istruzioni'), 'prudente');
  await userEvent.type(field('Leva massima'), '3');
  await userEvent.type(field('Esposizione massima del margine (%)'), '10');
  await userEvent.type(field('Capitale allocato'), capital);
};

describe('CreateFlow', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.giveAccountTo('anna', 'principale', 500);
    fakePlatform.registerProviderKey('anna', 'openrouter');
  });

  it('opens from the list of the flows', async () => {
    const { router } = await renderApp({ account: 'anna' });

    await userEvent.click(await screen.findByRole('link', { name: 'Nuovo flusso' }));

    expect(router.state.location.pathname).toBe(NEW_FLOW);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Nuovo flusso');
  });

  it('offers the choices of the catalogs of the API', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    const models = within(await screen.findByLabelText('Modello'));
    expect(models.getByRole('option', { name: MODEL })).toBeInTheDocument();
    expect(models.getByRole('option', { name: 'openai/gpt-4o' })).toBeInTheDocument();
    const sources = within(screen.getByRole('group', { name: 'Fonti' }));
    expect(sources.getAllByRole('checkbox').map((source) => source.getAttribute('id'))).toEqual([
      'flow-source-indicatori',
      'flow-source-sentiment',
      'flow-source-notizie',
    ]);
    expect(screen.getByRole('checkbox', { name: 'notizie' })).toHaveAccessibleDescription(
      'Le notizie recenti sugli asset del flusso.',
    );
  });

  it('builds the parameters of the chosen model from the catalog, starting again for a new model', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await userEvent.selectOptions(await screen.findByLabelText('Modello'), MODEL);
    expect(field('limite di lunghezza della risposta')).toHaveAttribute('placeholder', '4096');
    await userEvent.type(field('temperatura'), '0.3');
    await userEvent.selectOptions(field('Modello'), 'openai/gpt-4o');

    expect(screen.queryByLabelText('livello di ragionamento')).toBeNull();
    expect(field('temperatura')).toHaveValue('');
  });

  it('creates the flow with the configuration filled, and shows it among the flows', async () => {
    const { router } = await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow();
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(configurationOf(fakePlatform.flowNamed('alfa'))).toEqual({
      account_id: 'account-principale',
      version: 1,
      assets: ['BTC', 'ETH'],
      cycle_minutes: 30,
      model: {
        name: MODEL,
        parameters: { temperature: '0.5', max_tokens: '4096', reasoning_effort: 'high' },
      },
      sources: [
        { name: 'indicatori', weight: 2, parameters: { lunghezza_serie: 20 } },
        { name: 'sentiment', weight: 5, parameters: {} },
      ],
      instructions: 'prudente',
      risk_limits: {
        max_leverage: 3,
        max_margin_exposure_percent: '10',
        max_value_exposure_percent: null,
      },
      allocated_capital: '300',
      bring_to_minimum: false,
    });
    const row = within(await screen.findByRole('list', { name: 'Flussi' })).getByRole('listitem');
    expect(row).toHaveTextContent('alfa');
    expect(row).toHaveTextContent('fermo');
  });

  it('shows the reason of a refusal beside the field it concerns and creates nothing', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow({ capital: '600' });
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    await waitFor(() =>
      expect(field('Capitale allocato')).toHaveAccessibleDescription(
        'capitale allocato oltre il capitale libero: 500 USDC',
      ),
    );
    expect(field('Capitale allocato')).toHaveAttribute('aria-invalid', 'true');
    expect(fakePlatform.flowsOf('anna')).toEqual([]);
  });

  it('shows beside its field a value the API cannot read', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow();
    await userEvent.clear(field('Capitale allocato'));
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    expect(
      await screen.findByText('Field required', { selector: '#flow-allocated-capital-error' }),
    ).toBeInTheDocument();
  });

  it('shows the refusals of sources and model parameters beside their group', async () => {
    server.use(
      http.post('*/flows', () =>
        HttpResponse.json(
          { detail: 'fonte ripetuta: indicatori', field: 'sources' },
          { status: 422 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow();
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    expect(await screen.findByRole('group', { name: 'Fonti' })).toHaveAccessibleDescription(
      'fonte ripetuta: indicatori',
    );
  });

  it('shows the refusal of a parameter of the model beside the parameters', async () => {
    server.use(
      http.post('*/flows', () =>
        HttpResponse.json(
          {
            detail: 'parametro fuori dai valori ammessi: temperatura',
            field: 'model_parameters',
          },
          { status: 422 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow();
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    expect(
      await screen.findByRole('group', { name: 'Parametri del modello' }),
    ).toHaveAccessibleDescription('parametro fuori dai valori ammessi: temperatura');
  });

  it('shows at the head of the form a refusal that names no field', async () => {
    server.use(
      http.post('*/flows', () =>
        HttpResponse.json({ detail: 'conto non trovato' }, { status: 404 }),
      ),
    );
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow();
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('conto non trovato');
  });

  it('refuses beside its field a number that is not one, without asking the API', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow();
    await userEvent.type(field('Leva massima'), 'x');
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    await waitFor(() =>
      expect(field('Leva massima')).toHaveAccessibleDescription('Inserisci un numero'),
    );
    expect(fakePlatform.flowsOf('anna')).toEqual([]);
  });

  it('tells why the catalogs could not be read', async () => {
    server.use(
      http.get('*/models', () =>
        HttpResponse.json({ detail: 'catalogo dei modelli non disponibile' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: NEW_FLOW });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'catalogo dei modelli non disponibile',
    );
  });

  it('tells why the parameters of a source could not be read', async () => {
    server.use(
      http.get('*/sources/:name', () =>
        HttpResponse.json({ detail: 'fonte non disponibile: indicatori' }, { status: 404 }),
      ),
    );
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await userEvent.click(await screen.findByRole('checkbox', { name: 'indicatori' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('fonte non disponibile: indicatori');
  });
});
