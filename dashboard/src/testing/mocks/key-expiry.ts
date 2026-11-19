import { fakeClock } from './clock';

/** The day a key of the fake platform stops working, and who gave it: read by the adapter or entered by the user. */
export type FakeKeyExpiry = { readonly expiresOn: string; readonly source: 'read' | 'entered' };

const DAY_MS = 86_400_000;
const EXPIRING_WITHIN_DAYS = 30;

const dayNumberOf = (isoDate: string): number => Date.parse(`${isoDate}T00:00:00Z`) / DAY_MS;

const todayNumber = (): number => Math.floor(fakeClock.now() / DAY_MS);

const statusOf = (daysLeft: number): 'expired' | 'expiring' | 'valid' => {
  if (daysLeft <= 0) {
    return 'expired';
  }
  return daysLeft <= EXPIRING_WITHIN_DAYS ? 'expiring' : 'valid';
};

/**
 * The expiry of a key as the API reads it today (UTC): unknown without a date, expiring within 30 days, expired on the
 * day itself (R6.2.2, ADR scadenza-delle-chiavi-letta-o-indicata).
 */
export const keyExpiryResponse = (expiry: FakeKeyExpiry | undefined, editable: boolean) => {
  if (expiry === undefined) {
    return { expiry: null, expiry_status: 'unknown', days_left: null, expiry_editable: editable };
  }
  const daysLeft = dayNumberOf(expiry.expiresOn) - todayNumber();
  return {
    expiry: { expires_on: expiry.expiresOn, source: expiry.source },
    expiry_status: statusOf(daysLeft),
    days_left: daysLeft,
    expiry_editable: editable,
  };
};

/** The date the user enters for a key, none when the field stays empty. */
export const enteredExpiryOf = (expiresOn: unknown): FakeKeyExpiry | undefined =>
  typeof expiresOn === 'string' && expiresOn !== '' ? { expiresOn, source: 'entered' } : undefined;
