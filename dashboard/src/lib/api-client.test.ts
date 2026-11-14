import { http, HttpResponse } from 'msw';
import { z } from 'zod';

import { server } from '@/testing/mocks/server';

import {
  ApiError,
  createApiClient,
  documentBody,
  readData,
  readDone,
  readFile,
  type ApiClient,
} from './api-client';
import type { components } from './api-schema';
import { SessionExpiredError } from './auth';

const identitySchema = z.object({ user_id: z.string() });
const providerKeySchema = z.object({ provider: z.string() });
const flowSchema = z.object({ name: z.string() });

const clientWith = (accessToken: () => Promise<string> = () => Promise.resolve('token-1')) => {
  const onSessionExpired = vi.fn();
  return { api: createApiClient({ accessToken, onSessionExpired }), onSessionExpired };
};

const readIdentity = async (api: ApiClient) => readData(await api.GET('/me'), identitySchema);

const registerKey = async (api: ApiClient) =>
  readData(
    await api.POST('/provider-keys', { body: { provider: 'openrouter', key: 'chiave-finta' } }),
    providerKeySchema,
  );

const downloadStrategy = async (api: ApiClient) =>
  readFile(
    await api.GET('/flows/{flow_id}/strategy', {
      params: { path: { flow_id: 'flow-1' } },
      parseAs: 'blob',
    }),
  );

describe('createApiClient', () => {
  it('reads from the API of the same origin with the access token of the user', async () => {
    server.use(
      http.get('http://localhost:3000/me', ({ request }) =>
        request.headers.get('Authorization') === 'Bearer token-1'
          ? HttpResponse.json({ user_id: 'oid-anna', tenant_id: 'tenant-anna' })
          : HttpResponse.json({}, { status: 401 }),
      ),
    );
    const { api } = clientWith();

    expect(await readIdentity(api)).toEqual({ user_id: 'oid-anna' });
  });

  it('fills the path of a function with its parameters, encoded', async () => {
    const received: string[] = [];
    server.use(
      http.get('http://localhost:3000/flows/:flowId/cycles', ({ request }) => {
        const url = new URL(request.url);
        received.push(`${url.pathname}${url.search}`);
        return HttpResponse.json({ page: 2, has_next: false, cycles: [] });
      }),
    );
    const { api } = clientWith();

    const page = readData(
      await api.GET('/flows/{flow_id}/cycles', {
        params: { path: { flow_id: 'flow alfa' }, query: { page: 2 } },
      }),
      z.object({ page: z.number() }),
    );

    expect(page).toEqual({ page: 2 });
    expect(received).toEqual(['/flows/flow%20alfa/cycles?page=2']);
  });

  it('sends the user to sign in again when the API no longer accepts the token', async () => {
    server.use(http.get('*/me', () => HttpResponse.json({}, { status: 401 })));
    const { api, onSessionExpired } = clientWith();

    await expect(readIdentity(api)).rejects.toBeInstanceOf(SessionExpiredError);
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });

  it('sends the user to sign in again when no token can be had', async () => {
    const { api, onSessionExpired } = clientWith(() => Promise.reject(new SessionExpiredError()));

    await expect(readIdentity(api)).rejects.toBeInstanceOf(SessionExpiredError);
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });

  it('sends a JSON body with the access token of the user, and reads the answer', async () => {
    const received: unknown[] = [];
    server.use(
      http.post('http://localhost:3000/provider-keys', async ({ request }) => {
        received.push([
          request.headers.get('Authorization'),
          request.headers.get('Content-Type'),
          await request.json(),
        ]);
        return HttpResponse.json(
          { provider: 'openrouter', registered_at: 'ieri' },
          { status: 201 },
        );
      }),
    );
    const { api } = clientWith();

    expect(await registerKey(api)).toEqual({ provider: 'openrouter' });
    expect(received).toEqual([
      ['Bearer token-1', 'application/json', { provider: 'openrouter', key: 'chiave-finta' }],
    ]);
  });
});

