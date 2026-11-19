// ADR-legenda-condivisa-dei-grafici (R6.5.6): a chart of components/charts with a legend draws it with ChartLegend, the
// shared legend that wraps on a phone and shows the marks of the chart; no chart has a legend of its own, neither a
// list of its own nor the legend of Recharts.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const CHARTS = fileURLToPath(new URL('../src/components/charts', import.meta.url));
const LEGEND = 'chart-legend.tsx';

type SourceFile = { readonly path: string; readonly source: string };

const chartsOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { encoding: 'utf8' })
    .filter((path) => path.endsWith('.tsx') && !path.endsWith('.test.tsx'))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

const OWN_LIST = /<(?:ul|ol)\b/;
const RECHARTS_LEGEND = /import\s*\{[^}]*\bLegend\b[^}]*\}\s*from\s*'recharts'/s;
const FOOTER = /\bfooter=\{\s*(<\w+)?/g;

const footersWithoutTheSharedLegend = (file: SourceFile): string[] =>
  [...file.source.matchAll(FOOTER)]
    .filter((footer) => footer[1] !== '<ChartLegend')
    .map(() => `${file.path}: legenda senza ChartLegend`);

const problemsOf = (file: SourceFile): string[] => [
  ...(OWN_LIST.test(file.source) ? [`${file.path}: legenda propria`] : []),
  ...(RECHARTS_LEGEND.test(file.source) ? [`${file.path}: legenda di Recharts`] : []),
  ...footersWithoutTheSharedLegend(file),
];

/** Each chart that draws a legend without the shared one, with the reason. */
const legendsOutsideTheSharedOne = (files: readonly SourceFile[]): string[] =>
  files.filter((file) => file.path !== LEGEND).flatMap(problemsOf);

const CONFORMING = `import { Line, LineChart } from 'recharts';
import { ChartFrame } from './chart-frame';
import { ChartLegend } from './chart-legend';
export const Curves = () => (
  <ChartFrame label="Curve" footer={<ChartLegend entries={[]} />}>
    <LineChart><Line dataKey="value" /></LineChart>
  </ChartFrame>
);`;

const chart = (source: string): SourceFile[] => [{ path: 'curves.tsx', source }];

describe('ADR-legenda-condivisa-dei-grafici: every legend of a chart is the shared one', () => {
  it('is red when a chart passes its frame a legend of its own', () => {
    const source = CONFORMING.replace('<ChartLegend entries={[]} />', '<Legend series={[]} />');

    expect(legendsOutsideTheSharedOne(chart(source))).toEqual([
      'curves.tsx: legenda senza ChartLegend',
    ]);
  });

  it('is red when a chart draws a list of its own', () => {
    const source = `${CONFORMING}\nconst Legend = () => <ul aria-label="Legenda" />;`;

    expect(legendsOutsideTheSharedOne(chart(source))).toEqual(['curves.tsx: legenda propria']);
  });

  it('is red when a chart uses the legend of Recharts', () => {
    const source = CONFORMING.replace(
      "import { Line, LineChart } from 'recharts';",
      "import { Legend, Line, LineChart } from 'recharts';",
    );

    expect(legendsOutsideTheSharedOne(chart(source))).toEqual(['curves.tsx: legenda di Recharts']);
  });

  it('is silent on a chart with the shared legend, and on the shared legend itself', () => {
    const legend = { path: LEGEND, source: 'export const ChartLegend = () => <ul />;' };

    expect(legendsOutsideTheSharedOne([...chart(CONFORMING), legend])).toEqual([]);
  });

  it('finds every legend of the dashboard charts drawn with ChartLegend', () => {
    expect(legendsOutsideTheSharedOne(chartsOf(CHARTS))).toEqual([]);
  });
});
