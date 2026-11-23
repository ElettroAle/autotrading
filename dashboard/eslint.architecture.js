// The structure of the dashboard, from bulletproof-react (ADR 0116): dependencies flow one way, shared code ──> features
// ──> app, no feature imports another, production never imports the testing code, the server and the application
// never import each other. One chart library, Recharts, used only by the shared charts of src/components/charts
// (ADR 0121). One icon library, lucide-react, used only by the shared icons of src/components/ui/icons (ADR
// icone-con-lucide-react-e-comandi-condivisi). The query string changes through the shared hook of src/hooks/use-search-change.ts, never with a function
// of the last render (ADR 0166). A test creates the client of TanStack Query with the configuration of the platform (ADR
// test-della-dashboard-deterministici). A list counts its period from when it receives it, never from the clock of its
// render (ADR intervallo-delle-liste-fissato-alla-scelta-del-periodo). Every rule is proved red on a violating example in
// architecture/structure.test.ts, the last two in architecture/query-client-in-tests.test.ts and
// architecture/list-interval-fixed.test.ts.
import { readdirSync } from 'node:fs';

import checkFile from 'eslint-plugin-check-file';
import importPlugin from 'eslint-plugin-import';
import tseslint from 'typescript-eslint';

const FEATURES = readdirSync(new URL('./src/features', import.meta.url), { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name);

const SHARED = [
  './src/components',
  './src/config',
  './src/hooks',
  './src/lib',
  './src/stores',
  './src/types',
  './src/utils',
];

export const SOURCE_FILES = ['**/*.{ts,tsx,js}'];

const TEST_FILES = ['src/**/*.test.{ts,tsx}', 'src/testing/**'];

// One rule configuration per file: ESLint replaces, never merges, the options of a rule set twice.
const APPLICATION_ZONES = [
  ...FEATURES.map((feature) => ({
    target: `./src/features/${feature}`,
    from: './src/features',
    except: [`./${feature}`],
    message: "una funzionalità non importa un'altra funzionalità: la composizione sta in src/app",
  })),
  {
    target: './src/features',
    from: './src/app',
    message:
      'le dipendenze vanno in una sola direzione: src/app importa le funzionalità, mai il contrario',
  },
  {
    target: SHARED,
    from: ['./src/features', './src/app'],
    message: 'il codice condiviso non importa funzionalità né src/app',
  },
  {
    target: './src',
    from: ['./server', './e2e'],
    message: "l'applicazione non importa il server né le prove degli scenari",
  },
];

// A test gives TanStack Query the configuration of the platform, without retries and their exponential wait, so its
// result never depends on the speed of the machine (ADR test-della-dashboard-deterministici).
const BARE_QUERY_CLIENT_IN_TESTS = {
  selector:
    "NewExpression[callee.name='QueryClient']:not(:has(Property[key.name='defaultOptions'][value.name='queryConfig']))",
  message:
    'nei test il QueryClient ha la configurazione della piattaforma: new QueryClient({ defaultOptions: queryConfig }) o renderApp/renderInApp di src/testing/test-utils.tsx',
};

// A list asks its interval of useListInterval, fixed when the period is chosen: an instant read in the render changes the
// key of the query at every minute and drops the pages already read (ADR
// intervallo-delle-liste-fissato-alla-scelta-del-periodo).
const LIST_INTERVAL_MESSAGE =
  "l'intervallo di una lista si fissa alla scelta del periodo: useListInterval di src/components/ui/period-selector/use-period.ts, mai l'orologio letto nel render (ADR intervallo-delle-liste-fissato-alla-scelta-del-periodo)";

const CLOCK_IN_THE_RENDER = [
  { selector: "ImportSpecifier[imported.name='listIntervalOf']", message: LIST_INTERVAL_MESSAGE },
  {
    selector: "NewExpression[callee.name='Date'][arguments.length=0]",
    message: LIST_INTERVAL_MESSAGE,
  },
  {
    selector: "CallExpression[callee.object.name='Date'][callee.property.name='now']",
    message: LIST_INTERVAL_MESSAGE,
  },
];

// The API is called only through the client generated from its OpenAPI document (ADR 0119).
const API_CLIENT = 'src/lib/api-client.ts';

const OPENAPI_FETCH_OUTSIDE_THE_CLIENT = {
  name: 'openapi-fetch',
  message: "l'API si chiama solo dal client di src/lib/api-client.ts",
};

const NO_FAKES_IN_PRODUCTION = {
  target: './src',
  from: './src/testing',
  message: 'il codice di produzione non importa i finti di src/testing',
};

const CHARTS = 'src/components/charts/**';

const OTHER_CHART_LIBRARIES = {
  group: [
    'chart.js',
    'chart.js/*',
    'react-chartjs-2',
    'echarts',
    'echarts/*',
    'echarts-for-react',
    'd3',
    'd3-*',
    '@nivo/*',
    '@visx/*',
    'victory',
    'victory-*',
    'apexcharts',
    'react-apexcharts',
    'highcharts',
    'highcharts-react-official',
    'plotly.js',
    'plotly.js-*',
    'react-plotly.js',
  ],
  message: 'una sola libreria di grafici nella dashboard: Recharts (ADR 0121)',
};

const RECHARTS_OUTSIDE_THE_CHARTS = {
  group: ['recharts', 'recharts/*'],
  message:
    'Recharts si usa solo nei grafici condivisi di src/components/charts: le funzionalità passano i dati (ADR 0121)',
};

// Features and shared components name an icon of src/components/ui/icons, never draw one.
const ICONS = 'src/components/ui/icons/**';

const LUCIDE_OUTSIDE_THE_ICONS = {
  group: ['lucide-react', 'lucide-react/*'],
  message:
    'lucide-react si usa solo nelle icone condivise di src/components/ui/icons: comandi, azioni e direzioni ne nominano una (ADR icone-con-lucide-react-e-comandi-condivisi)',
};

// React Router hands the function of setSearchParams the query string of the last render, not the last one asked for:
// changes made before the page shows the previous one would overwrite each other (ADR 0166).
const SEARCH_CHANGE = 'src/hooks/use-search-change.ts';

const isFunction = (node) =>
  node?.type === 'ArrowFunctionExpression' || node?.type === 'FunctionExpression';

const isSearchParamsSetter = (declarator) =>
  declarator.init?.type === 'CallExpression' &&
  declarator.init.callee.type === 'Identifier' &&
  declarator.init.callee.name === 'useSearchParams' &&
  declarator.id.type === 'ArrayPattern' &&
  declarator.id.elements[1]?.type === 'Identifier';

const noSearchChangeFromTheLastRender = {
  meta: {
    type: 'problem',
    schema: [],
    messages: {
      fromTheLastRender:
        "l'indirizzo si cambia con useSearchChange di src/hooks/use-search-change.ts: setSearchParams con una funzione parte dall'ultima resa e perde i cambi in rapida successione (ADR 0166)",
    },
  },
  create: (context) => ({
    VariableDeclarator(declarator) {
      if (!isSearchParamsSetter(declarator)) {
        return;
      }
      const setter = declarator.id.elements[1];
      const variable = context.sourceCode
        .getDeclaredVariables(declarator)
        .find((declared) => declared.name === setter.name);
      variable?.references
        .map((reference) => reference.identifier)
        .filter(
          (identifier) =>
            identifier.parent.type === 'CallExpression' &&
            identifier.parent.callee === identifier &&
            isFunction(identifier.parent.arguments[0]),
        )
        .forEach((identifier) =>
          context.report({ node: identifier.parent, messageId: 'fromTheLastRender' }),
        );
    },
  }),
};

const searchPlugin = {
  rules: { 'no-search-change-from-the-last-render': noSearchChangeFromTheLastRender },
};

export default tseslint.config(
  {
    ignores: [
      'node_modules/',
      'dist/',
      'coverage/',
      'reports/',
      'test-results/',
      'playwright-report/',
      '.features-gen/',
      // Generated from the OpenAPI document of the API by npm run generate:api-client (ADR 0119).
      'src/lib/api-schema.d.ts',
    ],
  },
  {
    files: SOURCE_FILES,
    languageOptions: { parser: tseslint.parser, ecmaVersion: 'latest', sourceType: 'module' },
    plugins: { import: importPlugin, 'check-file': checkFile },
    settings: {
      'import/resolver': {
        typescript: { project: './tsconfig.json' },
      },
    },
    rules: {
      'import/no-cycle': 'error',
      'check-file/filename-naming-convention': [
        'error',
        { '**/*.{ts,tsx,js}': 'KEBAB_CASE' },
        { ignoreMiddleExtensions: true },
      ],
      'check-file/folder-naming-convention': [
        'error',
        { '{src,server,e2e,architecture}/**/': 'KEBAB_CASE' },
      ],
    },
  },
  {
    files: SOURCE_FILES,
    ignores: [CHARTS, API_CLIENT, ICONS],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [OPENAPI_FETCH_OUTSIDE_THE_CLIENT],
          patterns: [OTHER_CHART_LIBRARIES, RECHARTS_OUTSIDE_THE_CHARTS, LUCIDE_OUTSIDE_THE_ICONS],
        },
      ],
    },
  },
  {
    files: [API_CLIENT],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [OTHER_CHART_LIBRARIES, RECHARTS_OUTSIDE_THE_CHARTS, LUCIDE_OUTSIDE_THE_ICONS],
        },
      ],
    },
  },
  {
    files: [CHARTS],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [OPENAPI_FETCH_OUTSIDE_THE_CLIENT],
          patterns: [OTHER_CHART_LIBRARIES, LUCIDE_OUTSIDE_THE_ICONS],
        },
      ],
    },
  },
  {
    files: [ICONS],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [OPENAPI_FETCH_OUTSIDE_THE_CLIENT],
          patterns: [OTHER_CHART_LIBRARIES, RECHARTS_OUTSIDE_THE_CHARTS],
        },
      ],
    },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: TEST_FILES,
    rules: {
      'import/no-restricted-paths': [
        'error',
        { zones: [...APPLICATION_ZONES, NO_FAKES_IN_PRODUCTION] },
      ],
    },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: [SEARCH_CHANGE],
    plugins: { search: searchPlugin },
    rules: { 'search/no-search-change-from-the-last-render': 'error' },
  },
  {
    files: ['src/features/**/*.{ts,tsx}', 'src/app/**/*.{ts,tsx}'],
    ignores: TEST_FILES,
    rules: { 'no-restricted-syntax': ['error', ...CLOCK_IN_THE_RENDER] },
  },
  {
    files: TEST_FILES,
    rules: {
      'import/no-restricted-paths': ['error', { zones: APPLICATION_ZONES }],
      'no-restricted-syntax': ['error', BARE_QUERY_CLIENT_IN_TESTS],
    },
  },
  {
    files: ['server/**/*.ts'],
    rules: {
      'import/no-restricted-paths': [
        'error',
        {
          zones: [
            {
              target: './server',
              from: ['./src', './e2e'],
              message: "il server serve la build: non importa l'applicazione né le prove",
            },
          ],
        },
      ],
    },
  },
);
