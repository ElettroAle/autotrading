import { ConfirmationDialog } from './confirmation-dialog';

/** The network the API names for an exchange configured on real money (Bug 277). */
export const REAL_NETWORK = 'real';

export const isRealMoney = (network: string | undefined): boolean => network === REAL_NETWORK;

/** Said before an account is saved on an exchange that trades real money (Bug 277). */
export const RealMoneyNotice = ({ subject }: { readonly subject: string }) => (
  <p role="note" className="rounded bg-red-100 px-2 py-1 font-semibold text-red-900">
    {subject} opererà con denaro reale
  </p>
);

type RealMoneyStartConfirmationProps = {
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
  readonly pending: boolean;
};

/** A flow on an exchange that trades real money starts only once the user confirms it (Bug 277). */
export const RealMoneyStartConfirmation = (props: RealMoneyStartConfirmationProps) => (
  <ConfirmationDialog title="Conferma dell'avvio" confirmLabel="Avvia con denaro reale" {...props}>
    <RealMoneyNotice subject="Il flusso" />
  </ConfirmationDialog>
);
