import { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { z } from 'zod';

import { paths } from '@/config/paths';

import { SessionExpiredError, useAccessToken } from './auth';

/** An answer of the API other than success, with the reason its Problem Details give (ADR 0027). */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
  }
}

const problemSchema = z.object({ detail: z.string() });

export type ApiClient = {
  get<T>(path: string, schema: z.ZodType<T>): Promise<T>;
};

type ApiClientOptions = {
  readonly accessToken: () => Promise<string>;
  readonly onSessionExpired: () => void;
  readonly fetcher?: typeof fetch;
};

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

  return {
    async get<T>(path: string, schema: z.ZodType<T>): Promise<T> {
      const token = await tokenOrSignIn();
      const response = await fetcher(new URL(path, window.location.origin), {
        headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
      });
      if (response.status === 401) {
        onSessionExpired();
        throw new SessionExpiredError();
      }
      if (!response.ok) {
        throw new ApiError(response.status, await reasonOf(response));
      }
      return schema.parse(await response.json());
    },
  };
};

const reasonOf = async (response: Response): Promise<string> => {
  const problem = problemSchema.safeParse(await response.json().catch(() => null));
  return problem.success ? problem.data.detail : response.statusText;
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
