import { z } from 'zod';

/** A reason of a refusal, with the field of the request it concerns when the API names one. */
export type FieldProblem = { readonly field: string | undefined; readonly reason: string };

// A refusal names its field (R2.3.3); an invalid request lists where and why for each value, with the body first.
const problemSchema = z.object({
  detail: z.string(),
  field: z.string().optional(),
  errors: z
    .array(z.object({ loc: z.array(z.union([z.string(), z.number()])), msg: z.string() }))
    .optional(),
});

export type ProblemDetails = { readonly detail: string; readonly problems: FieldProblem[] };

const BODY = 'body';

const bodyFieldOf = (location: ReadonlyArray<string | number>): string | undefined => {
  const [where, field] = location;
  return where === BODY && typeof field === 'string' ? field : undefined;
};

/** The reason of a Problem Details answer (RFC 9457, ADR 0027) and the fields it concerns, when it is one. */
export const problemDetailsOf = (body: unknown): ProblemDetails | undefined => {
  const parsed = problemSchema.safeParse(body);
  if (!parsed.success) {
    return undefined;
  }
  const { detail, field, errors } = parsed.data;
  if (errors !== undefined && errors.length > 0) {
    return {
      detail,
      problems: errors.map((error) => ({ field: bodyFieldOf(error.loc), reason: error.msg })),
    };
  }
  return { detail, problems: [{ field, reason: detail }] };
};
