/** A day as the API writes it (ISO 8601, «2026-12-15»), shown in Italian, «15/12/2026», with no time zone to apply. */
export const formatDay = (day: string): string => day.split('-').reverse().join('/');

/** The day of a date input, absent when the input stays empty: the API reads no day as no date (R6.2.2). */
export const dayOrNothing = (value: string | undefined): string | undefined =>
  value === undefined || value === '' ? undefined : value;
