import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';
import { formatInstant } from '@/utils/format-instant';

const ACCOUNTS_PAGE = '/accounts';
const ACCOUNT_ID = 'account-test-1';
const COMPARED_AT = new Date(Date.UTC(2026, 10, 16, 9, 0));

// The account is read first, its reconciliation after: the section has its title at once, its data once read.
const reconciliation = async (): Promise<HTMLElement> => {
  const section = await screen.findByRole('region', { name: 'Riconciliazione del conto test-1' });
  await within(section).findByRole('button', { name: 'Modifica la soglia' });
  return section;
};

const detail = (section: HTMLElement, term: string): HTMLElement =>
  within(section).getByLabelText(term, { selector: 'dd' });

// Whether the account is aligned is said in the header of its box, outside the section (ADR conti-a-riquadri).
const state = (): Promise<HTMLElement> =>
  within(screen.getByRole('article', { name: 'test-1' })).findByRole('status', {
    name: 'Stato della riconciliazione',
  });

const confirmationDialog = (section: HTMLElement): HTMLElement =>
  within(section).getByRole('alertdialog', { name: 'Verifica del conto test-1' });

describe('ReconciliationStatus', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'test-1', 1000);
  });

  it('shows an aligned account with its last comparison and threshold, without the confirmation', async () => {
    fakeReconciliation.compare(ACCOUNT_ID, 1000, 1000.5, COMPARED_AT);
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const section = await reconciliation();
    expect(await state()).toHaveTextContent('Riconciliazione: allineato');
    expect(detail(section, 'Ultimo confronto')).toHaveTextContent(
      formatInstant(COMPARED_AT.toISOString()),
    );
    expect(detail(section, 'Saldo atteso')).toHaveTextContent('1000 USDC');
    expect(detail(section, 'Saldo letto')).toHaveTextContent('1000,5 USDC');
    expect(detail(section, 'Scostamento')).toHaveTextContent('0,05%');
    expect(detail(section, 'Soglia')).toHaveTextContent('1%');
    expect(
      within(section).queryByRole('button', { name: 'Ho verificato' }),
    ).not.toBeInTheDocument();
  });

  it('says when the balance of the account was never compared', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const section = await reconciliation();
    expect(detail(section, 'Ultimo confronto')).toHaveTextContent('nessun confronto ancora');
    expect(within(section).queryByLabelText('Saldo atteso')).not.toBeInTheDocument();
  });

  it('shows an alarm with its balances and offers the confirmation', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, COMPARED_AT);
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const section = await reconciliation();
    expect(await state()).toHaveTextContent('Riconciliazione: allarme');
    expect(detail(section, 'Scostamento')).toHaveTextContent('2%');
    expect(within(section).getByRole('button', { name: 'Ho verificato' })).toBeInTheDocument();
  });

  it('closes the alarm once the user confirms having checked the account', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, COMPARED_AT);
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const section = await reconciliation();
    await userEvent.click(within(section).getByRole('button', { name: 'Ho verificato' }));
    expect(confirmationDialog(section)).toHaveTextContent(
      "Confermi di aver verificato il saldo del conto test-1: l'allarme si chiude",
    );
    await userEvent.click(
      within(confirmationDialog(section)).getByRole('button', { name: 'Conferma la verifica' }),
    );

    expect(
      await within(screen.getByRole('article', { name: 'test-1' })).findByText(
        'Riconciliazione: allineato',
      ),
    ).toBeInTheDocument();
    expect(within(section).queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(fakeReconciliation.statusOf(ACCOUNT_ID).aligned).toBe(true);
  });

  it('keeps the alarm open when the user cancels the confirmation', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, COMPARED_AT);
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const section = await reconciliation();
    await userEvent.click(within(section).getByRole('button', { name: 'Ho verificato' }));
    await userEvent.click(
      within(confirmationDialog(section)).getByRole('button', { name: 'Annulla' }),
    );

    expect(within(section).queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(await state()).toHaveTextContent('Riconciliazione: allarme');
    expect(fakeReconciliation.statusOf(ACCOUNT_ID).aligned).toBe(false);
  });

  it('tells why the API refuses the confirmation', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, COMPARED_AT);
    server.use(
      http.post('*/accounts/:accountId/reconciliation/confirmation', () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Conflict',
            status: 409,
            detail: 'il conto test-1 non ha un allarme di riconciliazione aperto',
          },
          { status: 409, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const section = await reconciliation();
    await userEvent.click(within(section).getByRole('button', { name: 'Ho verificato' }));
    await userEvent.click(
      within(confirmationDialog(section)).getByRole('button', { name: 'Conferma la verifica' }),
    );

    expect(await within(confirmationDialog(section)).findByRole('alert')).toHaveTextContent(
      'il conto test-1 non ha un allarme di riconciliazione aperto',
    );
  });

  it('leads to the alarms of the account', async () => {
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    const section = await reconciliation();
    expect(within(section).getByRole('link', { name: 'Allarmi' })).toHaveAttribute(
      'href',
      '/accounts/account-test-1/alarms',
    );
  });

  it('tells when the reconciliation cannot be read, beside the rest of the account', async () => {
    server.use(
      http.get('*/accounts/:accountId/reconciliation', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Error', status: 500, detail: 'errore interno' },
          { status: 500, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: ACCOUNTS_PAGE });

    expect(await screen.findByText(/errore interno/)).toBeInTheDocument();
    expect(screen.getByRole('article', { name: 'test-1' })).toBeInTheDocument();
  });
});
