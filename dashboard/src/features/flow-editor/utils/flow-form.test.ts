import type { Flow } from '../api/get-flow';

import {
  changesOf,
  creationRequestOf,
  emptyFormValues,
  flowFormSchema,
  formFieldOf,
  formValuesOf,
  type FlowFormValues,
} from './flow-form';

const filled = (changes: Partial<FlowFormValues> = {}): FlowFormValues => ({
  ...emptyFormValues(),
  name: ' alfa ',
  account_id: 'account-principale',
  assets: ['BTC', 'ETH'],
  cycle_minutes: '15',
  model: 'openrouter/deepseek-chat',
  model_parameters: { temperature: '0,7', max_tokens: '', reasoning_effort: 'high' },
  sources: {
    indicatori: { active: true, weight: '2', parameters: { lunghezza_serie: '20' } },
    sentiment: { active: true, weight: '', parameters: {} },
    notizie: { active: false },
    pivot: { active: true },
  },
  instructions: 'prudente',
  max_leverage: '3',
  max_margin_exposure_percent: '10',
  default_take_profit_percent: '10',
  allocated_capital: '300',
  ...changes,
});

const FLOW: Flow = {
  id: 'flow-alfa',
  name: 'alfa',
  account_id: 'account-principale',
  status: 'fermo',
  version: 1,
  assets: ['BTC', 'ETH'],
  cycle_minutes: 15,
  model: { name: 'openrouter/deepseek-chat', parameters: { temperature: '0.7' } },
  sources: [
    { name: 'indicatori', weight: 2, parameters: { lunghezza_serie: 10 } },
    { name: 'sentiment', weight: 1, parameters: {} },
  ],
  instructions: 'prudente',
  risk_limits: {
    max_leverage: 3,
    max_margin_exposure_percent: '10',
    max_value_exposure_percent: null,
  },
  default_stop_loss_percent: '5',
  default_take_profit_percent: null,
  allocated_capital: '300',
  bring_to_minimum: false,
  system_prompt: '{instructions} su {assets}',
  system_prompt_is_default: true,
  system_prompt_placeholders: [{ name: 'assets', description: 'gli asset del flusso' }],
};

const CUSTOM: Flow = { ...FLOW, system_prompt: '{instructions}', system_prompt_is_default: false };

describe('creationRequestOf', () => {
  it('sends the configuration the user filled, leaving to the API the defaults of the blank values', () => {
    expect(creationRequestOf(filled())).toEqual({
      name: 'alfa',
      account_id: 'account-principale',
      assets: ['BTC', 'ETH'],
      cycle_minutes: 15,
      model: 'openrouter/deepseek-chat',
      model_parameters: { temperature: '0.7', reasoning_effort: 'high' },
      sources: [
        { name: 'indicatori', weight: 2, parameters: { lunghezza_serie: 20 } },
        { name: 'sentiment', weight: null, parameters: {} },
        { name: 'pivot', weight: null, parameters: {} },
      ],
      instructions: 'prudente',
      max_leverage: 3,
      max_margin_exposure_percent: '10',
      max_value_exposure_percent: null,
      default_stop_loss_percent: null,
      default_take_profit_percent: '10',
      allocated_capital: '300',
      bring_to_minimum: false,
      system_prompt: null,
    });
  });

  it('sends the system prompt the user wrote instead of the default', () => {
    const values = filled({ system_prompt: '{instructions}', system_prompt_default: false });

    expect(creationRequestOf(values).system_prompt).toBe('{instructions}');
  });

  it('leaves out a blank capital, so the API names it as missing', () => {
    const request = creationRequestOf(filled({ allocated_capital: ' ', cycle_minutes: '' }));

    expect(request).not.toHaveProperty('allocated_capital');
    expect(request.cycle_minutes).toBeNull();
  });
});

describe('formValuesOf', () => {
  it('fills the form with the configuration version in force', () => {
    expect(formValuesOf(FLOW)).toEqual({
      name: 'alfa',
      account_id: 'account-principale',
      assets: ['BTC', 'ETH'],
      cycle_minutes: '15',
      model: 'openrouter/deepseek-chat',
      model_parameters: { temperature: '0.7' },
      sources: {
        indicatori: { active: true, weight: '2', parameters: { lunghezza_serie: '10' } },
        sentiment: { active: true, weight: '1', parameters: {} },
      },
      instructions: 'prudente',
      max_leverage: '3',
      max_margin_exposure_percent: '10',
      max_value_exposure_percent: '',
      default_stop_loss_percent: '5',
      default_take_profit_percent: '',
      allocated_capital: '300',
      bring_to_minimum: false,
      system_prompt: '',
      system_prompt_default: true,
    });
  });

  it('fills the system prompt the user wrote, apart from the default', () => {
    expect(formValuesOf(CUSTOM)).toMatchObject({
      system_prompt: '{instructions}',
      system_prompt_default: false,
    });
  });

  it('leaves blank a maximum leverage the flow does not have', () => {
    const flow = { ...FLOW, risk_limits: { ...FLOW.risk_limits, max_leverage: null } };

    expect(formValuesOf(flow).max_leverage).toBe('');
  });
});

