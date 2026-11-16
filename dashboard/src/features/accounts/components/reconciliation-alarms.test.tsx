import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';
import { formatInstant } from '@/utils/format-instant';

const ACCOUNT_ID = 'account-test-1';
const ALARMS_PAGE = `/accounts/${ACCOUNT_ID}/alarms`;
const YESTERDAY = new Date(Date.UTC(2026, 10, 15, 9, 0));
const CONFIRMED = new Date(Date.UTC(2026, 10, 15, 10, 30));
const TODAY = new Date(Date.UTC(2026, 10, 16, 9, 0));

const rows = async (): Promise<HTMLElement[]> => {
  const table = await screen.findByRole('table', { name: 'Allarmi di riconciliazione' });
  return within(table).getAllByRole('row').slice(1);
};

describe('ReconciliationAlarms', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'test-1', 1000);
  });

  it('titles the page with the name of the account', async () => {
    await renderApp({ account: 'anna', url: ALARMS_PAGE });

    // The title waits for the accounts, read beside the alarms.
    await screen.findByText('Nessun allarme di riconciliazione.');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Allarmi del conto test-1' }),
    ).toBeInTheDocument();
  });

  it('lists the alarms from the most recent, open and closed, with the instant of the confirmation', async () => {
    fakeReconciliation.closedAlarm(ACCOUNT_ID, YESTERDAY, CONFIRMED);
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, TODAY);
    await renderApp({ account: 'anna', url: ALARMS_PAGE });

    const [open, closed] = await rows();
    expect(open).toHaveTextContent(formatInstant(TODAY.toISOString()));
    expect(open).toHaveTextContent('aperto');
    expect(open).toHaveTextContent('—');
    expect(open).toHaveTextContent('2%');
    expect(closed).toHaveTextContent(formatInstant(YESTERDAY.toISOString()));
    expect(closed).toHaveTextContent('chiuso');
    expect(closed).toHaveTextContent(formatInstant(CONFIRMED.toISOString()));
  });

  it('says when the account never raised an alarm', async () => {
    await renderApp({ account: 'anna', url: ALARMS_PAGE });

    expect(await screen.findByText('Nessun allarme di riconciliazione.')).toBeInTheDocument();
  });

  it('tells when the alarms cannot be read', async () => {
    server.use(
      http.get('*/accounts/:accountId/reconciliation/alarms', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Error', status: 500, detail: 'errore interno' },
          { status: 500, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: ALARMS_PAGE });

    expect(await screen.findByText(/errore interno/)).toBeInTheDocument();
  });

  it('titles the page with the subject alone for an account the user does not have', async () => {
    await renderApp({ account: 'anna', url: '/accounts/account-altrui/alarms' });

    expect(await screen.findByText(/non trovato/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/^Allarmi$/);
  });
});
