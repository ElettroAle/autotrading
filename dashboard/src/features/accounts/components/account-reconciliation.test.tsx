import { screen, within } from '@testing-library/react';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderInApp, untilEveryRequestIsAnswered } from '@/testing/test-utils';

import { AccountReconciliation } from './account-reconciliation';

// ADR elenco-dei-conti-e-pagina-del-conto: the tab Riconciliazione holds the reconciliation, then the movements.
describe('AccountReconciliation', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
  });

  it('shows the reconciliation of the account, then the movements no flow explains', async () => {
    await renderInApp(<AccountReconciliation accountId="account-principale" />, {
      account: 'anna',
    });

    const reconciliation = await screen.findByRole('region', {
      name: 'Riconciliazione del conto principale',
    });
    const movements = screen.getByRole('region', {
      name: 'Movimenti non spiegati del conto principale',
    });
    expect(
      reconciliation.compareDocumentPosition(movements) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(await within(reconciliation).findByRole('link', { name: 'Allarmi' })).toBeVisible();
  });

  it('shows nothing for an account the user does not have', async () => {
    await renderInApp(<AccountReconciliation accountId="account-omega" />, { account: 'anna' });

    await untilEveryRequestIsAnswered();
    expect(screen.queryByRole('region')).not.toBeInTheDocument();
  });
});
