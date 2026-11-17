import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { DESTRUCTIVE_COMMAND } from '@/components/ui/commands';
import { fakePlatform, type FakeFlow } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

// ADR impostazioni-del-flusso-dall-ingranaggio: Archivia stays at the bottom of the settings of the flow, with the
// confirmation of the archiving (ADR 0132).
const SETTINGS = '/flows/flow-alfa/settings';
const ARCHIVE_CONFIRMATION = "Conferma dell'archiviazione";

const click = async (name: string): Promise<void> => {
  await userEvent.click(await screen.findByRole('button', { name }));
};

describe('ArchiveFlowCommand', () => {
  let alfa: FakeFlow;

  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    alfa = fakePlatform.addFlow('anna', 'alfa', { status: 'fermo' });
  });

  it('shows Archivia as destructive and without an icon', async () => {
    await renderApp({ account: 'anna', url: SETTINGS });

    const button = await screen.findByRole('button', { name: 'Archivia' });
    expect(button).toHaveAttribute('class', DESTRUCTIVE_COMMAND);
    expect(within(button).queryByRole('img', { hidden: true })).toBeNull();
  });

  it('asks to confirm the archiving, saying it is final and leaves no position to manage', async () => {
    await renderApp({ account: 'anna', url: SETTINGS });

    await click('Archivia');

    expect(screen.getByRole('alertdialog', { name: ARCHIVE_CONFIRMATION })).toHaveTextContent(
      "L'archiviazione è definitiva: il flusso non si potrà più avviare né modificare. Un flusso fermo non ha posizioni aperte da gestire e il suo capitale allocato torna libero sul conto.",
    );
    expect(screen.queryByRole('button', { name: 'Archivia' })).toBeNull();
    expect(fakePlatform.flowNamed('alfa').status).toBe('fermo');
  });

  it('keeps the flow when the user cancels the archiving', async () => {
    await renderApp({ account: 'anna', url: SETTINGS });

    await click('Archivia');
    await click('Annulla');

    expect(screen.queryByRole('alertdialog', { name: ARCHIVE_CONFIRMATION })).toBeNull();
    expect(await screen.findByRole('button', { name: 'Archivia' })).toBeVisible();
    expect(fakePlatform.flowNamed('alfa').status).toBe('fermo');
  });

  it('archives the flow once the user confirms and goes back to the flows in use', async () => {
    fakePlatform.addFlow('anna', 'beta');
    const { router } = await renderApp({ account: 'anna', url: SETTINGS });

    await click('Archivia');
    await click("Conferma l'archiviazione");

    expect(await screen.findByRole('link', { name: 'beta' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
    expect(screen.queryByRole('link', { name: 'alfa' })).toBeNull();
    expect(fakePlatform.flowNamed('alfa').status).toBe('archiviato');
  });

  it('archives a draft too', async () => {
    alfa.status = 'bozza';
    const { router } = await renderApp({ account: 'anna', url: SETTINGS });

    await click('Archivia');
    await click("Conferma l'archiviazione");

    await vi.waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(fakePlatform.flowNamed('alfa').status).toBe('archiviato');
  });

  it('shows the reason the API gives for an archiving it refuses and closes the confirmation', async () => {
    server.use(
      http.post('*/flows/:flowId/archive', () =>
        HttpResponse.json({ detail: 'si archivia solo un flusso fermo' }, { status: 409 }),
      ),
    );
    await renderApp({ account: 'anna', url: SETTINGS });

    await click('Archivia');
    await click("Conferma l'archiviazione");

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Archiviazione non riuscita: si archivia solo un flusso fermo',
    );
    expect(screen.queryByRole('alertdialog', { name: ARCHIVE_CONFIRMATION })).toBeNull();
  });
});
