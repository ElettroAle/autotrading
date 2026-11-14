import { dateTimeText } from './date-time';

describe('dateTimeText', () => {
  it('writes the date and the time in Italian, in the time zone of the browser', () => {
    expect(dateTimeText('2026-11-14T10:30:00Z', 'UTC')).toBe('14 nov 2026, 10:30');
    expect(dateTimeText('2026-11-14T10:30:00Z', 'Europe/Rome')).toBe('14 nov 2026, 11:30');
  });
});