describe('readData', () => {
  it('tells the status and the reason of the Problem Details of a refusal', async () => {
    server.use(
      http.get('*/me', () =>
        HttpResponse.json({ detail: 'ruolo Utente assente' }, { status: 403 }),
      ),
    );
    const { api } = clientWith();

    const error = await readIdentity(api).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 403, message: 'ruolo Utente assente' });
  });

  it('tells the status text when the refusal has no Problem Details', async () => {
    server.use(
      http.get('*/me', () => new HttpResponse('down', { status: 502, statusText: 'Bad Gateway' })),
    );
    const { api } = clientWith();

    await expect(readIdentity(api)).rejects.toMatchObject({ status: 502, message: 'Bad Gateway' });
  });

  it('tells the status text of a refusal without a body', async () => {
    server.use(
      http.get('*/me', () => new HttpResponse(null, { status: 503, statusText: 'Unavailable' })),
    );
    const { api } = clientWith();

    await expect(readIdentity(api)).rejects.toMatchObject({ status: 503, message: 'Unavailable' });
  });

  it('refuses an answer that is not what the dashboard reads', async () => {
    server.use(http.get('*/me', () => HttpResponse.json({ user: 'anna' })));
    const { api } = clientWith();

    await expect(readIdentity(api)).rejects.toBeInstanceOf(z.ZodError);
  });

  it('keeps the field a refusal names, so a form can show the reason beside it', async () => {
    server.use(
      http.post('*/provider-keys', () =>
        HttpResponse.json({ detail: 'chiave rifiutata', field: 'key' }, { status: 422 }),
      ),
    );
    const { api } = clientWith();

    await expect(registerKey(api)).rejects.toMatchObject({
      status: 422,
      message: 'chiave rifiutata',
      problems: [{ field: 'key', reason: 'chiave rifiutata' }],
    });
  });

  it('keeps each field an invalid request names, with its reason', async () => {
    server.use(
      http.post('*/provider-keys', () =>
        HttpResponse.json(
          {
            detail: 'richiesta non valida',
            errors: [
              { loc: ['body', 'key'], msg: 'Field required', type: 'missing' },
              { loc: ['query', 'page'], msg: 'Input should be a valid integer', type: 'int' },
            ],
          },
          { status: 422 },
        ),
      ),
    );
    const { api } = clientWith();

    await expect(registerKey(api)).rejects.toMatchObject({
      problems: [
        { field: 'key', reason: 'Field required' },
        { field: undefined, reason: 'Input should be a valid integer' },
      ],
    });
  });

  it('keeps the reason alone when the refusal names no field', async () => {
    server.use(
      http.post('*/provider-keys', () =>
        HttpResponse.json({ detail: 'fornitore sconosciuto' }, { status: 404 }),
      ),
    );
    const { api } = clientWith();

    await expect(registerKey(api)).rejects.toMatchObject({
      problems: [{ field: undefined, reason: 'fornitore sconosciuto' }],
    });
  });
});

describe('readDone', () => {
  it('accepts a command the API answers without content', async () => {
    const received: string[] = [];
    server.use(
      http.delete('http://localhost:3000/telegram/chat', ({ request }) => {
        received.push(request.headers.get('Authorization') ?? '');
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { api } = clientWith();

    expect(readDone(await api.DELETE('/telegram/chat'))).toBeUndefined();
    expect(received).toEqual(['Bearer token-1']);
  });

  it('tells the reason of a command the API refuses', async () => {
    server.use(
      http.post('*/telegram/test-notification', () =>
        HttpResponse.json({ detail: 'nessuna chat collegata' }, { status: 409 }),
      ),
    );
    const { api } = clientWith();
    const result = await api.POST('/telegram/test-notification');

    expect(() => readDone(result)).toThrow(
      expect.objectContaining({ status: 409, message: 'nessuna chat collegata' }),
    );
  });
});

describe('documentBody', () => {
  it('posts a JSON document as it is, with the access token of the user', async () => {
    const document = '{ "format": "autotrading-strategy",\n  "strategy": {} }';
    server.use(
      http.post('http://localhost:3000/flows/import', async ({ request }) =>
        request.headers.get('Authorization') === 'Bearer token-1' &&
        request.headers.get('Content-Type') === 'application/json' &&
        new URL(request.url).searchParams.get('name') === 'alfa bis' &&
        (await request.text()) === document
          ? HttpResponse.json({ name: 'alfa bis' }, { status: 201 })
          : HttpResponse.json({}, { status: 400 }),
      ),
    );
    const { api } = clientWith();

    const imported = readData(
      await api.POST('/flows/import', {
        params: { query: { name: 'alfa bis' } },
        ...documentBody<components['schemas']['StrategyDocument-Input']>(document),
      }),
      flowSchema,
    );

    expect(imported).toEqual({ name: 'alfa bis' });
  });
});

describe('readFile', () => {
  it('downloads a file with the name the API gives it, in its full form', async () => {
    server.use(
      http.get('http://localhost:3000/flows/flow-1/strategy', ({ request }) =>
        request.headers.get('Authorization') === 'Bearer token-1'
          ? HttpResponse.json(
              { format: 'autotrading-strategy' },
              {
                headers: {
                  'Content-Disposition':
                    'attachment; filename="per_.json"; filename*=UTF-8\'\'per%C3%B2.json',
                },
              },
            )
          : HttpResponse.json({}, { status: 401 }),
      ),
    );
    const { api } = clientWith();

    const file = await downloadStrategy(api);

    expect(file.name).toBe('però.json');
    expect(JSON.parse(await file.content.text())).toEqual({ format: 'autotrading-strategy' });
  });

  it('downloads a file with its plain name when the API gives no other', async () => {
    server.use(
      http.get('*/flows/flow-1/strategy', () =>
        HttpResponse.json(
          {},
          { headers: { 'Content-Disposition': 'attachment; filename="alfa.json"' } },
        ),
      ),
    );
    const { api } = clientWith();

    expect((await downloadStrategy(api)).name).toBe('alfa.json');
  });

  it('names a downloaded file after the path when the API names it not', async () => {
    server.use(http.get('*/flows/flow-1/strategy', () => HttpResponse.json({})));
    const { api } = clientWith();

    expect((await downloadStrategy(api)).name).toBe('strategy');
  });

  it('tells the reason of a download the API refuses', async () => {
    server.use(
      http.get('*/flows/flow-1/strategy', () =>
        HttpResponse.json({ detail: 'flusso non trovato' }, { status: 404 }),
      ),
    );
    const { api } = clientWith();

    await expect(downloadStrategy(api)).rejects.toMatchObject({
      status: 404,
      message: 'flusso non trovato',
    });
  });
});
