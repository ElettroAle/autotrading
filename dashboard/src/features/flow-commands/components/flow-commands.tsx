import { useState } from 'react';
import { useNavigate } from 'react-router';

import { CommandButton, type CommandTone } from '@/components/ui/command-button';
import { ErrorMessage } from '@/components/ui/error-message';
import type { IconName } from '@/components/ui/icons/icon';
import { RealMoneyStartConfirmation } from '@/components/ui/network-notice';
import { paths } from '@/config/paths';
import { formatAmount } from '@/utils/format-amount';

import { useCashOutProfits, type CashOutOutcome } from '../api/cash-out-profits';
import { useFlowState } from '../api/get-flow-state';
import { useRunFlowCommand } from '../api/run-flow-command';
import { hasProfits } from '../utils/cash-out-question';
import { commandsAllowedIn, type FlowCommand } from '../utils/flow-transitions';

import { CashOutConfirmation } from './cash-out-confirmation';
import { ArchiveConfirmation, StopConfirmation } from './command-confirmation';

const LABELS: Readonly<Record<FlowCommand, string>> = {
  start: 'Avvia',
  pause: 'Pausa',
  resume: 'Riprendi',
  stop: 'Stop',
  archive: 'Archivia',
};

type CommandLook = { readonly tone: CommandTone; readonly icon?: IconName };

// Each command of the status has a colour and an icon of its own, the archiving cannot be undone (R6.4.1, R6.5.3).
const LOOKS: Readonly<Record<FlowCommand, CommandLook>> = {
  start: { tone: 'go', icon: 'play' },
  resume: { tone: 'go', icon: 'play' },
  pause: { tone: 'hold', icon: 'pause' },
  stop: { tone: 'stop', icon: 'square' },
  archive: { tone: 'destructive' },
};

type ConfirmedCommand = Extract<FlowCommand, 'stop' | 'archive' | 'start'>;

// The stop closes the positions and the archiving is final: both run only once the user confirms (ADR 0132). A start
// on an account that trades real money is confirmed too (Bug 277).
const needsConfirmation = (command: FlowCommand, realMoney: boolean): command is ConfirmedCommand =>
  command === 'stop' || command === 'archive' || (command === 'start' && realMoney);

type Confirming = ConfirmedCommand | 'cash-out';

type CashOutResultProps = {
  readonly outcome: CashOutOutcome;
  readonly currency: string;
};

// With a position left open the cash-out frees nothing, and says which position and why (R3.4.1).
const CashOutResult = ({ outcome, currency }: CashOutResultProps) =>
  outcome.freed === null ? (
    <div role="alert" className="text-red-700">
      <p>Incasso non completato: nessun capitale liberato.</p>
      <ul className="list-disc pl-5">
        {outcome.left_open.map((position) => (
          <li key={position.asset}>
            La posizione su {position.asset} non è stata chiusa: {position.reason}
          </li>
        ))}
      </ul>
    </div>
  ) : (
    <p role="status">
      Profitti incassati: liberati {formatAmount(outcome.freed)} {currency}.
    </p>
  );

type FlowCommandsProps = {
  readonly flowId: string;
  readonly flowName: string;
  readonly status: string;
  readonly realMoney: boolean;
};

/** The commands the status of the flow admits, with the reason of a command the API refuses (R2.3.4). */
export const FlowCommands = ({ flowId, flowName, status, realMoney }: FlowCommandsProps) => {
  const [confirming, setConfirming] = useState<Confirming | null>(null);
  const state = useFlowState(flowId);
  const cashOut = useCashOutProfits(flowId);
  const navigate = useNavigate();
  const run = useRunFlowCommand(flowId, {
    onSuccess: (command) => {
      // An archived flow is no longer among the flows in use: its page would find nothing.
      if (command === 'archive') {
        void navigate(paths.home.getHref());
      }
    },
  });

  const request = (command: FlowCommand) => {
    if (needsConfirmation(command, realMoney)) {
      setConfirming(command);
      return;
    }
    run.mutate(command);
  };

  const confirm = (command: ConfirmedCommand) => {
    run.mutate(command, { onSettled: () => setConfirming(null) });
  };

  const confirmCashOut = (capital: string | null) => {
    cashOut.mutate(capital, { onSettled: () => setConfirming(null) });
  };

  const confirmation = {
    pending: run.isPending,
    onCancel: () => setConfirming(null),
  };

  // The cash-out is offered only on a flow worth more than its capital (ADR incasso-dei-profitti-nella-dashboard).
  const profitable =
    state.data !== undefined && hasProfits(state.data.total_value, state.data.allocated_capital);
  const busy = run.isPending || cashOut.isPending;

  return (
    <div className="mt-3 space-y-2">
      {confirming === null && (
        <div role="group" aria-label="Comandi del flusso" className="flex flex-wrap gap-2">
          {commandsAllowedIn(status).map((command) => (
            <CommandButton
              key={command}
              {...LOOKS[command]}
              onClick={() => request(command)}
              disabled={busy}
            >
              {LABELS[command]}
            </CommandButton>
          ))}
          {profitable && (
            <CommandButton
              tone="secondary"
              onClick={() => setConfirming('cash-out')}
              disabled={busy}
            >
              Incassa i profitti
            </CommandButton>
          )}
        </div>
      )}
      {confirming === 'stop' && (
        <StopConfirmation flowId={flowId} onConfirm={() => confirm('stop')} {...confirmation} />
      )}
      {confirming === 'start' && (
        <RealMoneyStartConfirmation onConfirm={() => confirm('start')} {...confirmation} />
      )}
      {confirming === 'archive' && (
        <ArchiveConfirmation onConfirm={() => confirm('archive')} {...confirmation} />
      )}
      {confirming === 'cash-out' && state.data !== undefined && (
        <CashOutConfirmation
          flowName={flowName}
          state={state.data}
          pending={cashOut.isPending}
          onConfirm={confirmCashOut}
          onCancel={() => setConfirming(null)}
        />
      )}
      {run.isError && <ErrorMessage error={run.error} prefix="Comando non riuscito" />}
      {cashOut.isSuccess && (
        <CashOutResult outcome={cashOut.data} currency={state.data?.currency ?? ''} />
      )}
      {cashOut.isError && <ErrorMessage error={cashOut.error} prefix="Incasso non riuscito" />}
    </div>
  );
};
