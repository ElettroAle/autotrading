import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderInApp, untilEveryRequestIsAnswered } from '@/testing/test-utils';

import { FlowMemory } from './flow-memory';

// The memory on the page of the flow, only with the memory on (R5.3.4, ADR
// memoria-del-flusso-dalle-decisioni-operative-precedenti).

const REMEMBERED = [
  {
    asset: 'BTC',
    entries: [
      {
        planned_at: '2026-11-24T09:00:00Z',
        asset: 'BTC',
        action: 'apri',
        direction: 'long',
        price: '95000',
        reasoning: 'rottura della resistenza',
        outcome: { pnl: '12.5', realized: false },
      },
    ],
  },
];

describe('FlowMemory', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
  });

  it('shows what the agent will receive at the next cycle, for every asset', async () => {
    fakePlatform.addFlow('anna', 'alfa', {
      memory: { active: true, decisions: 5, days: 14 },
      remembered: REMEMBERED,
    });

    await renderInApp(<FlowMemory flowId="flow-alfa" />, { account: 'anna' });

    const panel = await screen.findByRole('region', { name: 'Memoria' });
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

    expect(await screen.findByRole('region', { name: 'Memoria' })).toHaveTextContent(
      'flusso non trovato',
    );
  });

  it('shows nothing with the memory off', async () => {
    fakePlatform.addFlow('anna', 'alfa', { remembered: REMEMBERED });

    await renderInApp(<FlowMemory flowId="flow-alfa" />, { account: 'anna' });

    await untilEveryRequestIsAnswered();
    expect(screen.queryByRole('region', { name: 'Memoria' })).not.toBeInTheDocument();
  });
});
