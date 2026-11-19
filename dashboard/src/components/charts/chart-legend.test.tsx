import { render, screen, within } from '@testing-library/react';

import { ChartLegend } from './chart-legend';

const ENTRIES = [
  { mark: <circle r={4} fill="#16a34a" />, label: 'sopra' },
  { mark: <line x1={-8} x2={8} stroke="#475569" />, label: 'capitale' },
];

// ADR legenda-condivisa-dei-grafici: one legend for every chart, each entry the mark of the chart beside its name.
describe('ChartLegend, ADR legenda-condivisa-dei-grafici', () => {
  it('names each entry in the order given', () => {
    render(<ChartLegend entries={ENTRIES} />);

    const legend = screen.getByRole('list', { name: 'Legenda' });
    expect(
      within(legend)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['sopra', 'capitale']);
  });

  it('draws the mark of each entry beside its name, hidden from the readers of the page', () => {
    render(<ChartLegend entries={ENTRIES} />);

    const [first, second] = screen.getAllByRole('listitem');
    const mark = within(first as HTMLElement).getByRole('img', { hidden: true });
    expect(mark).toHaveAttribute('aria-hidden', 'true');
    expect(mark).toContainHTML('fill="#16a34a"');
    expect(within(second as HTMLElement).getByRole('img', { hidden: true })).toContainHTML(
      'stroke="#475569"',
    );
    expect(screen.queryAllByRole('img')).toHaveLength(0);
  });

  it('wraps its entries on more rows when they do not fit on one', () => {
    render(<ChartLegend entries={ENTRIES} />);

    expect(screen.getByRole('list', { name: 'Legenda' })).toHaveClass('flex', 'flex-wrap');
  });
});
