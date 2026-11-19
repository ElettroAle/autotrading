import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { FAKE_SYSTEM_PROMPT } from '@/testing/mocks/catalogs';
import { configurationOf, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const NEW_FLOW = '/flows/new';
const MODEL = 'openrouter/deepseek-chat';

const field = (label: string) => screen.getByLabelText(label, { exact: true });

/** Chooses an asset as a user does: typing part of its name and picking it among the tradable ones. */
const chooseAsset = async (search: string, asset: string) => {
  await userEvent.type(field('Asset'), search);
  await userEvent.click(
    within(screen.getByRole('list', { name: 'Asset negoziabili' })).getByRole('button', {
      name: asset,
    }),
  );
};

const fillValidFlow = async ({ capital = '300' }: { capital?: string } = {}) => {
  await userEvent.type(await screen.findByLabelText('Nome'), 'alfa');
  await userEvent.selectOptions(field('Conto'), 'principale');
  await chooseAsset('bt', 'BTC');
  await chooseAsset('eth', 'ETH');
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
    fakePlatform.saveProviderKey('anna', 'openrouter', '2026-11-14T09:00:00+00:00');
  });

  it('opens from the list of the flows', async () => {
    const { router } = await renderApp({ account: 'anna' });

    await userEvent.click(await screen.findByRole('link', { name: 'Nuovo flusso' }));

    expect(router.state.location.pathname).toBe(NEW_FLOW);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Nuovo flusso');
  });

  // ADR pannello-del-system-prompt-chiuso: a new flow follows the default, in a closed panel.
  it('keeps the system prompt of a new flow in a closed panel that says it follows the default', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    const summary = await screen.findByText('System prompt', { selector: 'summary *' });
    const panel = screen.getByRole('group', { name: /^System prompt/ });
    expect(panel).not.toHaveAttribute('open');
    expect(within(panel).getByText('predefinito')).toBeVisible();
    expect(screen.getByLabelText('System prompt')).not.toBeVisible();

    await userEvent.click(summary);

    expect(screen.getByLabelText('System prompt')).toHaveValue(FAKE_SYSTEM_PROMPT.system_prompt);
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

  it('sends nothing while the API cannot list the assets', async () => {
    server.use(
      http.get('*/assets', () =>
        HttpResponse.json(
          { detail: 'exchange non raggiungibile, riprovare' },
          { status: 503, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: NEW_FLOW });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossibile leggere gli asset negoziabili: exchange non raggiungibile, riprovare',
    );
    expect(field('Asset')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Crea il flusso' })).toBeDisabled();
  });

  it('groups the models by provider, naming whether the key of each provider is registered', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    const models = within(await screen.findByLabelText('Modello'));
    const groups = models.getAllByRole('group').map((group) => ({
      label: group.getAttribute('label'),
      models: within(group)
        .getAllByRole('option')
        .map((option) => option.textContent),
    }));
    expect(groups).toEqual([
      {
        label: 'openrouter · chiave registrata',
        models: [
          MODEL,
          'openrouter/nvidia/llama-3.1-nemotron-ultra-253b-v1-instruct-extended-reasoning-preview',
        ],
      },
      { label: 'openai · chiave mancante', models: ['openai/gpt-4o'] },
      { label: 'anthropic · chiave mancante', models: ['anthropic/claude-sonnet'] },
    ]);
  });

  it('shows but does not let choose a model whose provider misses the key, pointing to the keys', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    const models = within(await screen.findByLabelText('Modello'));
    expect(models.getByRole('option', { name: 'anthropic/claude-sonnet' })).toBeDisabled();
    expect(models.getByRole('option', { name: MODEL })).toBeEnabled();
    expect(screen.getByRole('link', { name: 'Chiavi dei fornitori IA' })).toHaveAttribute(
      'href',
      '/provider-keys',
    );
  });

  it('points to the keys only while a provider misses its key', async () => {
    fakePlatform.saveProviderKey('anna', 'openai', '2026-11-14T09:00:00+00:00');
    fakePlatform.saveProviderKey('anna', 'anthropic', '2026-11-14T09:00:00+00:00');
    await renderApp({ account: 'anna', url: NEW_FLOW });

    const models = within(await screen.findByLabelText('Modello'));
    expect(models.getByRole('option', { name: 'anthropic/claude-sonnet' })).toBeEnabled();
    expect(screen.queryByRole('link', { name: 'Chiavi dei fornitori IA' })).toBeNull();
  });

  it('builds the parameters of the chosen model from the catalog, starting again for a new model', async () => {
    fakePlatform.saveProviderKey('anna', 'openai', '2026-11-14T09:00:00+00:00');
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
        max_total_margin_exposure_percent: null,
        max_total_value_exposure_percent: null,
      },
      default_stop_loss_percent: '5',
      default_take_profit_percent: null,
      minimum_confidence: null,
      allocated_capital: '300',
      bring_to_minimum: false,
      system_prompt: FAKE_SYSTEM_PROMPT.system_prompt,
      system_prompt_is_default: true,
      system_prompt_placeholders: FAKE_SYSTEM_PROMPT.system_prompt_placeholders,
      max_consecutive_failures: null,
      max_daily_loss_percent: null,
      max_drawdown_percent: null,
      openings_resume: 'manual',
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

  it('saves the maximum of consecutive failed cycles, refusing it beside its field out of range', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow();
    await userEvent.type(field('Massimo di cicli falliti consecutivi'), '101');
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    await waitFor(() =>
      expect(field('Massimo di cicli falliti consecutivi')).toHaveAccessibleDescription(
        'il massimo di cicli falliti consecutivi va da 1 a 100',
      ),
    );
    expect(fakePlatform.flowsOf('anna')).toEqual([]);

    await userEvent.clear(field('Massimo di cicli falliti consecutivi'));
    await userEvent.type(field('Massimo di cicli falliti consecutivi'), '3');
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    await waitFor(() =>
      expect(configurationOf(fakePlatform.flowNamed('alfa')).max_consecutive_failures).toBe(3),
    );
  });

  // ADR perdita-massima-nella-dashboard: the maximum losses and the resume among the risk limits, the range as the API's.
  it('saves the maximum losses and the resume, refusing a loss out of range beside its field', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow();
    await userEvent.type(field('Perdita giornaliera massima (%)'), '101');
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    expect(await screen.findByText('la perdita massima va da 0,1 a 100')).toBeInTheDocument();
    expect(field('Perdita giornaliera massima (%)')).toHaveAttribute('aria-invalid', 'true');
    expect(fakePlatform.flowsOf('anna')).toEqual([]);

    await userEvent.clear(field('Perdita giornaliera massima (%)'));
    await userEvent.type(field('Perdita giornaliera massima (%)'), '5');
    await userEvent.type(field('Perdita massima dal picco (%)'), '12,5');
    await userEvent.selectOptions(field('Ripresa delle aperture'), 'il giorno dopo');
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    await waitFor(() =>
      expect(configurationOf(fakePlatform.flowNamed('alfa'))).toMatchObject({
        max_daily_loss_percent: '5',
        max_drawdown_percent: '12.5',
        openings_resume: 'next_day',
      }),
    );
  });

  // ADR esposizione-complessiva-nel-controllo-del-rischio: the overall limits beside the limits per operation.
  it('saves the overall exposure limits, refusing one out of range beside its field', async () => {
    await renderApp({ account: 'anna', url: NEW_FLOW });

    await fillValidFlow();
    await userEvent.type(field('Esposizione complessiva massima del margine (%)'), '1001');
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    await waitFor(() =>
      expect(field('Esposizione complessiva massima del margine (%)')).toHaveAccessibleDescription(
        "l'esposizione complessiva massima va da 0,1 a 1000",
      ),
    );
    expect(fakePlatform.flowsOf('anna')).toEqual([]);

    await userEvent.clear(field('Esposizione complessiva massima del margine (%)'));
    await userEvent.type(field('Esposizione complessiva massima del margine (%)'), '30');
    await userEvent.type(field('Esposizione complessiva massima del valore (%)'), '0,5');
    await userEvent.click(screen.getByRole('button', { name: 'Crea il flusso' }));

    await waitFor(() =>
      expect(configurationOf(fakePlatform.flowNamed('alfa')).risk_limits).toMatchObject({
        max_total_margin_exposure_percent: '30',
        max_total_value_exposure_percent: '0.5',
      }),
    );
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
