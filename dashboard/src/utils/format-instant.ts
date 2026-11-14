const INSTANT = new Intl.DateTimeFormat('it-IT', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

/** An instant as the API writes it (ISO 8601), shown in Italian in the time zone of the browser. */
export const formatInstant = (instant: string): string => INSTANT.format(new Date(instant));
