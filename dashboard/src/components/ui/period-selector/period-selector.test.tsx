import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';

import { PeriodSelector } from './period-selector';
import { apiSearchOf, isComplete, usePeriod, type Period } from './use-period';

const Probe = () => {
  const [period] = usePeriod();
  const { search } = useLocation();
  return (
    <>
      <PeriodSelector />
      <output aria-label="query string">{search}</output>
      <output aria-label="periodo letto">{JSON.stringify(period)}</output>
    </>
  );
};

const renderAt = (url: string) => {
  const router = createMemoryRouter([{ path: '/flows/:flowId', element: <Probe /> }], {
    initialEntries: [url],
  });
  render(<RouterProvider router={router} />);
};

const searchShown = () => screen.getByLabelText('query string').textContent;

const periodRead = () => JSON.parse(screen.getByLabelText('periodo letto').textContent ?? '');

describe('PeriodSelector', () => {
  it('starts from the whole life', () => {
    renderAt('/flows/alfa');

    expect(screen.getByLabelText('Periodo')).toHaveDisplayValue('Tutta la vita');
    expect(periodRead()).toEqual({ kind: 'all', from: '', to: '' });
  });

  it('keeps the chosen period in the query string of the page', async () => {
    renderAt('/flows/alfa');

    await userEvent.selectOptions(screen.getByLabelText('Periodo'), '7 giorni');

    expect(searchShown()).toBe('?period=7d');
    expect(periodRead()).toEqual({ kind: '7d', from: '', to: '' });
  });

  it('reads the period the page opens with', () => {
    renderAt('/flows/alfa?period=30d');

    expect(screen.getByLabelText('Periodo')).toHaveDisplayValue('30 giorni');
  });

  it('asks the days of a range and keeps them in the query string', async () => {
    renderAt('/flows/alfa');

    await userEvent.selectOptions(screen.getByLabelText('Periodo'), 'Intervallo');
    await userEvent.type(screen.getByLabelText('Dal'), '2026-11-01');
    await userEvent.type(screen.getByLabelText('Al'), '2026-11-03');

    expect(searchShown()).toBe('?period=range&from=2026-11-01&to=2026-11-03');
    expect(periodRead()).toEqual({ kind: 'range', from: '2026-11-01', to: '2026-11-03' });
  });

  it('forgets the days when a period other than a range is chosen', async () => {
    renderAt('/flows/alfa?period=range&from=2026-11-01&to=2026-11-03');

    await userEvent.selectOptions(screen.getByLabelText('Periodo'), 'Tutta la vita');

    expect(searchShown()).toBe('');
    expect(screen.queryByLabelText('Dal')).not.toBeInTheDocument();
  });

  it('reads a period it does not know as the whole life', () => {
    renderAt('/flows/alfa?period=1y');

    expect(periodRead()).toEqual({ kind: 'all', from: '', to: '' });
  });
});

describe('apiSearchOf', () => {
  it('names the period and, for a range, its days', () => {
    const range: Period = { kind: 'range', from: '2026-11-01', to: '2026-11-03' };

    expect(apiSearchOf({ kind: 'all', from: '', to: '' })).toBe('period=all');
    expect(apiSearchOf({ kind: '7d', from: '2026-11-01', to: '' })).toBe('period=7d');
    expect(apiSearchOf(range)).toBe('period=range&from=2026-11-01&to=2026-11-03');
  });
});

describe('isComplete', () => {
  it('needs both days only for a range', () => {
    expect(isComplete({ kind: '30d', from: '', to: '' })).toBe(true);
    expect(isComplete({ kind: 'range', from: '2026-11-01', to: '' })).toBe(false);
    expect(isComplete({ kind: 'range', from: '', to: '2026-11-01' })).toBe(false);
    expect(isComplete({ kind: 'range', from: '2026-11-01', to: '2026-11-01' })).toBe(true);
  });
});
