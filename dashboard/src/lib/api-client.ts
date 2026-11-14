import { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { z } from 'zod';

import { paths } from '@/config/paths';

import { SessionExpiredError, useAccessToken } from './auth';

export type FieldErrors = Readonly<Record<string, string>>;

/** An answer of the API other than success, with the reason its Problem Details give (ADR 0027). */
export class ApiError extends Error {
  readonly status: number;
  /** For an invalid request, why each field named by the API is wrong. */
  readonly fieldErrors: FieldErrors;

  constructor(status: number, detail: string, fieldErrors: FieldErrors = {}) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

const problemSchema = z.object({
  detail: z.string(),
  errors: z
    .array(z.object({ loc: z.array(z.union([z.string(), z.number()])), msg: z.string() }))
    .optional(),
});

export type ApiClient = {
  get<T>(path: string, schema: z.ZodType<T>): Promise<T>;
  post<T>(path: string, schema: z.ZodType<T>): Promise<T>;
  put<T>(path: string, body: unknown, schema: z.ZodType<T>): Promise<T>;
  /** A command the API answers without content. */
  send(method: 'POST' | 'DELETE', path: string): Promise<void>;
};

type ApiClientOptions = {
  readonly accessToken: () => Promise<string>;
  readonly onSessionExpired: () => void;
  readonly fetcher?: typeof fetch;
};

type Command = { readonly method: string; readonly body?: unknown };

// Dashboard and API share the origin under Tailscale Serve: no CORS, no address to configure (ADR 0117).
export const createApiClient = ({
  accessToken,
  onSessionExpired,
  fetcher = fetch,
}: ApiClientOptions): ApiClient => {
  const tokenOrSignIn = async (): Promise<string> => {
    try {
      return await accessToken();
    } catch (error) {
      onSessionExpired();
      throw error;
    }
  };

  const request = async (path: string, { method, body }: Command): Promise<Response> => {
    const token = await tokenOrSignIn();
    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    };
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }
    const response = await fetcher(new URL(path, window.location.origin), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 401) {
      onSessionExpired();
      throw new SessionExpiredError();
    }
    if (!response.ok) {
      throw await refusalOf(response);
    }
    return response;
  };

  const parsed = async <T>(response: Promise<Response>, schema: z.ZodType<T>): Promise<T> =>
    schema.parse(await (await response).json());

  return {
    get: (path, schema) => parsed(request(path, { method: 'GET' }), schema),
    post: (path, schema) => parsed(request(path, { method: 'POST' }), schema),
    put: (path, body, schema) => parsed(request(path, { method: 'PUT', body }), schema),
    async send(method, path) {
      await request(path, { method });
    },
  };
};

const refusalOf = async (response: Response): Promise<ApiError> => {
  const problem = problemSchema.safeParse(await response.json().catch(() => null));
  if (!problem.success) {
    return new ApiError(response.status, response.statusText);
  }
  const fieldErrors = Object.fromEntries(
    (problem.data.errors ?? []).map(({ loc, msg }) => [String(loc[loc.length - 1]), msg]),
  );
  return new ApiError(response.status, problem.data.detail, fieldErrors);
};

export const useApiClient = (): ApiClient => {
  const accessToken = useAccessToken();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  return useMemo(
    () =>
      createApiClient({
        accessToken,
        onSessionExpired: () => {
          void navigate(paths.login.getHref(pathname), { replace: true });
        },
      }),
    [accessToken, navigate, pathname],
  );
};
