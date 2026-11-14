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

/** The body of a request as JSON, every field read as text: a missing one arrives empty, as on the API. */
export const textFieldsOf = async (request: Request): Promise<Record<string, string>> => {
  const body: unknown = await request.json().catch(() => ({}));
  const fields = typeof body === 'object' && body !== null ? Object.entries(body) : [];
  return Object.fromEntries(
    fields.map(([name, value]) => [name, typeof value === 'string' ? value : '']),
  );
};
