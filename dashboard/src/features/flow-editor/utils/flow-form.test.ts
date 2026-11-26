import type { Flow } from '../api/get-flow';

import {
  adapterKeyOf,
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
    indicatori: {
      active: true,
      adapters: {
        Hyperliquid: { active: true, weight: '2', parameters: { lunghezza_serie: '20' } },
      },
    },
    sentiment: {
      active: true,
      adapters: {
        'alternative%2Eme': { active: true, weight: '', parameters: {} },
        CoinMarketCap: { active: false },
      },
    },
    notizie: { active: false, adapters: { RSS: { active: true, weight: '4' } } },
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
    {
      name: 'indicatori',
      adapters: [{ name: 'Hyperliquid', weight: 2, parameters: { lunghezza_serie: 10 } }],
    },
    { name: 'sentiment', adapters: [{ name: 'alternative.me', weight: 1, parameters: {} }] },
  ],
  instructions: 'prudente',
  risk_limits: {
    max_leverage: 3,
    max_margin_exposure_percent: '10',
    max_value_exposure_percent: null,
    max_total_margin_exposure_percent: null,
    max_total_value_exposure_percent: null,
  },
  default_stop_loss_percent: '5',
  default_take_profit_percent: null,
  minimum_confidence: null,
  allocated_capital: '300',
  bring_to_minimum: false,
  system_prompt: '{instructions} su {assets}',
  system_prompt_is_default: true,
  system_prompt_placeholders: [{ name: 'assets', description: 'gli asset del flusso' }],
  max_consecutive_failures: null,
  max_daily_loss_percent: null,
  max_drawdown_percent: null,
  openings_resume: 'manual',
  memory: {
    active: false,
    decisions: 10,
    days: 30,
    text_length: 160,
    all_decisions: false,
    summary: false,
    other_assets: false,
  },
  trailing_stop: {
    distance_percent: null,
    activation_percent: null,
    breakeven_percent: null,
    max_profit_in_context: false,
  },
  consecutive_loss_limit: null,
};

const CUSTOM: Flow = { ...FLOW, system_prompt: '{instructions}', system_prompt_is_default: false };

