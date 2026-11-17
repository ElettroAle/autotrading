import { z } from 'zod';

import './zod-config';

describe('zod-config', () => {
  // ADR content-security-policy-rigida-della-dashboard: no eval, not even the attempt zod makes to see if it may.
  it('parses without compiling the schemas, which the content security policy forbids (ADR content-security-policy-rigida-della-dashboard)', () => {
    expect(z.config().jitless).toBe(true);
  });
});
