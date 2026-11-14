import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform, type FakeStrategyDocument } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

type SavedFile = { readonly name: string; readonly content: string };

/** What the browser receives to save: the anchor it is asked to follow and the content behind its address. */
const watchSavedFiles = (): SavedFile[] => {
  const saved: SavedFile[] = [];
  const contents = new Map<string, Blob>();
  vi.spyOn(URL, 'createObjectURL').mockImplementation((content) => {
    const url = `blob:saved-${contents.size}`;
    contents.set(url, content as Blob);
    return url;
  });
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    const content = contents.get(this.href);
    if (content !== undefined) {
      void content.text().then((text) => saved.push({ name: this.download, content: text }));
    }
  });
  return saved;
};

const importForm = () => screen.getByRole('form', { name: 'Importazione di una strategia' });

const fileOf = (content: string, name = 'alfa.json') =>
  new File([content], name, { type: 'application/json' });

const exportedFromAlfa = (): FakeStrategyDocument =>
  fakePlatform.exportStrategy(fakePlatform.user('anna'), 'flow-alfa').document;

const importAs = async (name: string, file: File) => {
  const form = await screen.findByRole('form', { name: 'Importazione di una strategia' });
  if (name !== '') {
    await userEvent.type(within(form).getByLabelText('Nome del nuovo flusso'), name);
  }
  await userEvent.upload(within(form).getByLabelText('File della strategia'), file);
  await userEvent.click(within(form).getByRole('button', { name: 'Importa' }));
};

describe('Strategy export and import', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa', {
      model: 'openrouter/deepseek-chat',
      sources: [{ name: 'indicatori', weight: 2 }],
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('saves the strategy file of the flow under the name the API gives it', async () => {
    const saved = watchSavedFiles();
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    await userEvent.click(await screen.findByRole('button', { name: 'Esporta' }));

    await waitFor(() => expect(saved).toHaveLength(1));
    const [file] = saved;
    expect(file?.name).toBe('alfa.json');
    expect(JSON.parse(file?.content ?? '')).toEqual(exportedFromAlfa());
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:saved-0');
  });

  it('tells why the strategy could not be exported', async () => {
    server.use(
      http.get('*/flows/:flowId/strategy', () =>
        HttpResponse.json({ detail: 'flusso non trovato' }, { status: 404 }),
      ),
    );
    const saved = watchSavedFiles();
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    await userEvent.click(await screen.findByRole('button', { name: 'Esporta' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Esportazione rifiutata: flusso non trovato',
    );
    expect(saved).toEqual([]);
  });

  it('imports the file as a draft and opens it, ready for the assignment', async () => {
    const { router } = await renderApp({ account: 'anna' });

    await importAs('alfa bis', fileOf(JSON.stringify(exportedFromAlfa())));

    await waitFor(() => expect(router.state.location.pathname).toBe('/flows/flow-alfa%20bis'));
    expect(await screen.findByRole('heading', { level: 2, name: 'alfa bis' })).toBeVisible();
    expect(screen.getByText('Bozza')).toBeInTheDocument();
    expect(screen.getByRole('form', { name: 'Assegnazione della bozza' })).toBeInTheDocument();
    expect(fakePlatform.flowNamed('alfa bis').sources).toEqual([{ name: 'indicatori', weight: 2 }]);
  });

  it('sends the file as it is, the API decides whether it is valid', async () => {
    const sent: string[] = [];
    server.use(
      http.post('*/flows/import', async ({ request }) => {
        sent.push(`${new URL(request.url).searchParams.get('name')} ${await request.text()}`);
        return HttpResponse.json({ detail: 'modello mancante' }, { status: 422 });
      }),
    );
    await renderApp({ account: 'anna' });

    await importAs(' alfa bis ', fileOf('{ "format": "altro" }'));

    expect(await within(importForm()).findByRole('alert')).toHaveTextContent(
      'Importazione rifiutata: modello mancante',
    );
    expect(sent).toEqual(['alfa bis { "format": "altro" }']);
  });

  it('shows the reason the API refuses the file and creates nothing', async () => {
    const { router } = await renderApp({ account: 'anna' });
    const withoutModel = { ...exportedFromAlfa() };
    withoutModel.strategy = { ...withoutModel.strategy, model: undefined };

    await importAs('importato', fileOf(JSON.stringify(withoutModel)));

    expect(await within(importForm()).findByRole('alert')).toHaveTextContent(
      'Importazione rifiutata: modello mancante',
    );
    expect(router.state.location.pathname).toBe('/');
    expect(fakePlatform.user('anna').flows.map((flow) => flow.name)).toEqual(['alfa']);
  });

  it('refuses a file that is not JSON without sending it', async () => {
    const sent: string[] = [];
    server.use(
      http.post('*/flows/import', () => {
        sent.push('import');
        return HttpResponse.json({}, { status: 500 });
      }),
    );
    await renderApp({ account: 'anna' });

    await importAs('alfa bis', fileOf('non è JSON'));

    expect(await within(importForm()).findByRole('alert')).toHaveTextContent(
      'Importazione rifiutata: il file non è un JSON valido',
    );
    expect(sent).toEqual([]);
  });

  it('asks for the name and for a file before reading it', async () => {
    await renderApp({ account: 'anna' });
    const form = await screen.findByRole('form', { name: 'Importazione di una strategia' });

    await userEvent.click(within(form).getByRole('button', { name: 'Importa' }));

    expect(await within(form).findByText('nome del flusso obbligatorio')).toBeInTheDocument();
    expect(within(form).getByText('scegli un file')).toBeInTheDocument();
  });

  it('refuses a file larger than a strategy can be', async () => {
    await renderApp({ account: 'anna' });

    await importAs('alfa bis', fileOf(' '.repeat(64 * 1024 + 1)));

    expect(await within(importForm()).findByText('il file supera i 64 KB')).toBeInTheDocument();
    expect(fakePlatform.user('anna').flows).toHaveLength(1);
  });
});
