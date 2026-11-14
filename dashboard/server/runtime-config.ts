/** The public configuration of the installation the dashboard needs in the browser: no secret (ADR 0117, ADR 0118). */
export type RuntimeConfig = {
  readonly environment: string;
  readonly issuer: string;
  readonly clientId: string;
  readonly scope: string;
};

type Variables = Readonly<Record<string, string | undefined>>;

// The same variables the pipeline writes for api, so one installation configures both alike.
export const runtimeConfigFrom = (variables: Variables): RuntimeConfig => ({
  environment: variables.APP_ENVIRONMENT ?? '',
  issuer: variables.AUTH_ISSUER ?? '',
  clientId: variables.AUTH_CLIENT_ID ?? '',
  scope: variables.AUTH_SCOPE ?? '',
});
