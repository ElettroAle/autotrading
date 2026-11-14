import type { FieldValues, Path, UseFormSetError } from 'react-hook-form';

import { ApiError } from './api-client';
import { SessionExpiredError } from './auth';

/** Where a form keeps the reasons of a refusal that concern none of its fields: shown at its head. */
export const FORM_ERROR = 'root.server';

const SERVER = 'server';

/**
 * The reason kept for a field of the form. A field holding a record of values (parameters, sources) types its error
 * as that record too, where `message` could be one of its keys: only a text is a reason.
 */
export const reasonOf = (error: { message?: unknown } | undefined): string | undefined =>
  typeof error?.message === 'string' ? error.message : undefined;

const problemsOf = (error: unknown) => {
  if (error instanceof ApiError && error.problems.length > 0) {
    return error.problems;
  }
  return [{ field: undefined, reason: error instanceof Error ? error.message : String(error) }];
};

/**
 * Shows each reason of a refusal of the API beside the field of the form it concerns, the others together at the head
 * of the form: the rules stay with the API, the form only places its answer (ADR 0130, ADR 0131).
 */
export const showRefusal = <T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fieldOf: (field: string) => Path<T> | undefined,
): void => {
  if (error instanceof SessionExpiredError) {
    return;
  }
  const unplaced: string[] = [];
  for (const { field, reason } of problemsOf(error)) {
    const target = field === undefined ? undefined : fieldOf(field);
    if (target === undefined) {
      unplaced.push(reason);
      continue;
    }
    setError(target, { type: SERVER, message: reason });
  }
  if (unplaced.length > 0) {
    setError(FORM_ERROR, { type: SERVER, message: unplaced.join('; ') });
  }
};
