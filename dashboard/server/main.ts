import { join } from 'node:path';

import { runtimeConfigFrom } from './runtime-config.ts';
import { startDashboardServer } from './static-server.ts';

await startDashboardServer({
  root: process.env.DASHBOARD_ROOT ?? join(import.meta.dirname, '..', 'dist'),
  basePath: '/dashboard',
  config: runtimeConfigFrom(process.env),
  port: Number(process.env.DASHBOARD_PORT ?? '8080'),
});
