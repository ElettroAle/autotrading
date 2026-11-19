import { useId, useRef, useState, type ReactElement } from 'react';
import { Link } from 'react-router';
import {
  Area,
  AreaChart,
  CartesianGrid,
  DefaultZIndexes,
  ReferenceArea,
  ReferenceLine,
  useXAxisScale,
  useYAxisScale,
  YAxis,
  ZIndexLayer,
  type DotItemDotProps,
  type MouseHandlerDataParam,
} from 'recharts';

import {
  ChartFrame,
  ChartTooltip,
  DOT_RADIUS,
  dotRadius,
  TimeAxis,
  useChartWidth,
} from './chart-frame';
import { ChartLegend, type LegendEntry } from './chart-legend';

export type EquityPoint = { readonly plannedAt: string; readonly equity: number };

/**
 * Something that happened at an instant, drawn on the curve: its label names it, its destination tells it in full. A
 * failed cycle is a red cross (ADR cicli-falliti-sull-equity-curve), a change of the capital a violet diamond (ADR
 * rendimento-composto-tra-le-variazioni-di-capitale).
 */
export type ChartEvent = {
  readonly kind: 'failed-cycle' | 'capital-change';
  readonly instant: string;
  readonly label: string;
  readonly to: string;
};

/** A drag on the chart: pressed, and the instants of its first and last point on the axis of time; empty with no drag. */
export type Selection = {
  readonly pressed?: boolean;
  readonly start?: number;
  readonly end?: number;
};

type EquityChartProps = {
  readonly points: readonly EquityPoint[];
  /** The initial capital: the curve is green above it and red below it (RF-23.01). */
  readonly baseline: number;
  /** The events marked on the curve, each with the mark of its kind and a link to it. */
  readonly events?: readonly ChartEvent[];
  /** Called with the instants of the first and the last point of a drag on the chart, the earlier first. */
  readonly onSelect?: (from: string, to: string) => void;
  /** What the chart says without points; by default, that the period has no cycle. */
  readonly empty?: string;
};

type EquityDatum = EquityPoint & { readonly time: number };

export const ABOVE_COLOR = '#16a34a';
export const BELOW_COLOR = '#dc2626';
export const CHANGE_COLOR = '#7c3aed';
const BASELINE_COLOR = '#475569';
export const BASELINE_DASH = '4 4';
const SELECTION_COLOR = '#2563eb';
const MARK_SIZE = 6;
// A finger needs more than the cross to hit it (ADR viste-e-comandi-della-pagina-del-flusso).
const MARK_TOUCH_RADIUS = 12;
// A lone point sits in the middle of an hour of axis, so it shows as a point and not on the edge of the chart.
const LONE_POINT_MARGIN_MS = 30 * 60 * 1000;
const NO_CYCLE = 'Nessun ciclo nel periodo';

