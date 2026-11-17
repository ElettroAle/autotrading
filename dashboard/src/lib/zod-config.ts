import { z } from 'zod';

// The content security policy forbids eval (ADR content-security-policy-rigida-della-dashboard): zod parses without
// compiling its schemas and never tries to, as the attempt is itself a violation the browser reports. The schemas
// read this when they are built, so the entry imports this module first.
z.config({ jitless: true });
