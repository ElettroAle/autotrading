/**
 * A parameter of the catalog as far as its kind goes: a whole number, or a list of them each in the range, with at most
 * the values it declares. Every field of a list derives from this declaration alone, never from its key (ADR
 * parametri-delle-fonti-come-liste-libere).
 */
export type KindedParameter = {
  readonly kind: 'number' | 'list';
  readonly label: string;
  readonly default: number | readonly number[];
  readonly minimum: number;
  readonly maximum: number;
  readonly maximum_values: number | null;
};

// Whole numbers separated by commas or spaces; a blank field is the empty list, the value switched off.
const LIST_TEXT = /^[\d\s,]*$/;
const SEPARATORS = /[\s,]+/;

/** The reason of a list written in another shape, as the form says it before sending. */
export const LIST_SHAPE = 'Inserisci numeri interi separati da virgole';

export const isList = (parameter: Pick<KindedParameter, 'kind'>): boolean =>
  parameter.kind === 'list';

export const isListText = (text: string): boolean => LIST_TEXT.test(text);

/** The numbers written, in the order typed: the API saves them ordered and without repetitions. */
export const listOf = (text: string): number[] =>
  text
    .split(SEPARATORS)
    .filter((piece) => piece !== '')
    .map(Number);

export const listTextOf = (values: readonly number[]): string => values.join(', ');

/** The default of a parameter of either kind, as its field holds it. */
export const defaultTextOf = (parameter: Pick<KindedParameter, 'default'>): string =>
  typeof parameter.default === 'number' ? String(parameter.default) : listTextOf(parameter.default);

/** What a list admits, as its field says it. */
export const listRangeOf = (parameter: KindedParameter): string =>
  `ogni valore tra ${parameter.minimum} e ${parameter.maximum}, al massimo ${parameter.maximum_values} valori`;

/** The refusal of the rules common to every list, with the reasons of the API; none when the list is admitted. */
export const listRefusalOf = (
  parameter: KindedParameter,
  values: readonly number[],
): string | undefined => {
  if (values.some((value) => value < parameter.minimum || value > parameter.maximum)) {
    return `${parameter.label}: ogni valore tra ${parameter.minimum} e ${parameter.maximum}`;
  }
  if (parameter.maximum_values !== null && new Set(values).size > parameter.maximum_values) {
    return `${parameter.label}: al massimo ${parameter.maximum_values} valori`;
  }
  return undefined;
};

/** A saved parameter as the API writes it in the differences of the configuration: a list in brackets. */
export const parameterTextOf = (value: string | number | readonly number[]): string =>
  typeof value === 'object' ? `[${listTextOf(value)}]` : String(value);
