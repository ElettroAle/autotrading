import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakeClock } from '@/testing/mocks/clock';
import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

const PROVIDER_KEYS = '/provider-keys';
const EARLIER = '2026-11-01T08:00:00.000Z';
const TODAY = new Date('2026-11-15T06:00:00Z');

const keyItem = (provider: string) => screen.findByRole('listitem', { name: provider });

const expiryOf = (item: HTMLElement) => within(item).getByLabelText('Scadenza della chiave');

const notice = () => screen.queryByRole('region', { name: 'Chiavi da rinnovare' });

const keyExpiringOn = (expiresOn: string) =>
  fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER, { expiresOn, source: 'entered' });

describe('the expiry of the keys of the providers (R6.2.2)', () => {
  beforeEach(() => {
    fakeClock.fix(TODAY);
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('shows a key without a date as of unknown expiry, with no notice', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    expect(expiryOf(await keyItem('openrouter'))).toHaveTextContent('scadenza sconosciuta');
    expect(notice()).not.toBeInTheDocument();
  });

  it('gives the expiry of a key, which the key then shows', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const item = await keyItem('openrouter');

    await userEvent.click(within(item).getByRole('button', { name: 'Indica scadenza' }));
    await userEvent.type(within(item).getByLabelText('Scadenza'), '2027-03-15');
    await userEvent.click(within(item).getByRole('button', { name: 'Salva la scadenza' }));

    await waitFor(() => expect(expiryOf(item)).toHaveTextContent('scade il 15/03/2027'));
    expect(within(item).queryByLabelText('Scadenza')).not.toBeInTheDocument();
  });

  it('closes the date without saving it', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const item = await keyItem('openrouter');

    await userEvent.click(within(item).getByRole('button', { name: 'Indica scadenza' }));
    await userEvent.click(within(item).getByRole('button', { name: 'Annulla' }));

    expect(within(item).queryByLabelText('Scadenza')).not.toBeInTheDocument();
    expect(fakePlatform.providerKeyOf('anna', 'openrouter')?.expiry).toBeUndefined();
  });

  it('warns at the head of the page of a key that expires, until a new key with a later date replaces it', async () => {
    keyExpiringOn('2026-11-20');
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const item = await keyItem('openrouter');
    expect(expiryOf(item)).toHaveTextContent('scade tra 5 giorni · 20/11/2026');
    const warning = notice();
    expect(warning).toHaveTextContent('Chiave openrouter: scade tra 5 giorni');

    await userEvent.click(
      within(warning as HTMLElement).getByRole('button', {
        name: 'Sostituisci la chiave di openrouter',
      }),
    );
    await userEvent.type(within(item).getByLabelText('Chiave API'), 'chiave-nuova');
    await userEvent.type(within(item).getByLabelText('Scadenza'), '2027-03-15');
    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    expect(await within(item).findByRole('status')).toHaveTextContent(
      'Chiave di openrouter sostituita',
    );
    await waitFor(() => expect(notice()).not.toBeInTheDocument());
    expect(expiryOf(item)).toHaveTextContent('scade il 15/03/2027');
  });

  it('marks a key expired as critical', async () => {
    keyExpiringOn('2026-11-15');
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    expect(expiryOf(await keyItem('openrouter'))).toHaveTextContent('scaduta · 15/11/2026');
    expect(notice()).toHaveTextContent('Chiave openrouter: scaduta');
  });

  it('registers a key with its expiry', async () => {
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const region = await screen.findByRole('region', { name: 'Nuova chiave' });
    await within(region).findByRole('option', { name: 'openrouter' });

    await userEvent.selectOptions(within(region).getByLabelText('Fornitore'), 'openrouter');
    await userEvent.type(within(region).getByLabelText('Chiave API'), 'chiave');
    await userEvent.type(within(region).getByLabelText('Scadenza'), '2027-01-15');
    await userEvent.click(within(region).getByRole('button', { name: 'Registra la chiave' }));

    await waitFor(() => expect(region).toHaveTextContent('Chiave di openrouter registrata'));
    expect(expiryOf(await keyItem('openrouter'))).toHaveTextContent('scade il 15/01/2027');
  });
});
