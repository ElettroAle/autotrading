import { http, HttpResponse } from 'msw';
import { z } from 'zod';

import { server } from '@/testing/mocks/server';

import { ApiError, createApiClient } from './api-client';
import { SessionExpiredError } from './auth';

const itemsSchema = z.array(z.object({ name: z.string() }));

const clientWith = (accessToken: () => Promise<string> = () => Promise.resolve('token-1')) => {
  const onSessionExpired = vi.fn();
  return { api: createApiClient({ accessToken, onSessionExpired }), onSessionExpired };
};

describe('createApiClient', () => {
  it('reads from the API of the same origin with the access token of the user', async () => {
    server.use(
      http.get('http://localhost:3000/items', ({ request }) =>
        request.headers.get('Authorization') === 'Bearer token-1'
          ? HttpResponse.json([{ name: 'alfa', extra: true }])
          : HttpResponse.json([], { status: 401 }),
      ),
    );
    const { api } = clientWith();

    expect(await api.get('/items', itemsSchema)).toEqual([{ name: 'alfa' }]);
  });

  it('sends the user to sign in again when the API no longer accepts the token', async () => {
    server.use(http.get('*/items', () => HttpResponse.json({}, { status: 401 })));
    const { api, onSessionExpired } = clientWith();

    await expect(api.get('/items', itemsSchema)).rejects.toBeInstanceOf(SessionExpiredError);
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });

  it('sends the user to sign in again when no token can be had', async () => {
    const { api, onSessionExpired } = clientWith(() => Promise.reject(new SessionExpiredError()));

    await expect(api.get('/items', itemsSchema)).rejects.toBeInstanceOf(SessionExpiredError);
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });

  it('tells the status and the reason of the Problem Details of a refusal', async () => {
    server.use(
      http.get('*/items', () =>
        HttpResponse.json({ detail: 'ruolo Utente assente' }, { status: 403 }),
      ),
    );
    const { api } = clientWith();

    const error = await api.get('/items', itemsSchema).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 403, message: 'ruolo Utente assente' });
  });

  it('tells the status text when the refusal has no Problem Details', async () => {
    server.use(
      http.get(
        '*/items',
        () => new HttpResponse('down', { status: 502, statusText: 'Bad Gateway' }),
      ),
    );
    const { api } = clientWith();

    await expect(api.get('/items', itemsSchema)).rejects.toMatchObject({
      status: 502,
      message: 'Bad Gateway',
    });
  });

  it('posts to the API with the access token of the user and reads the answer', async () => {
    server.use(
      http.post('http://localhost:3000/codes', ({ request }) =>
        request.headers.get('Authorization') === 'Bearer token-1'
          ? HttpResponse.json([{ name: 'beta' }], { status: 201 })
          : HttpResponse.json([], { status: 401 }),
      ),
    );
    const { api } = clientWith();

    expect(await api.post('/codes', itemsSchema)).toEqual([{ name: 'beta' }]);
  });

  it.each(['POST', 'DELETE'] as const)(
    'sends a %s without content with the access token of the user',
    async (method) => {
      const received: string[] = [];
      server.use(
        http.all('http://localhost:3000/chat', ({ request }) => {
          received.push(`${request.method} ${request.headers.get('Authorization') ?? ''}`);
          return new HttpResponse(null, { status: 204 });
        }),
      );
      const { api } = clientWith();

      await expect(api.send(method, '/chat')).resolves.toBeUndefined();
      expect(received).toEqual([`${method} Bearer token-1`]);
    },
  );

  it('tells the reason of a command the API refuses', async () => {
    server.use(
      http.post('*/chat', () =>
        HttpResponse.json({ detail: 'nessuna chat collegata' }, { status: 409 }),
      ),
    );
    const { api } = clientWith();

    await expect(api.send('POST', '/chat')).rejects.toMatchObject({
      status: 409,
      message: 'nessuna chat collegata',
    });
  });

  it('sends the user to sign in again when the API no longer accepts the token of a command', async () => {
    server.use(http.delete('*/chat', () => HttpResponse.json({}, { status: 401 })));
    const { api, onSessionExpired } = clientWith();

    await expect(api.send('DELETE', '/chat')).rejects.toBeInstanceOf(SessionExpiredError);
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });
});

