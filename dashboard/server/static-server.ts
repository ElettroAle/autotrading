import { readdir, readFile } from 'node:fs/promises';
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';
import { extname, join, relative, sep } from 'node:path';

import type { RuntimeConfig } from './runtime-config.ts';

export type DashboardServer = Server;

export type DashboardSite = {
  readonly root: string;
  readonly basePath: string;
  readonly config: RuntimeConfig;
  readonly port: number;
};

type SiteFiles = ReadonlyMap<string, Buffer>;

const CONTENT_TYPES: Readonly<Record<string, string>> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
};
const BINARY = 'application/octet-stream';
const IMMUTABLE = 'public, max-age=31536000, immutable';
const REVALIDATE = 'no-cache';
const INDEX = '/index.html';

/**
 * Serves the built dashboard read only (ADR 0117): the files are read once at start, so a request can only ever name
 * one of them and no path reaches the disk; every other route of the single page application gets index.html.
 */
export const startDashboardServer = async (site: DashboardSite): Promise<DashboardServer> => {
  const files = await readSite(site.root);
  const server = createServer(dashboardHandler(site, files));
  await new Promise<void>((resolve) => server.listen(site.port, resolve));
  return server;
};

const readSite = async (root: string): Promise<SiteFiles> => {
  const entries = await readdir(root, { recursive: true, withFileTypes: true });
  const files = entries
    .filter((entry) => entry.isFile())
    .map((entry) => join(entry.parentPath, entry.name));
  const contents = await Promise.all(files.map((file) => readFile(file)));
  return new Map(files.map((file, index) => [urlPathOf(root, file), contents[index] as Buffer]));
};

const urlPathOf = (root: string, file: string): string =>
  `/${relative(root, file).split(sep).join('/')}`;

const dashboardHandler =
  (site: DashboardSite, files: SiteFiles) =>
  (request: IncomingMessage, response: ServerResponse): void => {
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      response.writeHead(405, { Allow: 'GET, HEAD' }).end();
      return;
    }
    const path = decodedPath(request.url ?? '/');
    if (path === undefined) {
      response.writeHead(400).end();
      return;
    }
    if (path === site.basePath) {
      response.writeHead(308, { Location: `${site.basePath}/` }).end();
      return;
    }
    if (!path.startsWith(`${site.basePath}/`)) {
      response.writeHead(404).end();
      return;
    }
    const sitePath = path.slice(site.basePath.length);
    const reply = replyFor(sitePath, site, files);
    response.writeHead(200, { ...securityHeaders(site.config), ...reply.headers });
    response.end(request.method === 'HEAD' ? undefined : reply.body);
  };

const decodedPath = (url: string): string | undefined => {
  try {
    return decodeURIComponent(new URL(url, 'http://dashboard').pathname);
  } catch {
    return undefined;
  }
};

type Reply = { readonly headers: Readonly<Record<string, string>>; readonly body: Buffer | string };

const replyFor = (sitePath: string, site: DashboardSite, files: SiteFiles): Reply => {
  if (sitePath === '/health') {
    return json({ status: 'ok' });
  }
  if (sitePath === '/config.json') {
    return json(site.config);
  }
  const file = files.get(sitePath);
  if (file !== undefined && sitePath !== INDEX) {
    return { headers: fileHeaders(sitePath), body: file };
  }
  return { headers: fileHeaders(INDEX), body: files.get(INDEX) ?? '' };
};

const json = (value: object): Reply => ({
  headers: { 'Content-Type': CONTENT_TYPES['.json'] ?? BINARY, 'Cache-Control': 'no-store' },
  body: JSON.stringify(value),
});

// Vite names every file under assets/ by its content: a new build never reuses a name, so those never expire.
const fileHeaders = (sitePath: string): Record<string, string> => ({
  'Content-Type': CONTENT_TYPES[extname(sitePath)] ?? BINARY,
  'Cache-Control': sitePath.startsWith('/assets/') ? IMMUTABLE : REVALIDATE,
});

const securityHeaders = (config: RuntimeConfig): Record<string, string> => ({
  'Content-Security-Policy': [
    "default-src 'self'",
    `connect-src 'self' ${issuerOrigin(config.issuer)}`.trimEnd(),
    "img-src 'self' data:",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; '),
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
});

// The browser exchanges the authorization code and refreshes the token with the identity provider (ADR 0118).
const issuerOrigin = (issuer: string): string => {
  try {
    return new URL(issuer).origin;
  } catch {
    return '';
  }
};
