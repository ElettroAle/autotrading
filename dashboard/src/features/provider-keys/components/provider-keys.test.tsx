import { MutationCache } from '@tanstack/react-query';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const PROVIDER_KEYS = '/provider-keys';
const KEY = 'sk-or-v1-chiave-di-prova';
const EARLIER = '2026-11-01T08:00:00.000Z';

const form = () => screen.getByRole('region', { name: 'Nuova chiave' });

const registerKey = async (provider: string, key = KEY) => {
  const region = await screen.findByRole('region', { name: 'Nuova chiave' });
  await userEvent.type(within(region).getByLabelText('Fornitore'), provider);
  await userEvent.type(within(region).getByLabelText('Chiave'), key);
  await userEvent.click(within(region).getByRole('button', { name: 'Registra la chiave' }));
};

const keyItem = (provider: string) => screen.findByRole('listitem', { name: provider });

describe('ProviderKeysList', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addUser('bruno', { hasUserRole: true });
    fakePlatform.saveProviderKey('bruno', 'anthropic', EARLIER);
  });

  it('lists the providers of the user with the instant of registration, never the keys', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    const item = await keyItem('openrouter');
    const registeredAt = within(item).getByLabelText('Data di registrazione');
    expect(registeredAt).toHaveAttribute('datetime', EARLIER);
    expect(registeredAt).toHaveTextContent('01/11/2026, 09:00:00');
    expect(screen.queryByText('anthropic')).not.toBeInTheDocument();
  });

  it('says the user has no key yet', async () => {
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    expect(await screen.findByText('Non hai ancora chiavi di fornitori IA.')).toBeInTheDocument();
  });

  it('tells why the keys could not be read', async () => {
    server.use(
      http.get('*/provider-keys', () =>
        HttpResponse.json({ detail: 'piattaforma non raggiungibile' }, { status: 503 }),
      ),
    );
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossibile leggere i dati: piattaforma non raggiungibile',
    );
  });

  it('replaces the key, and the list shows the new instant', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const item = await keyItem('openrouter');

    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci la chiave' }));
    await userEvent.type(within(item).getByLabelText('Nuova chiave'), `${KEY}-nuova`);
    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    expect(await within(item).findByRole('status')).toHaveTextContent(
      'Chiave di openrouter sostituita',
    );
    const replacedAt = fakePlatform.providerKeyOf('anna', 'openrouter')?.registeredAt;
    expect(replacedAt).not.toBe(EARLIER);
    await waitFor(() =>
      expect(within(item).getByLabelText('Data di registrazione')).toHaveAttribute(
        'datetime',
        replacedAt,
      ),
    );
    expect(document.body.innerHTML).not.toContain(KEY);
  });

  it('tells why the replacement was refused and empties the key', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    server.use(
      http.put('*/provider-keys/:provider', () =>
        HttpResponse.json(
          { detail: 'nessuna chiave registrata per il fornitore: openrouter' },
          { status: 404 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const item = await keyItem('openrouter');

    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci la chiave' }));
    await userEvent.type(within(item).getByLabelText('Nuova chiave'), KEY);
    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    expect(await within(item).findByRole('alert')).toHaveTextContent(
      'nessuna chiave registrata per il fornitore: openrouter',
    );
    expect(within(item).getByLabelText('Nuova chiave')).toHaveValue('');
  });

  it('asks for the new key before sending, and the replacement can be cancelled', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const item = await keyItem('openrouter');

    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci la chiave' }));
    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    expect(await within(item).findByLabelText('Nuova chiave')).toHaveAccessibleDescription(
      'Campo obbligatorio',
    );
    await userEvent.click(within(item).getByRole('button', { name: 'Annulla' }));
    expect(within(item).queryByLabelText('Nuova chiave')).not.toBeInTheDocument();
  });

  it('removes the key once the user confirms, naming the provider', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const item = await keyItem('openrouter');

    await userEvent.click(within(item).getByRole('button', { name: 'Rimuovi' }));
    const dialog = within(item).getByRole('alertdialog', {
      name: 'Rimozione della chiave di openrouter',
    });
    expect(dialog).toHaveAccessibleDescription(
      'La chiave del fornitore openrouter sarà cancellata.',
    );
    await userEvent.click(within(dialog).getByRole('button', { name: 'Conferma la rimozione' }));

    expect(await screen.findByText('Non hai ancora chiavi di fornitori IA.')).toBeInTheDocument();
    expect(fakePlatform.providerKeyOf('anna', 'openrouter')).toBeUndefined();
  });

  it('tells why the removal was refused and keeps the key', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    server.use(
      http.delete('*/provider-keys/:provider', () =>
        HttpResponse.json(
          { detail: 'chiave usata da flussi attivi o in pausa: alfa' },
          { status: 409 },
        ),
      ),
    );
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const item = await keyItem('openrouter');

    await userEvent.click(within(item).getByRole('button', { name: 'Rimuovi' }));
    await userEvent.click(within(item).getByRole('button', { name: 'Conferma la rimozione' }));

    expect(await within(item).findByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: chiave usata da flussi attivi o in pausa: alfa',
    );
    await userEvent.click(within(item).getByRole('button', { name: 'Annulla' }));
    expect(within(item).queryByRole('alertdialog')).not.toBeInTheDocument();
  });
});

describe('RegisterProviderKeyForm', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('registers the key, which joins the list with its instant, and empties the form', async () => {
    const mutations = vi.spyOn(MutationCache.prototype, 'build');
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    await registerKey('openrouter');

    expect(await within(form()).findByRole('status')).toHaveTextContent(
      'Chiave di openrouter registrata',
    );
    const item = await keyItem('openrouter');
    expect(within(item).getByLabelText('Data di registrazione')).toHaveAttribute(
      'datetime',
      fakePlatform.providerKeyOf('anna', 'openrouter')?.registeredAt,
    );
    expect(within(form()).getByLabelText('Fornitore')).toHaveValue('');
    expect(within(form()).getByLabelText('Chiave')).toHaveValue('');
    expect(document.body.innerHTML).not.toContain(KEY);
    const mutationCache = mutations.mock.contexts[0] as MutationCache;
    await waitFor(() => expect(mutationCache.getAll()).toEqual([]));
  });

  it('hides the key while typed', async () => {
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    const region = await screen.findByRole('region', { name: 'Nuova chiave' });

    expect(within(region).getByLabelText('Chiave')).toHaveAttribute('type', 'password');
  });

  it('shows the reason of a refusal at the head of the form and empties the key', async () => {
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    await registerKey('mistral');

    expect(await within(form()).findByRole('alert')).toHaveTextContent(
      'fornitore non supportato: mistral',
    );
    expect(within(form()).getByLabelText('Fornitore')).toHaveValue('mistral');
    expect(within(form()).getByLabelText('Chiave')).toHaveValue('');
  });

  it('asks for the provider and the key before sending anything', async () => {
    const sent = vi.fn();
    server.use(http.post('*/provider-keys', sent));
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const region = await screen.findByRole('region', { name: 'Nuova chiave' });

    await userEvent.click(within(region).getByRole('button', { name: 'Registra la chiave' }));

    expect(await within(region).findByLabelText('Fornitore')).toHaveAccessibleDescription(
      'Campo obbligatorio',
    );
    expect(within(region).getByLabelText('Chiave')).toHaveAccessibleDescription(
      'Campo obbligatorio',
    );
    expect(sent).not.toHaveBeenCalled();
  });
});
