import { render, screen, within } from '@testing-library/react';

import type { AssetMemory } from '@/types/flow-memory';

import { FlowMemoryTable } from './flow-memory-table';

const MEMORY: AssetMemory[] = [
  {
    asset: 'BTC',
    summary: [],
    other_assets: [],
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
  { asset: 'ETH', summary: [], other_assets: [], entries: [] },
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
      summary: [],
      other_assets: [],
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
      summary: [],
      other_assets: [],
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

  it('shows before the decisions of an asset its summary lines and those of the other assets, as the API gives them (R5.3.7)', () => {
    const summarized: AssetMemory = {
      asset: 'NEAR',
      summary: ['NEAR short — oggi: 3 chiuse, 0 vinte, 3 perse, PnL -6,27 USDC'],
      other_assets: ['SUI short — oggi: 1 chiuse, 0 vinte, 1 perse, PnL -0,81 USDC'],
      entries: MEMORY[0]?.entries ?? [],
    };

    render(<FlowMemoryTable memory={[summarized]} />);

    const near = screen.getByRole('region', { name: 'NEAR' });
    expect(within(near).getByRole('list', { name: 'Riepilogo di NEAR' })).toHaveTextContent(
      'NEAR short — oggi: 3 chiuse, 0 vinte, 3 perse, PnL -6,27 USDC',
    );
    const others = within(near).getByRole('list', { name: 'Altri asset del flusso' });
    expect(others).toHaveTextContent(
      'SUI short — oggi: 1 chiuse, 0 vinte, 1 perse, PnL -0,81 USDC',
    );
    const table = within(near).getByRole('table', { name: 'Memoria di NEAR' });
    expect(others.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows no summary list for an asset without summary lines', () => {
    render(<FlowMemoryTable memory={MEMORY} />);

    expect(screen.queryByRole('list')).not.toBeInTheDocument();
  });

  it('says so for an asset without previous decisions', () => {
    render(<FlowMemoryTable memory={MEMORY} />);

    expect(screen.getByRole('heading', { name: 'ETH' })).toBeInTheDocument();
    expect(screen.getByText('Nessuna decisione precedente.')).toBeInTheDocument();
  });
});
