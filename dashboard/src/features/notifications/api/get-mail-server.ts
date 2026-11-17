import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { readData, useApiClient } from '@/lib/api-client';
import { pageDataQuery } from '@/lib/react-query';

export const SECURITIES = ['STARTTLS', 'TLS'] as const;

export const securitySchema = z.enum(SECURITIES);

// Never the password: the API says only whether one is saved (ADR server-di-posta-per-tenant).
const mailServerSchema = z
  .object({
    host: z.string(),
    port: z.number(),
    security: securitySchema,
    username: z.string(),
    sender: z.string(),
    password_saved: z.boolean(),
  })
  .nullable();

export type MailServer = NonNullable<z.infer<typeof mailServerSchema>>;

export const MAIL_SERVER_QUERY_KEY = ['mail-server'] as const;

/** The mail server of the user, the one its emails leave from, or null when there is none (R3.5.5). */
export const useMailServer = () => {
  const api = useApiClient();
  return useQuery({
    ...pageDataQuery(...MAIL_SERVER_QUERY_KEY),
    queryFn: async () => readData(await api.GET('/notifications/mail-server'), mailServerSchema),
  });
};
