import { comparedFlowsIn, MAX_COMPARED_FLOWS, withComparedFlows } from './compared-flows';

describe('comparedFlowsIn', () => {
  it('reads the flows from the repeated parameter, in their order', () => {
    expect(comparedFlowsIn(new URLSearchParams('flow=b&period=7d&flow=a'))).toEqual(['b', 'a']);
  });

  it('keeps each flow once and the first five at most', () => {
    const search = new URLSearchParams('flow=a&flow=a&flow=b&flow=c&flow=d&flow=e&flow=f');

    expect(comparedFlowsIn(search)).toEqual(['a', 'b', 'c', 'd', 'e']);
    expect(MAX_COMPARED_FLOWS).toBe(5);
  });

  it('ignores an empty parameter', () => {
    expect(comparedFlowsIn(new URLSearchParams('flow=&flow=a'))).toEqual(['a']);
  });
});

describe('withComparedFlows', () => {
  it('replaces the flows and keeps the other parameters', () => {
    const next = withComparedFlows(new URLSearchParams('period=30d&flow=old'), ['a', 'b']);

    expect(next.toString()).toBe('period=30d&flow=a&flow=b');
  });

  it('leaves no parameter without flows', () => {
    expect(withComparedFlows(new URLSearchParams('period=7d&flow=a'), []).toString()).toBe(
      'period=7d',
    );
  });

  it('does not change the search it receives', () => {
    const current = new URLSearchParams('flow=a');

    withComparedFlows(current, ['b']);

    expect(current.toString()).toBe('flow=a');
  });
});
