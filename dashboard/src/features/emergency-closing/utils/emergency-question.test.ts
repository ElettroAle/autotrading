import { describe, expect, it } from 'vitest';

import { emergencyQuestion, scopeQuery } from './emergency-question';

const FLOW = { kind: 'flow', flowId: 'flow-alfa', flowName: 'alfa' } as const;
const ACCOUNT = { kind: 'account', accountId: 'account-test-1', accountName: 'test-1' } as const;
const ALL = { kind: 'all' } as const;

describe('emergencyQuestion', () => {
  it('names the flow and puts it in pause', () => {
    expect(emergencyQuestion(FLOW, 1)).toBe(
      'Chiudere 1 posizione del flusso alfa e metterlo in pausa?',
    );
  });

  it('names the account whose flows close and pause', () => {
    expect(emergencyQuestion(ACCOUNT, 2)).toBe(
      'Chiudere 2 posizioni dei flussi del conto test-1 e metterli in pausa?',
    );
  });

  it('names every flow', () => {
    expect(emergencyQuestion(ALL, 3)).toBe(
      'Chiudere 3 posizioni di tutti i flussi e metterli in pausa?',
    );
  });

  it('says so when no position closes', () => {
    expect(emergencyQuestion(FLOW, 0)).toBe(
      'Chiudere 0 posizioni del flusso alfa e metterlo in pausa?',
    );
  });
});

describe('scopeQuery', () => {
  it('sends the flow, the account or nothing', () => {
    expect(scopeQuery(FLOW)).toEqual({ flow_id: 'flow-alfa' });
    expect(scopeQuery(ACCOUNT)).toEqual({ account_id: 'account-test-1' });
    expect(scopeQuery(ALL)).toEqual({});
  });
});
