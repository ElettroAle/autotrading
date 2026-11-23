import { http, HttpResponse } from 'msw';

import type { FakeSourceParameter } from './catalogs';
import { problem, withUser } from './responses';
import { fakeSourceCredentials } from './source-credentials';
import { listOutcomeOf, type FakeParameterValue } from './source-parameters';
import { fakeSourceTrials } from './source-trials';

const UNPROCESSABLE = 'Unprocessable Content';

const numbersOf = (value: unknown): Record<string, unknown> =>
  typeof value === 'object' && value !== null ? Object.fromEntries(Object.entries(value)) : {};

// The rules of the domain of the API on the parameters, with their reasons and the field (R4.1.1, R6.3.1).
const refusalOfParameters = (
  source: string,
  declared: readonly FakeSourceParameter[],
  parameters: Record<string, unknown>,
): Response | undefined => {
  for (const [key, value] of Object.entries(parameters)) {
    const parameter = declared.find((candidate) => candidate.key === key);
    if (parameter === undefined) {
      return problem(422, UNPROCESSABLE, `parametro sconosciuto della fonte ${source}: ${key}`);
    }
    if (parameter.kind === 'list') {
      const outcome = listOutcomeOf(parameter, value);
      if ('refusal' in outcome) {
        return problem(422, UNPROCESSABLE, outcome.refusal, { field: key });
      }
      continue;
    }
    if (
      parameter.choices.length > 0 &&
      !parameter.choices.some((choice) => choice.value === value)
    ) {
      const labels = parameter.choices.map((choice) => choice.label).join(', ');
      return problem(422, UNPROCESSABLE, `${parameter.label}: ammessi ${labels}`, {
        field: key,
        choices: parameter.choices.map((choice) => choice.label),
      });
    }
    if (
      typeof value !== 'number' ||
      !Number.isInteger(value) ||
      value < parameter.minimum ||
      value > parameter.maximum
    ) {
      return problem(
        422,
        UNPROCESSABLE,
        `parametro fuori dai valori ammessi: ${parameter.label}, da ${parameter.minimum} a ${parameter.maximum}`,
        { field: key, minimum: parameter.minimum, maximum: parameter.maximum },
      );
    }
  }
  return undefined;
};

/** The trial of an adapter of a source on the fake API, run by its worker (R6.3.1). */
export const sourceTrialHandlers = [
  http.post('*/sources/:name/adapters/:adapter/trials', ({ request, params }) =>
    withUser(request, async (user) => {
      const name = String(params.name);
      const adapterName = String(params.adapter);
      const source = fakeSourceCredentials
        .offeredTo(user.account)
        .find((candidate) => candidate.name === name);
      if (source === undefined) {
        return problem(404, 'Not Found', `fonte non disponibile: ${name}`);
      }
      const adapter = source.adapters.find((candidate) => candidate.name === adapterName);
      if (adapter === undefined) {
        return problem(
          404,
          'Not Found',
          `adapter non disponibile per la fonte ${name}: ${adapterName}`,
        );
      }
      const body = numbersOf(await request.json().catch(() => ({})));
      const parameters = numbersOf(body.parameters);
      const refusal = refusalOfParameters(name, adapter.parameters, parameters);
      if (refusal !== undefined) {
        return refusal;
      }
      const asset = typeof body.asset === 'string' ? body.asset.trim() : '';
      if (source.per_asset && asset === '') {
        return problem(422, UNPROCESSABLE, `scegli l'asset su cui provare la fonte ${name}`, {
          field: 'asset',
        });
      }
      return HttpResponse.json(
        fakeSourceTrials.run({
          account: user.account,
          source: name,
          adapter: adapterName,
          asset: source.per_asset ? asset : null,
          // A list reaches the worker as the API accepted it: ordered and without repetitions.
          parameters: Object.fromEntries(
            Object.entries(parameters).flatMap(([key, value]): [string, FakeParameterValue][] => {
              if (typeof value === 'number') {
                return [[key, value]];
              }
              return Array.isArray(value)
                ? [[key, [...new Set(value as number[])].sort((one, other) => one - other)]]
                : [];
            }),
          ),
        }),
      );
    }),
  ),
];
