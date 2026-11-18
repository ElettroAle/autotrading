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

describe('paths.flowCycles', () => {
  it.each([
    [1, '', '/flows/flow-alfa/cycles'],
    [2, '', '/flows/flow-alfa/cycles?page=2'],
    [1, 'fallito', '/flows/flow-alfa/cycles?outcome=fallito'],
    [3, 'fallito', '/flows/flow-alfa/cycles?outcome=fallito&page=3'],
  ])('leads to page %i of the cycles with the outcome «%s» as %s', (page, outcome, href) => {
    expect(paths.flowCycles.getHref('flow-alfa', page, outcome)).toBe(href);
  });
});

// ADR elenco-dei-conti-e-pagina-del-conto: the page of an account and its tabs, each with an address of its own.
describe('paths of the page of an account', () => {
  it.each([
    ['account', '/accounts/account%201'],
    ['accountReconciliation', '/accounts/account%201/reconciliation'],
    ['accountCapital', '/accounts/account%201/capital'],
    ['accountSettings', '/accounts/account%201/settings'],
  ] as const)('leads %s to %s', (name, href) => {
    expect(paths[name].getHref('account 1')).toBe(href);
  });
});

describe('paths.accountAlarms', () => {
  it('leads to the alarms of the account', () => {
    expect(paths.accountAlarms.getHref('account-test-1')).toBe('/accounts/account-test-1/alarms');
  });
});

describe('paths.alerts', () => {
  it('leads to the alerts, filtered by the parameters of the API when given', () => {
    expect(paths.alerts.getHref()).toBe('/alerts');
    expect(paths.alerts.getHref({ resource_id: 'account-test-1', state: 'all' })).toBe(
      '/alerts?resource_id=account-test-1&state=all',
    );
  });

  it('leads to the detail of an alert', () => {
    expect(paths.alert.getHref('alert 1')).toBe('/alerts/alert%201');
  });
});
