// ADR-grafici-condivisi-larghi-come-lo-schermo (Bug 593): every chart of components/charts behaves the same on any
// width. It is drawn inside ChartFrame, with TimeAxis and ChartTooltip; no chart has a width of its own, a figure
// that scrolls sideways, or an axis of time, a tooltip or a responsive container that are not the shared ones.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const CHARTS = fileURLToPath(new URL('../src/components/charts', import.meta.url));
const FRAME = 'chart-frame.tsx';

type SourceFile = { readonly path: string; readonly source: string };

const chartsOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { encoding: 'utf8' })
    .filter((path) => path.endsWith('.tsx') && !path.endsWith('.test.tsx'))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

const DRAWS_A_CHART = /<\w+Chart\b/;
const FIXED_WIDTH = /<\w+Chart\b[^>]*\bwidth=/s;
const SCROLLS_SIDEWAYS = /overflow-x-(?:auto|scroll)/;
const OWN_PARTS =
  /import\s*\{[^}]*\b(?:ResponsiveContainer|XAxis|Tooltip)\b[^}]*\}\s*from\s*'recharts'/s;
const SHARED_PARTS = ['ChartFrame', 'TimeAxis', 'ChartTooltip'] as const;

const missingSharedParts = (file: SourceFile): string[] =>
  SHARED_PARTS.filter((part) => !new RegExp(`<${part}\\b`).test(file.source)).map(
    (part) => `${file.path}: non usa ${part}`,
  );

const problemsOf = (file: SourceFile): string[] => [
  ...(FIXED_WIDTH.test(file.source) ? [`${file.path}: larghezza fissa del grafico`] : []),
  ...(SCROLLS_SIDEWAYS.test(file.source) ? [`${file.path}: scorrimento orizzontale`] : []),
  ...(OWN_PARTS.test(file.source)
    ? [`${file.path}: contenitore, asse del tempo o tooltip propri`]
    : []),
  ...missingSharedParts(file),
];

/** Each chart that breaks the decision, with the reason. */
const chartsOutsideTheFrame = (files: readonly SourceFile[]): string[] =>
  files
    .filter((file) => file.path !== FRAME && DRAWS_A_CHART.test(file.source))
    .flatMap(problemsOf);

const CONFORMING = `import { Line, LineChart } from 'recharts';
import { ChartFrame, ChartTooltip, TimeAxis } from './chart-frame';
export const Curves = () => (
  <ChartFrame label="Curve">
    <LineChart accessibilityLayer>
      <TimeAxis dataKey="instant" domain={['dataMin', 'dataMax']} />
      <YAxis width={72} />
      <ChartTooltip />
      <Line dataKey="value" />
    </LineChart>
  </ChartFrame>
);`;

const chart = (source: string): SourceFile[] => [{ path: 'curves.tsx', source }];

describe('ADR-grafici-condivisi-larghi-come-lo-schermo: every chart in the shared frame', () => {
  it.each(['{720}', '{WIDTH}'])('is red when a chart has a width of its own, as %s', (width) => {
    const source = CONFORMING.replace(
      '<LineChart accessibilityLayer>',
      `<LineChart width=${width} accessibilityLayer>`,
    );

    expect(chartsOutsideTheFrame(chart(source))).toEqual([
      'curves.tsx: larghezza fissa del grafico',
    ]);
  });

  it('is red when a figure scrolls sideways', () => {
    const source = `${CONFORMING}\nconst Box = () => <figure className="overflow-x-auto" />;`;

    expect(chartsOutsideTheFrame(chart(source))).toEqual(['curves.tsx: scorrimento orizzontale']);
  });

  it('is red when a chart uses an axis, a tooltip or a container of Recharts of its own', () => {
    const source = CONFORMING.replace(
      "import { Line, LineChart } from 'recharts';",
      "import { Line, LineChart, Tooltip, XAxis } from 'recharts';",
    );

    expect(chartsOutsideTheFrame(chart(source))).toEqual([
      'curves.tsx: contenitore, asse del tempo o tooltip propri',
    ]);
  });

  it('is red when a chart is drawn outside the shared frame, axis and tooltip', () => {
    const source = `import { Line, LineChart } from 'recharts';
export const Curves = () => <LineChart><Line dataKey="value" /></LineChart>;`;

    expect(chartsOutsideTheFrame(chart(source))).toEqual([
      'curves.tsx: non usa ChartFrame',
      'curves.tsx: non usa TimeAxis',
      'curves.tsx: non usa ChartTooltip',
    ]);
  });

  it('is silent on a chart in the shared frame, and on the frame itself', () => {
    const frame = { path: FRAME, source: "import { ResponsiveContainer, XAxis } from 'recharts';" };

    expect(chartsOutsideTheFrame([...chart(CONFORMING), frame])).toEqual([]);
  });

  it('finds every chart of the dashboard in the shared frame', () => {
    expect(chartsOutsideTheFrame(chartsOf(CHARTS))).toEqual([]);
  });
});
