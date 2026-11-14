// ADR-0116: the dashboard follows the structure of bulletproof-react. ADR-0121: Recharts is the one chart library, used
// only by the shared charts of src/components/charts. Every rule of eslint.architecture.js is red on an example that
// breaks it and silent on one that respects it, and the dashboard itself breaks none.
import { fileURLToPath } from 'node:url';

import { ESLint } from 'eslint';
import { beforeAll, describe, expect, it } from 'vitest';

const DASHBOARD = fileURLToPath(new URL('..', import.meta.url));

const architecture = new ESLint({ cwd: DASHBOARD, overrideConfigFile: 'eslint.architecture.js' });

const brokenRules = async (path: string, source: string): Promise<string[]> => {
  const [result] = await architecture.lintText(source, { filePath: `${DASHBOARD}${path}` });
  return (result?.messages ?? []).map((message) => message.ruleId ?? message.message);
};

const WARM_UP_TIMEOUT_MS = 60_000;

// The first lint loads the TypeScript resolver and the import graph of the dashboard, generated client included: it is
// paid once here, so no rule below is timed on it.
beforeAll(async () => {
  await architecture.lintFiles(['src/lib/api-client.ts']);
}, WARM_UP_TIMEOUT_MS);

const VIOLATING: ReadonlyArray<readonly [string, string, string]> = [
  [
    'a feature imports another feature',
    'src/features/flows/components/flow-summary.tsx',
    "import { useIdentity } from '@/features/access/api/get-identity';\n",
  ],
  [
    'a feature imports the app',
    'src/features/flows/components/flow-summary.tsx',
    "import { routes } from '@/app/router';\n",
  ],
  [
    'shared code imports a feature',
    'src/lib/flow-cache.ts',
    "import { useFlows } from '@/features/flows/api/get-flows';\n",
  ],
  [
    'shared code imports the app',
    'src/components/layouts/wide-layout.tsx',
    "import { AppProvider } from '@/app/provider';\n",
  ],
  [
    'production imports the fakes of the tests',
    'src/app/routes/demo.tsx',
    "import { renderApp } from '@/testing/test-utils';\n",
  ],
  [
    'the application imports the server',
    'src/config/server-config.ts',
    "import { runtimeConfigFrom } from '../../server/runtime-config.ts';\n",
  ],
  [
    'the server imports the application',
    'server/route-list.ts',
    "import { paths } from '../src/config/paths';\n",
  ],
  [
    'ADR-0121: a feature draws a chart with Recharts itself',
    'src/features/flows/components/flow-chart.tsx',
    "import { AreaChart } from 'recharts';\n",
  ],
  [
    'ADR-0121: the app draws a chart with Recharts itself',
    'src/app/routes/app/comparison.tsx',
    "import { LineChart } from 'recharts';\n",
  ],
  [
    'ADR-0121: the shared charts use a second chart library',
    'src/components/charts/bar-chart.tsx',
    "import { Bar } from 'react-chartjs-2';\n",
  ],
  [
    'ADR-0121: a feature uses a second chart library',
    'src/features/flows/components/flow-chart.tsx',
    "import * as d3 from 'd3';\n",
  ],
  ['a file is not named in kebab-case', 'src/components/ui/EnvironmentLabel.tsx', 'export {};\n'],
  [
    'a folder is not named in kebab-case',
    'src/features/flowHistory/api/get-history.ts',
    'export {};\n',
  ],
];

const CONFORMING: ReadonlyArray<readonly [string, string, string]> = [
  [
    'the app composes the features',
    'src/app/routes/app/summary.tsx',
    "import { FlowsList } from '@/features/flows/components/flows-list';\n",
  ],
  [
    'a feature uses shared code and its own modules',
    'src/features/flows/components/flow-summary.tsx',
    "import { useApiClient } from '@/lib/api-client';\nimport { useFlows } from '../api/get-flows';\n",
  ],
  [
    'ADR-0121: the shared charts use Recharts',
    'src/components/charts/line-chart.tsx',
    "import { LineChart } from 'recharts';\n",
  ],
  [
    'ADR-0121: a feature draws its data with a shared chart',
    'src/features/flows/components/flow-chart.tsx',
    "import { EquityChart } from '@/components/charts/equity-chart';\n",
  ],
  [
    'a test uses the fakes',
    'src/features/flows/components/flow-summary.test.tsx',
    "import { renderApp } from '@/testing/test-utils';\n",
  ],
  [
    'the server uses its own modules',
    'server/route-list.ts',
    "import { runtimeConfigFrom } from './runtime-config.ts';\n",
  ],
];

describe('ADR-0116, ADR-0121: the structure of the dashboard', () => {
  it.each(VIOLATING)('is red when %s', async (_rule, path, source) => {
    expect(await brokenRules(path, source)).not.toEqual([]);
  });

  it.each(CONFORMING)('is silent when %s', async (_rule, path, source) => {
    expect(await brokenRules(path, source)).toEqual([]);
  });

  it('is respected by the dashboard', async () => {
    const results = await architecture.lintFiles(['src', 'server', 'e2e', 'architecture']);
    const broken = results.flatMap((result) =>
      result.messages.map((message) => `${result.filePath}:${message.line} ${message.ruleId}`),
    );

    expect(broken).toEqual([]);
  });
});

describe('ADR-0119: one client for the API, generated from its OpenAPI document', () => {
  it('is red when the API is called without the client of src/lib/api-client.ts', async () => {
    expect(
      await brokenRules(
        'src/features/flows/api/get-cycles.ts',
        "import createClient from 'openapi-fetch';\n",
      ),
    ).toEqual(['no-restricted-imports']);
  });

  it('is silent when the client of src/lib/api-client.ts calls the API', async () => {
    expect(
      await brokenRules('src/lib/api-client.ts', "import createClient from 'openapi-fetch';\n"),
    ).toEqual([]);
  });
});
