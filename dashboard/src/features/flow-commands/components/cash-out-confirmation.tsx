import { useState } from 'react';

import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { InputField } from '@/components/ui/form/input-field';

import type { FlowState } from '../api/get-flow-state';
import { cashOutQuestion, estimatedFreed } from '../utils/cash-out-question';

const DECIMAL = /^\d+(\.\d+)?$/;

type CashOutConfirmationProps = {
  readonly flowName: string;
  readonly state: FlowState;
  readonly pending: boolean;
  /** The capital the flow keeps, null for the capital allocated now. */
  readonly onConfirm: (capital: string | null) => void;
  readonly onCancel: () => void;
};

/**
 * Asks to confirm the cash-out with what it would free at the value of the flow now, for the capital allocated now or
 * the one the user writes; nothing closes before the confirmation (ADR incasso-dei-profitti-nella-dashboard).
 */
export const CashOutConfirmation = ({
  flowName,
  state,
  pending,
  onConfirm,
  onCancel,
}: CashOutConfirmationProps) => {
  const [capital, setCapital] = useState('');
  const written = capital.trim();
  // A value not yet a number leaves the estimate on the capital allocated now; the API judges what is sent.
  const kept = DECIMAL.test(written) ? written : state.allocated_capital;
  const question = cashOutQuestion({
    flowName,
    positions: state.positions.length,
    freed: estimatedFreed(state.total_value, kept),
    currency: state.currency,
  });
  return (
    <ConfirmationDialog
      title="Conferma dell'incasso"
      confirmLabel="Conferma l'incasso"
      pending={pending}
      onConfirm={() => onConfirm(written === '' ? null : written)}
      onCancel={onCancel}
    >
      <p>{question}</p>
      <InputField
        label={`Capitale da mantenere (${state.currency}, facoltativo)`}
        info="Capitale che il flusso tiene dopo l'incasso: le posizioni si chiudono e ciò che il flusso ha oltre questo capitale torna libero nel conto. Un importo. Vuoto: il capitale allocato ora."
        inputMode="decimal"
        placeholder={state.allocated_capital}
        value={capital}
        onChange={(event) => setCapital(event.target.value)}
      />
    </ConfirmationDialog>
  );
};
