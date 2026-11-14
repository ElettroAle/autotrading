import { useId } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
  type DotItemDotProps,
} from 'recharts';

export type EquityPoint = { readonly plannedAt: string; readonly equity: number };

type EquityChartProps = {
  readonly points: readonly EquityPoint[];
  /** The initial capital: the curve is green above it and red below it (RF-23.01). */
  readonly baseline: number;
};

export const ABOVE_COLOR = '#16a34a';
export const BELOW_COLOR = '#dc2626';
const WIDTH = 720;
const HEIGHT = 320;

const amountFormat = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 2 });
const instantFormat = new Intl.DateTimeFormat('it-IT', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});
const dayFormat = new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: '2-digit' });

const amountText = (value: number): string => amountFormat.format(value);
const instantText = (instant: string): string => instantFormat.format(new Date(instant));

/** What the tooltip of a point says: the instant of the cycle, then its equity. */
export const tooltipLabel = (instant: unknown): string => instantText(String(instant));
export const tooltipValue = (value: unknown): [string, string] => [
  amountText(Number(value)),
  'Equity',
];

const isAbove = (equity: number, baseline: number): boolean => equity >= baseline;

/**
 * Where, from the top of the chart, the colour turns from green to red: the initial capital between the highest and
 * the lowest equity, as a fraction of the gradient (ADR 0121).
 */
export const splitOffset = (equities: readonly number[], baseline: number): number => {
  const highest = Math.max(...equities);
  const lowest = Math.min(...equities);
  if (highest === lowest) {
    return isAbove(highest, baseline) ? 1 : 0;
  }
  return Math.min(1, Math.max(0, (highest - baseline) / (highest - lowest)));
};

const EquityDot = ({ cx, cy, payload, baseline }: DotItemDotProps & { baseline: number }) => {
  const point = payload as EquityPoint;
  const above = isAbove(point.equity, baseline);
  return (
    <circle
      cx={cx}
      cy={cy}
      r={4}
      fill={above ? ABOVE_COLOR : BELOW_COLOR}
      role="img"
      aria-label={`Equity ${amountText(point.equity)} del ${instantText(point.plannedAt)}, nell'area ${above ? 'verde' : 'rossa'}`}
      data-planned-at={point.plannedAt}
    />
  );
};

/** The equity curve of a flow, a point for each cycle, green above the initial capital and red below (ADR 0121). */
export const EquityChart = ({ points, baseline }: EquityChartProps) => {
  const id = `equity-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const offset = splitOffset(
    points.map((point) => point.equity),
    baseline,
  );
  const colours = (suffix: string) => (
    <linearGradient id={`${id}-${suffix}`} x1="0" y1="0" x2="0" y2="1">
      <stop offset={offset} stopColor={ABOVE_COLOR} stopOpacity={suffix === 'fill' ? 0.3 : 1} />
      <stop offset={offset} stopColor={BELOW_COLOR} stopOpacity={suffix === 'fill' ? 0.3 : 1} />
    </linearGradient>
  );
  return (
    <figure aria-label="Equity curve" className="overflow-x-auto">
      <AreaChart width={WIDTH} height={HEIGHT} data={[...points]} accessibilityLayer>
        <defs>
          {colours('fill')}
          {colours('stroke')}
        </defs>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="plannedAt"
          tickFormatter={(instant: string) => dayFormat.format(new Date(instant))}
        />
        <YAxis domain={['auto', 'auto']} tickFormatter={amountText} width={72} />
        <Tooltip labelFormatter={tooltipLabel} formatter={tooltipValue} />
        <ReferenceLine
          y={baseline}
          stroke="#475569"
          strokeDasharray="4 4"
          label={`Capitale iniziale ${amountText(baseline)}`}
        />
        <Area
          type="linear"
          dataKey="equity"
          baseValue={baseline}
          stroke={`url(#${id}-stroke)`}
          fill={`url(#${id}-fill)`}
          dot={(props: DotItemDotProps) => (
            <EquityDot key={props.index} {...props} baseline={baseline} />
          )}
          isAnimationActive={false}
        />
      </AreaChart>
    </figure>
  );
};
