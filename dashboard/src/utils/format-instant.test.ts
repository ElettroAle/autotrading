import { formatInstant } from './format-instant';

describe('formatInstant', () => {
  it('writes an instant of the API in Italian, in the time zone of the browser', () => {
    expect(formatInstant('2026-11-14T09:07:00Z')).toBe('14/11/2026, 10:07:00');
  });
});
