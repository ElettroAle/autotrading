import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import type { AddressInfo } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import type { RuntimeConfig } from './runtime-config.ts';
import { startDashboardServer, type DashboardServer } from './static-server.ts';

const CONFIG: RuntimeConfig = {
  environment: 'dev',
  issuer: 'https://login.example.test/tenant/v2.0',
  clientId: 'client',
  scope: 'api://client/access',
};

let root: string;
let server: DashboardServer;
let origin: string;

beforeEach(async () => {
  root = await mkdtemp(join(tmpdir(), 'dashboard-'));
  await mkdir(join(root, 'assets'));
  await writeFile(join(root, 'index.html'), '<html>app</html>');
  await writeFile(join(root, 'assets', 'index-abc.js'), 'console.log(1)');
  await writeFile(join(root, 'favicon.svg'), '<svg/>');
  server = await startDashboardServer({ root, basePath: '/dashboard', config: CONFIG, port: 0 });
  origin = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

afterEach(async () => {
  await new Promise((resolve) => server.close(resolve));
  await rm(root, { recursive: true, force: true });
});

describe('dashboard server', () => {
  it('answers the health check of the compose', async () => {
    const response = await fetch(`${origin}/dashboard/health`);

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: 'ok' });
  });

  it('serves the configuration of the installation, never cached', async () => {
    const response = await fetch(`${origin}/dashboard/config.json`);

    expect(response.status).toBe(200);
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(await response.json()).toEqual(CONFIG);
  });

  it('serves a built asset with its type and a long cache', async () => {
    const response = await fetch(`${origin}/dashboard/assets/index-abc.js`);

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toBe('text/javascript; charset=utf-8');
    expect(response.headers.get('cache-control')).toBe('public, max-age=31536000, immutable');
    expect(await response.text()).toBe('console.log(1)');
  });

  it('serves a file outside the assets without a long cache', async () => {
    const response = await fetch(`${origin}/dashboard/favicon.svg`);

    expect(response.headers.get('content-type')).toBe('image/svg+xml');
    expect(response.headers.get('cache-control')).toBe('no-cache');
  });

  it('falls back to the application page for the routes of the single page application', async () => {
    const response = await fetch(`${origin}/dashboard/flows/123`);

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toBe('text/html; charset=utf-8');
    expect(response.headers.get('cache-control')).toBe('no-cache');
    expect(await response.text()).toBe('<html>app</html>');
  });

  // ADR content-security-policy-rigida-della-dashboard: the tokens live in localStorage, so no script but the
  // dashboard's own may run, nothing else may be loaded and the page sits in no frame.
  const directivesOf = (policy: string): Map<string, string> =>
    new Map(
      policy.split(';').map((directive) => {
        const [name = '', ...sources] = directive.trim().split(' ');
        return [name, sources.join(' ')];
      }),
    );

  it('serves the strict content security policy of the dashboard (ADR content-security-policy-rigida-della-dashboard)', async () => {
    const response = await fetch(`${origin}/dashboard/`);
    const policy = response.headers.get('content-security-policy') ?? '';

    expect(Object.fromEntries(directivesOf(policy))).toEqual({
      'default-src': "'none'",
      'script-src': "'self'",
      'style-src': "'self'",
      'img-src': "'self' data:",
      'font-src': "'self'",
      'connect-src': "'self' https://login.example.test",
      'manifest-src': "'self'",
      'frame-src': "'none'",
      'frame-ancestors': "'none'",
      'object-src': "'none'",
      'base-uri': "'none'",
      'form-action': "'self'",
    });
    expect(policy).not.toContain('unsafe-inline');
    expect(policy).not.toContain('unsafe-eval');
  });

  it('serves the other security headers of the dashboard', async () => {
    const response = await fetch(`${origin}/dashboard/`);

    expect(response.headers.get('x-content-type-options')).toBe('nosniff');
    expect(response.headers.get('referrer-policy')).toBe('no-referrer');
    expect(response.headers.get('strict-transport-security')).toBe('max-age=31536000');
  });

  it('allows only the dashboard itself while the identity provider is not configured', async () => {
    await new Promise((resolve) => server.close(resolve));
    server = await startDashboardServer({
      root,
      basePath: '/dashboard',
      config: { ...CONFIG, issuer: '' },
      port: 0,
    });
    origin = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;

    const response = await fetch(`${origin}/dashboard/`);

    expect(response.headers.get('content-security-policy')).toContain("; connect-src 'self';");
  });

  it('never serves a file outside the built site', async () => {
    const response = await fetch(`${origin}/dashboard/..%2F..%2Fetc%2Fpasswd`);

    expect(await response.text()).toBe('<html>app</html>');
  });

  it('redirects the bare base path to the application', async () => {
    const response = await fetch(`${origin}/dashboard`, { redirect: 'manual' });

    expect(response.status).toBe(308);
    expect(response.headers.get('location')).toBe('/dashboard/');
  });

  it('answers not found outside the base path', async () => {
    const response = await fetch(`${origin}/flows`);

    expect(response.status).toBe(404);
  });

  it('accepts only reads', async () => {
    const response = await fetch(`${origin}/dashboard/`, { method: 'POST' });

    expect(response.status).toBe(405);
    expect(response.headers.get('allow')).toBe('GET, HEAD');
  });

  it('answers a read of the head without a body', async () => {
    const response = await fetch(`${origin}/dashboard/health`, { method: 'HEAD' });

    expect(response.status).toBe(200);
    expect(await response.text()).toBe('');
  });

  it('rejects a path that cannot be decoded', async () => {
    const response = await fetch(`${origin}/dashboard/%E0%A4%A`);

    expect(response.status).toBe(400);
  });
});
