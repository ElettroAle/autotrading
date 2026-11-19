import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { FAKE_SYSTEM_PROMPT } from '@/testing/mocks/catalogs';
import { configurationOf, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const EDIT_ALFA = '/flows/flow-alfa/edit';
const SAVE = 'Salva le modifiche';
const RESTORE = 'Ripristina predefinito';

const field = (label: string) => screen.getByLabelText(label, { exact: true });

/** The panel that holds the system prompt, named by its summary. */
const systemPromptPanel = () => screen.findByRole('group', { name: /^System prompt/ });

const openSystemPrompt = async () => {
  await userEvent.click(await screen.findByText('System prompt', { selector: 'summary *' }));
};

const giveAlfa = () =>
  fakePlatform.addConfiguredFlow('anna', 'alfa', {
    account_id: 'account-principale',
    assets: ['BTC'],
    model: { name: 'openrouter/deepseek-chat', parameters: { temperature: '1' } },
    sources: [
      { name: 'indicatori', weight: 2, parameters: { lunghezza_serie: 10 } },
      { name: 'sentiment', weight: 1, parameters: {} },
    ],
    risk_limits: {
      max_leverage: 3,
      max_margin_exposure_percent: '10',
      max_value_exposure_percent: null,
      max_total_margin_exposure_percent: null,
      max_total_value_exposure_percent: null,
    },
    allocated_capital: '300',
  });

describe('EditFlow', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.giveAccountTo('anna', 'principale', 500);
    fakePlatform.saveProviderKey('anna', 'openrouter', '2026-11-14T09:00:00+00:00');
  });

  it('opens from the settings of the flow, behind the gear of its page, with the configuration in force', async () => {
    giveAlfa();
    const { router } = await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    await userEvent.click(await screen.findByRole('link', { name: 'Impostazioni del flusso' }));
    await userEvent.click(await screen.findByRole('link', { name: 'Modifica' }));

    expect(router.state.location.pathname).toBe(EDIT_ALFA);
    expect(await screen.findByText('Versione in vigore: 1')).toBeInTheDocument();
    expect(await screen.findByLabelText('Nome')).toHaveValue('alfa');
    expect(field('Nome')).not.toHaveAttribute('readonly');
    // Out of draft the account never changes: it reads, it is not chosen (ADR assegnazione-della-bozza).
    expect(field('Conto')).toHaveValue('principale');
    expect(field('Conto')).toHaveAttribute('readonly');
    expect(
      within(screen.getByRole('list', { name: 'Asset scelti' })).getByRole('listitem'),
    ).toHaveTextContent('BTC');
    expect(screen.getByRole('checkbox', { name: 'indicatori' })).toBeChecked();
    expect(field('Peso di sentiment')).toHaveValue(1);
    expect(await screen.findByLabelText('lunghezza serie di indicatori')).toHaveValue(10);
    expect(field('temperatura')).toHaveValue('1');
    expect(field('Capitale allocato')).toHaveValue('300');
  });

  it('names by its identifier the account of a flow that the accounts no longer list', async () => {
    fakePlatform.addConfiguredFlow('anna', 'alfa', {});
    fakePlatform.changeFlow('alfa', { accountId: 'account-rimosso' });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    expect(await screen.findByLabelText('Conto')).toHaveValue('account-rimosso');
  });

  it('keeps the model of the flow chosen when its provider has no key, as the current choice', async () => {
    fakePlatform.addConfiguredFlow('anna', 'alfa', {
      account_id: 'account-principale',
      model: { name: 'anthropic/claude-sonnet', parameters: {} },
    });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const models = await screen.findByLabelText('Modello');
    expect(models).toHaveValue('anthropic/claude-sonnet');
    const missing = within(models).getByRole('group', { name: 'anthropic · chiave mancante' });
    expect(within(missing).getByRole('option', { name: 'anthropic/claude-sonnet' })).toBeEnabled();
    expect(within(models).getByRole('option', { name: 'openai/gpt-4o' })).toBeDisabled();
  });

  it('saves a change as the next version, sending only what changed', async () => {
    giveAlfa();
    const sent: unknown[] = [];
    server.events.on('request:start', ({ request }) => {
      if (request.method === 'PATCH') {
        void request
          .clone()
          .json()
          .then((body) => sent.push(body));
      }
    });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const weight = await screen.findByLabelText('Peso di sentiment');
    await userEvent.clear(weight);
    await userEvent.type(weight, '3');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 2'),
    );
    expect(await screen.findByText('Versione in vigore: 2')).toBeInTheDocument();
    expect(sent).toEqual([
      {
        sources: [
          { name: 'indicatori', weight: 2, parameters: { lunghezza_serie: 10 } },
          { name: 'sentiment', weight: 3, parameters: {} },
        ],
      },
    ]);
    server.events.removeAllListeners();
  });

  // ADR pannello-del-system-prompt-chiuso: the system prompt waits in a closed panel, opened to change it.
  it('keeps the system prompt in a closed panel that says the flow follows the default', async () => {
    giveAlfa();
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const panel = await systemPromptPanel();
    expect(panel).not.toHaveAttribute('open');
    expect(within(panel).getByText('System prompt', { selector: 'summary *' })).toBeVisible();
    expect(within(panel).getByText('predefinito')).toBeVisible();
    expect(screen.getByLabelText('System prompt')).not.toBeVisible();
  });

  it('says in the closed panel that the flow follows a system prompt of its own', async () => {
    giveAlfa();
    fakePlatform.flowNamed('alfa').systemPrompt = 'Leva {max_leverage}';
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const panel = await systemPromptPanel();
    expect(panel).not.toHaveAttribute('open');
    expect(within(panel).getByText('personalizzato')).toBeVisible();
    expect(within(panel).queryByText('predefinito')).not.toBeInTheDocument();
  });

  it('shows, once opened, the default system prompt with the placeholders the API declares', async () => {
    giveAlfa();
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    await openSystemPrompt();

    const prompt = screen.getByLabelText('System prompt');
    expect(prompt).toBeVisible();
    expect(prompt).toHaveValue(FAKE_SYSTEM_PROMPT.system_prompt);
    expect(screen.getByText('predefinito')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: RESTORE })).not.toBeInTheDocument();
    for (const placeholder of FAKE_SYSTEM_PROMPT.system_prompt_placeholders) {
      expect(screen.getByText(`{${placeholder.name}}`)).toBeVisible();
      expect(screen.getByText(placeholder.description)).toBeVisible();
    }
  });

  it('saves the system prompt the user writes, then goes back to the default', async () => {
    giveAlfa();
    const sent: unknown[] = [];
    server.events.on('request:start', ({ request }) => {
      if (request.method === 'PATCH') {
        void request
          .clone()
          .json()
          .then((body) => sent.push(body));
      }
    });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    await openSystemPrompt();
    const prompt = screen.getByLabelText('System prompt');
    await userEvent.clear(prompt);
    await userEvent.type(prompt, 'Leva {{max_leverage}');
    expect(screen.getByText('personalizzato')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: SAVE }));
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 2'),
    );
    expect(screen.queryByText('predefinito')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: RESTORE }));
    expect(screen.getByLabelText('System prompt')).toHaveValue(FAKE_SYSTEM_PROMPT.system_prompt);
    expect(screen.getByText('predefinito')).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 3'),
    );
    expect(sent).toEqual([{ system_prompt: 'Leva {max_leverage}' }, { system_prompt: null }]);
    server.events.removeAllListeners();
  });

  it('opens the panel of the system prompt by itself to show why the system prompt is refused', async () => {
    giveAlfa();
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    await openSystemPrompt();
    const prompt = screen.getByLabelText('System prompt');
    await userEvent.clear(prompt);
    await userEvent.type(prompt, 'Leva al massimo {{leverage}');
    await userEvent.click(screen.getByText('System prompt', { selector: 'summary *' }));
    expect(prompt).not.toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(prompt).toHaveAccessibleDescription(
        expect.stringContaining('il segnaposto "leverage" non esiste'),
      ),
    );
    expect(await systemPromptPanel()).toHaveAttribute('open');
    expect(prompt).toBeVisible();
    expect(fakePlatform.flowNamed('alfa').systemPrompt).toBeNull();
  });

  it('keeps the panel of the system prompt open while the user corrects the refused text', async () => {
    giveAlfa();
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    await openSystemPrompt();
    const prompt = screen.getByLabelText('System prompt');
    await userEvent.clear(prompt);
    await userEvent.type(prompt, 'Leva al massimo {{leverage}');
    await userEvent.click(screen.getByText('System prompt', { selector: 'summary *' }));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));
    await waitFor(() => expect(prompt).toHaveAttribute('aria-invalid', 'true'));
    await userEvent.clear(prompt);
    await userEvent.type(prompt, 'Leva al massimo {{max_leverage}');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 2'),
    );
    expect(await systemPromptPanel()).toHaveAttribute('open');
  });

  it('changes the capital through its own request, as one more version', async () => {
    giveAlfa();
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const capital = await screen.findByLabelText('Capitale allocato');
    await userEvent.clear(capital);
    await userEvent.type(capital, '400');
    await userEvent.type(field('Istruzioni'), 'audace');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 3'),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa'))).toMatchObject({
      instructions: 'audace',
      allocated_capital: '400',
      version: 3,
    });
  });

  it('changes the stop loss and take profit defaults as new versions, and removes the take profit', async () => {
    fakePlatform.addConfiguredFlow('anna', 'alfa', { account_id: 'account-principale' });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const stopLoss = await screen.findByLabelText('Stop loss predefinito (%)');
    expect(stopLoss).toHaveValue('5');
    await userEvent.clear(stopLoss);
    await userEvent.type(stopLoss, '3,5');
    await userEvent.type(field('Take profit predefinito (%)'), '8');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 2'),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa'))).toMatchObject({
      default_stop_loss_percent: '3.5',
      default_take_profit_percent: '8',
    });
    await userEvent.clear(field('Take profit predefinito (%)'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 3'),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa'))).toMatchObject({
      default_stop_loss_percent: '3.5',
      default_take_profit_percent: null,
    });
  });

  it('sets the minimum confidence as a new version, refuses one out of range and removes it', async () => {
    fakePlatform.addConfiguredFlow('anna', 'alfa', { account_id: 'account-principale' });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const minimum = await screen.findByLabelText('Confidenza minima (0-100)');
    expect(minimum).toHaveValue('');
    await userEvent.type(minimum, '60');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 2'),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa')).minimum_confidence).toBe(60);
    await userEvent.clear(field('Confidenza minima (0-100)'));
    await userEvent.type(field('Confidenza minima (0-100)'), '101');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(field('Confidenza minima (0-100)')).toHaveAccessibleDescription(
        'la confidenza minima va da 0 a 100',
      ),
    );
    await userEvent.clear(field('Confidenza minima (0-100)'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 3'),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa')).minimum_confidence).toBeNull();
  });

  it('removes an exposure limit the user empties, and refuses emptying both', async () => {
    fakePlatform.addConfiguredFlow('anna', 'alfa', {
      account_id: 'account-principale',
      risk_limits: {
        max_leverage: 3,
        max_margin_exposure_percent: '20',
        max_value_exposure_percent: '40',
        max_total_margin_exposure_percent: null,
        max_total_value_exposure_percent: null,
      },
    });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    await userEvent.clear(await screen.findByLabelText('Esposizione massima del valore (%)'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 2'),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa')).risk_limits).toEqual({
      max_leverage: 3,
      max_margin_exposure_percent: '20',
      max_value_exposure_percent: null,
      max_total_margin_exposure_percent: null,
      max_total_value_exposure_percent: null,
    });
    await userEvent.clear(field('Esposizione massima del margine (%)'));
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(field('Esposizione massima del margine (%)')).toHaveAccessibleDescription(
        'almeno un limite di esposizione è obbligatorio',
      ),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa')).version).toBe(2);
  });

  // ADR esposizione-complessiva-nel-controllo-del-rischio: the overall limits beside the limits per operation.
  it('changes and removes an overall exposure limit, as a new version', async () => {
    fakePlatform.addConfiguredFlow('anna', 'alfa', {
      account_id: 'account-principale',
      risk_limits: {
        max_leverage: 3,
        max_margin_exposure_percent: '10',
        max_value_exposure_percent: null,
        max_total_margin_exposure_percent: '30',
        max_total_value_exposure_percent: null,
      },
    });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const totalMargin = await screen.findByLabelText(
      'Esposizione complessiva massima del margine (%)',
    );
    expect(totalMargin).toHaveValue('30');
    await userEvent.clear(totalMargin);
    await userEvent.type(field('Esposizione complessiva massima del valore (%)'), '150,5');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 2'),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa')).risk_limits).toMatchObject({
      max_total_margin_exposure_percent: null,
      max_total_value_exposure_percent: '150.5',
    });
  });

  it('renames the flow without a new version (ADR nome-del-flusso-modificabile)', async () => {
    giveAlfa();
    const sent: unknown[] = [];
    server.events.on('request:start', ({ request }) => {
      if (request.method === 'PATCH') {
        void request
          .clone()
          .json()
          .then((body) => sent.push(body));
      }
    });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const name = await screen.findByLabelText('Nome');
    await userEvent.clear(name);
    await userEvent.type(name, 'gamma');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate'));
    expect(await screen.findByRole('heading', { level: 2, name: 'gamma' })).toBeInTheDocument();
    expect(screen.getByText('Versione in vigore: 1')).toBeInTheDocument();
    expect(sent).toEqual([{ name: 'gamma' }]);
    server.events.removeAllListeners();
  });

  it('shows beside the name that another flow has it', async () => {
    giveAlfa();
    fakePlatform.addConfiguredFlow('anna', 'beta', { account_id: 'account-principale' });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const name = await screen.findByLabelText('Nome');
    await userEvent.clear(name);
    await userEvent.type(name, 'beta');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(field('Nome')).toHaveAccessibleDescription('nome già usato da un altro flusso'),
    );
  });

  it('preselects the account of a copy and saves account, capital and assets of the draft with the configuration', async () => {
    giveAlfa();
    fakePlatform.giveAccountTo('anna', 'secondario', 1000);
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    const sent: { method: string; body: unknown }[] = [];
    server.events.on('request:start', ({ request }) => {
      if (request.method === 'PATCH' || request.method === 'PUT') {
        void request
          .clone()
          .json()
          .then((body) => sent.push({ method: request.method, body }));
      }
    });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)/edit' });

    const account = await screen.findByLabelText('Conto');
    expect(account).toHaveValue('account-principale');
    expect(account).not.toHaveAttribute('readonly');
    await userEvent.selectOptions(account, 'secondario');
    const capital = field('Capitale allocato');
    await userEvent.clear(capital);
    await userEvent.type(capital, '200');
    await userEvent.type(field('Asset'), 'ETH');
    await userEvent.click(
      within(screen.getByRole('list', { name: 'Asset negoziabili' })).getByRole('button', {
        name: 'ETH',
      }),
    );
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Modifiche salvate: versione 2'),
    );
    expect(sent).toEqual([
      {
        method: 'PATCH',
        body: { account_id: 'account-secondario', assets: ['ETH'], allocated_capital: '200' },
      },
    ]);
    expect(fakePlatform.flowNamed('alfa (copia)')).toMatchObject({
      accountId: 'account-secondario',
      allocatedCapital: 200,
      assets: ['ETH'],
    });
    server.events.removeAllListeners();
  });

  it('shows beside the capital of a draft that it exceeds the free capital', async () => {
    giveAlfa();
    fakePlatform.duplicate(fakePlatform.user('anna'), 'flow-alfa');
    await renderApp({ account: 'anna', url: '/flows/flow-alfa%20(copia)/edit' });

    const capital = await screen.findByLabelText('Capitale allocato');
    await userEvent.clear(capital);
    await userEvent.type(capital, '900');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(field('Capitale allocato')).toHaveAccessibleDescription(
        'capitale allocato oltre il capitale libero: 200 USDC',
      ),
    );
  });

  it('says there is nothing to save when nothing changed', async () => {
    giveAlfa();
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    await userEvent.click(await screen.findByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Nessuna modifica da salvare'),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa')).version).toBe(1);
  });

  it('shows beside the assets that one is already used by another flow of the account', async () => {
    giveAlfa();
    fakePlatform.addConfiguredFlow('anna', 'beta', {
      account_id: 'account-principale',
      assets: ['ETH'],
    });
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    await userEvent.type(await screen.findByLabelText('Asset'), 'ETH');
    await userEvent.click(
      within(screen.getByRole('list', { name: 'Asset negoziabili' })).getByRole('button', {
        name: 'ETH',
      }),
    );
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(field('Asset')).toHaveAccessibleDescription(
        'asset già assegnati al flusso beta sullo stesso conto: ETH',
      ),
    );
    expect(configurationOf(fakePlatform.flowNamed('alfa')).version).toBe(1);
  });

  it('shows beside the capital why the new capital is refused', async () => {
    giveAlfa();
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    const capital = await screen.findByLabelText('Capitale allocato');
    await userEvent.clear(capital);
    await userEvent.type(capital, '900');
    await userEvent.click(screen.getByRole('button', { name: SAVE }));

    await waitFor(() =>
      expect(field('Capitale allocato')).toHaveAccessibleDescription(
        'capitale allocato oltre il capitale disponibile: 500 USDC',
      ),
    );
  });

  it('says a flow outside the tenant of the user does not exist', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-omega/edit' });

    expect(await screen.findByText('Flusso non trovato.')).toBeInTheDocument();
  });

  it('tells why the flow could not be read', async () => {
    server.use(
      http.get('*/flows', () => HttpResponse.json({ detail: 'errore interno' }, { status: 500 })),
    );
    await renderApp({ account: 'anna', url: EDIT_ALFA });

    expect(await screen.findByRole('alert')).toHaveTextContent('errore interno');
  });
});
