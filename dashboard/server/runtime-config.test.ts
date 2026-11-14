import { describe, expect, it } from 'vitest';

import { runtimeConfigFrom } from './runtime-config.ts';

describe('runtimeConfigFrom', () => {
  it('reads the public configuration of the installation from its variables', () => {
    const config = runtimeConfigFrom({
      APP_ENVIRONMENT: 'dev',
      AUTH_ISSUER: 'https://login.example.test/tenant/v2.0',
      AUTH_CLIENT_ID: 'client',
      AUTH_SCOPE: 'api://client/access',
    });

    expect(config).toEqual({
      environment: 'dev',
      issuer: 'https://login.example.test/tenant/v2.0',
      clientId: 'client',
      scope: 'api://client/access',
    });
  });

  it('leaves a missing value empty so the dashboard can say the access is not configured', () => {
    expect(runtimeConfigFrom({ APP_ENVIRONMENT: 'prod' })).toEqual({
      environment: 'prod',
      issuer: '',
      clientId: '',
      scope: '',
    });
  });
});
