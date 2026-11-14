import { render, screen, within } from '@testing-library/react';

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
