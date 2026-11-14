/// <reference types="node" />
import '@testing-library/jest-dom/vitest';
import { webcrypto } from 'node:crypto';

import { cleanup } from '@testing-library/react';

import { fakePlatform } from './mocks/platform';
import { server } from './mocks/server';

// MSAL computes the PKCE challenge with Web Crypto, which jsdom leaves out.
Object.defineProperty(globalThis, 'crypto', { value: webcrypto, configurable: true });

beforeAll(() => server.listen({ onUnhandledFrame: 'error' }));
afterAll(() => server.close());
afterEach(() => {
  cleanup();
  server.resetHandlers();
  fakePlatform.reset();
  sessionStorage.clear();
  localStorage.clear();
});
