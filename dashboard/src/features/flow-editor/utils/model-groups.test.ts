import type { Model, Provider } from '../api/get-model-catalog';

import { missesProviderKey, modelGroupsOf } from './model-groups';

const modelOf = (name: string, provider: string): Model => ({ name, provider, parameters: [] });

const MODELS: Model[] = [
  modelOf('openrouter/deepseek-chat', 'openrouter'),
  modelOf('anthropic/claude-sonnet', 'anthropic'),
  modelOf('openrouter/llama', 'openrouter'),
];

const PROVIDERS: Provider[] = [
  { name: 'anthropic', key_registered: false },
  { name: 'openrouter', key_registered: true },
];

describe('modelGroupsOf', () => {
  it('groups the models by provider, in the order the catalog first names each provider', () => {
    const groups = modelGroupsOf(MODELS, PROVIDERS, '');

    expect(groups.map((group) => group.provider)).toEqual(['openrouter', 'anthropic']);
    expect(groups[0]?.models.map((model) => model.name)).toEqual([
      'openrouter/deepseek-chat',
      'openrouter/llama',
    ]);
  });

  it('tells for each group whether the key of its provider is registered', () => {
    const groups = modelGroupsOf(MODELS, PROVIDERS, '');

    expect(groups.map((group) => group.keyRegistered)).toEqual([true, false]);
  });

  it('lets choose only the models of a provider with a key', () => {
    const groups = modelGroupsOf(MODELS, PROVIDERS, '');

    expect(groups.flatMap((group) => group.models)).toEqual([
      { name: 'openrouter/deepseek-chat', selectable: true },
      { name: 'openrouter/llama', selectable: true },
      { name: 'anthropic/claude-sonnet', selectable: false },
    ]);
  });

  it('keeps choosable the model a flow already has, even without the key of its provider', () => {
    const groups = modelGroupsOf(MODELS, PROVIDERS, 'anthropic/claude-sonnet');

    expect(groups[1]?.models).toEqual([{ name: 'anthropic/claude-sonnet', selectable: true }]);
    expect(groups[1]?.keyRegistered).toBe(false);
  });

  it('counts as missing the key of a provider the catalog does not list', () => {
    const groups = modelGroupsOf([modelOf('openai/gpt-4o', 'openai')], PROVIDERS, '');

    expect(groups).toEqual([
      {
        provider: 'openai',
        keyRegistered: false,
        models: [{ name: 'openai/gpt-4o', selectable: false }],
      },
    ]);
  });
});

describe('missesProviderKey', () => {
  it('is true when a group misses the key of its provider', () => {
    expect(missesProviderKey(modelGroupsOf(MODELS, PROVIDERS, ''))).toBe(true);
  });

  it('is false when every provider has its key', () => {
    expect(missesProviderKey(modelGroupsOf(MODELS.slice(0, 1), PROVIDERS, ''))).toBe(false);
  });
});
