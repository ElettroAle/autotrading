import createClient, { type Client } from 'openapi-fetch';
import { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { z } from 'zod';

import { paths as dashboardPaths } from '@/config/paths';

import type { paths } from './api-schema';
import { SessionExpiredError, useAccessToken } from './auth';
import { problemDetailsOf, type FieldProblem } from './problem-details';

/** An answer of the API other than success, with the reason its Problem Details give (ADR 0027). */
export class ApiError extends Error {
  readonly status: number;
  /** Each reason with the field of the request it concerns, when the API names one. */
  readonly problems: FieldProblem[];

  constructor(status: number, detail: string, problems: FieldProblem[] = []) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.problems = problems;
  }
}

/** The functions of the API with the types its OpenAPI document declares (ADR 0119). */
export type ApiClient = Client<paths>;

/** A file the API gives to download, with the name it gives it. */
export type DownloadedFile = { readonly name: string; readonly content: Blob };

type ApiClientOptions = {
  readonly accessToken: () => Promise<string>;
  readonly onSessionExpired: () => void;
};

const UNAUTHORIZED = 401;

// Dashboard and API share the origin under Tailscale Serve: no CORS, no address to configure (ADR 0117).
export const createApiClient = ({ accessToken, onSessionExpired }: ApiClientOptions): ApiClient => {
  const client = createClient<paths>({ baseUrl: window.location.origin });
  client.use({
    async onRequest({ request }) {
      request.headers.set(
        'Authorization',
        `Bearer ${await tokenOrSignIn(accessToken, onSessionExpired)}`,
      );
      request.headers.set('Accept', 'application/json');
      return request;
    },
    onResponse({ response }) {
      if (response.status === UNAUTHORIZED) {
        onSessionExpired();
        throw new SessionExpiredError();
      }
    },
  });
  return client;
};

const tokenOrSignIn = async (
  accessToken: () => Promise<string>,
  onSessionExpired: () => void,
): Promise<string> => {
  try {
    return await accessToken();
  } catch (error) {
    onSessionExpired();
    throw error;
  }
};

type ApiResult<Data> = {
  readonly data?: Data;
  readonly error?: unknown;
  readonly response: Response;
};

const refusalOf = ({ error, response }: ApiResult<unknown>): ApiError => {
  const problem = problemDetailsOf(error);
  return problem === undefined
    ? new ApiError(response.status, response.statusText)
    : new ApiError(response.status, problem.detail, problem.problems);
};

/**
 * The data of a successful answer, validated by the schema of what the dashboard reads. The schema must read a part
 * of the type the API declares, so a change of the API that breaks the dashboard fails the compilation; what the
 * schema turns it into is the dashboard's.
 */
export const readData = <Read, Answer, Data extends Answer>(
  result: ApiResult<Data>,
  schema: z.ZodType<Read, Answer>,
): Read => {
  if (!result.response.ok) {
    throw refusalOf(result);
  }
  return schema.parse(result.data);
};

/** The outcome of a command the API answers without content. */
export const readDone = (result: ApiResult<unknown>): void => {
  if (!result.response.ok) {
    throw refusalOf(result);
  }
};

// RFC 6266: the full name, encoded, wins over the plain one that every client reads.
const ENCODED_FILE_NAME = /filename\*=UTF-8''([^;]+)/i;
const PLAIN_FILE_NAME = /filename="([^"]+)"/i;

const fileNameOf = (url: string, disposition: string | null): string => {
  const encoded = ENCODED_FILE_NAME.exec(disposition ?? '')?.[1];
  if (encoded !== undefined) {
    return decodeURIComponent(encoded);
  }
  const { pathname } = new URL(url);
  return (
    PLAIN_FILE_NAME.exec(disposition ?? '')?.[1] ?? pathname.slice(pathname.lastIndexOf('/') + 1)
  );
};

/** A file the API answers with, read with `parseAs: 'blob'`, and the name the API gives it. */
export const readFile = (result: ApiResult<Blob>): DownloadedFile => {
  if (!result.response.ok || result.data === undefined) {
    throw refusalOf(result);
  }
  return {
    name: fileNameOf(result.response.url, result.response.headers.get('Content-Disposition')),
    content: result.data,
  };
};

/**
 * The text of a file the user chose as the body of a request, sent as it is: the API, not the dashboard, judges the
 * file and tells what is wrong with it (R2.5.2). The types see the text as the body they ask for; it is never serialized.
 */
export const documentBody = <Body>(document: string) => ({
  body: document as Body,
  bodySerializer: () => document,
});

export const useApiClient = (): ApiClient => {
  const accessToken = useAccessToken();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  return useMemo(
    () =>
      createApiClient({
        accessToken,
        onSessionExpired: () => {
          void navigate(dashboardPaths.login.getHref(pathname), { replace: true });
        },
      }),
    [accessToken, navigate, pathname],
  );
};
