import { z } from 'zod';

import type { TrialAdapter, TrialParameter, TrialSource } from '../api/get-trial-sources';
import type { SourceTrialRequest } from '../api/try-source-adapter';

/** What the form of a trial holds: the adapter, the asset and every parameter as typed. */
export type TrialFormValues = {
  adapter: string;
  asset: string;
  parameters: Record<string, string>;
};

const WHOLE_NUMBER = /^-?\d+$/;

/** The values a parameter admits, as the field says them when a value is outside (R6.3.1). */
export const admittedRangeOf = (parameter: TrialParameter): string =>
  `ammesso da ${parameter.minimum} a ${parameter.maximum}`;

const accepts = (parameter: TrialParameter, typed: string): boolean => {
  const value = Number(typed.trim());
  return (
    WHOLE_NUMBER.test(typed.trim()) && value >= parameter.minimum && value <= parameter.maximum
  );
};

/** The adapter of the source the form names, the only one when the source has one. */
export const adapterNamed = (source: TrialSource, name: string): TrialAdapter | undefined =>
  source.adapters.find((adapter) => adapter.name === name);

/**
 * The rules of a trial, from the limits the catalog declares: a value outside them stops the trial before the request
 * leaves (ADR pagina-fonti-con-la-prova); the API keeps the same rules.
 */
export const trialSchemaOf = (source: TrialSource, adapter: TrialAdapter | undefined) =>
  z.object({
    adapter: z.string().min(1, "scegli l'adapter"),
    asset: source.per_asset ? z.string().trim().min(1, "scegli l'asset") : z.string(),
    parameters: z.object(
      Object.fromEntries(
        (adapter?.parameters ?? []).map((parameter) => [
          parameter.key,
          z.string().refine((typed) => accepts(parameter, typed), admittedRangeOf(parameter)),
        ]),
      ),
    ),
  });

/** The parameters of the adapter at the defaults of the catalog. */
export const defaultParametersOf = (adapter: TrialAdapter | undefined): Record<string, string> =>
  Object.fromEntries(
    (adapter?.parameters ?? []).map((parameter) => [parameter.key, String(parameter.default)]),
  );

/** The first values of the form: the only adapter, or none to choose, and its defaults. */
export const initialValuesOf = (source: TrialSource): TrialFormValues => {
  const only = source.adapters.length === 1 ? source.adapters[0] : undefined;
  return { adapter: only?.name ?? '', asset: '', parameters: defaultParametersOf(only) };
};

/** The request of the trial: an asset only for a per-asset source, every parameter as a whole number. */
export const trialRequestOf = (
  source: TrialSource,
  values: TrialFormValues,
): SourceTrialRequest => ({
  source: source.name,
  adapter: values.adapter,
  asset: source.per_asset ? values.asset.trim() : null,
  parameters: Object.fromEntries(
    Object.entries(values.parameters).map(([key, typed]) => [key, Number(typed.trim())]),
  ),
});
