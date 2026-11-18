import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakeAlerts } from '@/testing/mocks/alerts';
import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { renderApp } from '@/testing/test-utils';
import { formatInstant } from '@/utils/format-instant';

const ACCOUNT_ID = 'account-test-1';
const OPENED_AT = new Date(Date.UTC(2026, 10, 18, 9, 0));

const alarmId = (): string => `alarm-${ACCOUNT_ID}-${OPENED_AT.toISOString()}`;

const pause = () => {
  const flow = fakePlatform.addFlow('anna', 'alfa', { status: 'in pausa' });
  return fakeAlerts.open(
    'tenant-anna',
    'flow_paused',
    { kind: 'flow', id: flow.id, name: 'alfa' },
    [{ label: 'Motivo', value: 'credito esaurito' }],
    OPENED_AT,
  );
};

const fill = () =>
  fakeAlerts.open(
    'tenant-anna',
    'unattributable_fill',
    { kind: 'account', id: ACCOUNT_ID, name: 'test-1' },
    [{ label: 'Asset', value: 'SOL' }],
    OPENED_AT,
  );

const whatToDo = (): Promise<HTMLElement> => screen.findByRole('region', { name: 'Che cosa fare' });

const confirm = async (command: string, confirmation: string) => {
  await userEvent.click(within(await whatToDo()).getByRole('button', { name: command }));
  const dialog = screen.getByRole('alertdialog', { name: command });
  await userEvent.click(within(dialog).getByRole('button', { name: confirmation }));
};

describe('AlertDetailView', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'test-1', 1000);
  });

  it('tells what happened with the values read and leads to the resource', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, OPENED_AT);
    await renderApp({ account: 'anna', url: `/alerts/${alarmId()}` });

    const article = await screen.findByRole('article', { name: 'Allarme di riconciliazione' });
    expect(within(article).getByText('Critica')).toBeInTheDocument();
    expect(within(article).getByRole('link', { name: 'Conto test-1' })).toHaveAttribute(
      'href',
      `/accounts/${ACCOUNT_ID}`,
    );
    const happened = within(article).getByRole('region', { name: 'Che cosa è successo' });
    expect(happened).toHaveTextContent(`Aperto il${formatInstant(OPENED_AT.toISOString())}`);
    expect(happened).toHaveTextContent('Saldo letto980 USDC');
    expect(happened).toHaveTextContent('Saldo atteso1000 USDC');
  });

  it('resolves an alarm by confirming the balance, and tells when it was resolved', async () => {
    fakeReconciliation.openAlarm(ACCOUNT_ID, 1000, 980, OPENED_AT);
    await renderApp({ account: 'anna', url: `/alerts/${alarmId()}` });

    await confirm('Conferma il saldo', 'Conferma la verifica');

    expect(await screen.findByText("Niente: l'avviso è risolto.")).toBeInTheDocument();
    expect(fakeReconciliation.statusOf(ACCOUNT_ID).aligned).toBe(true);
    expect(screen.getByRole('region', { name: 'Che cosa è successo' })).toHaveTextContent(
      'Risolto il',
    );
  });

  it('resumes a flow paused on its own, which resolves its alert, and offers no resolution by hand', async () => {
    const alert = pause();
    await renderApp({ account: 'anna', url: `/alerts/${alert.id}` });

    expect(
      within(await whatToDo()).queryByRole('button', { name: 'Segna come risolto' }),
    ).toBeNull();
    await confirm('Riprendi il flusso', 'Conferma la ripresa');

    expect(await screen.findByText("Niente: l'avviso è risolto.")).toBeInTheDocument();
    expect(fakePlatform.flowNamed('alfa').status).toBe('attivo');
  });

  it('resolves by hand an execution no flow explains', async () => {
    const alert = fill();
    await renderApp({ account: 'anna', url: `/alerts/${alert.id}` });

    await confirm('Segna come risolto', 'Conferma la risoluzione');

    expect(await screen.findByText("Niente: l'avviso è risolto.")).toBeInTheDocument();
    expect(alert.resolved_at).not.toBeNull();
  });

  it('keeps the dialog open when the command is refused, and closes it on Annulla', async () => {
    const alert = pause();
    fakePlatform.changeFlow('alfa', { status: 'attivo' });
    await renderApp({ account: 'anna', url: `/alerts/${alert.id}` });

    await confirm('Riprendi il flusso', 'Conferma la ripresa');

    const dialog = screen.getByRole('alertdialog', { name: 'Riprendi il flusso' });
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Operazione non riuscita');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Annulla' }));
    expect(screen.queryByRole('alertdialog')).toBeNull();
  });

  it('says an alert that resolves on its own has no command', async () => {
    const alert = fakeAlerts.open(
      'tenant-anna',
      'unattributable_position',
      { kind: 'account', id: ACCOUNT_ID, name: 'test-1' },
      [{ label: 'Asset', value: 'SOL' }],
      OPENED_AT,
    );
    await renderApp({ account: 'anna', url: `/alerts/${alert.id}` });

    expect(await whatToDo()).toHaveTextContent(
      "Nessun comando: l'avviso si risolve da solo quando la sua causa sparisce.",
    );
  });

  it('tells when the alert is not found', async () => {
    await renderApp({ account: 'anna', url: '/alerts/alert-altrui' });

    expect(await screen.findByRole('alert')).toHaveTextContent('avviso non trovato');
  });
});