describe('createApiClient commands', () => {
  it('sends a command with its body as JSON and reads the answer', async () => {
    server.use(
      http.put('http://localhost:3000/items/1', async ({ request }) =>
        request.headers.get('Authorization') === 'Bearer token-1' &&
        request.headers.get('Content-Type') === 'application/json'
          ? HttpResponse.json({ name: ((await request.json()) as { name: string }).name })
          : HttpResponse.json({}, { status: 400 }),
      ),
    );
    const { api } = clientWith();

    expect(await api.put('/items/1', { name: 'beta' }, z.object({ name: z.string() }))).toEqual({
      name: 'beta',
    });
  });

  it('sends a command without body', async () => {
    server.use(
      http.post('*/items/1/copy', async ({ request }) =>
        (await request.text()) === ''
          ? HttpResponse.json({ name: 'alfa (copia)' }, { status: 201 })
          : HttpResponse.json({}, { status: 400 }),
      ),
    );
    const { api } = clientWith();

    expect(await api.post('/items/1/copy', z.object({ name: z.string() }))).toEqual({
      name: 'alfa (copia)',
    });
  });

  it('tells, for an invalid request, which field is wrong and why', async () => {
    server.use(
      http.put('*/items/1', () =>
        HttpResponse.json(
          {
            detail: 'richiesta non valida',
            errors: [
              { loc: ['body', 'allocated_capital'], msg: 'Input should be a valid decimal' },
              { loc: ['body'], msg: 'Field required' },
            ],
          },
          { status: 422 },
        ),
      ),
    );
    const { api } = clientWith();

    await expect(api.put('/items/1', {}, itemsSchema)).rejects.toMatchObject({
      status: 422,
      message: 'richiesta non valida',
      fieldErrors: { allocated_capital: 'Input should be a valid decimal', body: 'Field required' },
    });
  });

  it('sends the user to sign in again when a command is refused for the token', async () => {
    server.use(http.post('*/items/1/copy', () => HttpResponse.json({}, { status: 401 })));
    const { api, onSessionExpired } = clientWith();

    await expect(api.post('/items/1/copy', itemsSchema)).rejects.toBeInstanceOf(
      SessionExpiredError,
    );
    expect(onSessionExpired).toHaveBeenCalledOnce();
  });
});

describe('createApiClient documents', () => {
  it('posts a JSON document as it is, with the access token of the user', async () => {
    const document = '{ "format": "autotrading-strategy",\n  "strategy": {} }';
    server.use(
      http.post('http://localhost:3000/flows/import', async ({ request }) =>
        request.headers.get('Authorization') === 'Bearer token-1' &&
        request.headers.get('Content-Type') === 'application/json' &&
        (await request.text()) === document
          ? HttpResponse.json({ name: 'alfa bis' }, { status: 201 })
          : HttpResponse.json({}, { status: 400 }),
      ),
    );
    const { api } = clientWith();

    expect(await api.post('/flows/import', z.object({ name: z.string() }), document)).toEqual({
      name: 'alfa bis',
    });
  });

  it('downloads a file with the name the API gives it, in its full form', async () => {
    server.use(
      http.get('http://localhost:3000/flows/1/strategy', ({ request }) =>
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

    const file = await api.download('/flows/1/strategy');

    expect(file.name).toBe('però.json');
    expect(JSON.parse(await file.content.text())).toEqual({ format: 'autotrading-strategy' });
  });

  it('downloads a file with its plain name when the API gives no other', async () => {
    server.use(
      http.get('*/files/1', () =>
        HttpResponse.text('a,b', {
          headers: { 'Content-Disposition': 'attachment; filename="operazioni.csv"' },
        }),
      ),
    );
    const { api } = clientWith();

    expect((await api.download('/files/1')).name).toBe('operazioni.csv');
  });

  it('names a downloaded file after the path when the API names it not', async () => {
    server.use(http.get('*/flows/1/strategy', () => HttpResponse.json({})));
    const { api } = clientWith();

    expect((await api.download('/flows/1/strategy')).name).toBe('strategy');
  });

  it('tells the reason of a download the API refuses', async () => {
    server.use(
      http.get('*/flows/1/strategy', () =>
        HttpResponse.json({ detail: 'flusso non trovato' }, { status: 404 }),
      ),
    );
    const { api } = clientWith();

    await expect(api.download('/flows/1/strategy')).rejects.toMatchObject({
      status: 404,
      message: 'flusso non trovato',
    });
  });
});
