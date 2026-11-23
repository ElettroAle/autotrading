/** A value a parameter of the catalog admits, with the name a user knows it by (ADR orizzonti-lunghi-del-forecast). */
export type ParameterChoice = { readonly value: number; readonly label: string };

/** A parameter of the catalog as far as its choices go: none means it admits its whole range. */
export type ChoosableParameter = {
  // A list parameter has no choices (ADR parametri-delle-fonti-come-liste-libere).
  readonly default: number | readonly number[];
  readonly choices: readonly ParameterChoice[];
};

export const hasChoices = (parameter: ChoosableParameter): boolean => parameter.choices.length > 0;

/** The options of a selection: the value as the form holds it, the label as the user reads it. */
export const choiceOptionsOf = (
  parameter: ChoosableParameter,
): { readonly value: string; readonly label: string }[] =>
  parameter.choices.map((choice) => ({ value: String(choice.value), label: choice.label }));

/** The default by its label; the catalog always has it among the choices, its value otherwise. */
export const defaultChoiceLabelOf = (parameter: ChoosableParameter): string =>
  parameter.choices.find((choice) => choice.value === parameter.default)?.label ??
  String(parameter.default);

export const isAmongChoices = (parameter: ChoosableParameter, value: number): boolean =>
  parameter.choices.some((choice) => choice.value === value);

/** The choices a parameter admits, as a field says them when a value is not one of them. */
export const admittedChoicesOf = (parameter: ChoosableParameter): string =>
  `ammessi ${parameter.choices.map((choice) => choice.label).join(', ')}`;
