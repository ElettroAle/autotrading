import { expect, type Locator } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import {
  isBlue,
  isTransparent,
  isWhite,
  lightnessOf,
  paintedColourOf,
} from '../../../support/colours';
import type { DashboardPages } from '../../../support/dashboard-pages';
import { aStoppedFlow } from '../../../support/every-page';
import { Then, When } from '../../../support/fixtures';

// The flow the scenarios open: a stopped flow of the user.
const THE_FLOW = 'prova-btc';
const HISTORIES = ['Cicli', 'Posizioni chiuse', 'Ordini'];
const LEAST_MARK_WIDTH = 2;

const viewsOfTheFlows = (dashboard: DashboardPages): Locator =>
  dashboard.content().getByRole('navigation', { name: 'Viste dei flussi' });

const borderWidthOf = (locator: Locator): Promise<number> =>
  locator.evaluate((element) => parseFloat(getComputedStyle(element).borderBottomWidth));

When("{string} apre l'elenco dei flussi", async ({ dashboard }, account: string) => {
  fakePlatform.ensureUser(account);
  await dashboard.openAndSignInAs(account);
  await expect(dashboard.pageHeading()).toHaveText('I tuoi flussi');
});

Then(
  "la scheda {string} è evidenziata come scelta e {string} ha l'aspetto di una scheda non scelta",
  async ({ dashboard }, chosenName: string, otherName: string) => {
    const bar = viewsOfTheFlows(dashboard).getByRole('list');
    const chosen = viewsOfTheFlows(dashboard).getByRole('link', { name: chosenName, exact: true });
    const other = viewsOfTheFlows(dashboard).getByRole('link', { name: otherName, exact: true });
    await expect(chosen).toHaveAttribute('aria-current', 'page');
    await expect(other).not.toHaveAttribute('aria-current');

    const barBackground = await paintedColourOf(bar, 'backgroundColor');
    const chosenBackground = await paintedColourOf(chosen, 'backgroundColor');
    expect(isTransparent(barBackground), 'the bar has its own background').toBe(false);
    expect(isWhite(chosenBackground), 'the chosen tab is white').toBe(true);
    expect(lightnessOf(chosenBackground), 'the chosen tab stands out on the bar').toBeGreaterThan(
      lightnessOf(barBackground),
    );
    expect(
      isBlue(await paintedColourOf(chosen, 'borderBottomColor')),
      'the chosen tab has its mark',
    ).toBe(true);
    expect(await borderWidthOf(chosen)).toBeGreaterThanOrEqual(LEAST_MARK_WIDTH);
    expect(
      lightnessOf(await paintedColourOf(chosen, 'color')),
      'the text of the chosen tab is darker than the others',
    ).toBeLessThan(lightnessOf(await paintedColourOf(other, 'color')));

    expect(
      isTransparent(await paintedColourOf(other, 'backgroundColor')),
      'the other tab shows the bar',
    ).toBe(true);
    expect(
      isTransparent(await paintedColourOf(other, 'borderBottomColor')),
      'the other tab has no mark',
    ).toBe(true);
    expect((await other.boundingBox())?.height).toBe((await chosen.boundingBox())?.height);
  },
);

When('{string} apre lo storico', async ({ dashboard }, account: string) => {
  fakePlatform.ensureUser(account);
  await dashboard.openHistory();
  await dashboard.signInAs(account);
  await expect(dashboard.historyTab('Cicli')).toBeVisible();
});

Then(
  'le viste Cicli, Posizioni chiuse e Ordini sono schede di un gruppo di schede',
  async ({ dashboard }) => {
    const group = dashboard.content().getByRole('tablist', { name: 'Storici' });
    await expect(group.getByRole('tab')).toHaveText(HISTORIES);
    await expect(group.getByRole('tab', { selected: true })).toHaveText('Cicli');
  },
);

When('{string} apre la pagina del flusso', async ({ dashboard, memory }, account: string) => {
  memory.flow = THE_FLOW;
  aStoppedFlow(account, THE_FLOW);
  await dashboard.openFlowAs(account, THE_FLOW);
  await expect(dashboard.flowName()).toHaveText(THE_FLOW);
});

Then(
  'la barra delle schede sta su una riga e la pagina non scorre in orizzontale',
  async ({ dashboard }) => {
    const bar = dashboard.content().getByRole('navigation', { name: 'Dati del flusso' });
    const tops = await bar
      .getByRole('link')
      .evaluateAll((tabs) => tabs.map((tab) => Math.round(tab.getBoundingClientRect().top)));
    expect(tops.length).toBeGreaterThan(1);
    expect(new Set(tops).size, 'every tab on the same row').toBe(1);
    const width = dashboard.page.viewportSize()?.width ?? 0;
    expect(
      await dashboard.page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
  },
);
