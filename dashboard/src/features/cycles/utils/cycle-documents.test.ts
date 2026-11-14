import { contextOf, decisionLabelsOf, decisionsOf, sourcesOf } from './cycle-documents';

const OPENING = {
  tipo: 'Decision',
  asset: 'BTC',
  action: 'apri',
  reasoning: 'RSI in risalita',
  opening: { tipo: 'TradeOpening', direction: 'long', margin_fraction: '0.1', leverage: 2 },
};

const AGENT_DECISION = {
  risposta: '{"decisions": []}',
  decisioni: [
    OPENING,
    { tipo: 'Decision', asset: 'ETH', action: 'mantieni', reasoning: 'laterale', opening: null },
  ],
  scartate: [{ tipo: 'DiscardedDecision', asset: 'SOL', reason: 'leva assente' }],
  mancanti: ['DOGE'],
};

describe('decisionsOf', () => {
  it('reads the decisions, the raw answer, the discarded and the missing assets of the agent', () => {
    const decisions = decisionsOf(AGENT_DECISION);

    expect(decisions?.risposta).toBe('{"decisions": []}');
    expect(decisions?.decisioni.map((decision) => decision.reasoning)).toEqual([
      'RSI in risalita',
      'laterale',
    ]);
    expect(decisions?.scartate).toHaveLength(1);
    expect(decisions?.mancanti).toEqual(['DOGE']);
  });

  it('gives nothing for a document of another shape', () => {
    expect(decisionsOf({ risultato: [] })).toBeUndefined();
    expect(decisionsOf(null)).toBeUndefined();
  });
});

describe('decisionLabelsOf', () => {
  it('names each decision by action, direction of an opening and asset', () => {
    expect(decisionLabelsOf(AGENT_DECISION)).toEqual(['apri long BTC', 'mantieni ETH']);
  });

  it('names no decision when the cycle never got to the agent', () => {
    expect(decisionLabelsOf(null)).toEqual([]);
  });
});

describe('contextOf', () => {
  it('reads the messages sent to the agent, each with its role', () => {
    expect(contextOf({ messaggi: [{ ruolo: 'system', contenuto: 'regole' }] })).toEqual([
      { ruolo: 'system', contenuto: 'regole' },
    ]);
  });

  it('gives nothing for a document of another shape', () => {
    expect(contextOf({ messaggi: 'testo' })).toBeUndefined();
  });
});

describe('sourcesOf', () => {
  it('reads the data of each source as recorded', () => {
    expect(sourcesOf({ fonti: [{ fonte: 'indicatori', dati: [{ rsi: '31' }] }] })).toEqual([
      { fonte: 'indicatori', dati: [{ rsi: '31' }] },
    ]);
  });

  it('gives nothing for a document of another shape', () => {
    expect(sourcesOf({ fonti: [{ dati: [] }] })).toBeUndefined();
  });
});
