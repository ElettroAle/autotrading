import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { configurationOf, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const EDIT_ALFA = '/flows/flow-alfa/edit';
const SAVE = 'Salva le modifiche';

const field = (label: string) => screen.getByLabelText(label, { exact: true });

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
    },
    allocated_capital: '300',
  });

describe('EditFlow', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.giveAccountTo('anna', 'principale', 500);
    fakePlatform.saveProviderKey('anna', 'openrouter', '2026-11-14T09:00:00+00:00');
  });

  it('opens from the page of the flow with the configuration in force', async () => {
    giveAlfa();
    const { router } = await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    await userEvent.click(await screen.findByRole('link', { name: 'Modifica la configurazione' }));

    expect(router.state.location.pathname).toBe(EDIT_ALFA);
    expect(await screen.findByText('Versione in vigore: 1')).toBeInTheDocument();
    expect(await screen.findByLabelText('Nome')).toHaveValue('alfa');
    expect(field('Nome')).toHaveAttribute('readonly');
    expect(field('Conto')).toHaveValue('account-principale');
    expect(field('Asset')).toHaveValue('BTC');
    expect(screen.getByRole('checkbox', { name: 'indicatori' })).toBeChecked();
    expect(field('Peso di sentiment')).toHaveValue(1);
    expect(await screen.findByLabelText('lunghezza serie di indicatori')).toHaveValue(10);
    expect(field('temperatura')).toHaveValue('1');
    expect(field('Capitale allocato')).toHaveValue('300');
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

    const assets = await screen.findByLabelText('Asset');
    await userEvent.type(assets, ', ETH');
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
