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
});
