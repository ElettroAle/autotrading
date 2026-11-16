import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http } from 'msw';

import { fakePlatform, type FakeFlow } from '@/testing/mocks/platform';
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

// ADR perdita-massima-nella-dashboard: the suspension comes from the API, the command resumes it after a confirmation.
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

  it('tells why the suspension could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/openings', () =>
        problem(500, 'Internal Server Error', 'database non raggiungibile'),
      ),
    );
    await renderApp({ account: 'anna', url: FLOW_PAGE });

    expect(await screen.findByText(/database non raggiungibile/)).toBeInTheDocument();
  });
});
