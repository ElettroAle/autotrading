// ADR-test-della-dashboard-deterministici (Bug 610): a test that uses TanStack Query creates its client with the
// configuration of the platform, without retries and their exponential wait, or goes through src/testing/test-utils.tsx.
// No bare new QueryClient() in a test file: the rule of eslint.architecture.js is red on one, silent on a conforming one.
import { fileURLToPath } from 'node:url';

import { ESLint } from 'eslint';
import { beforeAll, describe, expect, it } from 'vitest';

const DASHBOARD = fileURLToPath(new URL('..', import.meta.url));
const RULE = 'no-restricted-syntax';

// Only the rule under proof runs: the import rules would load the resolver of the whole dashboard for nothing.
const architecture = new ESLint({
  cwd: DASHBOARD,
  overrideConfigFile: 'eslint.architecture.js',
  ruleFilter: ({ ruleId }) => ruleId === RULE,
});

const brokenRules = async (path: string, source: string): Promise<string[]> => {
  const [result] = await architecture.lintText(source, { filePath: `${DASHBOARD}${path}` });
  return (result?.messages ?? []).map((message) => message.ruleId ?? message.message);
};

const WARM_UP_TIMEOUT_MS = 60_000;

// The first lint loads the configuration and the parser, a fixed cost of seconds on a busy machine: it is paid once
// here, so no proof below is timed on it.
beforeAll(async () => {
  await brokenRules('src/testing/warm-up.test.ts', 'export {};\n');
}, WARM_UP_TIMEOUT_MS);

const IMPORTS =
  "import { QueryClient } from '@tanstack/react-query';\nimport { queryConfig } from '@/lib/react-query';\n";

const TEST_FILE = 'src/components/layouts/user-menu.test.tsx';

describe('ADR-test-della-dashboard-deterministici: the client of TanStack Query in the tests', () => {
  it.each([
    ['without options', 'const client = new QueryClient();\n'],
    ['with options of its own', 'const client = new QueryClient({ defaultOptions: {} });\n'],
    [
      'with retries of its own',
      'const client = new QueryClient({ defaultOptions: { queries: { retry: 3 } } });\n',
    ],
  ])('is red on a client %s in a test', async (_case, creation) => {
    expect(await brokenRules(TEST_FILE, `${IMPORTS}${creation}`)).toEqual([RULE]);
  });

  it('is red on a bare client in the testing code', async () => {
    expect(
      await brokenRules('src/testing/query-client.ts', `${IMPORTS}new QueryClient();\n`),
    ).toEqual([RULE]);
  });

  it('is silent on a client with the configuration of the platform', async () => {
    expect(
      await brokenRules(
        TEST_FILE,
        `${IMPORTS}const client = new QueryClient({ defaultOptions: queryConfig });\n`,
      ),
    ).toEqual([]);
  });
});
