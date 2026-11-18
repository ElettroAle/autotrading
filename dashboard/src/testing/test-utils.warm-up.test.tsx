import { fakePlatform } from './mocks/platform';
import { WARM_UP_ACCOUNT } from './test-utils';

// ADR test-della-dashboard-deterministici: the first opening of the dashboard in a file costs more than the next ones,
// so test-utils opens it before the tests, and leaves nothing behind. The only test of its file, so always the first.
describe('the opening of the dashboard before the tests of a file', () => {
  it('leaves an empty page, an empty platform and an empty browser to the first test', () => {
    expect(document.body).toBeEmptyDOMElement();
    expect(fakePlatform.hasUser(WARM_UP_ACCOUNT)).toBe(false);
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });
});
