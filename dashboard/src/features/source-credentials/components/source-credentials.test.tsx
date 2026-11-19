import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakeClock } from '@/testing/mocks/clock';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { fakeSourceCredentials } from '@/testing/mocks/source-credentials';
import { renderApp } from '@/testing/test-utils';

const KEYS_PAGE = '/provider-keys';
const PAID = 'LunarCrush';
const TODAY = new Date('2026-11-15T06:00:00Z');
const SAVED_AT = '2026-11-14T09:00:00.000Z';
const ACCOUNT_FIELD = { name: 'account', label: 'Account', secret: false };
const API_KEY_FIELD = { name: 'api_key', label: 'Chiave API', secret: true };
const TYPED_KEY = 'K-LUNAR-SEGRETA';

const sourcesSection = () => screen.findByRole('region', { name: 'Fonti' });

const adapterItem = async () =>
  within(await sourcesSection()).findByRole('listitem', { name: PAID });

const offerPaid = () =>
  fakeSourceCredentials.offerAdapter('sentiment', PAID, [API_KEY_FIELD, ACCOUNT_FIELD]);

const savePaid = (expiresOn?: string) => {
  fakeSourceCredentials.configure(
    'anna',
    PAID,
    { api_key: TYPED_KEY, account: 'anna' },
    SAVED_AT,
    expiresOn === undefined ? undefined : { expiresOn, source: 'entered' },
  );
};