const amountFormat = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 2 });
const instantFormat = new Intl.DateTimeFormat('it-IT', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

const amountText = (value: number): string => amountFormat.format(value);
const instantText = (instant: string | number): string => instantFormat.format(new Date(instant));

/** What the tooltip of a point says: the instant of the cycle, then its equity. */
export const tooltipLabel = (instant: unknown): string =>
  instantText(typeof instant === 'number' ? instant : String(instant));
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

const timeOf = (point: EquityPoint): number => Date.parse(point.plannedAt);

/** The equity of the curve at an instant: on the line between the points around it, the nearest point outside them. */
export const equityAt = (points: readonly EquityPoint[], time: number): number => {
  const sorted = points.toSorted((first, second) => timeOf(first) - timeOf(second));
  const after = sorted.findIndex((point) => timeOf(point) >= time);
  const next = sorted[after];
  const previous = sorted[after - 1];
  if (next === undefined) {
    return sorted.at(-1)?.equity ?? 0;
  }
  if (previous === undefined) {
    return next.equity;
  }
  const share = (time - timeOf(previous)) / (timeOf(next) - timeOf(previous));
  return previous.equity + share * (next.equity - previous.equity);
};

/** A drag starts on the point pressed; a press that finds no point, as a finger's first touch, waits for one. */
export const selectionStarted = (at: number | undefined): Selection =>
  at === undefined ? { pressed: true } : { pressed: true, start: at, end: at };

/** A drag follows the point reached, starting from it if the press found none; away from the points it stays. */
export const selectionMoved = (selection: Selection, at: number | undefined): Selection => {
  if (selection.pressed !== true || at === undefined) {
    return selection;
  }
  return { pressed: true, start: selection.start ?? at, end: at };
};

/** The instants a drag chooses, the earlier first; a press that never moved chooses nothing. */
export const chosenRange = (selection: Selection): [number, number] | undefined => {
  const { start, end } = selection;
  if (start === undefined || end === undefined || start === end) {
    return undefined;
  }
  return [Math.min(start, end), Math.max(start, end)];
};

const pointAt = (state: MouseHandlerDataParam): number | undefined =>
  typeof state.activeLabel === 'number' ? state.activeLabel : undefined;

const EquityDot = ({
  cx,
  cy,
  payload,
  baseline,
  radius,
}: DotItemDotProps & { baseline: number; radius: number }) => {
  const point = payload as EquityPoint;
  const above = isAbove(point.equity, baseline);
  return (
    <circle
      cx={cx}
      cy={cy}
      r={radius}
      fill={above ? ABOVE_COLOR : BELOW_COLOR}
      // A point only shows: the marks of the events above it take the pointer.
      pointerEvents="none"
      role="img"
      aria-label={`Equity ${amountText(point.equity)} del ${instantText(point.plannedAt)}, nell'area ${above ? 'verde' : 'rossa'}`}
      data-planned-at={point.plannedAt}
    />
  );
};

const CROSS = `M${-MARK_SIZE},${-MARK_SIZE}L${MARK_SIZE},${MARK_SIZE}M${-MARK_SIZE},${MARK_SIZE}L${MARK_SIZE},${-MARK_SIZE}`;
const DIAMOND = `M0,${-MARK_SIZE}L${MARK_SIZE},0L0,${MARK_SIZE}L${-MARK_SIZE},0Z`;

const MARKS: Readonly<Record<ChartEvent['kind'], ReactElement>> = {
  'failed-cycle': <path d={CROSS} stroke={BELOW_COLOR} strokeWidth={3} strokeLinecap="round" />,
  'capital-change': <path d={DIAMOND} fill={CHANGE_COLOR} stroke="#ffffff" strokeWidth={1} />,
};

// The legend names the marks the chart draws, with the same marks (ADR legenda-condivisa-dei-grafici).
const POINT_LEGEND: readonly LegendEntry[] = [
  { mark: <circle r={DOT_RADIUS} fill={ABOVE_COLOR} />, label: 'sopra il capitale iniziale' },
  { mark: <circle r={DOT_RADIUS} fill={BELOW_COLOR} />, label: 'sotto il capitale iniziale' },
  {
    mark: (
      <line
        x1={-MARK_SIZE}
        x2={MARK_SIZE}
        stroke={BASELINE_COLOR}
        strokeDasharray={BASELINE_DASH}
      />
    ),
    label: 'capitale iniziale',
  },
];

const EVENT_NAMES: Readonly<Record<ChartEvent['kind'], string>> = {
  'failed-cycle': 'ciclo fallito',
  'capital-change': 'variazione di capitale',
};

const EVENT_KINDS: readonly ChartEvent['kind'][] = ['failed-cycle', 'capital-change'];

/** The entries of the legend: the points and the initial capital always, a kind of event only if the chart has one. */
const legendOf = (events: readonly ChartEvent[]): LegendEntry[] => [
  ...POINT_LEGEND,
  ...EVENT_KINDS.filter((kind) => events.some((event) => event.kind === kind)).map((kind) => ({
    mark: MARKS[kind],
    label: EVENT_NAMES[kind],
  })),
];

// Inside the chart, where its scales place each event on the curve at its instant.
const EventMarks = ({
  events,
  points,
}: {
  events: readonly ChartEvent[];
  points: readonly EquityPoint[];
}) => {
  const x = useXAxisScale();
  const y = useYAxisScale();
  if (x === undefined || y === undefined) {
    return null;
  }
  // Above the curve, its points and its labels, so a mark takes the pointer wherever it lies.
  return (
    <ZIndexLayer zIndex={DefaultZIndexes.label + 1}>
      {events.map((event) => {
        const time = Date.parse(event.instant);
        const left = x(time) ?? 0;
        const top = y(equityAt(points, time)) ?? 0;
        return (
          <Link
            key={`${event.kind}-${event.instant}`}
            to={event.to}
            aria-label={event.label}
            data-instant={event.instant}
          >
            <g transform={`translate(${left} ${top})`}>
              <circle r={MARK_TOUCH_RADIUS} fill="transparent" />
              {MARKS[event.kind]}
            </g>
          </Link>
        );
      })}
    </ZIndexLayer>
  );
};

/** The axis of time from the first to the last instant, centred on a lone one (ADR periodi-brevi-nel-selettore-condiviso). */
export const timeDomainOf = (times: readonly number[]): [number, number] => {
  const first = Math.min(...times);
  const last = Math.max(...times);
  return first === last
    ? [first - LONE_POINT_MARGIN_MS, last + LONE_POINT_MARGIN_MS]
    : [first, last];
};

const domainOf = (data: readonly EquityDatum[], events: readonly ChartEvent[]): [number, number] =>
  timeDomainOf([
    ...data.map((datum) => datum.time),
    ...events.map((event) => Date.parse(event.instant)),
  ]);

/**
 * The equity curve of a flow, a point for each cycle on an axis of time, green above the initial capital and red below
 * (ADR 0121), with the events of the page marked on their instants: failed cycles as red crosses (ADR
 * cicli-falliti-sull-equity-curve), changes of the capital as violet diamonds (ADR
 * rendimento-composto-tra-le-variazioni-di-capitale). A drag from a point to another, with the mouse or a finger,
 * chooses an interval (ADR intervallo-trascinando-sull-equity-curve). The chart is as wide as its room, never wider,
 * with fewer dates and smaller points as they crowd, in the frame every chart shares (ADR equity-curve-larga-come-lo-schermo,
 * ADR grafici-condivisi-larghi-come-lo-schermo). A lone point shows in the
 * middle of the chart, and without points the chart says so (ADR periodi-brevi-nel-selettore-condiviso). Below the
 * chart the shared legend names its marks (ADR legenda-condivisa-dei-grafici).
 */
export const EquityChart = ({ points, empty = NO_CYCLE, ...chart }: EquityChartProps) =>
  points.length === 0 ? (
    <p className="text-slate-600">{empty}</p>
  ) : (
    <EquityArea points={points} {...chart} />
  );

const EquityArea = ({
  points,
  baseline,
  events = [],
  onSelect,
}: Omit<EquityChartProps, 'empty'>) => {
  const id = `equity-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const [selection, setSelection] = useState<Selection>({});
  const [width, setWidth] = useChartWidth();
  const radius = dotRadius(points.length, width);
  // The release reads the drag as the last move left it, not as the last render saw it.
  const latest = useRef<Selection>({});
  const select = (next: Selection) => {
    latest.current = next;
    setSelection(next);
  };
  const data: EquityDatum[] = points.map((point) => ({ ...point, time: timeOf(point) }));
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
  const start = (state: MouseHandlerDataParam) => select(selectionStarted(pointAt(state)));
  const move = (state: MouseHandlerDataParam) =>
    select(selectionMoved(latest.current, pointAt(state)));
  const end = (state: MouseHandlerDataParam) => {
    const range = chosenRange(selectionMoved(latest.current, pointAt(state)));
    select({});
    if (range !== undefined) {
      onSelect?.(new Date(range[0]).toISOString(), new Date(range[1]).toISOString());
    }
  };
  const selecting =
    onSelect === undefined
      ? {}
      : {
          // A drag follows every move, so its release falls on the point the pointer left, not on one a frame behind.
          throttledEvents: [],
          onMouseDown: start,
          onMouseMove: move,
          onMouseUp: end,
          onMouseLeave: () => select({}),
          onTouchStart: start,
          onTouchMove: move,
          onTouchEnd: end,
        };
  const range = chosenRange(selection);
  // A horizontal drag on the chart chooses an interval: on a touch screen the page scrolls only up and down.
  const touches = onSelect === undefined ? undefined : 'touch-pan-y';
  return (
    <ChartFrame
      label="Equity curve"
      className={touches}
      onResize={setWidth}
      footer={<ChartLegend entries={legendOf(events)} />}
    >
      <AreaChart data={data} accessibilityLayer {...selecting}>
        <defs>
          {colours('fill')}
          {colours('stroke')}
        </defs>
        <CartesianGrid strokeDasharray="3 3" />
        <TimeAxis dataKey="time" domain={domainOf(data, events)} />
        <YAxis domain={['auto', 'auto']} tickFormatter={amountText} width={72} />
        <ChartTooltip labelFormatter={tooltipLabel} formatter={tooltipValue} />
        <ReferenceLine
          y={baseline}
          stroke={BASELINE_COLOR}
          strokeDasharray={BASELINE_DASH}
          label={`Capitale iniziale ${amountText(baseline)}`}
        />
        <Area
          type="linear"
          dataKey="equity"
          baseValue={baseline}
          stroke={`url(#${id}-stroke)`}
          fill={`url(#${id}-fill)`}
          dot={(props: DotItemDotProps) => (
            <EquityDot key={props.index} {...props} baseline={baseline} radius={radius} />
          )}
          isAnimationActive={false}
        />
        {range === undefined ? null : (
          <ReferenceArea x1={range[0]} x2={range[1]} fill={SELECTION_COLOR} fillOpacity={0.15} />
        )}
        <EventMarks events={events} points={points} />
      </AreaChart>
    </ChartFrame>
  );
};
