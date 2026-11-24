import { render, screen, within } from '@testing-library/react';

import type { AssetMemory } from '@/types/flow-memory';

import { FlowMemoryTable } from './flow-memory-table';

const MEMORY: AssetMemory[] = [
  {
    asset: 'BTC',
    entries: [
      {
        planned_at: '2026-11-24T09:00:00Z',
        action: 'apri',
        direction: 'long',
        price: '95000',
        reasoning: 'rottura della resistenza',
        outcome: { pnl: '12.5', realized: false },
      },
      {
        planned_at: '2026-11-23T09:00:00Z',
        action: 'aggiorna',
        direction: null,
        price: null,
        reasoning: 'stop più alto',
        outcome: null,
      },
    ],
  },
  { asset: 'ETH', entries: [] },
];

describe('FlowMemoryTable', () => {
  it('shows for each asset its decisions with instant, action, price, reasoning and outcome', () => {
    render(<FlowMemoryTable memory={MEMORY} />);

    const bitcoin = screen.getByRole('table', { name: 'Memoria di BTC' });
    const [, opening, update] = within(bitcoin).getAllByRole('row');
    expect(opening).toHaveTextContent('24/11/2026, 10:00:00');
    expect(opening).toHaveTextContent('apri');
    expect(opening).toHaveTextContent('long');
    expect(opening).toHaveTextContent('95.000');
    expect(opening).toHaveTextContent('rottura della resistenza');
    expect(opening).toHaveTextContent('+12,5 non realizzato');
    expect(update).toHaveTextContent('aggiorna');
    expect(update).toHaveTextContent('stop più alto');
    expect(within(update as HTMLElement).getAllByText('—')).toHaveLength(2);
  });

  it('says realized the PnL of a position closed', () => {
    const closed: AssetMemory = {
      asset: 'SOL',
      entries: [
        {
          planned_at: '2026-11-24T09:00:00Z',
          action: 'chiudi',
          direction: null,
          price: '150',
          reasoning: 'obiettivo',
          outcome: { pnl: '-3', realized: true },
        },
      ],
    };

    render(<FlowMemoryTable memory={[closed]} />);

    expect(screen.getByRole('table', { name: 'Memoria di SOL' })).toHaveTextContent(
      '-3 realizzato',
    );
  });

  it('says so for an asset without previous decisions', () => {
    render(<FlowMemoryTable memory={MEMORY} />);

    expect(screen.getByRole('heading', { name: 'ETH' })).toBeInTheDocument();
    expect(screen.getByText('Nessuna decisione precedente.')).toBeInTheDocument();
  });
});