describe('the section Fonti of the page of the keys (R4.1.2, ADR sezione-fonti-nella-pagina-chiavi)', () => {
  beforeEach(() => {
    fakeClock.fix(TODAY);
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('says no adapter needs configuration when none does', async () => {
    await renderApp({ account: 'anna', url: KEYS_PAGE });

    expect(
      await within(await sourcesSection()).findByText(
        'Nessun adapter di fonte richiede configurazione.',
      ),
    ).toBeInTheDocument();
  });

  it('lists only the adapters that need configuration, not configured, with the command to configure', async () => {
    offerPaid();
    await renderApp({ account: 'anna', url: KEYS_PAGE });
    const item = await adapterItem();

    expect(item).toHaveTextContent('sentiment · LunarCrush');
    expect(item).toHaveTextContent('non configurato');
    expect(within(item).getByRole('button', { name: 'Configura' })).toBeVisible();
    expect(within(item).queryByRole('button', { name: 'Rimuovi' })).not.toBeInTheDocument();
    expect(within(await sourcesSection()).getAllByRole('listitem')).toHaveLength(1);
  });

  it('configures the adapter with a secret field that is never shown nor kept on the page', async () => {
    offerPaid();
    await renderApp({ account: 'anna', url: KEYS_PAGE });
    const item = await adapterItem();

    await userEvent.click(within(item).getByRole('button', { name: 'Configura' }));
    const secret = within(item).getByLabelText('Chiave API');
    expect(secret).toHaveAttribute('type', 'password');
    // Never filled by the browser nor by a password manager (ADR campi-delle-credenziali-fuori-dall-autocompletamento).
    expect(secret).toHaveAttribute('autocomplete', 'new-password');
    expect(secret).toHaveAttribute('data-lpignore', 'true');
    await userEvent.type(secret, TYPED_KEY);
    await userEvent.type(within(item).getByLabelText('Account'), 'anna');
    await userEvent.click(within(item).getByRole('button', { name: 'Salva le credenziali' }));

    await waitFor(() => expect(item).toHaveTextContent('configurato'));
    expect(item).not.toHaveTextContent('non configurato');
    expect(item).toHaveTextContent('Account:anna');
    expect(item).toHaveTextContent('scadenza sconosciuta');
    expect(document.body).not.toHaveTextContent(TYPED_KEY);
    expect(fakeSourceCredentials.of('anna', PAID)?.secrets).toEqual({ api_key: TYPED_KEY });
  });

  it('shows beside the field the reason the API refuses the credentials, emptying the secret', async () => {
    offerPaid();
    await renderApp({ account: 'anna', url: KEYS_PAGE });
    const item = await adapterItem();

    await userEvent.click(within(item).getByRole('button', { name: 'Configura' }));
    await userEvent.type(within(item).getByLabelText('Chiave API'), TYPED_KEY);
    await userEvent.click(within(item).getByRole('button', { name: 'Salva le credenziali' }));

    expect(await within(item).findByText('account obbligatorio')).toBeVisible();
    expect(within(item).getByLabelText('Chiave API')).toHaveValue('');
  });

  it('shows at the head of the form a refusal that names no field', async () => {
    offerPaid();
    server.use(
      http.put('*/source-credentials/:adapter', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Not Found', status: 404, detail: 'adapter sparito' },
          { status: 404, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: KEYS_PAGE });
    const item = await adapterItem();

    await userEvent.click(within(item).getByRole('button', { name: 'Configura' }));
    await userEvent.type(within(item).getByLabelText('Chiave API'), TYPED_KEY);
    await userEvent.type(within(item).getByLabelText('Account'), 'anna');
    await userEvent.click(within(item).getByRole('button', { name: 'Salva le credenziali' }));

    expect(await within(item).findByRole('alert')).toHaveTextContent('adapter sparito');
  });

  it('replaces the credentials asking the secret again and starting from the values saved', async () => {
    offerPaid();
    savePaid();
    await renderApp({ account: 'anna', url: KEYS_PAGE });
    const item = await adapterItem();

    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    expect(within(item).getByLabelText('Chiave API')).toHaveValue('');
    expect(within(item).getByLabelText('Account')).toHaveValue('anna');
    await userEvent.click(within(item).getByRole('button', { name: 'Annulla' }));
    expect(within(item).queryByLabelText('Chiave API')).not.toBeInTheDocument();
  });

  it('marks credentials the provider refused, with the command to replace them', async () => {
    offerPaid();
    savePaid();
    fakeSourceCredentials.reject('anna', PAID);
    await renderApp({ account: 'anna', url: KEYS_PAGE });
    const item = await adapterItem();

    expect(item).toHaveTextContent('rifiutata dal fornitore');
    expect(within(item).getByRole('button', { name: 'Sostituisci' })).toBeVisible();
  });

  it('gives the expiry of the credentials, which the adapter then shows', async () => {
    offerPaid();
    savePaid();
    await renderApp({ account: 'anna', url: KEYS_PAGE });
    const item = await adapterItem();

    await userEvent.click(within(item).getByRole('button', { name: 'Indica scadenza' }));
    await userEvent.type(within(item).getByLabelText('Scadenza'), '2026-11-20');
    await userEvent.click(within(item).getByRole('button', { name: 'Salva la scadenza' }));

    await waitFor(() =>
      expect(within(item).getByLabelText('Scadenza della chiave')).toHaveTextContent(
        'scade tra 5 giorni · 20/11/2026',
      ),
    );
  });

  it('removes the credentials after the confirmation', async () => {
    offerPaid();
    savePaid('2027-01-31');
    await renderApp({ account: 'anna', url: KEYS_PAGE });
    const item = await adapterItem();
    expect(item).toHaveTextContent('scade il 31/01/2027');

    await userEvent.click(within(item).getByRole('button', { name: 'Rimuovi' }));
    await userEvent.click(screen.getByRole('button', { name: 'Conferma la rimozione' }));

    await waitFor(() => expect(item).toHaveTextContent('non configurato'));
    expect(fakeSourceCredentials.of('anna', PAID)).toBeUndefined();
  });

  it('warns when the adapters cannot be read', async () => {
    server.use(http.get('*/source-credentials', () => HttpResponse.error()));
    await renderApp({ account: 'anna', url: KEYS_PAGE });

    expect(await within(await sourcesSection()).findByRole('alert')).toBeVisible();
  });
});
