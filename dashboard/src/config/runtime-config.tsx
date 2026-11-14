import { createContext, use, type ReactNode } from 'react';
import { z } from 'zod';

/** The public configuration of the installation, served by the container as config.json (ADR 0117). */
const runtimeConfigSchema = z.object({
  environment: z.string().min(1),
  issuer: z.string(),
  clientId: z.string(),
  scope: z.string(),
});

export type RuntimeConfig = z.infer<typeof runtimeConfigSchema>;

export class RuntimeConfigUnavailableError extends Error {
  constructor(options?: ErrorOptions) {
    super('configurazione della dashboard non disponibile', options);
    this.name = 'RuntimeConfigUnavailableError';
  }
}

export const loadRuntimeConfig = async (fetcher: typeof fetch = fetch): Promise<RuntimeConfig> => {
  const address = new URL(`${import.meta.env.BASE_URL}config.json`, window.location.origin);
  const response = await fetcher(address, { cache: 'no-store' });
  if (!response.ok) {
    throw new RuntimeConfigUnavailableError();
  }
  const parsed = runtimeConfigSchema.safeParse(await response.json());
  if (!parsed.success) {
    throw new RuntimeConfigUnavailableError({ cause: parsed.error });
  }
  return parsed.data;
};

// Without an identity provider nobody gets in: the dashboard fails closed, as the API does (ADR 0016).
export const isAccessConfigured = (config: RuntimeConfig): boolean =>
  config.issuer !== '' && config.clientId !== '' && config.scope !== '';

const RuntimeConfigContext = createContext<RuntimeConfig | null>(null);

export const RuntimeConfigProvider = ({
  config,
  children,
}: {
  config: RuntimeConfig;
  children: ReactNode;
}) => <RuntimeConfigContext value={config}>{children}</RuntimeConfigContext>;

export const useRuntimeConfig = (): RuntimeConfig => {
  const config = use(RuntimeConfigContext);
  if (config === null) {
    throw new RuntimeConfigUnavailableError();
  }
  return config;
};
