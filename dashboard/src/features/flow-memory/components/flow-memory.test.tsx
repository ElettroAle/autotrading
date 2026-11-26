import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { DEFAULT_MEMORY, fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderInApp, untilEveryRequestIsAnswered } from '@/testing/test-utils';

import { FLOW_MEMORY_TITLE, FlowMemory } from './flow-memory';

// The memory in the tab Decisioni, closed until opened, only with the memory on (R5.3.4, ADR
// memoria-del-flusso-dalle-decisioni-operative-precedenti).

const REMEMBERED = [
  {
    asset: 'BTC',
    summary: [],
    other_assets: [],
    entries: [
      {
        planned_at: '2026-11-24T09:00:00Z',
        asset: 'BTC',
        action: 'apri',
        direction: 'long',
        price: '95000',
        motive: 'rottura della resistenza',
        invalidation: null,
        outcome: { pnl: '12.5', realized: false, course: null },
      },
    ],
  },
];

describe('FlowMemory', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('keeps what the agent will receive closed until the user opens it, for every asset', async () => {
    fakePlatform.addFlow('anna', 'alfa', {
      memory: { ...DEFAULT_MEMORY, active: true, decisions: 5, days: 14 },
      remembered: REMEMBERED,
    });

    await renderInApp(<FlowMemory flowId="flow-alfa" />, { account: 'anna' });

    const panel = await screen.findByRole('group', { name: FLOW_MEMORY_TITLE });
    expect(panel).not.toHaveAttribute('open');
    await userEvent.click(within(panel).getByText(FLOW_MEMORY_TITLE));
    expect(panel).toHaveAttribute('open');
    expect(panel).toHaveTextContent("ciò che l'agente riceverà al prossimo ciclo");
    expect(within(panel).getByRole('table', { name: 'Memoria di BTC' })).toHaveTextContent(
      'rottura della resistenza',
    );
  });

  it('tells why the memory could not be read', async () => {
    fakePlatform.addFlow('anna', 'alfa');
    server.use(
      http.get('*/flows/:flowId/memory', () =>
        HttpResponse.json(
          { type: 'about:blank', title: 'Not Found', status: 404, detail: 'flusso non trovato' },
          { status: 404, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );

    await renderInApp(<FlowMemory flowId="flow-alfa" />, { account: 'anna' });

    expect(await screen.findByRole('group', { name: FLOW_MEMORY_TITLE })).toHaveTextContent(
      'flusso non trovato',
    );
  });

  it('shows nothing with the memory off', async () => {
    fakePlatform.addFlow('anna', 'alfa', { remembered: REMEMBERED });

    await renderInApp(<FlowMemory flowId="flow-alfa" />, { account: 'anna' });

    await untilEveryRequestIsAnswered();
    expect(screen.queryByRole('group', { name: FLOW_MEMORY_TITLE })).not.toBeInTheDocument();
  });
});
