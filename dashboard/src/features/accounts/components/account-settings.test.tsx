import { screen, within } from '@testing-library/react';

import { fakePlatform } from '@/testing/mocks/platform';
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
