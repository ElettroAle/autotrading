import { useState } from 'react';

import { CommandButton } from '@/components/ui/command-button';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { DETAIL_VALUE, DETAILS_GRID } from '@/components/ui/details-list';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { formatInstant } from '@/utils/format-instant';

import { useAlert, type AlertCommand, type AlertDetail } from '../api/get-alert';
import { useRunAlertCommand } from '../api/run-alert-command';

import { AlertResourceLink, AlertSeverityLabel } from './alert-parts';

type CommandWords = {
  readonly label: string;
  readonly confirmLabel: string;
  readonly consequence: (alert: AlertDetail) => string;
};

// The commands the API admits on the alert, each with what it does, said before the user confirms it.
const COMMANDS: Readonly<Record<AlertCommand, CommandWords>> = {
  confirm_reconciliation: {
    label: 'Conferma il saldo',
    confirmLabel: 'Conferma la verifica',
    consequence: (alert) =>
      `Confermi di aver verificato il saldo del conto ${alert.resource.name}: l'allarme si chiude e i suoi flussi tornano ad aprire posizioni.`,
  },
  resume_flow: {
    label: 'Riprendi il flusso',
    confirmLabel: 'Conferma la ripresa',
    consequence: (alert) =>
      `Il flusso ${alert.resource.name} riprende i suoi cicli: verifica prima di aver rimosso la causa della pausa.`,
  },
  resolve: {
    label: 'Segna come risolto',
    confirmLabel: 'Conferma la risoluzione',
    consequence: () => "L'avviso passa tra i risolti: fallo dopo aver verificato l'esecuzione.",
  },
};

type CommandsProps = { readonly alert: AlertDetail };

const AlertCommands = ({ alert }: CommandsProps) => {
  const [chosen, setChosen] = useState<AlertCommand | undefined>(undefined);
  const run = useRunAlertCommand(alert);
  if (alert.commands.length === 0) {
    return <p>Nessun comando: l&apos;avviso si risolve da solo quando la sua causa sparisce.</p>;
  }
  const done = () => setChosen(undefined);
  return (
    <>
      <div className="flex flex-wrap gap-2">
        {alert.commands.map((command) => (
          <CommandButton key={command} tone="secondary" onClick={() => setChosen(command)}>
            {COMMANDS[command].label}
          </CommandButton>
        ))}
      </div>
      {chosen !== undefined && (
        <ConfirmationDialog
          title={COMMANDS[chosen].label}
          confirmLabel={COMMANDS[chosen].confirmLabel}
          onConfirm={() => run.mutate(chosen, { onSuccess: done })}
          onCancel={done}
          pending={run.isPending}
          error={run.error}
        >
          {COMMANDS[chosen].consequence(alert)}
        </ConfirmationDialog>
      )}
    </>
  );
};

const AlertContent = ({ alert }: { readonly alert: AlertDetail }) => (
  <article aria-label={alert.title} className="space-y-4">
    <header className="space-y-1">
      <h2 className="text-xl font-semibold">{alert.title}</h2>
      <AlertSeverityLabel severity={alert.severity} />
      <p>
        <AlertResourceLink resource={alert.resource} />
      </p>
    </header>
    <section aria-label="Che cosa è successo" className="space-y-2">
      <h3 className="font-semibold">Che cosa è successo</h3>
      <dl className={DETAILS_GRID}>
        <dt className="font-medium text-slate-600">Aperto il</dt>
        <dd className={DETAIL_VALUE}>{formatInstant(alert.opened_at)}</dd>
        {alert.values.map(({ label, value }) => (
          <div key={label} className="contents">
            <dt className="font-medium text-slate-600">{label}</dt>
            <dd className={DETAIL_VALUE}>{value}</dd>
          </div>
        ))}
        {alert.resolved_at !== null && (
          <>
            <dt className="font-medium text-slate-600">Risolto il</dt>
            <dd className={DETAIL_VALUE}>{formatInstant(alert.resolved_at)}</dd>
          </>
        )}
      </dl>
    </section>
    <section aria-label="Che cosa fare" className="space-y-2">
      <h3 className="font-semibold">Che cosa fare</h3>
      {alert.resolved_at === null ? (
        <AlertCommands alert={alert} />
      ) : (
        <p>Niente: l&apos;avviso è risolto.</p>
      )}
    </section>
  </article>
);

/**
 * An alert: what happened with the values read, what to do with the commands the API admits now, each confirmed
 * first, and the link to the resource; a resolved alert tells when (R6.2.3, ADR pagina-avvisi-nella-dashboard).
 */
export const AlertDetailView = ({ alertId }: { readonly alertId: string }) => {
  const alert = useAlert(alertId);
  if (alert.isPending) {
    return <Loading />;
  }
  if (alert.data === undefined) {
    return <ErrorMessage error={alert.error} />;
  }
  return <AlertContent alert={alert.data} />;
};
