import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';

import {
  instantOfLocalInput,
  intervalOfInstants,
  listIntervalOf,
  localInputOf,
  usePeriod,
  usePeriodInterval,
  usePeriodSearch,
  type Period,
} from './use-period';

const Probe = () => {
  const [period] = usePeriod();
  const { interval, chooseInterval, clearInterval } = usePeriodInterval();
  const periodSearch = usePeriodSearch();
  const { search } = useLocation();
  return (
    <>
      <output aria-label="query string">{search}</output>
      <output aria-label="periodo letto">{JSON.stringify(period)}</output>
      <output aria-label="intervallo">{JSON.stringify(interval ?? null)}</output>
      <output aria-label="periodo da portare">{periodSearch}</output>
      <button
        type="button"
        onClick={() => chooseInterval({ from: '2026-11-10T09:15Z', to: '2026-11-12T10:40Z' })}
      >
        Scegli
      </button>
      <button type="button" onClick={clearInterval}>
        Togli
      </button>
    </>
  );
};

const renderAt = (url: string) => {
  const router = createMemoryRouter([{ path: '/flows/:flowId', element: <Probe /> }], {
    initialEntries: [url],
  });
  render(<RouterProvider router={router} />);
};

const shown = (label: string) => screen.getByLabelText(label).textContent ?? '';

const read = (label: string): unknown => JSON.parse(shown(label));

// ADR intervallo-trascinando-sull-equity-curve: an interval chosen on the chart rides in the address as from/to, beside
// the period of the menu, and every panel of the page reads it in place of that period.
describe('the interval of the page, ADR intervallo-trascinando-sull-equity-curve', () => {
  it('has no interval without days in the address', () => {
    renderAt('/flows/alfa?period=7d');

    expect(read('intervallo')).toBeNull();
    expect(read('periodo letto')).toEqual({ kind: '7d', from: '', to: '' });
  });

  it('writes the interval chosen beside the period of the menu, from the first page of the lists', async () => {
    renderAt('/flows/alfa?period=7d&page=3&outcome=fallito');

    await userEvent.click(screen.getByRole('button', { name: 'Scegli' }));

    expect(shown('query string')).toBe(
      '?period=7d&outcome=fallito&from=2026-11-10T09%3A15Z&to=2026-11-12T10%3A40Z',
    );
    expect(read('intervallo')).toEqual({ from: '2026-11-10T09:15Z', to: '2026-11-12T10:40Z' });
  });

  it('gives the panels the interval in place of the period of the menu', () => {
    renderAt('/flows/alfa?period=30d&from=2026-11-10&to=2026-11-12');

    expect(read('periodo letto')).toEqual({ kind: 'range', from: '2026-11-10', to: '2026-11-12' });
  });

  it('takes the interval of a page without a period of the menu', () => {
    renderAt('/flows/alfa?from=2026-11-10&to=2026-11-12');

    expect(read('intervallo')).toEqual({ from: '2026-11-10', to: '2026-11-12' });
  });

  it('ignores an interval with only one of its days', () => {
    renderAt('/flows/alfa?period=7d&from=2026-11-10');

    expect(read('intervallo')).toBeNull();
    expect(read('periodo letto')).toEqual({ kind: '7d', from: '2026-11-10', to: '' });
  });

  it('leaves the days of a range of the menu to the menu', () => {
    renderAt('/flows/alfa?period=range&from=2026-11-01&to=2026-11-03');

    expect(read('intervallo')).toBeNull();
  });

  it('goes back to the period of the menu when the interval is removed', async () => {
    renderAt('/flows/alfa?period=7d&outcome=fallito&page=2&from=2026-11-10&to=2026-11-12');

    await userEvent.click(screen.getByRole('button', { name: 'Togli' }));

    expect(shown('query string')).toBe('?period=7d&outcome=fallito');
    expect(read('periodo letto')).toEqual({ kind: '7d', from: '', to: '' });
  });

  it('keeps a range of the menu when there is no interval to remove', async () => {
    renderAt('/flows/alfa?period=range&from=2026-11-01&to=2026-11-03');

    await userEvent.click(screen.getByRole('button', { name: 'Togli' }));

    expect(shown('query string')).toBe('?period=range&from=2026-11-01&to=2026-11-03');
  });
});

// ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune: the tabs carry the period to one another, not the filters.
describe('usePeriodSearch, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune', () => {
  it('carries only the period and the interval of the address', () => {
    renderAt('/flows/alfa?period=7d&outcome=fallito&page=2&from=2026-11-10&to=2026-11-12');

    expect(shown('periodo da portare')).toBe('?period=7d&from=2026-11-10&to=2026-11-12');
  });

  it('carries nothing for the whole life', () => {
    renderAt('/flows/alfa?outcome=fallito');

    expect(shown('periodo da portare')).toBe('');
  });
});

// ADR periodo-al-minuto: the lists read the same minutes as the other panels, the last 7 and 30 days from now.
describe('listIntervalOf, ADR periodo-al-minuto', () => {
  const NOW = new Date('2026-11-16T09:30:42Z');
  const period = (kind: Period['kind'], from = '', to = ''): Period => ({ kind, from, to });

  it('asks no instant for the whole life', () => {
    expect(listIntervalOf(period('all'), NOW)).toEqual({});
  });

  it('asks the instants of a range', () => {
    expect(listIntervalOf(period('range', '2026-11-16T08:15Z', '2026-11-16T10:40Z'), NOW)).toEqual({
      from: '2026-11-16T08:15Z',
      to: '2026-11-16T10:40Z',
    });
  });

  it('asks from the minute 7 days before now', () => {
    expect(listIntervalOf(period('7d'), NOW)).toEqual({ from: '2026-11-09T09:30Z' });
  });

  it('asks from the minute 30 days before now', () => {
    expect(listIntervalOf(period('30d'), NOW)).toEqual({ from: '2026-10-17T09:30Z' });
  });
});

describe('intervalOfInstants, ADR periodo-al-minuto', () => {
  it('gives the minutes of the two instants, the earlier first, in UTC', () => {
    expect(intervalOfInstants('2026-11-12T10:15:00Z', '2026-11-09T23:30:45Z')).toEqual({
      from: '2026-11-09T23:30Z',
      to: '2026-11-12T10:15Z',
    });
  });
});

describe('the fields of date and time, ADR periodo-al-minuto', () => {
  it('shows an instant of the address in the time zone of the browser', () => {
    expect(localInputOf('2026-11-16T08:15Z')).toBe('2026-11-16T09:15');
    expect(localInputOf('2026-07-16T08:15Z')).toBe('2026-07-16T10:15');
  });

  it('writes the date and time chosen as the instant in UTC, to the minute', () => {
    expect(instantOfLocalInput('2026-11-16T09:15')).toBe('2026-11-16T08:15Z');
  });

  it('leaves an empty field empty', () => {
    expect(localInputOf('')).toBe('');
    expect(instantOfLocalInput('')).toBe('');
  });

  it('shows nothing for an instant it cannot read', () => {
    expect(localInputOf('ieri')).toBe('');
  });
});