describe('changesOf', () => {
  it('changes nothing when the user changed nothing', () => {
    expect(changesOf(FLOW, formValuesOf(FLOW))).toEqual({ settings: {} });
  });

  it('sends only the settings that changed, the sources whole', () => {
    const values = formValuesOf(FLOW);
    values.sources.sentiment = { active: true, weight: '3', parameters: {} };
    values.instructions = 'audace';

    expect(changesOf(FLOW, values)).toEqual({
      settings: {
        sources: [
          { name: 'indicatori', weight: 2, parameters: { lunghezza_serie: 10 } },
          { name: 'sentiment', weight: 3, parameters: {} },
        ],
        instructions: 'audace',
      },
    });
  });

  it('sends a new model with its parameters, and new parameters alone', () => {
    const otherModel = { ...formValuesOf(FLOW), model: 'openai/gpt-4o', model_parameters: {} };
    const otherParameters = { ...formValuesOf(FLOW), model_parameters: { temperature: '1' } };

    expect(changesOf(FLOW, otherModel).settings).toEqual({
      model: 'openai/gpt-4o',
      model_parameters: {},
    });
    expect(changesOf(FLOW, otherParameters).settings).toEqual({
      model_parameters: { temperature: '1' },
    });
  });

  it('does not send a setting the user emptied, which the API would keep anyway', () => {
    const values = { ...formValuesOf(FLOW), cycle_minutes: '', max_leverage: '' };

    expect(changesOf(FLOW, values)).toEqual({ settings: {} });
  });

  // ADR limite-di-esposizione-tolto-con-un-null-inviato-apposta: the emptied limit goes as null, which the API reads as removed.
  it('sends null for an exposure limit the user emptied, so the API removes it', () => {
    const both: Flow = {
      ...FLOW,
      risk_limits: { ...FLOW.risk_limits, max_value_exposure_percent: '40' },
    };
    const withoutValue = { ...formValuesOf(both), max_value_exposure_percent: ' ' };
    const withoutMargin = { ...formValuesOf(both), max_margin_exposure_percent: '' };

    expect(changesOf(both, withoutValue)).toEqual({
      settings: { max_value_exposure_percent: null },
    });
    expect(changesOf(both, withoutMargin)).toEqual({
      settings: { max_margin_exposure_percent: null },
    });
    expect(changesOf(FLOW, formValuesOf(FLOW))).toEqual({ settings: {} });
  });

  // R3.1.2: the stop loss is mandatory, so an emptied one keeps the value in force; the take profit may go.
  it('sends the protection defaults the user changed, and null for a take profit the user emptied', () => {
    const withTakeProfit: Flow = { ...FLOW, default_take_profit_percent: '8' };
    const changed = { ...formValuesOf(withTakeProfit), default_stop_loss_percent: '3,5' };
    const emptied = {
      ...formValuesOf(withTakeProfit),
      default_stop_loss_percent: '',
      default_take_profit_percent: ' ',
    };

    expect(changesOf(withTakeProfit, changed)).toEqual({
      settings: { default_stop_loss_percent: '3.5' },
    });
    expect(changesOf(withTakeProfit, emptied)).toEqual({
      settings: { default_take_profit_percent: null },
    });
  });

  it('sends a system prompt the user wrote, and null to go back to the default', () => {
    const written = {
      ...formValuesOf(FLOW),
      system_prompt: 'audace',
      system_prompt_default: false,
    };
    const restored = { ...formValuesOf(CUSTOM), system_prompt: '', system_prompt_default: true };

    expect(changesOf(FLOW, written)).toEqual({ settings: { system_prompt: 'audace' } });
    expect(changesOf(CUSTOM, restored)).toEqual({ settings: { system_prompt: null } });
    expect(changesOf(CUSTOM, formValuesOf(CUSTOM))).toEqual({ settings: {} });
  });

  it('keeps the capital apart, as it changes through its own request', () => {
    const values = {
      ...formValuesOf(FLOW),
      allocated_capital: '350,5',
      assets: ['BTC', 'ETH', 'SOL'],
    };

    expect(changesOf(FLOW, values)).toEqual({
      settings: { assets: ['BTC', 'ETH', 'SOL'] },
      capital: '350.5',
    });
  });
});

describe('formFieldOf', () => {
  it('places a refusal on the field of the form named after the setting of the API', () => {
    expect(formFieldOf('allocated_capital')).toBe('allocated_capital');
    expect(formFieldOf('model_parameters')).toBe('model_parameters');
  });

  it('places nowhere a setting the form does not have', () => {
    expect(formFieldOf('requestId')).toBeUndefined();
  });
});

describe('flowFormSchema', () => {
  it('admits blank numbers and numbers with a decimal comma or point', () => {
    expect(flowFormSchema.safeParse(filled({ allocated_capital: '10,5' })).success).toBe(true);
    expect(flowFormSchema.safeParse(filled({ cycle_minutes: '' })).success).toBe(true);
  });

  it('refuses a number that is not one, beside its field', () => {
    const parsed = flowFormSchema.safeParse(filled({ max_leverage: 'tre' }));

    expect(parsed.error?.issues.map((issue) => [issue.path.join('.'), issue.message])).toEqual([
      ['max_leverage', 'Inserisci un numero'],
    ]);
  });
});
