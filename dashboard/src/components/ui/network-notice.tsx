import { ConfirmationDialog } from './confirmation-dialog';

/** The network the API names for an exchange configured on real money (Bug 277). */
export const REAL_NETWORK = 'real';

export const isRealMoney = (network: string | undefined): boolean => network === REAL_NETWORK;

type NetworkProps = {
  /** Test or real, as the API says it; the dashboard knows no exchange and no network by name (R2.3.10). */
  readonly network: string;
  /** The name the adapter of the exchange gives the network. */
  readonly networkName: string;
};

/** Said before an account is saved on an exchange that trades real money (Bug 277). */
export const RealMoneyNotice = ({ subject }: { readonly subject: string }) => (
  <p role="note" className="rounded bg-red-100 px-2 py-1 font-semibold text-red-900">
    {subject} opererà con denaro reale
  </p>
);

type TestNetworkNoticeProps = { readonly subject: string; readonly networkName: string };

/** Said wherever an account or a flow trades on the test network of its exchange (R2.3.10). */
export const TestNetworkNotice = ({ subject, networkName }: TestNetworkNoticeProps) => (
  <p role="note" className="rounded bg-yellow-100 px-2 py-1 font-semibold text-yellow-900">
    {subject} opererà sulla rete di test {networkName}, senza denaro reale
  </p>
);

/** Red for real money, yellow for the test network: the same notice wherever the network matters (R2.3.10). */
export const NetworkNotice = ({
  subject,
  network,
  networkName,
}: NetworkProps & { readonly subject: string }) =>
  isRealMoney(network) ? (
    <RealMoneyNotice subject={subject} />
  ) : (
    <TestNetworkNotice subject={subject} networkName={networkName} />
  );

/** The network of an account beside its name: real or test, with the name the exchange gives it (R2.3.10). */
export const NetworkBadge = ({ network, networkName }: NetworkProps) => {
  const real = isRealMoney(network);
  const style = real ? 'bg-red-100 text-red-900' : 'bg-yellow-100 text-yellow-900';
  return (
    <span className={`rounded px-2 py-0.5 text-sm font-semibold whitespace-nowrap ${style}`}>
      {real ? 'REALE' : 'TEST'} · {networkName}
    </span>
  );
};

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
