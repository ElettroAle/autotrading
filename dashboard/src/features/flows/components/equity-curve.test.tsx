import { act, fireEvent, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { aCompletedCycle, aFailedCycle, STEPS } from '@/testing/mocks/cycles';
import { fakePlatform } from '@/testing/mocks/platform';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const DAY = 24 * 60 * 60 * 1000;
const daysAgo = (days: number) => new Date(Date.now() - days * DAY);

const curve = async () => screen.findByRole('figure', { name: 'Equity curve' });

describe('EquityCurve', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.addFlow('anna', 'alfa', { allocatedCapital: 300 });
  });

  it('draws a point for each cycle of the whole life of the flow by default', async () => {
    for (const [days, equity] of [
      [45, 310],
      [20, 295],
      [1, 305],
    ] as const) {
      fakePlatform.recordEquity('alfa', daysAgo(days), equity);
    }
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(within(await curve()).getAllByRole('img', { name: /^Equity / })).toHaveLength(3);
    expect(screen.getByRole('combobox', { name: 'Periodo' })).toHaveValue('all');
  });

  it('colours the points against the initial capital of the flow', async () => {
    fakePlatform.recordEquity('alfa', daysAgo(2), 310);
    fakePlatform.recordEquity('alfa', daysAgo(1), 295);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    const chart = await curve();
    expect(within(chart).getByRole('img', { name: /^Equity 310 .*verde$/ })).toBeInTheDocument();
    expect(within(chart).getByRole('img', { name: /^Equity 295 .*rossa$/ })).toBeInTheDocument();
    expect(within(chart).getByText('Capitale iniziale 300')).toBeInTheDocument();
  });

  it('shows only the cycles of the period the user chooses', async () => {
    fakePlatform.recordEquity('alfa', daysAgo(40), 310);
    fakePlatform.recordEquity('alfa', daysAgo(10), 295);
    fakePlatform.recordEquity('alfa', daysAgo(3), 305);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await curve();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Periodo' }), '7 giorni');

    await expect.poll(() => screen.getAllByRole('img', { name: /^Equity / })).toHaveLength(1);
    expect(screen.getByRole('img', { name: /^Equity 305 / })).toBeInTheDocument();
  });

  // ADR periodo-al-minuto: the menu takes the date and the time of each end of a range.
  it('shows the cycles of a range from its first to its last minute', async () => {
    const fiveDaysAgo = daysAgo(5);
    fakePlatform.recordEquity('alfa', daysAgo(10), 310);
    fakePlatform.recordEquity('alfa', fiveDaysAgo, 295);
    fakePlatform.recordEquity('alfa', daysAgo(1), 305);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await curve();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Periodo' }), 'Intervallo');
    expect(
      within(screen.getByRole('region', { name: 'Equity curve' })).getByText(
        "Scegli il primo e l'ultimo giorno dell'intervallo.",
      ),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Dal'), { target: { value: localInput(fiveDaysAgo) } });
    fireEvent.change(screen.getByLabelText('Al'), { target: { value: localInput(fiveDaysAgo) } });

    await expect.poll(() => screen.queryAllByRole('img', { name: /^Equity / })).toHaveLength(1);
    expect(screen.getByRole('img', { name: /^Equity 295 / })).toBeInTheDocument();
  });

  it('tells why a range that ends before it starts is refused', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await screen.findByText('Nessun ciclo ancora eseguito');

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Periodo' }), 'Intervallo');
    fireEvent.change(screen.getByLabelText('Dal'), { target: { value: localInput(daysAgo(1)) } });
    fireEvent.change(screen.getByLabelText('Al'), { target: { value: localInput(daysAgo(3)) } });

    const panel = screen.getByRole('region', { name: 'Equity curve' });
    expect(await within(panel).findByText(/l'inizio è successivo alla fine/)).toBeInTheDocument();
  });

  it('says when the flow has not run a cycle yet', async () => {
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByText('Nessun ciclo ancora eseguito')).toBeInTheDocument();
    expect(screen.queryByRole('figure', { name: 'Equity curve' })).not.toBeInTheDocument();
  });

  it('shows no curve for a draft, which has no capital and no cycle yet', async () => {
    fakePlatform.addFlow('anna', 'bozza', { status: 'bozza', allocatedCapital: null });
    await renderApp({ account: 'anna', url: '/flows/flow-bozza' });

    expect(await screen.findByText('Nessun ciclo ancora eseguito')).toBeInTheDocument();
  });

  it('says when no cycle falls in the period', async () => {
    fakePlatform.recordEquity('alfa', daysAgo(40), 310);
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });
    await curve();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Periodo' }), '30 giorni');

    expect(await screen.findByText('Nessun ciclo nel periodo scelto')).toBeInTheDocument();
  });

  it('tells why the curve could not be read', async () => {
    server.use(
      http.get('*/flows/:flowId/equity', () =>
        HttpResponse.json({ detail: 'errore interno' }, { status: 500 }),
      ),
    );
    await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

    expect(await screen.findByRole('alert')).toHaveTextContent('errore interno');
  });

  // ADR cicli-falliti-sull-equity-curve: every failed cycle of the period is a red cross that leads to its detail.
  describe('the failed cycles, ADR cicli-falliti-sull-equity-curve', () => {
    const FAILURE = {
      errorType: 'ExchangeUnavailableError',
      message: 'exchange non raggiungibile',
    };

    it('marks every failed cycle of the period, over every page of the list, and no concluded cycle', async () => {
      const failed = Array.from({ length: 51 }, (_, index) =>
        aFailedCycle(aCompletedCycle(daysAgo(1 + index / 100)), STEPS.composeContext, FAILURE),
      );
      fakePlatform.recordCycles('alfa', [aCompletedCycle(daysAgo(2)), ...failed]);
      fakePlatform.recordEquity('alfa', daysAgo(3), 300);
      fakePlatform.recordEquity('alfa', daysAgo(0.5), 305);
      await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

      const chart = await curve();
      await expect
        .poll(() => within(chart).queryAllByRole('link', { name: /^Ciclo fallito del / }))
        .toHaveLength(51);
    });

    it('leads from the mark to the detail of the cycle', async () => {
      const instant = daysAgo(1);
      fakePlatform.recordCycles('alfa', [
        aFailedCycle(aCompletedCycle(instant), STEPS.composeContext, FAILURE),
      ]);
      fakePlatform.recordEquity('alfa', daysAgo(2), 300);
      await renderApp({ account: 'anna', url: '/flows/flow-alfa' });

      const mark = await within(await curve()).findByRole('link', { name: /^Ciclo fallito del / });
      expect(mark).toHaveAttribute(
        'href',
        `/flows/flow-alfa/cycles/${encodeURIComponent(instant.toISOString())}`,
      );
    });
  });

  // ADR intervallo-trascinando-sull-equity-curve: the interval in the address narrows the page until it is removed.
  describe('the interval chosen on the chart, ADR intervallo-trascinando-sull-equity-curve', () => {
    it('narrows the curve to the interval and says it, with the command that removes it', async () => {
      fakePlatform.recordEquity('alfa', daysAgo(10), 310);
      fakePlatform.recordEquity('alfa', daysAgo(5), 295);
      fakePlatform.recordEquity('alfa', daysAgo(1), 305);
      const from = minuteOf(daysAgo(6));
      const to = minuteOf(daysAgo(4));
      await renderApp({
        account: 'anna',
        url: `/flows/flow-alfa?period=30d&from=${from}&to=${to}`,
      });

      await expect.poll(() => screen.queryAllByRole('img', { name: /^Equity / })).toHaveLength(1);
      const label = screen.getByLabelText('Intervallo scelto sul grafico');
      // ADR periodo-al-minuto: the label says the date and the time of each end, «16/11 09:15 – 16/11 11:40».
      expect(label).toHaveTextContent(`${labelOf(from)} – ${labelOf(to)}`);

      await userEvent.click(within(label).getByRole('button', { name: "Togli l'intervallo" }));

      await expect.poll(() => screen.queryAllByRole('img', { name: /^Equity / })).toHaveLength(3);
      expect(screen.queryByLabelText('Intervallo scelto sul grafico')).not.toBeInTheDocument();
      expect(screen.getByRole('combobox', { name: 'Periodo' })).toHaveValue('30d');
    });

    it('chooses the interval of the page with a drag across the curve', async () => {
      const sixDaysAgoAndAfter = [daysAgo(6), daysAgo(4), daysAgo(2)] as const;
      sixDaysAgoAndAfter.forEach((instant, index) => {
        fakePlatform.recordEquity('alfa', instant, 300 + index * 5);
      });
      const { router } = await renderApp({ account: 'anna', url: '/flows/flow-alfa?period=30d' });
      await curve();
      vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(
        DOMRect.fromRect({ width: 720, height: 320 }),
      );
      vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(720);
      vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(320);
      const chart = within(await curve()).getByRole('application');
      expect(await curve()).toHaveClass('touch-pan-y');
      // The chart reads the point under the pointer once the frame is drawn.
      const settle = () => act(() => new Promise((resolve) => setTimeout(resolve, 50)));

      fireEvent.mouseDown(chart, { clientX: 80, clientY: 100 });
      fireEvent.mouseMove(chart, { clientX: 80, clientY: 100 });
      await settle();
      fireEvent.mouseMove(chart, { clientX: 715, clientY: 100 });
      await settle();
      fireEvent.mouseUp(chart, { clientX: 715, clientY: 100 });
      vi.restoreAllMocks();

      // ADR periodo-al-minuto: the interval runs from the minute of the first point chosen to the minute of the last.
      await expect
        .poll(() => new URLSearchParams(router.state.location.search).get('to'))
        .toBe(minuteOf(sixDaysAgoAndAfter[2]));
      const search = new URLSearchParams(router.state.location.search);
      expect(search.get('from')).toBe(minuteOf(sixDaysAgoAndAfter[0]));
      expect(search.get('period')).toBe('30d');
    });
  });
});

// The instant of the address, UTC to the minute, as the dashboard writes it (ADR periodo-al-minuto).
const minuteOf = (instant: Date): string => `${instant.toISOString().slice(0, 16)}Z`;

const pad = (value: number) => String(value).padStart(2, '0');

// An end of the interval as the label says it, in the time zone of the browser: 16/11 09:15.
const labelOf = (instant: string): string => {
  const date = new Date(instant);
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

// The value of a field of date and time for an instant, in the time zone of the browser: 2026-11-16T09:15.
const localInput = (instant: Date): string =>
  `${instant.getFullYear()}-${pad(instant.getMonth() + 1)}-${pad(instant.getDate())}T${pad(instant.getHours())}:${pad(instant.getMinutes())}`;
