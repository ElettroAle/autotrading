import { render, screen, waitFor, within } from '@testing-library/react';

import { MIN_DOT_RADIUS } from './chart-frame';
import {
  COMPARISON_COLORS,
  ComparisonChart,
  percentText,
  tooltipLabel,
  tooltipValue,
} from './comparison-chart';

const ALFA = {
  id: 'flow-alfa',
  name: 'alfa',
  points: [
    { plannedAt: '2026-11-10T09:15:00Z', changePercent: 0 },
    { plannedAt: '2026-11-11T09:15:00Z', changePercent: 10 },
  ],
};
const BETA = {
  id: 'flow-beta',
  name: 'beta',
  points: [
    { plannedAt: '2026-11-10T12:00:00Z', changePercent: 0 },
    { plannedAt: '2026-11-11T12:00:00Z', changePercent: -2.5 },
  ],
};

describe('ComparisonChart', () => {
  it('draws the points of every curve on the same chart', () => {
    render(<ComparisonChart series={[ALFA, BETA]} />);

    const chart = screen.getByRole('figure', { name: 'Equity curve sovrapposte' });
    expect(within(chart).getAllByRole('img', { name: /^alfa / })).toHaveLength(2);
    expect(within(chart).getAllByRole('img', { name: /^beta / })).toHaveLength(2);
  });

  it('names each point with its change in percent and its instant, in Italian', () => {
    render(<ComparisonChart series={[ALFA, BETA]} />);

    expect(
      screen.getByRole('img', { name: /^alfa \+10,00% del 11\/11\/2026, 10:15$/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /^beta -2,50% del / })).toBeInTheDocument();
    expect(screen.getAllByRole('img', { name: / 0,00% del / })).toHaveLength(2);
  });

  it('gives each flow its own colour, the same in the legend and on its points', () => {
    render(<ComparisonChart series={[ALFA, BETA]} />);

    const legend = screen.getByRole('list', { name: 'Legenda' });
    const [first, second] = within(legend).getAllByRole('listitem');
    expect(first).toHaveTextContent('alfa');
    expect(first).toHaveAttribute('data-color', COMPARISON_COLORS[0]);
    expect(second).toHaveTextContent('beta');
    expect(second).toHaveAttribute('data-color', COMPARISON_COLORS[1]);
    expect(screen.getAllByRole('img', { name: /^beta / })[0]).toHaveAttribute(
      'fill',
      COMPARISON_COLORS[1],
    );
  });

  it('has a distinct colour for each of five flows', () => {
    expect(new Set(COMPARISON_COLORS).size).toBe(5);
  });

  it('leaves out a point whose change is not defined', () => {
    const undefinedChange = {
      ...ALFA,
      points: [{ plannedAt: '2026-11-10T09:15:00Z', changePercent: null }, ...ALFA.points.slice(1)],
    };

    render(<ComparisonChart series={[undefinedChange]} />);

    expect(screen.getAllByRole('img', { name: /^alfa / })).toHaveLength(1);
  });

  it('writes the tooltip with the instant, then the change of the flow', () => {
    expect(tooltipLabel(Date.parse('2026-11-11T09:15:00Z'))).toBe('11/11/2026, 10:15');
    expect(tooltipValue(10, 'alfa')).toEqual(['+10,00%', 'alfa']);
  });

  it('signs a change and keeps two decimals', () => {
    expect([percentText(5), percentText(-0.5), percentText(0)]).toEqual([
      '+5,00%',
      '-0,50%',
      '0,00%',
    ]);
  });
});

// ADR grafici-condivisi-larghi-come-lo-schermo: the compared curves are as wide as their room, never wider, and their
// points shrink as they crowd, as the equity curve of a flow.
describe('the width of the comparison chart, ADR grafici-condivisi-larghi-come-lo-schermo', () => {
  const HOUR = 60 * 60 * 1000;
  const MANY = {
    id: 'flow-many',
    name: 'molti',
    points: Array.from({ length: 300 }, (_, index) => ({
      plannedAt: new Date(Date.parse('2026-10-01T00:00:00Z') + index * HOUR).toISOString(),
      changePercent: index % 7,
    })),
  };

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

  it('is as wide as a phone screen, with nothing to scroll sideways', async () => {
    onAScreen(360);
    render(<ComparisonChart series={[ALFA, BETA]} />);

    const figure = screen.getByRole('figure', { name: 'Equity curve sovrapposte' });
    await waitFor(() => {
      expect(within(figure).getByRole('application')).toHaveAttribute('width', '360');
    });
    expect(figure).not.toHaveClass('overflow-x-auto');
  });

  it('draws smaller points when they are many for its width', async () => {
    onAScreen(360);
    render(<ComparisonChart series={[MANY]} />);

    await waitFor(() => {
      expect(screen.getAllByRole('img', { name: /^molti / })[0]).toHaveAttribute(
        'r',
        String(MIN_DOT_RADIUS),
      );
    });
  });

  it('keeps the points at full size when they have room', async () => {
    onAScreen(1280);
    render(<ComparisonChart series={[ALFA, BETA]} />);

    await waitFor(() => {
      expect(screen.getAllByRole('img', { name: /^alfa / })[0]).toHaveAttribute('r', '4');
    });
  });
});
