import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { aCompletedCycle, aFailedCycle, STEPS, withDecisions } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderInApp } from '@/testing/test-utils';

import { LastDecision } from './last-decision';

// The last decision in the Panoramica of the flow (R6.5.4, ADR riquadro-dell-ultima-decisione-nella-panoramica).

const TEN = new Date('2026-11-16T09:00:00Z');
const ELEVEN = new Date('2026-11-16T10:00:00Z');
const LONG_REASONING = `${'Il prezzo rompe la resistenza con volumi in aumento. '.repeat(4)}Fine del ragionamento.`;

const panel = () => screen.findByRole('region', { name: 'Ultima decisione' });

const decisionOn = async (asset: string) =>
  within(await panel()).findByRole('region', { name: asset });

const valueOf = (decision: HTMLElement, label: string) =>
  within(decision).getByLabelText(label, { exact: true });

// The reasoning without the command beside it, which opens and closes it (ADR testo-lungo-espandibile).
const reasoningOf = (decision: HTMLElement): string => {
  const value = valueOf(decision, 'Ragionamento');
  const command = within(value).getByRole('button');
  return (
    within(value).getByText((_, element) => element?.id === command.getAttribute('aria-controls'))
      .textContent ?? ''
  );
};

const decided = (plannedAt: Date) =>
  withDecisions(aCompletedCycle(plannedAt), [
    {
      asset: 'BTC',
      action: 'apri',
      reasoning: LONG_REASONING,
      confidence: 72,
      opening: { direction: 'long' },
    },
    { asset: 'ETH', action: 'mantieni', reasoning: 'attesa di conferme', opening: null },
  ]);

describe('LastDecision', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa');
  });

  it('shows each asset with action, direction, confidence and the reasoning shortened', async () => {
    fakePlatform.recordCycles('alfa', [decided(TEN)]);
    await renderInApp(<LastDecision flowId="flow-alfa" />, { account: 'anna' });

    const bitcoin = await decisionOn('BTC');
    expect(valueOf(bitcoin, 'Asset')).toHaveTextContent('BTC');
    expect(valueOf(bitcoin, 'Azione')).toHaveTextContent('apri');
    expect(valueOf(bitcoin, 'Direzione')).toHaveTextContent('long');
    expect(valueOf(bitcoin, 'Confidenza')).toHaveTextContent('72');
    const reasoning = reasoningOf(bitcoin);
    expect(reasoning.endsWith('…')).toBe(true);
    expect(reasoning.length).toBeLessThanOrEqual(161);
    expect(LONG_REASONING.startsWith(reasoning.slice(0, -1))).toBe(true);
  });

  // Bug 576, ADR-testo-lungo-espandibile: the whole reasoning is read in place.
  it('opens the whole reasoning in place with «Leggi tutto» and closes it with «Riduci»', async () => {
    fakePlatform.recordCycles('alfa', [decided(TEN)]);
    await renderInApp(<LastDecision flowId="flow-alfa" />, { account: 'anna' });
    const bitcoin = await decisionOn('BTC');

    await userEvent.click(within(bitcoin).getByRole('button', { name: 'Leggi tutto' }));

    expect(reasoningOf(bitcoin)).toBe(LONG_REASONING);
    await userEvent.click(within(bitcoin).getByRole('button', { name: 'Riduci' }));
    expect(reasoningOf(bitcoin).endsWith('…')).toBe(true);
  });

  // R6.5.3: the panel shows action and direction with the shared icons (ADR riquadro-dell-ultima-decisione-nella-panoramica).
  it('shows the action and the direction with their icons', async () => {
    fakePlatform.recordCycles('alfa', [decided(TEN)]);
    await renderInApp(<LastDecision flowId="flow-alfa" />, { account: 'anna' });

    const bitcoin = await decisionOn('BTC');
    expect(within(valueOf(bitcoin, 'Azione')).getByRole('img', { hidden: true })).toHaveAttribute(
      'data-icon',
      'plus',
    );
    expect(
      within(valueOf(bitcoin, 'Direzione')).getByRole('img', { hidden: true }),
    ).toHaveAttribute('data-icon', 'arrow-up');
  });

  it('shows no direction for a decision other than an opening, and a confidence the agent never gave as not available', async () => {
    fakePlatform.recordCycles('alfa', [decided(TEN)]);
    await renderInApp(<LastDecision flowId="flow-alfa" />, { account: 'anna' });

    const ether = await decisionOn('ETH');
    expect(valueOf(ether, 'Azione')).toHaveTextContent('mantieni');
    expect(within(ether).queryByLabelText('Direzione')).toBeNull();
    expect(valueOf(ether, 'Confidenza')).toHaveTextContent('non disponibile');
    expect(valueOf(ether, 'Ragionamento')).toHaveTextContent('attesa di conferme');
  });

  it('links the instant of the cycle to its detail and says it does not follow the period', async () => {
    fakePlatform.recordCycles('alfa', [decided(TEN)]);
    await renderInApp(<LastDecision flowId="flow-alfa" />, { account: 'anna' });

    const shown = await panel();
    expect(within(shown).getByText('indipendente dal periodo')).toBeInTheDocument();
    const link = within(shown).getByRole('link', { name: /16\/11\/2026, 10:00:00/ });
    expect(link).toHaveAttribute(
      'href',
      `/flows/flow-alfa/cycles/${encodeURIComponent('2026-11-16T09:00:00Z')}`,
    );
  });

  it('keeps the decision of the last completed cycle when a later one failed before deciding', async () => {
    const failed = aFailedCycle(aCompletedCycle(ELEVEN), STEPS.agentDecision, {
      errorType: 'ModelUnavailableError',
      message: 'fornitore IA non raggiungibile',
    });
    fakePlatform.recordCycles('alfa', [decided(TEN), failed]);
    await renderInApp(<LastDecision flowId="flow-alfa" />, { account: 'anna' });

    expect(
      within(await panel()).getByRole('link', { name: /16\/11\/2026, 10:00:00/ }),
    ).toBeInTheDocument();
  });

  it('says there is no decision yet before the first completed cycle', async () => {
    await renderInApp(<LastDecision flowId="flow-alfa" />, { account: 'anna' });

    expect(await within(await panel()).findByText('nessuna decisione ancora')).toBeInTheDocument();
  });

  it('says why the decision could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/decisions/latest', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Not Found', status: 404, detail: 'flusso non trovato' },
          { status: 404, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    await renderInApp(<LastDecision flowId="flow-alfa" />, { account: 'anna' });

    expect(await within(await panel()).findByText(/flusso non trovato/)).toBeInTheDocument();
  });
});
