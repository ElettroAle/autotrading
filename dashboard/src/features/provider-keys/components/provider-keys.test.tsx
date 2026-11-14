import { MutationCache } from '@tanstack/react-query';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const PROVIDER_KEYS = '/provider-keys';
const KEY = 'chiave-finta';
const EARLIER = '2026-11-01T08:00:00.000Z';

const form = () => screen.getByRole('region', { name: 'Nuova chiave' });

const registerKey = async (provider: string, key = KEY) => {
  const region = await screen.findByRole('region', { name: 'Nuova chiave' });
  await within(region).findByRole('option', { name: provider });
  await userEvent.selectOptions(within(region).getByLabelText('Fornitore'), provider);
  await userEvent.type(within(region).getByLabelText('Chiave API'), key);
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
    const keys = screen.getByRole('list', { name: 'Chiavi dei fornitori IA' });
    expect(within(keys).queryByText('anthropic')).not.toBeInTheDocument();
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
    await userEvent.type(within(item).getByLabelText('Chiave API'), `${KEY}-nuova`);
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
    await userEvent.type(within(item).getByLabelText('Chiave API'), KEY);
    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    expect(await within(item).findByRole('alert')).toHaveTextContent(
      'nessuna chiave registrata per il fornitore: openrouter',
    );
    expect(within(item).getByLabelText('Chiave API')).toHaveValue('');
  });

  it('tells the key is missing when the replacement is sent empty, and can be cancelled', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const item = await keyItem('openrouter');

    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci la chiave' }));
    await userEvent.click(within(item).getByRole('button', { name: 'Sostituisci' }));

    expect(await within(item).findByRole('alert')).toHaveTextContent('chiave obbligatoria');
    await userEvent.click(within(item).getByRole('button', { name: 'Annulla' }));
    expect(within(item).queryByLabelText('Chiave API')).not.toBeInTheDocument();
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
    expect(within(form()).queryByLabelText('Chiave API')).not.toBeInTheDocument();
    expect(document.body.innerHTML).not.toContain(KEY);
    const mutationCache = mutations.mock.contexts[0] as MutationCache;
    await waitFor(() => expect(mutationCache.getAll()).toEqual([]));
  });

  it('asks the fields the chosen provider declares, and hides the key while typed', async () => {
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const region = await screen.findByRole('region', { name: 'Nuova chiave' });

    expect(within(region).queryByLabelText('Chiave API')).not.toBeInTheDocument();
    await within(region).findByRole('option', { name: 'openrouter' });
    await userEvent.selectOptions(within(region).getByLabelText('Fornitore'), 'openrouter');

    expect(within(region).getByLabelText('Chiave API')).toHaveAttribute('type', 'password');
  });

  it('shows the reason of a refusal at the head of the form and empties the key', async () => {
    server.use(
      http.post('*/provider-keys', () =>
        HttpResponse.json({ detail: 'fornitore non supportato: openai' }, { status: 422 }),
      ),
    );
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    await registerKey('openai');

    expect(await within(form()).findByRole('alert')).toHaveTextContent(
      'fornitore non supportato: openai',
    );
    expect(within(form()).getByLabelText('Fornitore')).toHaveValue('openai');
    expect(within(form()).getByLabelText('Chiave API')).toHaveValue('');
  });

  it('offers the providers of the catalog of the models, none chosen at first', async () => {
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const region = await screen.findByRole('region', { name: 'Nuova chiave' });

    const provider = within(region).getByRole('combobox', { name: 'Fornitore' });
    expect(await within(provider).findByRole('option', { name: 'openrouter' })).toBeEnabled();
    expect(
      within(provider)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['Scegli un fornitore', 'openrouter', 'openai', 'anthropic']);
    expect(provider).toHaveValue('');
  });

  it('shows a provider whose key is registered as such, and it cannot be chosen', async () => {
    fakePlatform.saveProviderKey('anna', 'openrouter', EARLIER);
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const region = await screen.findByRole('region', { name: 'Nuova chiave' });

    expect(
      await within(region).findByRole('option', { name: 'openrouter · chiave già registrata' }),
    ).toBeDisabled();
    expect(within(region).getByRole('option', { name: 'anthropic' })).toBeEnabled();
  });

  it('shows the provider of a key just registered as registered, and as free once it is removed', async () => {
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });

    await registerKey('anthropic');

    expect(
      await within(form()).findByRole('option', { name: 'anthropic · chiave già registrata' }),
    ).toBeDisabled();
    const item = await keyItem('anthropic');
    await userEvent.click(within(item).getByRole('button', { name: 'Rimuovi' }));
    await userEvent.click(within(item).getByRole('button', { name: 'Conferma la rimozione' }));
    expect(await within(form()).findByRole('option', { name: 'anthropic' })).toBeEnabled();
  });

  it('tells the list of the providers is not available and sends nothing', async () => {
    server.use(
      http.get('*/models', () => HttpResponse.json({ detail: 'errore interno' }, { status: 500 })),
    );
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const region = await screen.findByRole('region', { name: 'Nuova chiave' });

    expect(await within(region).findByRole('alert')).toHaveTextContent(
      'Impossibile leggere i fornitori IA: errore interno',
    );
    expect(within(region).getByLabelText('Fornitore')).toBeDisabled();
    expect(within(region).getByRole('button', { name: 'Registra la chiave' })).toBeDisabled();
  });

  it('asks for the provider before sending anything, and the API for its key', async () => {
    const sent = vi.fn();
    server.use(http.post('*/provider-keys', sent));
    await renderApp({ account: 'anna', url: PROVIDER_KEYS });
    const region = await screen.findByRole('region', { name: 'Nuova chiave' });
    await within(region).findByRole('option', { name: 'openrouter' });

    await userEvent.click(within(region).getByRole('button', { name: 'Registra la chiave' }));

    expect(await within(region).findByLabelText('Fornitore')).toHaveAccessibleDescription(
      'Campo obbligatorio',
    );
    expect(sent).not.toHaveBeenCalled();
    server.resetHandlers();
    await userEvent.selectOptions(within(region).getByLabelText('Fornitore'), 'openrouter');
    await userEvent.click(within(region).getByRole('button', { name: 'Registra la chiave' }));
    expect(await within(region).findByRole('alert')).toHaveTextContent('chiave obbligatoria');
  });
});
