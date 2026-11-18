import { screen } from '@testing-library/react';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderInApp } from '@/testing/test-utils';

import { useAccounts } from '../api/get-accounts';

import { useAccount } from './use-account';

const Probe = ({ accountId }: { readonly accountId: string }) => {
  const read = useAccounts().data !== undefined;
  return (
    <>
      <output aria-label="conto">{useAccount(accountId)?.name ?? 'nessuno'}</output>
      {read && <p>conti letti</p>}
    </>
  );
};

describe('useAccount', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
    fakePlatform.giveAccountTo('bruno', 'altrui', 50);
  });

  it('gives the account of the user with the id, once read', async () => {
    await renderInApp(<Probe accountId="account-principale" />, { account: 'anna' });

    expect(await screen.findByText('principale')).toBe(screen.getByLabelText('conto'));
  });

  it('gives nothing for an account the user does not have', async () => {
    await renderInApp(<Probe accountId="account-altrui" />, { account: 'anna' });

    await screen.findByText('conti letti');
    expect(screen.getByLabelText('conto')).toHaveTextContent('nessuno');
  });
});
