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
        motive: 'rottura della resistenza',
        invalidation: 'chiusura sotto 94000',
        outcome: { pnl: '12.5', realized: false, course: 'aperta da 2 ore' },
      },
      {
        planned_at: '2026-11-23T09:00:00Z',
        action: 'aggiorna',
        direction: null,
        price: null,
        motive: 'stop più alto',
        invalidation: null,
        outcome: null,
      },
    ],
  },
  { asset: 'ETH', entries: [] },
];

describe('FlowMemoryTable', () => {
  it('shows for each asset its decisions with instant, action, price, outcome, motive and invalidation', () => {
    render(<FlowMemoryTable memory={MEMORY} />);

    const bitcoin = screen.getByRole('table', { name: 'Memoria di BTC' });
    const [, opening, update] = within(bitcoin).getAllByRole('row');
    expect(opening).toHaveTextContent('24/11/2026, 10:00:00');
    expect(opening).toHaveTextContent('apri');
    expect(opening).toHaveTextContent('long');
    expect(opening).toHaveTextContent('95.000');
    expect(opening).toHaveTextContent('rottura della resistenza');
    expect(opening).toHaveTextContent('aperta da 2 ore, +12,5 non realizzato');
    expect(opening).toHaveTextContent('chiusura sotto 94000');
    expect(update).toHaveTextContent('aggiorna');
    expect(update).toHaveTextContent('stop più alto');
    expect(within(update as HTMLElement).getAllByText('—')).toHaveLength(3);
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
          motive: 'obiettivo',
          invalidation: null,
          outcome: { pnl: '-3', realized: true },
        },
      ],
    };

    render(<FlowMemoryTable memory={[closed]} />);

    expect(screen.getByRole('table', { name: 'Memoria di SOL' })).toHaveTextContent(
      '-3 realizzato',
    );
  });

  it('says how and after how long the position of an opening closed, as the agent receives it (R5.3.5)', () => {
    const closed: AssetMemory = {
      asset: 'DOGE',
      entries: [
        {
          planned_at: '2026-11-24T09:00:00Z',
          action: 'apri',
          direction: 'long',
          price: '0.002452',
          motive: 'rottura',
          invalidation: null,
          outcome: {
            pnl: '-2.32',
            realized: true,
            course: 'chiusa dallo stop loss dopo 12 minuti',
          },
        },
      ],
    };

    render(<FlowMemoryTable memory={[closed]} />);

    expect(screen.getByRole('table', { name: 'Memoria di DOGE' })).toHaveTextContent(
      'chiusa dallo stop loss dopo 12 minuti, -2,32 realizzato',
    );
  });

  it('says so for an asset without previous decisions', () => {
    render(<FlowMemoryTable memory={MEMORY} />);

    expect(screen.getByRole('heading', { name: 'ETH' })).toBeInTheDocument();
    expect(screen.getByText('Nessuna decisione precedente.')).toBeInTheDocument();
  });
});
