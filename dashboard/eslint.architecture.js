// The structure of the dashboard, from bulletproof-react (ADR 0116): dependencies flow one way, shared code ──> features
// ──> app, no feature imports another, production never imports the testing code, the server and the application
// never import each other. One chart library, Recharts, used only by the shared charts of src/components/charts
// (ADR 0121). Every rule is proved red on a violating example in architecture/structure.test.ts.
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
    ignores: [CHARTS],
    rules: {
      'no-restricted-imports': [
        'error',
        { patterns: [OTHER_CHART_LIBRARIES, RECHARTS_OUTSIDE_THE_CHARTS] },
      ],
    },
  },
  {
    files: [CHARTS],
    rules: { 'no-restricted-imports': ['error', { patterns: [OTHER_CHART_LIBRARIES] }] },
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
    files: TEST_FILES,
    rules: { 'import/no-restricted-paths': ['error', { zones: APPLICATION_ZONES }] },
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
