import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

const PHONE_HEIGHT = 844;
const REFRESH_INTERVAL = '00:30';
const CYCLE_BEFORE_OPENING = '09:45:00';

/** The instant of today at the time of the scenario, in the time zone the browser shares with the steps. */
const instantAt = (time: string): Date => {
  const [hours = 0, minutes = 0, seconds = 0] = time.split(':').map(Number);
  const instant = new Date();
  instant.setHours(hours, minutes, seconds, 0);
  return instant;
};

// The clock of the browser stays at the instant of the scenario while its timers keep running, so every reading of
// the page is dated exactly; moving the timers forward fires the rereading of the page (ADR 0119).
Given(
  'che {string} ha aperto la pagina del flusso {string} alle {word}',
  async ({ dashboard }, account: string, flow: string, time: string) => {
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow);
    fakePlatform.concludeCycle(flow, instantAt(CYCLE_BEFORE_OPENING));
    await dashboard.openAndSignInAs(account);
    await expect(dashboard.flows()).toBeVisible();
    await dashboard.page.clock.setFixedTime(instantAt(time));
    await dashboard.openFlow(flow);
    await expect(dashboard.lastUpdate()).toHaveText(`Ultimo aggiornamento: ${time}`);
  },
);

When(
  'un nuovo ciclo del flusso {string} si conclude alle {word}',
  async ({ dashboard, memory }, flow: string, time: string) => {
    await dashboard.page.clock.setFixedTime(instantAt(time));
    fakePlatform.concludeCycle(flow, instantAt(time));
    memory.newCycleAt = time;
  },
);

Then('alle {word} la pagina mostra il nuovo ciclo', async ({ dashboard, memory }, time: string) => {
  await dashboard.page.clock.setFixedTime(instantAt(time));
  await dashboard.page.clock.fastForward(REFRESH_INTERVAL);
  await expect(dashboard.cycles()).toContainText(memory.newCycleAt);
});

Then("l'istante dell'ultimo aggiornamento è {word}", async ({ dashboard }, time: string) => {
  await expect(dashboard.lastUpdate()).toHaveText(`Ultimo aggiornamento: ${time}`);
});

When(
  '{string} preme {string} alle {word}',
  async ({ dashboard }, _account: string, button: string, time: string) => {
    await dashboard.page.clock.setFixedTime(instantAt(time));
    await dashboard.button(button).click();
  },
);

Then('la pagina mostra il nuovo ciclo', async ({ dashboard, memory }) => {
  await expect(dashboard.cycles()).toContainText(memory.newCycleAt);
});

Given("che l'interfaccia programmatica non risponde", () => {
  fakePlatform.stopApi();
});

When("arriva il momento dell'aggiornamento", async ({ dashboard }) => {
  await dashboard.page.clock.fastForward(REFRESH_INTERVAL);
});

Then('la pagina mostra ancora i dati delle {word}', async ({ dashboard }, time: string) => {
  await expect(dashboard.alert()).toBeVisible();
  await expect(dashboard.lastUpdate()).toHaveText(`Ultimo aggiornamento: ${time}`);
  await expect(dashboard.cycles()).toContainText(CYCLE_BEFORE_OPENING);
});

Then("mostra l'avviso {string}", async ({ dashboard }, warning: string) => {
  await expect(dashboard.alert()).toHaveText(warning);
});

When(
  '{string} apre la pagina del flusso {string} su uno schermo largo {int} pixel',
  async ({ dashboard }, _account: string, flow: string, width: number) => {
    await dashboard.page.setViewportSize({ width, height: PHONE_HEIGHT });
    await dashboard.openFlow(flow);
    await expect(dashboard.cycles()).toBeVisible();
  },
);

Then('tutti i contenuti sono leggibili senza scorrimento orizzontale', async ({ dashboard }) => {
  const width = dashboard.page.viewportSize()?.width ?? 0;
  expect(await dashboard.horizontalOverflow()).toBeLessThanOrEqual(0);
  for (const content of [
    dashboard.pageHeading(),
    dashboard.environment(),
    dashboard.flowName(),
    dashboard.cycles(),
    dashboard.lastUpdate(),
    dashboard.button('Aggiorna'),
  ]) {
    const box = await content.boundingBox();
    expect(box).not.toBeNull();
    expect(box?.x).toBeGreaterThanOrEqual(0);
    expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(width);
  }
});

When(
  '{string} apre le versioni della configurazione dalla pagina del flusso {string} su uno schermo largo {int} pixel',
  async ({ dashboard }, _account: string, flow: string, width: number) => {
    await dashboard.page.setViewportSize({ width, height: PHONE_HEIGHT });
    await expect(dashboard.flowName()).toHaveText(flow);
    await dashboard.page.getByRole('link', { name: 'Versioni della configurazione' }).click();
    await expect(dashboard.versions()).toBeVisible();
  },
);

When('preme {string}', async ({ dashboard }, command: string) => {
  await dashboard.headerCommand(command).click();
});

When(
  '{string} preme {string} sulla pagina del flusso {string} aperta direttamente',
  async ({ dashboard }, _account: string, command: string, flow: string) => {
    await expect(dashboard.flowName()).toHaveText(flow);
    await dashboard.headerCommand(command).click();
  },
);

When('{string} preme {string}', async ({ dashboard }, _account: string, command: string) => {
  await dashboard.headerCommand(command).click();
});

Then('torna alla pagina del flusso {string}', async ({ dashboard }, flow: string) => {
  await expect(dashboard.flowName()).toHaveText(flow);
  await expect(dashboard.page).toHaveURL(
    new RegExp(`/dashboard/flows/${fakePlatform.flowNamed(flow).id}$`),
  );
});

Then('torna alla pagina dei suoi flussi', async ({ dashboard }) => {
  await expect(dashboard.flows()).toBeVisible();
  await expect(dashboard.page).toHaveURL(/\/dashboard\/?$/);
});

Then("in alto non c'è il comando {string}", async ({ dashboard }, command: string) => {
  await expect(dashboard.flows()).toBeVisible();
  await expect(dashboard.headerCommand(command)).toHaveCount(0);
});
