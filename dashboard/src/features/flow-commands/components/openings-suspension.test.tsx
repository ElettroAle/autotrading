import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http } from 'msw';

import { fakePlatform, type FakeFlow } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { problem } from '@/testing/mocks/responses';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const FLOW_PAGE = '/flows/flow-alfa';
const REASON = 'perdita giornaliera 6% oltre il 5%';
const RESUME = 'Riprendi le aperture';
const CONFIRMATION = 'Conferma della ripresa delle aperture';

const suspend = (flow: FakeFlow): void => {
  flow.openingsSuspension = { reason: REASON, suspendedAt: '2026-11-14T09:00:00Z' };
};

// ADR perdita-massima-nella-dashboard: the suspension comes from the API, whatever its cause; the command resumes it
// after a confirmation, only when the API says the user may.
describe('OpeningsSuspension', () => {
  let alfa: FakeFlow;

  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    alfa = fakePlatform.addFlow('anna', 'alfa');
  });

  it('shows on the flow that its openings are suspended and why, with the command that resumes them', async () => {
    suspend(alfa);
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    const suspension = await screen.findByRole('region', { name: 'Aperture sospese' });
    expect(within(suspension).getByRole('status')).toHaveTextContent(`aperture sospese: ${REASON}`);
    expect(within(suspension).getByRole('button', { name: RESUME })).toBeEnabled();
  });

  it('shows nothing for a flow whose openings are not suspended', async () => {
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await screen.findByRole('group', { name: 'Comandi del flusso' });
    expect(screen.queryByRole('region', { name: 'Aperture sospese' })).not.toBeInTheDocument();
  });

  it('resumes the openings once the user confirms, and the notice goes away', async () => {
    suspend(alfa);
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await userEvent.click(await screen.findByRole('button', { name: RESUME }));
    const dialog = screen.getByRole('alertdialog', { name: CONFIRMATION });
    await userEvent.click(within(dialog).getByRole('button', { name: 'Conferma la ripresa' }));

    expect(await screen.findByRole('group', { name: 'Comandi del flusso' })).toBeInTheDocument();
    await expect.poll(() => screen.queryByRole('region', { name: 'Aperture sospese' })).toBeNull();
    expect(alfa.openingsSuspension).toBeNull();
  });

  it('keeps the openings suspended when the user cancels', async () => {
    suspend(alfa);
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await userEvent.click(await screen.findByRole('button', { name: RESUME }));
    await userEvent.click(screen.getByRole('button', { name: 'Annulla' }));

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: RESUME })).toBeInTheDocument();
    expect(alfa.openingsSuspension).not.toBeNull();
  });

  it('tells the reason of a resume the API refuses', async () => {
    suspend(alfa);
    server.use(
      http.post('*/flows/:flowId/openings/resume', () =>
        problem(409, 'Conflict', 'le aperture di alfa non sono sospese'),
      ),
    );
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    await userEvent.click(await screen.findByRole('button', { name: RESUME }));
    await userEvent.click(screen.getByRole('button', { name: 'Conferma la ripresa' }));

    expect(await screen.findByText(/le aperture di alfa non sono sospese/)).toBeInTheDocument();
  });

  it('shows the suspension of an alarm of reconciliation with the same notice, without the resume', async () => {
    fakeReconciliation.openAlarm(fakePlatform.accountOfFlow('alfa').id, 1000, 980, new Date());
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    const suspension = await screen.findByRole('region', { name: 'Aperture sospese' });
    expect(within(suspension).getByRole('status')).toHaveTextContent(
      'aperture sospese: allarme di riconciliazione sul conto principale',
    );
    expect(within(suspension).queryByRole('button', { name: RESUME })).not.toBeInTheDocument();
  });

  it('shows the maximum loss first when an alarm is open too, since the user can resume it', async () => {
    suspend(alfa);
    fakeReconciliation.openAlarm(fakePlatform.accountOfFlow('alfa').id, 1000, 980, new Date());
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    const suspension = await screen.findByRole('region', { name: 'Aperture sospese' });
    expect(within(suspension).getByRole('status')).toHaveTextContent(`aperture sospese: ${REASON}`);
    expect(within(suspension).getByRole('button', { name: RESUME })).toBeEnabled();
  });
});
