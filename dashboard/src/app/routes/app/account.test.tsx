import { act, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { anOpenPosition } from '@/testing/mocks/positions';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { partsAfter, renderApp } from '@/testing/test-utils';

const ACCOUNT_ID = 'account-principale';
const ACCOUNT_PAGE = `/accounts/${ACCOUNT_ID}`;
const TABS = ['Panoramica', 'Riconciliazione', 'Capitale', 'Impostazioni'];
const EMERGENCY_ZONE = 'Zona di emergenza';

const tabs = (): Promise<HTMLElement> =>
  screen.findByRole('navigation', { name: 'Schede del conto' });

const tab = async (name: string): Promise<HTMLElement> =>
  within(await tabs()).getByRole('link', { name });

const head = (): Promise<HTMLElement> => screen.findByRole('region', { name: 'principale' });

// ADR elenco-dei-conti-e-pagina-del-conto: the page of an account, with its head and four tabs, as the page of a flow.
describe('AccountRoute', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
  });

  it('titles the page with the name of the account and heads it with its network and reconciliation', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, new Date());
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

    expect(
      await screen.findByRole('heading', { level: 1, name: 'principale' }),
    ).toBeInTheDocument();
    const accountHead = await head();
    expect(within(accountHead).getByText('TEST · testnet')).toBeInTheDocument();
    expect(
      await within(accountHead).findByRole('status', { name: 'Stato della riconciliazione' }),
    ).toHaveTextContent('Riconciliazione: allarme');
  });

  it('titles the page «Conto» while no account of the user has the id', async () => {
    await renderApp({ account: 'anna', url: '/accounts/account-omega' });

    await screen.findByText('Conto non trovato.');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/^Conto$/);
  });

  it('offers the four tabs, on the overview first', async () => {
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

    const links = within(await tabs()).getAllByRole('link');
    expect(links.map((link) => link.textContent)).toEqual(TABS);
    expect(await tab('Panoramica')).toHaveAttribute('aria-current', 'page');
    expect(
      await screen.findByRole('region', { name: 'Panoramica del conto principale' }),
    ).toBeInTheDocument();
  });

  it.each([
    ['Riconciliazione', `${ACCOUNT_PAGE}/reconciliation`, 'Riconciliazione del conto principale'],
    ['Impostazioni', `${ACCOUNT_PAGE}/settings`, 'Credenziali del conto principale'],
  ])('opens the tab %s at its own address', async (name, path, region) => {
    const { router } = await renderApp({ account: 'anna', url: ACCOUNT_PAGE });

    await userEvent.click(await tab(name));

    expect(router.state.location.pathname).toBe(path);
    expect(await tab(name)).toHaveAttribute('aria-current', 'page');
    expect(await screen.findByRole('region', { name: region })).toBeInTheDocument();
  });

  it('shows the history of the capital in the tab Capitale, under its period', async () => {
    await renderApp({ account: 'anna', url: `${ACCOUNT_PAGE}/capital` });

    expect(await tab('Capitale')).toHaveAttribute('aria-current', 'page');
    expect(await screen.findByText(/^Nessuna variazione/)).toBeInTheDocument();
    expect(screen.getByLabelText('Periodo', { exact: true })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'principale' })).toBeInTheDocument();
  });

  it('shows the movements no flow explains in the tab Riconciliazione, with the link to the alerts', async () => {
    await renderApp({ account: 'anna', url: `${ACCOUNT_PAGE}/reconciliation` });

    expect(
      await screen.findByRole('region', { name: 'Movimenti non spiegati del conto principale' }),
    ).toBeInTheDocument();
    const reconciliation = screen.getByRole('region', {
      name: 'Riconciliazione del conto principale',
    });
    expect(await within(reconciliation).findByRole('link', { name: 'Allarmi' })).toHaveAttribute(
      'href',
      `/alerts?resource_id=${ACCOUNT_ID}&state=all`,
    );
  });

  it('says when the account does not exist', async () => {
    await renderApp({ account: 'anna', url: '/accounts/account-omega' });

    expect(await screen.findByText('Conto non trovato.')).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Schede del conto' })).toBeNull();
    expect(screen.queryByRole('region', { name: EMERGENCY_ZONE })).toBeNull();
  });

  // ADR zona-di-emergenza-nella-pagina-del-conto: the emergency closing of the account alone, at the bottom of its page,
  // whichever tab is open.
  it.each([
    ['Panoramica', ACCOUNT_PAGE],
    ['Riconciliazione', `${ACCOUNT_PAGE}/reconciliation`],
    ['Capitale', `${ACCOUNT_PAGE}/capital`],
    ['Impostazioni', `${ACCOUNT_PAGE}/settings`],
  ])(
    'keeps the emergency closing of the account alone at the bottom of the tab %s',
    async (name, url) => {
      await renderApp({ account: 'anna', url });
      expect(await tab(name)).toHaveAttribute('aria-current', 'page');

      const zone = await screen.findByRole('region', { name: EMERGENCY_ZONE });
      expect(
        within(zone)
          .getAllByRole('button')
          .map((button) => button.textContent),
      ).toEqual(['Chiusura di emergenza del conto principale']);
      expect(partsAfter(zone)).toEqual([]);
    },
  );

  it('asks to confirm the emergency closing of the account, closing nothing before', async () => {
    fakePlatform.addFlow('anna', 'alfa', { assets: ['BTC'] });
    fakePlatform.holdPositions('alfa', [anOpenPosition({ asset: 'BTC' })]);
    await renderApp({ account: 'anna', url: ACCOUNT_PAGE });
    const zone = await screen.findByRole('region', { name: EMERGENCY_ZONE });

    await userEvent.click(
      within(zone).getByRole('button', { name: 'Chiusura di emergenza del conto principale' }),
    );

    expect(
      await screen.findByRole('alertdialog', { name: 'Conferma della chiusura di emergenza' }),
    ).toHaveTextContent(
      'Chiudere 1 posizione dei flussi del conto principale e metterli in pausa?',
    );
    expect(fakePlatform.emergencyClosings()).toBe(0);
  });

  it('goes back to the accounts from the page the dashboard was opened on', async () => {
    const { router } = await renderApp({ account: 'anna', url: ACCOUNT_PAGE });
    await head();

    await userEvent.click(screen.getByRole('button', { name: 'Indietro' }));

    expect(router.state.location.pathname).toBe('/accounts');
  });

  it('goes back to the page it was reached from', async () => {
    const { router } = await renderApp({ account: 'anna', url: '/alerts' });
    await screen.findByRole('heading', { level: 1, name: 'Avvisi' });
    await act(() => router.navigate(ACCOUNT_PAGE));
    await head();

    await userEvent.click(screen.getByRole('button', { name: 'Indietro' }));

    expect(router.state.location.pathname).toBe('/alerts');
  });

  it('keeps the address of the alarms of before leading to the alerts of the account', async () => {
    const { router } = await renderApp({ account: 'anna', url: `${ACCOUNT_PAGE}/alarms` });

    await screen.findByRole('heading', { level: 1, name: 'Avvisi' });
    expect(router.state.location.pathname).toBe('/alerts');
  });

  describe('the tab Impostazioni', () => {
    const SETTINGS = `${ACCOUNT_PAGE}/settings`;

    it('replaces the credentials and confirms it', async () => {
      await renderApp({ account: 'anna', url: SETTINGS });
      const credentials = await screen.findByRole('region', {
        name: 'Credenziali del conto principale',
      });

      await userEvent.click(
        within(credentials).getByRole('button', { name: 'Sostituisci le credenziali' }),
      );
      await userEvent.type(
        await within(credentials).findByLabelText("Chiave dell'API wallet"),
        `0x${'7c'.repeat(32)}`,
      );
      await userEvent.click(within(credentials).getByRole('button', { name: 'Sostituisci' }));

      expect(
        await within(credentials).findByText('Credenziali del conto principale sostituite'),
      ).toHaveAttribute('role', 'status');
      expect(within(credentials).queryByRole('form')).toBeNull();
    });

    it('cancels the replacement of the credentials', async () => {
      await renderApp({ account: 'anna', url: SETTINGS });
      const credentials = await screen.findByRole('region', {
        name: 'Credenziali del conto principale',
      });

      await userEvent.click(
        within(credentials).getByRole('button', { name: 'Sostituisci le credenziali' }),
      );
      await userEvent.click(within(credentials).getByRole('button', { name: 'Annulla' }));

      expect(within(credentials).queryByRole('form')).toBeNull();
    });

    it('keeps the removal alone in the zone of danger, followed only by the zone of emergency', async () => {
      await renderApp({ account: 'anna', url: SETTINGS });

      const zone = await screen.findByRole('region', { name: 'Zona pericolosa' });
      expect(
        within(zone)
          .getAllByRole('button')
          .map((button) => button.textContent),
      ).toEqual(['Rimuovi']);
      const emergencyZone = screen.getByRole('region', { name: EMERGENCY_ZONE });
      expect(partsAfter(zone).every((part) => emergencyZone.contains(part))).toBe(true);
    });

    it('removes the account once confirmed and goes back to the accounts', async () => {
      const { router } = await renderApp({ account: 'anna', url: SETTINGS });
      const zone = await screen.findByRole('region', { name: 'Zona pericolosa' });

      await userEvent.click(within(zone).getByRole('button', { name: 'Rimuovi' }));
      await userEvent.click(
        within(
          screen.getByRole('alertdialog', { name: 'Rimozione del conto principale' }),
        ).getByRole('button', { name: 'Conferma la rimozione' }),
      );

      expect(await screen.findByText('Nessun conto registrato.')).toBeInTheDocument();
      expect(router.state.location.pathname).toBe('/accounts');
    });

    it('keeps the account when the removal is cancelled', async () => {
      await renderApp({ account: 'anna', url: SETTINGS });
      const zone = await screen.findByRole('region', { name: 'Zona pericolosa' });

      await userEvent.click(within(zone).getByRole('button', { name: 'Rimuovi' }));
      await userEvent.click(within(zone).getByRole('button', { name: 'Annulla' }));

      expect(within(zone).queryByRole('alertdialog')).toBeNull();
      expect(fakePlatform.user('anna').accounts.map(({ name }) => name)).toContain('principale');
    });
  });
});
