import { useState, type ReactElement, type ReactNode } from 'react';
import { ResponsiveContainer, Tooltip, XAxis, type TooltipProps, type XAxisProps } from 'recharts';

// The width a chart starts from until the browser measures its room (ADR grafici-condivisi-larghi-come-lo-schermo).
const INITIAL_CHART_WIDTH = 720;
export const CHART_HEIGHT = 320;
// The dates of the axis keep this much room between them, so the main dates show on any width.
const TIME_TICK_GAP = 32;
// Narrower than the plot of a chart on a phone, so the tooltip always finds room inside it.
export const TOOLTIP_MAX_WIDTH = 224;
const DOT_RADIUS = 4;
export const MIN_DOT_RADIUS = 1.5;
// A point keeps a quarter of the room each point has on the axis, between the least and the full size.
const ROOM_PER_RADIUS = 4;

const dayFormat = new Intl.DateTimeFormat('it-IT', { day: '2-digit', month: '2-digit' });

/** The radius of the points of a curve this wide: smaller as they crowd, never below the least size. */
export const dotRadius = (points: number, width: number): number => {
  const room = width / Math.max(points, 1);
  return Math.min(DOT_RADIUS, Math.max(MIN_DOT_RADIUS, room / ROOM_PER_RADIUS));
};

/** The width of the room of a chart, as the browser measures it, and what its frame calls when the room changes. */
export const useChartWidth = (): [number, (width: number) => void] => {
  const [width, setWidth] = useState(INITIAL_CHART_WIDTH);
  return [width, setWidth];
};

type ChartFrameProps = {
  /** The name of the chart for the readers of the page. */
  readonly label: string;
  readonly className?: string;
  /** Called with the width of the room of the chart whenever the browser measures it. */
  readonly onResize?: (width: number) => void;
  /** What the figure shows below the chart, as its legend. */
  readonly footer?: ReactNode;
  readonly children: ReactElement;
};

/**
 * The figure of every chart of the dashboard: as wide as its room and never wider, with nothing to scroll sideways, and
 * the same height on any screen (ADR grafici-condivisi-larghi-come-lo-schermo).
 */
export const ChartFrame = ({ label, className, onResize, footer, children }: ChartFrameProps) => (
  <figure aria-label={label} className={className}>
    <ResponsiveContainer
      width="100%"
      height={CHART_HEIGHT}
      initialDimension={{ width: INITIAL_CHART_WIDTH, height: CHART_HEIGHT }}
      onResize={onResize}
    >
      {children}
    </ResponsiveContainer>
    {footer}
  </figure>
);

type TimeAxisProps = {
  readonly dataKey: string;
  readonly domain: XAxisProps['domain'];
};

/** The axis of time of a chart: the days of the instants, fewer of them as the room shrinks. */
export const TimeAxis = ({ dataKey, domain }: TimeAxisProps) => (
  <XAxis
    dataKey={dataKey}
    type="number"
    scale="time"
    domain={domain}
    allowDuplicatedCategory={false}
    minTickGap={TIME_TICK_GAP}
    tickFormatter={(instant: number) => dayFormat.format(new Date(instant))}
  />
);

type ChartTooltipProps = Pick<
  TooltipProps,
  'labelFormatter' | 'formatter' | 'defaultIndex' | 'active'
>;

/** The tooltip of a chart: always inside it, with long names wrapping instead of leaving the screen. */
export const ChartTooltip = (props: ChartTooltipProps) => (
  <Tooltip
    {...props}
    allowEscapeViewBox={{ x: false, y: false }}
    contentStyle={{ maxWidth: TOOLTIP_MAX_WIDTH, whiteSpace: 'normal', overflowWrap: 'anywhere' }}
  />
);
