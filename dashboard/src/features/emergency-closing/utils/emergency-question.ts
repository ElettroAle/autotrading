import type { EmergencyScope } from '../types/emergency-scope';

const positionsText = (positions: number): string =>
  positions === 1 ? '1 posizione' : `${String(positions)} posizioni`;

/**
 * The question the emergency closing asks before it closes anything: the scope and how many positions close, as the
 * API counts them (ADR chiusura-di-emergenza-nella-dashboard).
 */
export const emergencyQuestion = (scope: EmergencyScope, positions: number): string => {
  const closed = `Chiudere ${positionsText(positions)}`;
  switch (scope.kind) {
    case 'flow':
      return `${closed} del flusso ${scope.flowName} e metterlo in pausa?`;
    case 'account':
      return `${closed} dei flussi del conto ${scope.accountName} e metterli in pausa?`;
    case 'all':
      return `${closed} di tutti i flussi e metterli in pausa?`;
  }
};

/**
 * The command of the emergency closing, naming its scope, so the zone it stands in reads by itself (ADR
 * zona-di-emergenza-in-fondo-alla-pagina).
 */
export const emergencyCommandLabel = (scope: EmergencyScope): string => {
  switch (scope.kind) {
    case 'flow':
      return `Chiusura di emergenza del flusso ${scope.flowName}`;
    case 'account':
      return `Chiusura di emergenza del conto ${scope.accountName}`;
    case 'all':
      return 'Chiusura di emergenza di tutti i flussi';
  }
};

/** The scope as the API reads it: a flow, an account, or neither for every flow. */
export const scopeQuery = (scope: EmergencyScope): { flow_id?: string; account_id?: string } => {
  switch (scope.kind) {
    case 'flow':
      return { flow_id: scope.flowId };
    case 'account':
      return { account_id: scope.accountId };
    case 'all':
      return {};
  }
};
