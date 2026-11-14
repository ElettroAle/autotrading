import { apiSearchOf, searchOf, withSearch, type HistorySearch } from './history-search';

const EVERYTHING: HistorySearch = { kind: 'cycles', flow: '', account: '', asset: '', version: '' };
const WHOLE_LIFE = { kind: 'all', from: '', to: '' } as const;

describe('searchOf', () => {
  it('reads tab and filters from the query string', () => {
    const params = new URLSearchParams('tab=orders&flow=f&account=a&asset=ETH&version=2');

    expect(searchOf(params)).toEqual({
      kind: 'orders',
      flow: 'f',
      account: 'a',
      asset: 'ETH',
      version: '2',
    });
  });

  it('opens the cycles without a tab or with one it does not know', () => {
    expect(searchOf(new URLSearchParams())).toEqual(EVERYTHING);
    expect(searchOf(new URLSearchParams('tab=operazioni')).kind).toBe('cycles');
  });
});

describe('withSearch', () => {
  it('keeps the other parameters and writes the tab as tab', () => {
    const next = withSearch(new URLSearchParams('period=7d'), { kind: 'closed-positions' });

    expect(next.toString()).toBe('period=7d&tab=closed-positions');
  });

  it('leaves no trace of an empty value', () => {
    const next = withSearch(new URLSearchParams('asset=BTC&account=a'), { asset: '' });

    expect(next.toString()).toBe('account=a');
  });

  it('forgets the version when another flow, or none, is chosen', () => {
    const current = new URLSearchParams('flow=f&version=2');

    expect(withSearch(current, { flow: 'g' }).toString()).toBe('flow=g');
    expect(withSearch(current, { flow: '' }).toString()).toBe('');
  });

  it('keeps the version when the same flow is chosen again or the version itself changes', () => {
    const current = new URLSearchParams('flow=f&version=2');

    expect(withSearch(current, { flow: 'f' }).toString()).toBe('flow=f&version=2');
    expect(withSearch(current, { version: '3' }).toString()).toBe('flow=f&version=3');
  });
});

describe('apiSearchOf', () => {
  it('names every filter as the API does, after the period', () => {
    const search = { ...EVERYTHING, flow: 'f', account: 'a', asset: 'ETH', version: '2' };

    expect(apiSearchOf(search, WHOLE_LIFE)).toBe(
      'period=all&flow_id=f&account_id=a&asset=ETH&version=2',
    );
  });

  it('passes a range with its days', () => {
    expect(apiSearchOf(EVERYTHING, { kind: 'range', from: '2026-11-10', to: '2026-11-20' })).toBe(
      'period=range&from=2026-11-10&to=2026-11-20',
    );
  });

  it('passes a version without its flow, as the API alone decides what a search means', () => {
    expect(apiSearchOf({ ...EVERYTHING, version: '2' }, WHOLE_LIFE)).toBe('period=all&version=2');
  });
});
