import { render, screen, waitFor, within } from '@testing-library/react';
import { Line, LineChart } from 'recharts';

import {
  CHART_HEIGHT,
  ChartFrame,
  ChartTooltip,
  dotRadius,
  MIN_DOT_RADIUS,
  TimeAxis,
  TOOLTIP_MAX_WIDTH,
} from './chart-frame';

const DATA = [
  { instant: Date.parse('2026-11-10T09:15:00Z'), value: 1 },
  { instant: Date.parse('2026-11-12T09:15:00Z'), value: 2 },
];

const onAScreen = (width: number) => {
  class MeasuringObserver {
    constructor(private readonly callback: ResizeObserverCallback) {}
    observe() {
      const entry = {
        contentRect: DOMRect.fromRect({ width, height: CHART_HEIGHT }),
      } as ResizeObserverEntry;
      this.callback([entry], this as unknown as ResizeObserver);
    }
    unobserve() {}
    disconnect() {}
  }
  vi.stubGlobal('ResizeObserver', MeasuringObserver);
};

afterEach(() => {
  vi.unstubAllGlobals();
});

const Chart = ({ tooltip = <ChartTooltip /> }: { tooltip?: React.ReactElement }) => (
  <ChartFrame label="Grafico">
    <LineChart data={DATA}>
      <TimeAxis dataKey="instant" domain={['dataMin', 'dataMax']} />
      {tooltip}
      <Line dataKey="value" isAnimationActive={false} />
    </LineChart>
  </ChartFrame>
);

describe('ChartFrame, ADR grafici-condivisi-larghi-come-lo-schermo', () => {
  it('names the figure of the chart for the readers of the page', () => {
    render(<Chart />);

    expect(screen.getByRole('figure', { name: 'Grafico' })).toBeInTheDocument();
  });

  it('makes the chart as wide as its room, with the height of every chart', async () => {
    onAScreen(360);
    render(<Chart />);

    const chart = within(screen.getByRole('figure', { name: 'Grafico' })).getByRole('application');
    await waitFor(() => {
      expect(chart).toHaveAttribute('width', '360');
    });
    expect(chart).toHaveAttribute('height', String(CHART_HEIGHT));
  });

  it('never lets the figure scroll sideways', () => {
    render(<Chart />);

    expect(screen.getByRole('figure', { name: 'Grafico' })).not.toHaveClass('overflow-x-auto');
  });

  it('adds the classes of the chart to its figure', () => {
    render(
      <ChartFrame label="Grafico" className="touch-pan-y">
        <LineChart data={DATA} />
      </ChartFrame>,
    );

    expect(screen.getByRole('figure', { name: 'Grafico' })).toHaveClass('touch-pan-y');
  });

  it('shows what follows the chart inside its figure', () => {
    render(
      <ChartFrame label="Grafico" footer={<p>Legenda del grafico</p>}>
        <LineChart data={DATA} />
      </ChartFrame>,
    );

    expect(screen.getByRole('figure', { name: 'Grafico' })).toHaveTextContent(
      'Legenda del grafico',
    );
  });

  it('draws the chart before the browser measures its room', () => {
    render(<Chart />);

    expect(
      within(screen.getByRole('figure', { name: 'Grafico' })).getByRole('application'),
    ).toHaveAttribute('width', '720');
  });

  it('tells the chart the width of its room once measured', async () => {
    onAScreen(360);
    const widths: number[] = [];

    render(
      <ChartFrame label="Grafico" onResize={(width) => widths.push(width)}>
        <LineChart data={DATA} />
      </ChartFrame>,
    );

    await waitFor(() => {
      expect(widths).toContain(360);
    });
  });
});

describe('TimeAxis, ADR grafici-condivisi-larghi-come-lo-schermo', () => {
  it('writes the days of the instants on the axis of time, in Italian', () => {
    render(<Chart />);

    expect(screen.getAllByText(/^\d{2}\/11$/).length).toBeGreaterThan(0);
  });
});

describe('ChartTooltip, ADR grafici-condivisi-larghi-come-lo-schermo', () => {
  const shown = (tooltip: React.ReactElement) => {
    render(<Chart tooltip={tooltip} />);
    return screen.getByRole('status');
  };

  it('is never wider than the room it has inside the chart', () => {
    const tooltip = shown(<ChartTooltip defaultIndex={1} active />);

    expect(tooltip).toHaveStyle({ maxWidth: `${TOOLTIP_MAX_WIDTH}px` });
  });

  it('wraps a long text instead of leaving the screen', () => {
    const tooltip = shown(<ChartTooltip defaultIndex={1} active />);

    expect(tooltip).toHaveStyle({ whiteSpace: 'normal', overflowWrap: 'anywhere' });
  });

  it('writes the label and the values as the chart says', () => {
    shown(
      <ChartTooltip
        defaultIndex={1}
        active
        labelFormatter={() => 'il momento'}
        formatter={(value) => [`valore ${String(value)}`, 'serie']}
      />,
    );

    expect(screen.getByText('il momento')).toBeInTheDocument();
    expect(screen.getByText('valore 2')).toBeInTheDocument();
  });
});

describe('dotRadius, ADR equity-curve-larga-come-lo-schermo', () => {
  it('keeps the full size when the points have room', () => {
    expect(dotRadius(3, 720)).toBe(4);
  });

  it('shrinks the points as they crowd', () => {
    expect(dotRadius(90, 720)).toBe(2);
  });

  it('never goes below the least size', () => {
    expect(dotRadius(1000, 360)).toBe(MIN_DOT_RADIUS);
  });

  it('keeps the full size without points', () => {
    expect(dotRadius(0, 720)).toBe(4);
  });
});
