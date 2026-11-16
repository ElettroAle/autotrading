import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';

import {
  ABOVE_COLOR,
  BELOW_COLOR,
  chosenRange,
  dotRadius,
  equityAt,
  EquityChart,
  selectionMoved,
  selectionStarted,
  MIN_DOT_RADIUS,
  splitOffset,
  tooltipLabel,
  tooltipValue,
  type ChartEvent,
} from './equity-chart';

const POINTS = [
  { plannedAt: '2026-11-12T09:15:00Z', equity: 310 },
  { plannedAt: '2026-11-12T09:30:00Z', equity: 295 },
  { plannedAt: '2026-11-12T09:45:00Z', equity: 305 },
];

describe('EquityChart', () => {
  it('draws a point for each cycle', () => {
    render(<EquityChart points={POINTS} baseline={300} />);

    expect(screen.getAllByRole('img', { name: /^Equity / })).toHaveLength(3);
  });

  it('puts the points above the initial capital in the green area', () => {
    render(<EquityChart points={POINTS} baseline={300} />);

    const point = screen.getByRole('img', { name: /^Equity 310 / });
    expect(point).toHaveAccessibleName(/nell'area verde$/);
    expect(point).toHaveAttribute('fill', ABOVE_COLOR);
  });

  it('puts the points below the initial capital in the red area', () => {
    render(<EquityChart points={POINTS} baseline={300} />);

    const point = screen.getByRole('img', { name: /^Equity 295 / });
    expect(point).toHaveAccessibleName(/nell'area rossa$/);
    expect(point).toHaveAttribute('fill', BELOW_COLOR);
  });

  it('keeps a point at the initial capital in the green area', () => {
    render(
      <EquityChart points={[{ plannedAt: '2026-11-12T09:15:00Z', equity: 300 }]} baseline={300} />,
    );

    expect(screen.getByRole('img', { name: /^Equity 300 / })).toHaveAttribute('fill', ABOVE_COLOR);
  });

  it('writes the amounts and the instants in Italian', () => {
    render(
      <EquityChart
        points={[{ plannedAt: '2026-11-12T09:15:00Z', equity: 305.5 }]}
        baseline={300}
      />,
    );

    expect(
      screen.getByRole('img', { name: /^Equity 305,5 del \d{2}\/11\/2026, \d{2}:15/ }),
    ).toBeInTheDocument();
  });

  it('marks the initial capital on the chart', () => {
    render(<EquityChart points={POINTS} baseline={300} />);

    expect(screen.getByText('Capitale iniziale 300')).toBeInTheDocument();
  });

  it('names the chart for the readers of the page', () => {
    render(<EquityChart points={POINTS} baseline={300} />);

    expect(screen.getByRole('figure', { name: 'Equity curve' })).toBeInTheDocument();
  });
});

describe('splitOffset', () => {
  it('splits the colours where the initial capital falls between the highest and the lowest equity', () => {
    expect(splitOffset([310, 290], 300)).toBe(0.5);
  });

  it('is all green when every equity is above the initial capital', () => {
    expect(splitOffset([310, 305], 300)).toBe(1);
  });

  it('is all red when every equity is below the initial capital', () => {
    expect(splitOffset([290, 295], 300)).toBe(0);
  });

  it('is all green for a flat curve at the initial capital', () => {
    expect(splitOffset([300, 300], 300)).toBe(1);
  });
});

describe('the tooltip of a point', () => {
  it('names the instant of the cycle', () => {
    expect(tooltipLabel('2026-11-12T09:15:00Z')).toMatch(/^12\/11\/2026, \d{2}:15$/);
  });

  it('names the instant of the cycle from its place on the axis of time', () => {
    expect(tooltipLabel(Date.parse('2026-11-12T09:15:00Z'))).toMatch(/^12\/11\/2026, \d{2}:15$/);
  });

  it('gives the equity in Italian', () => {
    expect(tooltipValue(305.5)).toEqual(['305,5', 'Equity']);
  });
});

const FAILED: ChartEvent = {
  instant: '2026-11-12T09:35:00Z',
  label: 'Ciclo fallito del 12/11/2026, 10:35:00',
  to: '/flows/alfa/cycles/2026-11-12T09:35:00Z',
};

const renderWithEvents = (events: readonly ChartEvent[]) => {
  const router = createMemoryRouter(
    [{ path: '*', element: <EquityChart points={POINTS} baseline={300} events={events} /> }],
    { initialEntries: ['/flows/alfa'] },
  );
  render(<RouterProvider router={router} />);
};

// ADR cicli-falliti-sull-equity-curve: the chart draws the events the page gives as red crosses on the curve, each a
// link to its destination with a name of its own.
describe('the events on the chart, ADR cicli-falliti-sull-equity-curve', () => {
  it('draws a red cross for each event, a link to its destination named by its label', async () => {
    renderWithEvents([FAILED]);

    const mark = await screen.findByRole('link', { name: FAILED.label });
    expect(mark).toHaveAttribute('href', FAILED.to);
    expect(mark).toContainHTML(`stroke="${BELOW_COLOR}"`);
  });

  it('draws no mark without events', async () => {
    renderWithEvents([]);
    await screen.findAllByRole('img');

    expect(screen.queryAllByRole('link')).toHaveLength(0);
  });
});

describe('equityAt', () => {
  const points = [
    { plannedAt: '2026-11-12T09:00:00Z', equity: 300 },
    { plannedAt: '2026-11-12T10:00:00Z', equity: 320 },
  ];

  it('reads the equity between two points on the line that joins them', () => {
    expect(equityAt(points, Date.parse('2026-11-12T09:15:00Z'))).toBe(305);
  });

  it('takes the equity of the first point before the curve begins', () => {
    expect(equityAt(points, Date.parse('2026-11-12T08:00:00Z'))).toBe(300);
  });

  it('takes the equity of the last point after the curve ends', () => {
    expect(equityAt(points, Date.parse('2026-11-12T11:00:00Z'))).toBe(320);
  });

  it('takes the equity of a point at its very instant', () => {
    expect(equityAt(points, Date.parse('2026-11-12T10:00:00Z'))).toBe(320);
  });
});

// ADR intervallo-trascinando-sull-equity-curve: a drag on the chart, with the mouse or a finger, chooses the instants
// from one point to another.
describe('the selection of an interval, ADR intervallo-trascinando-sull-equity-curve', () => {
  it('starts on the point pressed', () => {
    expect(selectionStarted(10)).toEqual({ pressed: true, start: 10, end: 10 });
  });

  it('starts from the first point reached when the press found none, as a finger does', () => {
    expect(selectionMoved(selectionStarted(undefined), 30)).toEqual({
      pressed: true,
      start: 30,
      end: 30,
    });
  });

  it('follows the point reached while dragging', () => {
    expect(selectionMoved(selectionStarted(10), 30)).toEqual({ pressed: true, start: 10, end: 30 });
  });

  it('keeps the point reached last when the drag leaves the points', () => {
    const dragged = { pressed: true, start: 10, end: 30 };

    expect(selectionMoved(dragged, undefined)).toEqual(dragged);
  });

  it('moves nothing when nothing is pressed', () => {
    expect(selectionMoved({}, 30)).toEqual({});
  });

  it('chooses the instants from the earlier to the later point', () => {
    expect(chosenRange({ pressed: true, start: 30, end: 10 })).toEqual([10, 30]);
  });

  it('chooses nothing with a press that never moved', () => {
    expect(chosenRange(selectionStarted(10))).toBeUndefined();
  });

  it('chooses nothing without a drag', () => {
    expect(chosenRange({})).toBeUndefined();
  });

  it('gives the page the instants of a drag across the chart', async () => {
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(
      DOMRect.fromRect({ width: 720, height: 320 }),
    );
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(720);
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(320);
    const chosen: [string, string][] = [];
    render(
      <EquityChart
        points={POINTS}
        baseline={300}
        onSelect={(from, to) => chosen.push([from, to])}
      />,
    );
    const chart = screen.getByRole('application');
    // The chart reads the point under the pointer once the frame is drawn.
    const settle = () => act(() => new Promise((resolve) => setTimeout(resolve, 50)));

    fireEvent.mouseDown(chart, { clientX: 80, clientY: 100 });
    fireEvent.mouseMove(chart, { clientX: 80, clientY: 100 });
    await settle();
    fireEvent.mouseMove(chart, { clientX: 715, clientY: 100 });
    await settle();
    fireEvent.mouseUp(chart, { clientX: 715, clientY: 100 });

    expect(chosen).toEqual([['2026-11-12T09:15:00.000Z', '2026-11-12T09:45:00.000Z']]);
    vi.restoreAllMocks();
  });

  it('forgets a drag that leaves the chart', async () => {
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(
      DOMRect.fromRect({ width: 720, height: 320 }),
    );
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(720);
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(320);
    const chosen: [string, string][] = [];
    render(
      <EquityChart
        points={POINTS}
        baseline={300}
        onSelect={(from, to) => chosen.push([from, to])}
      />,
    );
    const chart = screen.getByRole('application');
    const settle = () => act(() => new Promise((resolve) => setTimeout(resolve, 50)));

    fireEvent.mouseDown(chart, { clientX: 80, clientY: 100 });
    fireEvent.mouseMove(chart, { clientX: 80, clientY: 100 });
    await settle();
    fireEvent.mouseLeave(chart);
    fireEvent.mouseUp(chart, { clientX: 715, clientY: 100 });

    expect(chosen).toEqual([]);
    vi.restoreAllMocks();
  });

  it('lets the page scroll only up and down when the chart offers the selection', () => {
    render(<EquityChart points={POINTS} baseline={300} onSelect={() => undefined} />);

    expect(screen.getByRole('figure', { name: 'Equity curve' })).toHaveClass('touch-pan-y');
  });

  it('leaves the touches to the page when the chart offers no selection', () => {
    render(<EquityChart points={POINTS} baseline={300} />);

    expect(screen.getByRole('figure', { name: 'Equity curve' })).not.toHaveClass('touch-pan-y');
  });
});

// ADR equity-curve-larga-come-lo-schermo: the chart is as wide as the room it has, never wider, whatever its points; the
// points shrink as they crowd.
describe('the width of the chart, ADR equity-curve-larga-come-lo-schermo', () => {
  const HOUR = 60 * 60 * 1000;
  const MANY_POINTS = Array.from({ length: 300 }, (_, index) => ({
    plannedAt: new Date(Date.parse('2026-10-01T00:00:00Z') + index * HOUR).toISOString(),
    equity: 300 + (index % 7),
  }));

  // A browser measures the room of the chart, and tells it again whenever the room changes.
  const onAScreen = (width: number) => {
    class MeasuringObserver {
      constructor(private readonly callback: ResizeObserverCallback) {}
      observe() {
        const entry = {
          contentRect: DOMRect.fromRect({ width, height: 320 }),
        } as ResizeObserverEntry;
        this.callback([entry], this as unknown as ResizeObserver);
      }
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal('ResizeObserver', MeasuringObserver);
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(
      DOMRect.fromRect({ width, height: 320 }),
    );
  };

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('follows the width of its room with many points, without scrolling sideways', async () => {
    onAScreen(360);
    render(<EquityChart points={MANY_POINTS} baseline={300} onSelect={() => undefined} />);

    const figure = screen.getByRole('figure', { name: 'Equity curve' });
    await waitFor(() => {
      expect(within(figure).getByRole('application')).toHaveAttribute('width', '360');
    });
    expect(figure).not.toHaveClass('overflow-x-auto');
  });

  it('draws smaller points when they are many for its width', async () => {
    onAScreen(360);
    render(<EquityChart points={MANY_POINTS} baseline={300} />);

    await waitFor(() => {
      expect(screen.getAllByRole('img', { name: /^Equity / })[0]).toHaveAttribute(
        'r',
        String(MIN_DOT_RADIUS),
      );
    });
  });

  it('keeps the points at full size when they have room', async () => {
    onAScreen(1280);
    render(<EquityChart points={POINTS} baseline={300} />);

    await waitFor(() => {
      expect(screen.getAllByRole('img', { name: /^Equity / })[0]).toHaveAttribute('r', '4');
    });
  });
});

describe('dotRadius, ADR equity-curve-larga-come-lo-schermo', () => {
  it('keeps the full size when the points have room', () => {
    expect(dotRadius(3, 720)).toBe(4);
  });

  it('shrinks the points as they crowd', () => {
    expect(dotRadius(90, 720)).toBe(2);
  });

  it('never draws a point smaller than the least size', () => {
    expect(dotRadius(1000, 360)).toBe(MIN_DOT_RADIUS);
  });

  it('keeps the full size without points', () => {
    expect(dotRadius(0, 720)).toBe(4);
  });
});
