import { screen, within } from '@testing-library/react';

import { renderInApp } from '@/testing/test-utils';

import type { ResultsSummary as Summary } from '../api/get-flow-results';

import { ResultsSummary } from './results-summary';

const GAINING: Summary = {
  total_gain: '2.5',
  total_gain_percent: '2.50',
  period_gain: '0.4',
  period_gain_percent: '0.40',
  open_positions: 1,
  failed_cycles: 2,
  next_cycle_at: null,
};

const show = async (summary: Summary, currency = 'USDC', nextCycleAt?: string | null) => {
  await renderInApp(
    <ResultsSummary
      flowId="flow-alfa"
      currency={currency}
      summary={summary}
      nextCycleAt={nextCycleAt}
    />,
  );
  return screen.findByRole('region', { name: 'Riepilogo dei risultati' });
};

const valueOf = (summary: HTMLElement, term: string) => within(summary).getByLabelText(term);

// ADR riepilogo-dei-risultati-nella-dashboard: four values at a glance, gains in green or red, errors only if any.
describe('ResultsSummary', () => {
  it('shows both gains as amount and percent of the initial capital, a gain in green', async () => {
    const summary = await show(GAINING);

    expect(valueOf(summary, 'Guadagno attuale')).toHaveTextContent('+2,50 USDC · +2,50%');
    expect(valueOf(summary, 'Guadagno attuale')).toHaveClass('text-green-700');
    expect(valueOf(summary, 'Guadagno nel periodo')).toHaveTextContent('+0,40 USDC · +0,40%');
    expect(valueOf(summary, 'Guadagno nel periodo')).toHaveClass('text-green-700');
  });

  it('shows a loss in red and nothing gained without a colour', async () => {
    const summary = await show({
      ...GAINING,
      total_gain: '-1.2',
      total_gain_percent: '-1.20',
      period_gain: '0',
      period_gain_percent: '0.00',
    });

    expect(valueOf(summary, 'Guadagno attuale')).toHaveTextContent('-1,20 USDC · -1,20%');
    expect(valueOf(summary, 'Guadagno attuale')).toHaveClass('text-red-700');
    expect(valueOf(summary, 'Guadagno nel periodo')).toHaveTextContent('0,00 USDC · 0,00%');
    expect(valueOf(summary, 'Guadagno nel periodo')).toHaveClass('text-slate-700');
  });

  it('shows only the amount when the API could not measure the percent', async () => {
    const summary = await show({ ...GAINING, total_gain_percent: null });

    expect(valueOf(summary, 'Guadagno attuale')).toHaveTextContent(/^\+2,50 USDC$/);
  });

  it('writes the amounts in the currency of the account', async () => {
    const summary = await show(GAINING, 'USDT');

    expect(valueOf(summary, 'Guadagno attuale')).toHaveTextContent('+2,50 USDT · +2,50%');
    expect(valueOf(summary, 'Guadagno nel periodo')).toHaveTextContent('+0,40 USDT · +0,40%');
  });

  // The open positions are in the overview of the flow (R6.4.3).
  it('leads from the open positions to the overview of the flow', async () => {
    const summary = await show(GAINING);

    expect(within(summary).getByRole('link', { name: /1 posizione aperta/ })).toHaveAttribute(
      'href',
      '/flows/flow-alfa',
    );
  });

  it('counts the open positions in the plural', async () => {
    const summary = await show({ ...GAINING, open_positions: 3 });

    expect(valueOf(summary, 'Posizioni aperte')).toHaveTextContent('3 posizioni aperte');
  });

  it('shows the failed cycles in red, leading to the cycles of the flow filtered on the failed', async () => {
    const summary = await show(GAINING);

    const failed = within(summary).getByRole('link', { name: /2 cicli falliti/ });
    expect(failed).toHaveAttribute('href', '/flows/flow-alfa/cycles?outcome=fallito');
    expect(valueOf(summary, 'Cicli falliti')).toHaveClass('text-red-700');
  });

  it('says a single failed cycle in the singular', async () => {
    const summary = await show({ ...GAINING, failed_cycles: 1 });

    expect(valueOf(summary, 'Cicli falliti')).toHaveTextContent('1 ciclo fallito');
  });

  it('says there was no error without any evidence', async () => {
    const summary = await show({ ...GAINING, failed_cycles: 0 });

    expect(valueOf(summary, 'Cicli falliti')).toHaveTextContent('nessun errore');
    expect(valueOf(summary, 'Cicli falliti')).not.toHaveClass('text-red-700');
    expect(within(summary).queryByRole('link', { name: /errore/ })).not.toBeInTheDocument();
  });

  // R6.4.8, ADR prossima-esecuzione-nel-riepilogo-del-flusso: the instant the API plans, as the card of the flow shows it.
  it('shows when the next cycle falls, when the page gives it', async () => {
    const summary = await show(GAINING, 'USDC', '2026-11-18T09:15:00Z');

    expect(valueOf(summary, 'Prossima esecuzione prevista')).toHaveTextContent(
      '18/11/2026, 10:15:00',
    );
  });

  it('shows no next cycle for a flow that plans none', async () => {
    const summary = await show(GAINING, 'USDC', null);

    expect(
      within(summary).queryByLabelText('Prossima esecuzione prevista'),
    ).not.toBeInTheDocument();
  });

  // The card of the list says the next cycle among its details (R2.2.2): its summary does not repeat it.
  it('shows no next cycle where the page does not give it', async () => {
    const summary = await show(GAINING);

    expect(
      within(summary).queryByLabelText('Prossima esecuzione prevista'),
    ).not.toBeInTheDocument();
  });

  // Bug 612, ADR nomi-e-istanti-dei-guadagni: the gain read now is the current one, without notes below the values.
  it('calls the gain read now the current gain', async () => {
    const summary = await show(GAINING);

    const terms = Array.from(summary.querySelectorAll('dt'), (term) => term.textContent);
    expect(terms).toEqual([
      'Guadagno attuale',
      'Guadagno nel periodo',
      'Posizioni aperte',
      'Cicli falliti',
    ]);
  });
});
