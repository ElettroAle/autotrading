/**
 * Positions as the API answers them: the open ones in the state of a flow (R1.6.1), the closed ones in its history
 * (R1.7.2). Amounts are decimal strings, as the API writes them. Unit tests and scenarios build them here; the fake API
 * serves them, the closed ones from the most recent close and in pages.
 */
export type FakeOpenPosition = {
  readonly asset: string;
  readonly side: string;
  readonly size: string;
  readonly leverage: string;
  readonly entry_price: string;
  readonly margin: string;
  readonly unrealized_pnl: string;
  readonly unrealized_pnl_percent: string | null;
};

export type FakeClosedPosition = {
  readonly asset: string;
  readonly side: string;
  readonly leverage: number;
  readonly margin: string;
  readonly open_price: string;
  readonly close_price: string;
  readonly opened_at: string;
  readonly closed_at: string;
  readonly duration_seconds: number;
  readonly pnl: string;
  readonly pnl_percent_of_margin: string;
  readonly fees: string;
  readonly reason: string;
  readonly opening_cycle: string | null;
  readonly closing_cycle: string | null;
};

const HOUR = 3_600_000;

// The API measures the PnL on the margin, and has no percent without margin (ADR 0128).
const percentOf = (pnl: string, margin: string): string | null =>
  Number(margin) === 0 ? null : String((Number(pnl) / Number(margin)) * 100);

export const anOpenPosition = ({
  asset = 'BTC',
  side = 'long',
  size = '0.01',
  leverage = '3',
  entryPrice = '60000',
  margin = '200',
  pnl = '12',
}: {
  asset?: string;
  side?: string;
  size?: string;
  leverage?: string;
  entryPrice?: string;
  margin?: string;
  pnl?: string;
} = {}): FakeOpenPosition => ({
  asset,
  side,
  size,
  leverage,
  entry_price: entryPrice,
  margin,
  unrealized_pnl: pnl,
  unrealized_pnl_percent: percentOf(pnl, margin),
});

export const aClosedPosition = ({
  closedAt,
  asset = 'BTC',
  side = 'long',
  openPrice = '60000',
  closePrice = '60600',
  margin = '100',
  pnl = '1',
  fees = '0.08',
  reason = "decisione dell'agente",
}: {
  closedAt: Date;
  asset?: string;
  side?: string;
  openPrice?: string;
  closePrice?: string;
  margin?: string;
  pnl?: string;
  fees?: string;
  reason?: string;
}): FakeClosedPosition => ({
  asset,
  side,
  leverage: 1,
  margin,
  open_price: openPrice,
  close_price: closePrice,
  opened_at: new Date(closedAt.getTime() - HOUR).toISOString(),
  closed_at: closedAt.toISOString(),
  duration_seconds: HOUR / 1000,
  pnl,
  pnl_percent_of_margin: percentOf(pnl, margin) ?? '0',
  fees,
  reason,
  opening_cycle: null,
  closing_cycle: null,
});
