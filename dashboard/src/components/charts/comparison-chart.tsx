import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
  type DotItemDotProps,
} from 'recharts';

/** A point of a compared curve: the change of the equity from the first point of the period, null if not defined. */
export type ChangePoint = { readonly plannedAt: string; readonly changePercent: number | null };

export type ComparedSeries = {
  readonly id: string;
  readonly name: string;
  readonly points: readonly ChangePoint[];
};

/** One colour per compared flow, at most five, told apart also with the common forms of colour blindness. */
export const COMPARISON_COLORS = ['#0072B2', '#E69F00', '#009E73', '#CC79A7', '#D55E00'] as const;

const WIDTH = 720;
const HEIGHT = 320;

const percentFormat = new Intl.NumberFormat('it-IT', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: 'exceptZero',
});
const instantFormat = new Intl.DateTimeFormat('it-IT', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});
const dayFormat = new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: '2-digit' });

export const percentText = (percent: number): string => `${percentFormat.format(percent)}%`;
const instantText = (instant: number): string => instantFormat.format(new Date(instant));

/** What the tooltip says: the instant of the cycle, then the change of each flow with its name. */
export const tooltipLabel = (instant: unknown): string => instantText(Number(instant));
export const tooltipValue = (value: unknown, name: unknown): [string, string] => [
  percentText(Number(value)),
  String(name),
];

type PlottedPoint = { readonly instant: number; readonly changePercent: number | null };

const plotted = (points: readonly ChangePoint[]): PlottedPoint[] =>
  points.map((point) => ({
    instant: Date.parse(point.plannedAt),
    changePercent: point.changePercent,
  }));

type ColoredSeries = ComparedSeries & { readonly color: string };

// Colours go to the flows in their order; a sixth flow would have no colour of its own, so the chart has five at most.
const colored = (series: readonly ComparedSeries[]): ColoredSeries[] =>
  COMPARISON_COLORS.flatMap((color, index) => {
    const flow = series[index];
    return flow === undefined ? [] : [{ ...flow, color }];
  });

const ChangeDot = ({
  cx,
  cy,
  payload,
  name,
  color,
}: DotItemDotProps & { name: string; color: string }) => {
  const point = payload as PlottedPoint;
  if (point.changePercent === null) {
    return null;
  }
  return (
    <circle
      cx={cx}
      cy={cy}
      r={3}
      fill={color}
      role="img"
      aria-label={`${name} ${percentText(point.changePercent)} del ${instantText(point.instant)}`}
    />
  );
};

const Legend = ({ series }: { series: readonly ColoredSeries[] }) => (
  <ul aria-label="Legenda" className="mt-2 flex flex-wrap gap-4">
    {series.map((flow) => (
      <li key={flow.id} data-color={flow.color} className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className="inline-block h-3 w-3 rounded-full"
          style={{ backgroundColor: flow.color }}
        />
        {flow.name}
      </li>
    ))}
  </ul>
);

/**
 * The equity curves of up to five flows on the same time axis, each as the change in percent from its first point
 * of the period, so flows with different capitals compare (R2.4.3, ADR 0121, ADR 0137).
 */
export const ComparisonChart = ({ series }: { series: readonly ComparedSeries[] }) => {
  const curves = colored(series);
  return (
    <figure aria-label="Equity curve sovrapposte" className="overflow-x-auto">
      <LineChart width={WIDTH} height={HEIGHT} accessibilityLayer>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          type="number"
          dataKey="instant"
          domain={['dataMin', 'dataMax']}
          scale="time"
          allowDuplicatedCategory={false}
          tickFormatter={(instant: number) => dayFormat.format(new Date(instant))}
        />
        <YAxis domain={['auto', 'auto']} tickFormatter={percentText} width={72} />
        <Tooltip labelFormatter={tooltipLabel} formatter={tooltipValue} />
        <ReferenceLine y={0} stroke="#475569" strokeDasharray="4 4" />
        {curves.map((flow) => (
          <Line
            key={flow.id}
            type="linear"
            data={plotted(flow.points)}
            dataKey="changePercent"
            name={flow.name}
            stroke={flow.color}
            strokeWidth={2}
            dot={(props: DotItemDotProps) => (
              <ChangeDot key={props.index} {...props} name={flow.name} color={flow.color} />
            )}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
      <Legend series={curves} />
    </figure>
  );
};
