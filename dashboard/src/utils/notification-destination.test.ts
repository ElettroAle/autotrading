import { destinationOf, type NotificationTarget } from './notification-destination';

const target = (overrides: Partial<NotificationTarget>): NotificationTarget => ({
  kind: 'flow',
  flow_id: null,
  asset: null,
  closed_at: null,
  alert_id: null,
  ...overrides,
});

// ADR campanello-delle-notifiche-nella-dashboard: choosing a notification leads to its first page, by kind.
describe('destinationOf', () => {
  it('leads a flow to its page', () => {
    expect(destinationOf(target({ flow_id: 'flow-alfa' }))).toBe('/flows/flow-alfa');
  });

  it('leads an open position to the positions of its flow, on its asset', () => {
    expect(
      destinationOf(target({ kind: 'open_position', flow_id: 'flow-alfa', asset: 'BTC' })),
    ).toBe('/flows/flow-alfa/positions?asset=BTC');
  });

  it('leads a closed position to the closed positions of its flow, on its asset and instant', () => {
    const closed = target({
      kind: 'closed_position',
      flow_id: 'flow-alfa',
      asset: 'BTC',
      closed_at: '2026-11-19T08:00:00Z',
    });

    expect(destinationOf(closed)).toBe(
      '/flows/flow-alfa/closed-positions?asset=BTC&closed_at=2026-11-19T08%3A00%3A00Z',
    );
  });

  it('leads an alert to its detail', () => {
    expect(destinationOf(target({ kind: 'alert', alert_id: 'alert-1' }))).toBe('/alerts/alert-1');
  });

  it('leads nowhere when the target lacks what finds its page', () => {
    expect(destinationOf(target({}))).toBeUndefined();
    expect(destinationOf(target({ kind: 'alert' }))).toBeUndefined();
    expect(destinationOf(target({ kind: 'open_position', flow_id: 'flow-alfa' }))).toBeUndefined();
    expect(
      destinationOf(target({ kind: 'closed_position', flow_id: 'flow-alfa', asset: 'BTC' })),
    ).toBeUndefined();
  });

  it('leads nowhere without a target', () => {
    expect(destinationOf(undefined)).toBeUndefined();
  });
});
