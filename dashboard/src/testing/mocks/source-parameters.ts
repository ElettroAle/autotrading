import type { FakeSourceParameter } from './catalogs';

/** A parameter of a source as the fake platform keeps it: a whole number, or a list of them. */
export type FakeParameterValue = number | readonly number[];

/** The list the API saves, ordered and without repetitions, or the reason it refuses the value. */
type ListOutcome = { readonly saved: readonly number[] } | { readonly refusal: string };

const inRange = (parameter: FakeSourceParameter, value: unknown): value is number =>
  typeof value === 'number' &&
  Number.isInteger(value) &&
  value >= parameter.minimum &&
  value <= parameter.maximum;

/**
 * The rules common to every list parameter, from its declaration alone, with the reasons of the domain of the API
 * (ADR parametri-delle-fonti-come-liste-libere).
 */
export const listOutcomeOf = (parameter: FakeSourceParameter, value: unknown): ListOutcome => {
  if (!Array.isArray(value) || !value.every((each) => inRange(parameter, each))) {
    return {
      refusal: `${parameter.label}: ogni valore tra ${parameter.minimum} e ${parameter.maximum}`,
    };
  }
  const saved = [...new Set(value as number[])].sort((one, other) => one - other);
  if (parameter.maximum_values !== null && saved.length > parameter.maximum_values) {
    return { refusal: `${parameter.label}: al massimo ${parameter.maximum_values} valori` };
  }
  return { saved };
};