// A draft as an imported file makes it: the strategy alone (R2.5.2).
const DRAFT: Flow = {
  ...FLOW,
  status: 'bozza',
  account_id: null,
  allocated_capital: null,
  assets: [],
};

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
        {
          name: 'indicatori',
          adapters: [{ name: 'Hyperliquid', weight: 2, parameters: { lunghezza_serie: 20 } }],
        },
        { name: 'sentiment', adapters: [{ name: 'alternative.me', weight: null, parameters: {} }] },
        { name: 'pivot', adapters: [] },
      ],
      instructions: 'prudente',
      max_leverage: 3,
      max_margin_exposure_percent: '10',
      max_value_exposure_percent: null,
      max_total_margin_exposure_percent: null,
      max_total_value_exposure_percent: null,
      default_stop_loss_percent: null,
      default_take_profit_percent: '10',
      minimum_confidence: null,
      allocated_capital: '300',
      bring_to_minimum: false,
      system_prompt: null,
      max_consecutive_failures: null,
      max_daily_loss_percent: null,
      max_drawdown_percent: null,
      openings_resume: 'manual',
      memory: {
        active: false,
        decisions: null,
        days: null,
        text_length: null,
        all_decisions: null,
        summary: null,
        other_assets: null,
        unlimited_text_length: false,
      },
      trailing_stop: {
        distance_percent: null,
        activation_percent: null,
        breakeven_percent: null,
        max_profit_in_context: false,
        remove_distance: true,
        remove_activation: true,
        remove_breakeven: true,
      },
      consecutive_loss_limit: {
        max_consecutive_losses: null,
        loss_window_hours: null,
        block_minutes: null,
        count_scope: null,
        remove_limit: true,
      },
    });
  });

  // ADR blocco-delle-riaperture-nella-dashboard: the three blank take the limit away, the API checks the values.
  it('sends the block of the reopenings the user typed, with its scope (R5.5.2)', () => {
    const consecutive_loss_limit = {
      max_consecutive_losses: ' 2 ',
      loss_window_hours: '24',
      block_minutes: '120',
      count_scope: 'flusso' as const,
    };

    expect(creationRequestOf(filled({ consecutive_loss_limit })).consecutive_loss_limit).toEqual({
      max_consecutive_losses: 2,
      loss_window_hours: 24,
      block_minutes: 120,
      count_scope: 'flusso',
      remove_limit: false,
    });
  });

  it('sends a part left blank as missing, so the API says the three go together (R5.5.2)', () => {
    const consecutive_loss_limit = {
      max_consecutive_losses: '2',
      loss_window_hours: '',
      block_minutes: '',
      count_scope: 'asset' as const,
    };

    expect(creationRequestOf(filled({ consecutive_loss_limit })).consecutive_loss_limit).toEqual({
      max_consecutive_losses: 2,
      loss_window_hours: null,
      block_minutes: null,
      count_scope: 'asset',
      remove_limit: false,
    });
  });

  // ADR stop-che-segue-il-prezzo-nella-dashboard: blank parts stay empty, the API checks the values.
  it('sends the stop that follows the price the user typed (R5.5.1)', () => {
    const trailing_stop = {
      distance_percent: ' 2 ',
      activation_percent: '3',
      breakeven_percent: '1,5',
      max_profit_in_context: true,
    };

    expect(creationRequestOf(filled({ trailing_stop })).trailing_stop).toEqual({
      distance_percent: '2',
      activation_percent: '3',
      breakeven_percent: '1.5',
      max_profit_in_context: true,
      remove_distance: false,
      remove_activation: false,
      remove_breakeven: false,
    });
  });

  it('sends the memory the user turned on, with its decisions and days (R5.3.4)', () => {
    const memory = { active: true, decisions: ' 5 ', days: '14' };

    expect(creationRequestOf(filled({ memory })).memory).toEqual({
      active: true,
      decisions: 5,
      days: 14,
      text_length: null,
      all_decisions: false,
      summary: false,
      other_assets: false,
      unlimited_text_length: false,
    });
  });

  it('sends the length of the motive and every decision, the length taken away by an unlimited one (R5.3.5)', () => {
    const typed = { active: true, text_length: ' 80 ', all_decisions: true };
    const unlimited = { active: true, text_length: undefined, unlimited_text_length: true };

    expect(creationRequestOf(filled({ memory: typed })).memory).toMatchObject({
      text_length: 80,
      all_decisions: true,
      unlimited_text_length: false,
    });
    expect(creationRequestOf(filled({ memory: unlimited })).memory).toMatchObject({
      text_length: null,
      unlimited_text_length: true,
    });
  });

  it('sends the summary and the other assets the user switched on (R5.3.7)', () => {
    const memory = { active: true, summary: true, other_assets: true };

    expect(creationRequestOf(filled({ memory })).memory).toMatchObject({
      summary: true,
      other_assets: true,
    });
    expect(
      changesOf(FLOW, {
        ...formValuesOf(FLOW),
        memory: { ...formValuesOf(FLOW).memory, active: true, summary: true },
      }),
    ).toEqual(
      expect.objectContaining({
        settings: { memory: expect.objectContaining({ summary: true, other_assets: false }) },
      }),
    );
  });

  it('sends the memory off with decisions and days left to the version in force, as the form disables them', () => {
    const memory = { active: false, decisions: undefined, days: undefined };

    expect(creationRequestOf(filled({ memory })).memory).toEqual({
      active: false,
      decisions: null,
      days: null,
      text_length: null,
      all_decisions: null,
      summary: null,
      other_assets: null,
      unlimited_text_length: false,
    });
  });

  it('sends the maximum losses the user typed, with a decimal point, and the resume chosen', () => {
    const request = creationRequestOf(
      filled({
        max_daily_loss_percent: ' 5 ',
        max_drawdown_percent: '12,5',
        openings_resume: 'next_day',
      }),
    );

    expect([
      request.max_daily_loss_percent,
      request.max_drawdown_percent,
      request.openings_resume,
    ]).toEqual(['5', '12.5', 'next_day']);
  });

  // ADR esposizione-complessiva-nel-controllo-del-rischio: the overall limits travel as the limits per operation.
  it('sends the overall exposure limits the user typed, with a decimal point', () => {
    const request = creationRequestOf(
      filled({
        max_total_margin_exposure_percent: ' 30 ',
        max_total_value_exposure_percent: '150,5',
      }),
    );

    expect([
      request.max_total_margin_exposure_percent,
      request.max_total_value_exposure_percent,
    ]).toEqual(['30', '150.5']);
  });

  it('sends the maximum of consecutive failed cycles the user typed', () => {
    expect(
      creationRequestOf(filled({ max_consecutive_failures: ' 3 ' })).max_consecutive_failures,
    ).toBe(3);
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

describe('adapterKeyOf', () => {
  it('keeps the name of an adapter whole as the key of a field, its dots encoded', () => {
    expect([adapterKeyOf('alternative.me'), adapterKeyOf('CoinMarketCap')]).toEqual([
      'alternative%2Eme',
      'CoinMarketCap',
    ]);
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
        indicatori: {
          active: true,
          adapters: {
            Hyperliquid: {
              active: true,
              weight: '2',
              parameters: { lunghezza_serie: '10' },
              lists: {},
            },
          },
        },
        sentiment: {
          active: true,
          adapters: {
            'alternative%2Eme': { active: true, weight: '1', parameters: {}, lists: {} },
          },
        },
      },
      instructions: 'prudente',
      max_leverage: '3',
      max_margin_exposure_percent: '10',
      max_value_exposure_percent: '',
      max_total_margin_exposure_percent: '',
      max_total_value_exposure_percent: '',
      default_stop_loss_percent: '5',
      default_take_profit_percent: '',
      minimum_confidence: '',
      allocated_capital: '300',
      bring_to_minimum: false,
      system_prompt: '',
      system_prompt_default: true,
      max_consecutive_failures: '',
      max_daily_loss_percent: '',
      max_drawdown_percent: '',
      openings_resume: 'manual',
      memory: {
        active: false,
        decisions: '10',
        days: '30',
        text_length: '160',
        unlimited_text_length: false,
        all_decisions: false,
        summary: false,
        other_assets: false,
      },
      trailing_stop: {
        distance_percent: '',
        activation_percent: '',
        breakeven_percent: '',
        max_profit_in_context: false,
      },
      consecutive_loss_limit: {
        max_consecutive_losses: '',
        loss_window_hours: '',
        block_minutes: '',
        count_scope: 'asset',
      },
    });
  });

  it('fills the stop that follows the price of the flow (R5.5.1)', () => {
    const flow: Flow = {
      ...FLOW,
      trailing_stop: {
        distance_percent: '2',
        activation_percent: null,
        breakeven_percent: '1.5',
        max_profit_in_context: true,
      },
    };

    expect(formValuesOf(flow).trailing_stop).toEqual({
      distance_percent: '2',
      activation_percent: '',
      breakeven_percent: '1.5',
      max_profit_in_context: true,
    });
  });

  it('fills the block of the reopenings of the flow, and blanks with the scope of the asset without one (R5.5.2)', () => {
    const flow: Flow = {
      ...FLOW,
      consecutive_loss_limit: {
        max_consecutive_losses: 2,
        loss_window_hours: 24,
        block_minutes: 120,
        count_scope: 'flusso',
      },
    };

    expect(formValuesOf(flow).consecutive_loss_limit).toEqual({
      max_consecutive_losses: '2',
      loss_window_hours: '24',
      block_minutes: '120',
      count_scope: 'flusso',
    });
    expect(formValuesOf(FLOW).consecutive_loss_limit).toEqual({
      max_consecutive_losses: '',
      loss_window_hours: '',
      block_minutes: '',
      count_scope: 'asset',
    });
  });

  it('fills the maximum losses and the resume of the flow', () => {
    const flow: Flow = {
      ...FLOW,
      max_daily_loss_percent: '5',
      max_drawdown_percent: '10',
      openings_resume: 'next_day',
    };

    expect(formValuesOf(flow)).toMatchObject({
      max_daily_loss_percent: '5',
      max_drawdown_percent: '10',
      openings_resume: 'next_day',
    });
  });

  it('fills the overall exposure limits of the flow', () => {
    const flow: Flow = {
      ...FLOW,
      risk_limits: {
        ...FLOW.risk_limits,
        max_total_margin_exposure_percent: '30',
        max_total_value_exposure_percent: '0.5',
      },
    };

    expect(formValuesOf(flow)).toMatchObject({
      max_total_margin_exposure_percent: '30',
      max_total_value_exposure_percent: '0.5',
    });
  });

  it('fills the maximum of consecutive failed cycles of the flow', () => {
    expect(formValuesOf({ ...FLOW, max_consecutive_failures: 4 }).max_consecutive_failures).toBe(
      '4',
    );
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

// ADR parametri-delle-fonti-come-liste-libere: a list travels apart from the whole numbers, as typed and as saved.
describe('the list parameters of a source', () => {
  const WITH_LIST: Flow = {
    ...FLOW,
    sources: [
      {
        name: 'indicatori',
        adapters: [
          {
            name: 'Hyperliquid',
            weight: 2,
            parameters: { lunghezza_serie: 10, tendenza_giorni: [7, 30], medie_periodi: [] },
          },
        ],
      },
    ],
  };

  it('fills a saved list as the user types it, an empty one as a blank field', () => {
    expect(formValuesOf(WITH_LIST).sources.indicatori?.adapters?.Hyperliquid).toEqual({
      active: true,
      weight: '2',
      parameters: { lunghezza_serie: '10' },
      lists: { tendenza_giorni: '7, 30', medie_periodi: '' },
    });
  });

  it('sends every list typed as its numbers, a blank one as the empty list', () => {
    const values = filled({
      sources: {
        indicatori: {
          active: true,
          adapters: {
            Hyperliquid: {
              active: true,
              weight: '2',
              parameters: { lunghezza_serie: '20' },
              lists: { tendenza_giorni: '7, 30 90', medie_periodi: ' ' },
            },
          },
        },
      },
    });

    expect(creationRequestOf(values).sources).toEqual([
      {
        name: 'indicatori',
        adapters: [
          {
            name: 'Hyperliquid',
            weight: 2,
            parameters: { lunghezza_serie: 20, tendenza_giorni: [7, 30, 90], medie_periodi: [] },
          },
        ],
      },
    ]);
  });

  it('changes nothing when the lists stay as saved', () => {
    expect(changesOf(WITH_LIST, formValuesOf(WITH_LIST))).toEqual({ settings: {} });
  });

  it('checks only the shape of a list, leaving its rules to the API', () => {
    const shaped = (typed: string) =>
      flowFormSchema.safeParse(
        filled({
          sources: {
            indicatori: {
              active: true,
              adapters: { Hyperliquid: { active: true, lists: { tendenza_giorni: typed } } },
            },
          },
        }),
      ).success;

    expect([shaped('7, 30'), shaped('0, 99999'), shaped('7; 30')]).toEqual([true, true, false]);
  });
});

describe('changesOf', () => {
  it('changes nothing when the user changed nothing', () => {
    expect(changesOf(FLOW, formValuesOf(FLOW))).toEqual({ settings: {} });
  });

  it('sends only the settings that changed, the sources whole', () => {
    const values = formValuesOf(FLOW);
    values.sources.sentiment = {
      active: true,
      adapters: {
        'alternative%2Eme': { active: true, weight: '3', parameters: {} },
        CoinMarketCap: { active: true, weight: '7' },
      },
    };
    values.instructions = 'audace';

    expect(changesOf(FLOW, values)).toEqual({
      settings: {
        sources: [
          {
            name: 'indicatori',
            adapters: [{ name: 'Hyperliquid', weight: 2, parameters: { lunghezza_serie: 10 } }],
          },
          {
            name: 'sentiment',
            adapters: [
              { name: 'alternative.me', weight: 3, parameters: {} },
              { name: 'CoinMarketCap', weight: 7, parameters: {} },
            ],
          },
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

  it('sends a new overall exposure limit, and null for an emptied one so the API removes it', () => {
    const limited: Flow = {
      ...FLOW,
      risk_limits: { ...FLOW.risk_limits, max_total_value_exposure_percent: '100' },
    };

    expect(
      changesOf(FLOW, { ...formValuesOf(FLOW), max_total_margin_exposure_percent: '30' }),
    ).toEqual({ settings: { max_total_margin_exposure_percent: '30' } });
    expect(
      changesOf(limited, { ...formValuesOf(limited), max_total_value_exposure_percent: '' }),
    ).toEqual({ settings: { max_total_value_exposure_percent: null } });
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

  // R3.1.4: the minimum confidence is optional, so an emptied one is removed with a null.
  it('sends the minimum confidence the user set, and null for one the user emptied', () => {
    const withMinimum: Flow = { ...FLOW, minimum_confidence: 60 };

    expect(formValuesOf(withMinimum).minimum_confidence).toBe('60');
    expect(changesOf(FLOW, { ...formValuesOf(FLOW), minimum_confidence: ' 75 ' })).toEqual({
      settings: { minimum_confidence: 75 },
    });
    expect(
      changesOf(withMinimum, { ...formValuesOf(withMinimum), minimum_confidence: '' }),
    ).toEqual({
      settings: { minimum_confidence: null },
    });
  });

  it('changes nothing for the memory off, whose decisions and days the disabled fields do not give', () => {
    const memory = { active: false, decisions: undefined, days: undefined };

    expect(changesOf(FLOW, { ...formValuesOf(FLOW), memory })).toEqual({ settings: {} });
  });

  it('sends the whole memory when the user changed a part of it (R5.3.4)', () => {
    const memory = { ...formValuesOf(FLOW).memory, active: true, days: '14' };

    expect(changesOf(FLOW, { ...formValuesOf(FLOW), memory })).toEqual({
      settings: {
        memory: {
          active: true,
          decisions: 10,
          days: 14,
          text_length: 160,
          all_decisions: false,
          summary: false,
          other_assets: false,
          unlimited_text_length: false,
        },
      },
    });
  });

  it('changes nothing for the stop that follows the price left as it is (R5.5.1)', () => {
    expect(changesOf(FLOW, formValuesOf(FLOW))).toEqual({ settings: {} });
  });

  it('sends the whole stop that follows the price when the user changed a part, an emptied part removed', () => {
    const following: Flow = {
      ...FLOW,
      trailing_stop: { ...FLOW.trailing_stop, distance_percent: '2', activation_percent: '3' },
    };
    const trailing_stop = { ...formValuesOf(following).trailing_stop, activation_percent: ' ' };

    expect(changesOf(following, { ...formValuesOf(following), trailing_stop })).toEqual({
      settings: {
        trailing_stop: {
          distance_percent: '2',
          activation_percent: null,
          breakeven_percent: null,
          max_profit_in_context: false,
          remove_distance: false,
          remove_activation: true,
          remove_breakeven: true,
        },
      },
    });
  });

  it('sends the block of the reopenings the user set, and its removal when the user emptied it (R5.5.2)', () => {
    const limited: Flow = {
      ...FLOW,
      consecutive_loss_limit: {
        max_consecutive_losses: 2,
        loss_window_hours: 24,
        block_minutes: 120,
        count_scope: 'asset',
      },
    };
    const set = { ...formValuesOf(FLOW).consecutive_loss_limit, max_consecutive_losses: '2' };
    const emptied = { ...formValuesOf(limited).consecutive_loss_limit, loss_window_hours: '' };
    const values = { max_consecutive_losses: '', loss_window_hours: '', block_minutes: '' };
    const removed = { ...formValuesOf(limited).consecutive_loss_limit, ...values };

    expect(changesOf(limited, formValuesOf(limited))).toEqual({ settings: {} });
    expect(
      changesOf(FLOW, {
        ...formValuesOf(FLOW),
        consecutive_loss_limit: { ...set, loss_window_hours: '24', block_minutes: '120' },
      }).settings.consecutive_loss_limit,
    ).toEqual({
      max_consecutive_losses: 2,
      loss_window_hours: 24,
      block_minutes: 120,
      count_scope: 'asset',
      remove_limit: false,
    });
    expect(
      changesOf(limited, { ...formValuesOf(limited), consecutive_loss_limit: emptied }).settings
        .consecutive_loss_limit?.loss_window_hours,
    ).toBeNull();
    expect(
      changesOf(limited, { ...formValuesOf(limited), consecutive_loss_limit: removed }).settings
        .consecutive_loss_limit,
    ).toEqual({
      max_consecutive_losses: null,
      loss_window_hours: null,
      block_minutes: null,
      count_scope: null,
      remove_limit: true,
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

  // ADR limite-di-esposizione-tolto-con-un-null-inviato-apposta, applied to the maximum of consecutive failed cycles.
  it('sends a new maximum of consecutive failed cycles, and null for an emptied one so the API removes it', () => {
    const limited = { ...FLOW, max_consecutive_failures: 3 };

    expect(changesOf(FLOW, { ...formValuesOf(FLOW), max_consecutive_failures: '5' })).toEqual({
      settings: { max_consecutive_failures: 5 },
    });
    expect(changesOf(limited, { ...formValuesOf(limited), max_consecutive_failures: '' })).toEqual({
      settings: { max_consecutive_failures: null },
    });
    expect(changesOf(FLOW, { ...formValuesOf(FLOW), max_consecutive_failures: '' })).toEqual({
      settings: {},
    });
  });

  // ADR limite-di-esposizione-tolto-con-un-null-inviato-apposta, applied to the maximum losses (R3.2.2).
  it('sends new maximum losses and resume, and null for an emptied loss so the API removes it', () => {
    const limited: Flow = { ...FLOW, max_daily_loss_percent: '5', max_drawdown_percent: '10' };

    expect(
      changesOf(FLOW, {
        ...formValuesOf(FLOW),
        max_daily_loss_percent: '5',
        openings_resume: 'next_day',
      }),
    ).toEqual({ settings: { max_daily_loss_percent: '5', openings_resume: 'next_day' } });
    expect(changesOf(limited, { ...formValuesOf(limited), max_drawdown_percent: '' })).toEqual({
      settings: { max_drawdown_percent: null },
    });
  });

  it('sends a new name, trimmed, with the settings (ADR nome-del-flusso-modificabile)', () => {
    const values = { ...formValuesOf(FLOW), name: ' beta ', instructions: 'audace' };

    expect(changesOf(FLOW, values)).toEqual({ settings: { name: 'beta', instructions: 'audace' } });
  });

  it('sends account, capital and assets of a draft with its configuration (ADR assegnazione-della-bozza)', () => {
    const values = {
      ...formValuesOf(DRAFT),
      account_id: 'account-secondario',
      allocated_capital: '200,5',
      assets: ['ETH'],
    };

    expect(changesOf(DRAFT, values)).toEqual({
      settings: { account_id: 'account-secondario', assets: ['ETH'], allocated_capital: '200.5' },
    });
  });

  it('sends nothing for a draft whose account, capital and assets are left blank', () => {
    expect(changesOf(DRAFT, formValuesOf(DRAFT))).toEqual({ settings: {} });
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

  it('places a refusal of the memory on its decisions or its days', () => {
    expect(formFieldOf('memory.decisions')).toBe('memory.decisions');
    expect(formFieldOf('memory.days')).toBe('memory.days');
  });

  it('places a refusal of the stop that follows the price on its part (R5.5.1)', () => {
    expect(formFieldOf('trailing_stop.distance_percent')).toBe('trailing_stop.distance_percent');
    expect(formFieldOf('trailing_stop.activation_percent')).toBe(
      'trailing_stop.activation_percent',
    );
    expect(formFieldOf('trailing_stop.breakeven_percent')).toBe('trailing_stop.breakeven_percent');
  });

  it('places a refusal of the block of the reopenings on its part (R5.5.2)', () => {
    expect(formFieldOf('consecutive_loss_limit.max_consecutive_losses')).toBe(
      'consecutive_loss_limit.max_consecutive_losses',
    );
    expect(formFieldOf('consecutive_loss_limit.loss_window_hours')).toBe(
      'consecutive_loss_limit.loss_window_hours',
    );
    expect(formFieldOf('consecutive_loss_limit.block_minutes')).toBe(
      'consecutive_loss_limit.block_minutes',
    );
    expect(formFieldOf('consecutive_loss_limit.count_scope')).toBe(
      'consecutive_loss_limit.count_scope',
    );
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

  it.each(['0', '101', '0,05'])(
    'refuses a maximum loss of %s percent with the reason of the API, beside its field',
    (percent) => {
      const parsed = flowFormSchema.safeParse(
        filled({ max_daily_loss_percent: percent, max_drawdown_percent: percent }),
      );

      expect(parsed.error?.issues.map((issue) => [issue.path.join('.'), issue.message])).toEqual([
        ['max_daily_loss_percent', 'la perdita massima va da 0,1 a 100'],
        ['max_drawdown_percent', 'la perdita massima va da 0,1 a 100'],
      ]);
    },
  );

  it('admits a blank maximum loss and the bounds of the interval', () => {
    expect(
      flowFormSchema.safeParse(
        filled({ max_daily_loss_percent: '0,1', max_drawdown_percent: '100' }),
      ).success,
    ).toBe(true);
    expect(flowFormSchema.safeParse(filled({ max_daily_loss_percent: ' ' })).success).toBe(true);
  });

  it('refuses a number that is not one, beside its field', () => {
    const parsed = flowFormSchema.safeParse(filled({ max_leverage: 'tre' }));

    expect(parsed.error?.issues.map((issue) => [issue.path.join('.'), issue.message])).toEqual([
      ['max_leverage', 'Inserisci un numero'],
    ]);
  });
});
