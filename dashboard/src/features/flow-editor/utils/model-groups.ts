import type { Model, Provider } from '../api/get-model-catalog';

/** A model of the drop-down: it can be chosen when the key of its provider is registered. */
export type ModelChoice = { readonly name: string; readonly selectable: boolean };

/** The models of one provider, with whether the user registered the key of that provider (R2.3.7). */
export type ModelGroup = {
  readonly provider: string;
  readonly keyRegistered: boolean;
  readonly models: ModelChoice[];
};

const keyRegisteredFor = (providers: Provider[], provider: string): boolean =>
  providers.some((candidate) => candidate.name === provider && candidate.key_registered);

/**
 * The models of the catalog grouped by provider (ADR 0151): a model of a provider without a key cannot be chosen,
 * except the one the flow already has, so that the current choice stays visible and selected.
 */
export const modelGroupsOf = (
  models: Model[],
  providers: Provider[],
  currentModel: string,
): ModelGroup[] =>
  [...new Set(models.map((model) => model.provider))].map((provider) => {
    const keyRegistered = keyRegisteredFor(providers, provider);
    return {
      provider,
      keyRegistered,
      models: models
        .filter((model) => model.provider === provider)
        .map((model) => ({
          name: model.name,
          selectable: keyRegistered || model.name === currentModel,
        })),
    };
  });

/** Whether some provider of the drop-down misses its key, so the form points to the page of the keys. */
export const missesProviderKey = (groups: ModelGroup[]): boolean =>
  groups.some((group) => !group.keyRegistered);
