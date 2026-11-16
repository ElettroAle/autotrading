const INSTANT = new Intl.DateTimeFormat('it-IT', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

const TIME_OF_DAY = new Intl.DateTimeFormat('it-IT', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

/** An instant as the API writes it (ISO 8601), shown in Italian in the time zone of the browser. */
export const formatInstant = (instant: string): string => INSTANT.format(new Date(instant));

/** Only the time of the day of an instant of the API, where the day is evident. */
export const formatTimeOfDay = (instant: string): string => TIME_OF_DAY.format(new Date(instant));

const MINUTE = new Intl.DateTimeFormat('it-IT', {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
});

/** The date and the minute of an instant, «16/11 09:15», in the time zone of the browser (ADR periodo-al-minuto). */
export const formatMinute = (instant: string): string => {
  const parts = Object.fromEntries(
    MINUTE.formatToParts(new Date(instant)).map((part) => [part.type, part.value]),
  );
  return `${parts.day}/${parts.month} ${parts.hour}:${parts.minute}`;
};
