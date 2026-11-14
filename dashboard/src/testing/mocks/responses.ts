import { HttpResponse } from 'msw';

import { FakeRefusal, fakePlatform, type FakeUser } from './platform';

const BEARER = 'Bearer ';

// Answers as the API does: Problem Details, 401 without a valid token, 403 without the Utente role (R0.1.1).
export const problem = (
  status: number,
  title: string,
  detail: string,
  details: Record<string, unknown> = {},
) =>
  HttpResponse.json(
    { type: 'about:blank', title, status, detail, ...details },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  );

const userOf = (request: Request): FakeUser | undefined => {
  const authorization = request.headers.get('Authorization') ?? '';
  return authorization.startsWith(BEARER)
    ? fakePlatform.userOfToken(authorization.slice(BEARER.length))
    : undefined;
};

// A refusal of the platform answers as the API would, with its status and reason.
export const withUser = async (
  request: Request,
  respond: (user: FakeUser) => Response | Promise<Response>,
): Promise<Response> => {
  if (!fakePlatform.apiAnswers()) {
    return HttpResponse.error();
  }
  const user = userOf(request);
  if (user === undefined) {
    return problem(401, 'Unauthorized', 'token assente o non valido');
  }
  if (!user.hasUserRole) {
    return problem(403, 'Forbidden', 'ruolo Utente assente');
  }
  try {
    return await respond(user);
  } catch (error) {
    if (error instanceof FakeRefusal) {
      return problem(error.status, 'Refused', error.message);
    }
    throw error;
  }
};

const textRecordOf = (value: unknown): Record<string, string> =>
  Object.fromEntries(
    (typeof value === 'object' && value !== null ? Object.entries(value) : []).map(
      ([name, field]) => [name, typeof field === 'string' ? field : ''],
    ),
  );

/** The body of a request as JSON, every field read as text: a missing one arrives empty, as on the API. */
export const textFieldsOf = async (request: Request): Promise<Record<string, string>> =>
  textRecordOf(await request.json().catch(() => ({})));

/** The text fields of a request and those of the object it carries under `inner`, read as on the API. */
export const textFieldsWithin = async (
  request: Request,
  inner: string,
): Promise<{ fields: Record<string, string>; within: Record<string, string> }> => {
  const body: unknown = await request.json().catch(() => ({}));
  const nested = typeof body === 'object' && body !== null ? Reflect.get(body, inner) : undefined;
  return { fields: textRecordOf(body), within: textRecordOf(nested) };
};
