import {
  FAKE_SOURCES,
  type FakeSource,
  type FakeSourceAdapter,
  type FakeSourceParameter,
} from './catalogs';
import { keyExpiryResponse, type FakeKeyExpiry } from './key-expiry';

/** A field an adapter of a source declares for its configuration (R4.1.1). */
export type FakeConfigurationField = FakeSourceAdapter['configuration_fields'][number];

/** The secret API key of a paid adapter, as the adapters of the fake platform declare it (R4.1.2). */
export const SOURCE_API_KEY_FIELD: FakeConfigurationField = {
  name: 'api_key',
  label: 'Chiave API',
  secret: true,
};

/** The credentials a tenant gave an adapter: the secrets are kept only to prove they never come back (R4.1.2). */
export type FakeSourceCredentials = {
  readonly adapter: string;
  readonly publicValues: Record<string, string>;
  readonly secrets: Record<string, string>;
  readonly registeredAt: string;
  expiry?: FakeKeyExpiry;
  rejected: boolean;
};

type PaidAdapter = { readonly source: string; readonly adapter: FakeSourceAdapter };
type DeclaredParameter = { readonly source: string; readonly parameter: FakeSourceParameter };

const state = {
  // The adapters a scenario adds to the catalog: none by default, so the catalog of R4.1.1 stays as it is.
  paid: [] as PaidAdapter[],
  // The parameters a scenario adds to a source, valid for every adapter of it: none by default.
  declared: [] as DeclaredParameter[],
  credentials: new Map<string, FakeSourceCredentials[]>(),
};

const credentialsOfAccount = (account: string): FakeSourceCredentials[] => {
  const owned = state.credentials.get(account) ?? [];
  state.credentials.set(account, owned);
  return owned;
};

/** The reason the API gives for an adapter the tenant did not configure (R4.1.2). */
export const notConfiguredReason = (adapter: string): string =>
  `configura l'adapter ${adapter} in Impostazioni › Chiavi`;

/**
 * The adapters of the sources that need credentials, and the credentials each tenant gave them, as the API keeps them:
 * the secrets are sealed there and never answered (R4.1.2, ADR credenziali-degli-adapter-delle-fonti).
 */
export const fakeSourceCredentials = {
  reset(): void {
    state.paid = [];
    state.declared = [];
    state.credentials.clear();
  },

  /** A paid adapter of the source, which declares the fields given. */
  offerAdapter(
    source: string,
    name: string,
    fields: readonly FakeConfigurationField[] = [SOURCE_API_KEY_FIELD],
  ): void {
    state.paid.push({
      source,
      adapter: {
        name,
        description: `Indice di ${name}.`,
        parameters: [],
        configuration_fields: [...fields],
        offers_history: false,
      },
    });
  },

  /**
   * A parameter the source declares for every adapter of it: API, check and dashboard derive it from the declaration
   * alone (ADR parametri-delle-fonti-come-liste-libere).
   */
  declareParameter(source: string, parameter: FakeSourceParameter): void {
    state.declared.push({ source, parameter });
  },

  /** Every source with its adapters, those of the platform and the paid ones a scenario added. */
  sources(): FakeSource[] {
    return FAKE_SOURCES.map((source) => {
      const declared = state.declared
        .filter((each) => each.source === source.name)
        .map((each) => each.parameter);
      return {
        ...source,
        parameters: [...source.parameters, ...declared],
        adapters: [
          ...source.adapters,
          ...state.paid.filter((paid) => paid.source === source.name).map((paid) => paid.adapter),
        ].map((adapter) => ({ ...adapter, parameters: [...adapter.parameters, ...declared] })),
      };
    });
  },

  /** The adapters that need configuration, by name, each with the sources it offers. */
  configurable(): { readonly adapter: FakeSourceAdapter; readonly sources: string[] }[] {
    const adapters = new Map<string, { adapter: FakeSourceAdapter; sources: string[] }>();
    for (const source of fakeSourceCredentials.sources()) {
      for (const adapter of source.adapters.filter(
        (each) => each.configuration_fields.length > 0,
      )) {
        const entry = adapters.get(adapter.name) ?? { adapter, sources: [] };
        entry.sources.push(source.name);
        adapters.set(adapter.name, entry);
      }
    }
    return [...adapters.values()].sort((one, other) =>
      one.adapter.name.localeCompare(other.adapter.name),
    );
  },

  of(account: string, adapter: string): FakeSourceCredentials | undefined {
    return credentialsOfAccount(account).find((each) => each.adapter === adapter);
  },

  /** Saves the credentials of the adapter, or replaces them: a replacement clears the refusal and the old date. */
  save(
    account: string,
    adapter: FakeSourceAdapter,
    values: Record<string, string>,
    registeredAt: string,
    expiry?: FakeKeyExpiry,
  ): void {
    const owned = credentialsOfAccount(account);
    const kept = owned.filter((each) => each.adapter !== adapter.name);
    const valuesOf = (secret: boolean) =>
      Object.fromEntries(
        adapter.configuration_fields
          .filter((field) => field.secret === secret)
          .map((field) => [field.name, values[field.name] ?? '']),
      );
    owned.splice(0, owned.length, ...kept, {
      adapter: adapter.name,
      publicValues: valuesOf(false),
      secrets: valuesOf(true),
      registeredAt,
      expiry,
      rejected: false,
    });
  },

  /** The credentials a test gives the adapter of that name, as if the tenant had saved them on the page. */
  configure(
    account: string,
    adapter: string,
    values: Record<string, string>,
    registeredAt: string,
    expiry?: FakeKeyExpiry,
  ): void {
    const offered = fakeSourceCredentials
      .configurable()
      .find((each) => each.adapter.name === adapter);
    if (offered === undefined) {
      throw new Error(`l'adapter ${adapter} non richiede configurazione`);
    }
    fakeSourceCredentials.save(account, offered.adapter, values, registeredAt, expiry);
  },

  remove(account: string, adapter: string): boolean {
    const owned = credentialsOfAccount(account);
    const index = owned.findIndex((each) => each.adapter === adapter);
    if (index < 0) {
      return false;
    }
    owned.splice(index, 1);
    return true;
  },

  /** The provider refused the credentials in a cycle (R4.1.2). */
  reject(account: string, adapter: string): void {
    const credentials = fakeSourceCredentials.of(account, adapter);
    if (credentials !== undefined) {
      credentials.rejected = true;
    }
  },

  /** What the API answers for each adapter that needs configuration: never a secret. */
  summariesOf(account: string) {
    return fakeSourceCredentials.configurable().map(({ adapter, sources }) => {
      const credentials = fakeSourceCredentials.of(account, adapter.name);
      return {
        adapter: adapter.name,
        sources,
        configuration_fields: adapter.configuration_fields,
        configured: credentials !== undefined,
        public_values: credentials?.publicValues ?? {},
        registered_at: credentials?.registeredAt ?? null,
        rejected: credentials?.rejected ?? false,
        ...keyExpiryResponse(credentials?.expiry, true),
      };
    });
  },

  /** The catalog as the tenant reads it: an adapter it did not configure says why it cannot be activated. */
  offeredTo(account: string) {
    return fakeSourceCredentials.sources().map((source) => ({
      ...source,
      adapters: source.adapters.map((adapter) => {
        const needed = adapter.configuration_fields.length > 0;
        const configured = needed
          ? fakeSourceCredentials.of(account, adapter.name) !== undefined
          : null;
        return {
          ...adapter,
          configured,
          unavailable_reason: configured === false ? notConfiguredReason(adapter.name) : null,
        };
      }),
    }));
  },
};
