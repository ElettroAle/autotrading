import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderInApp, untilEveryRequestIsAnswered } from '@/testing/test-utils';

import { AccountSettings } from './account-settings';

// ADR elenco-dei-conti-e-pagina-del-conto: the tab Impostazioni holds the credentials, then the zone of danger.
describe('AccountSettings', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
  });

  it('shows the credentials of the account, then its removal in the zone of danger', async () => {
    await renderInApp(<AccountSettings accountId="account-principale" />, { account: 'anna' });

    const credentials = await screen.findByRole('region', {
      name: 'Credenziali del conto principale',
    });
    const zone = screen.getByRole('region', { name: 'Zona pericolosa' });
    expect(
      credentials.compareDocumentPosition(zone) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      within(credentials).getByRole('button', { name: 'Sostituisci le credenziali' }),
    ).toBeVisible();
    expect(within(zone).getByRole('button', { name: 'Rimuovi' })).toBeVisible();
  });

  it('shows nothing for an account the user does not have', async () => {
    await renderInApp(<AccountSettings accountId="account-omega" />, { account: 'anna' });

    await untilEveryRequestIsAnswered();
    expect(screen.queryByRole('region')).not.toBeInTheDocument();
  });
});

// R6.3.2: an account of the simulated exchange has no credentials but a virtual balance, which the user resets.
describe('AccountSettings of an account with a virtual balance', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addSimulatedAccount('anna', 'prova', 12);
  });

  const resetTo = async (balance: string) => {
    const region = await screen.findByRole('region', { name: 'Saldo virtuale del conto prova' });
    await userEvent.type(within(region).getByLabelText('Nuovo saldo virtuale (USDC)'), balance);
    await userEvent.click(within(region).getByRole('button', { name: 'Azzera il conto' }));
    return region;
  };

  it('asks no credentials but the balance the account starts again from', async () => {
    await renderInApp(<AccountSettings accountId="account-prova" />, { account: 'anna' });

    expect(
      await screen.findByRole('region', { name: 'Saldo virtuale del conto prova' }),
    ).toBeVisible();
    expect(
      screen.queryByRole('region', { name: 'Credenziali del conto prova' }),
    ).not.toBeInTheDocument();
  });

  it('resets the account once the user confirms what the reset closes', async () => {
    await renderInApp(<AccountSettings accountId="account-prova" />, { account: 'anna' });

    const region = await resetTo('1000');
    const dialog = within(region).getByRole('alertdialog', { name: 'Azzeramento del conto' });
    expect(dialog).toHaveTextContent(
      'Le posizioni aperte del conto si chiudono, gli ordini si cancellano e il conto riparte da 1000 USDC',
    );
    expect(fakePlatform.user('anna').accounts[0]?.balance).toBe(12);
    await userEvent.click(within(dialog).getByRole('button', { name: 'Azzera il conto' }));

    expect(await within(region).findByRole('status')).toHaveTextContent(
      'Conto prova azzerato con saldo 1000 USDC',
    );
    expect(fakePlatform.user('anna').accounts[0]?.balance).toBe(1000);
  });

  it('cancelled, leaves the account as it is', async () => {
    await renderInApp(<AccountSettings accountId="account-prova" />, { account: 'anna' });

    const region = await resetTo('1000');
    await userEvent.click(within(region).getByRole('button', { name: 'Annulla' }));

    expect(within(region).queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(fakePlatform.user('anna').accounts[0]?.balance).toBe(12);
  });

  it('shows the reason the API refuses the balance with', async () => {
    await renderInApp(<AccountSettings accountId="account-prova" />, { account: 'anna' });

    const region = await resetTo('0');
    await userEvent.click(
      within(within(region).getByRole('alertdialog')).getByRole('button', {
        name: 'Azzera il conto',
      }),
    );

    expect(
      await within(region).findByText(/il saldo virtuale deve essere maggiore di zero/),
    ).toBeVisible();
    expect(fakePlatform.user('anna').accounts[0]?.balance).toBe(12);
  });

  it('shows beside the balance the reason the API gives for it', async () => {
    server.use(
      http.put('*/accounts/:accountId/virtual-balance', () =>
        HttpResponse.json(
          {
            detail: 'richiesta non valida',
            errors: [
              { loc: ['body', 'balance'], msg: 'Input should be a valid decimal' },
              { loc: ['body', 'other'], msg: 'Extra inputs are not permitted' },
            ],
          },
          { status: 422 },
        ),
      ),
    );
    await renderInApp(<AccountSettings accountId="account-prova" />, { account: 'anna' });

    const region = await resetTo('mille');
    await userEvent.click(
      within(within(region).getByRole('alertdialog')).getByRole('button', {
        name: 'Azzera il conto',
      }),
    );

    await waitFor(() =>
      expect(
        within(region).getByLabelText('Nuovo saldo virtuale (USDC)'),
      ).toHaveAccessibleDescription('Input should be a valid decimal'),
    );
    expect(fakePlatform.user('anna').accounts[0]?.balance).toBe(12);
  });

  it('asks a balance before resetting', async () => {
    await renderInApp(<AccountSettings accountId="account-prova" />, { account: 'anna' });

    const region = await screen.findByRole('region', { name: 'Saldo virtuale del conto prova' });
    await userEvent.click(within(region).getByRole('button', { name: 'Azzera il conto' }));

    expect(await within(region).findByText('Campo obbligatorio')).toBeVisible();
    expect(within(region).queryByRole('alertdialog')).not.toBeInTheDocument();
  });
});
