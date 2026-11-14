import { paths } from './paths';

describe('paths.comparison', () => {
  it('carries the compared flows in the query string, one parameter each', () => {
    expect(paths.comparison.getHref(['flow-alfa', 'flow-beta'])).toBe(
      '/comparison?flow=flow-alfa&flow=flow-beta',
    );
  });

  it('keeps the period of the ranking', () => {
    expect(paths.comparison.getHref(['flow-alfa'], 'period=30d')).toBe(
      '/comparison?period=30d&flow=flow-alfa',
    );
  });
});
