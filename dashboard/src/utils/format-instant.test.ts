import { formatInstant, formatMinute, formatTimeOfDay } from './format-instant';

describe('formatInstant', () => {
  it('writes an instant of the API in Italian, in the time zone of the browser', () => {
    expect(formatInstant('2026-11-14T09:07:00Z')).toBe('14/11/2026, 10:07:00');
  });
});

describe('formatTimeOfDay', () => {
  it('writes only the time of an instant of the API, in the time zone of the browser', () => {
    expect(formatTimeOfDay('2026-11-14T09:07:00Z')).toBe('10:07:00');
  });
});

// ADR periodo-al-minuto: an end of an interval shows its date and its time, «16/11 09:15».
describe('formatMinute, ADR periodo-al-minuto', () => {
  it('writes the day, the month and the minute of an instant, in the time zone of the browser', () => {
    expect(formatMinute('2026-11-16T08:15Z')).toBe('16/11 09:15');
  });
});
