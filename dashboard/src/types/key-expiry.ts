import { z } from 'zod';

/**
 * The expiry of a key as the API reads it today: the day and who gave it, its state and the days left, and whether the
 * user may give it. The dashboard counts no day (R6.2.2, ADR scadenza-nelle-pagine-chiavi-e-conti).
 */
export const keyExpiryFields = {
  expiry: z.object({ expires_on: z.string(), source: z.enum(['read', 'entered']) }).nullable(),
  expiry_status: z.enum(['unknown', 'valid', 'expiring', 'expired']),
  days_left: z.number().nullable(),
  expiry_editable: z.boolean(),
};

export type KeyExpiry = z.infer<z.ZodObject<typeof keyExpiryFields>>;
