import { render, screen } from '@testing-library/react';

import {
  ABOVE_COLOR,
  BELOW_COLOR,
  EquityChart,
  splitOffset,
  tooltipLabel,
  tooltipValue,
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

  it('gives the equity in Italian', () => {
    expect(tooltipValue(305.5)).toEqual(['305,5', 'Equity']);
  });
});
