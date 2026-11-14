/** The date and time of an instant of the API, in Italian and in the time zone of the browser unless one is given. */
export const dateTimeText = (instant: string, timeZone?: string): string =>
  new Intl.DateTimeFormat('it-IT', { dateStyle: 'medium', timeStyle: 'short', timeZone }).format(
    new Date(instant),
  );
