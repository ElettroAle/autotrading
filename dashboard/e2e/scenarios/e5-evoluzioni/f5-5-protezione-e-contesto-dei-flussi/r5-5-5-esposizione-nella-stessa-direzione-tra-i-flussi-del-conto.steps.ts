import { expect } from '@playwright/test';

import { configurationOf, fakePlatform } from '@/testing/mocks/platform';

import { Then, When } from '../../../support/fixtures';

// The limit of the exposure of the flows of an account on one side, on the page of the account, and the option that
// shows the agent the exposure of the other flows, in the form of the flow (R5.5.5, ADR
// esposizione-del-conto-nella-dashboard): the API checks the limit, the dashboard sends what the user types.

const SAVE = 'Salva le modifiche';

When(
  /^"([^"]+)" imposta nella pagina del conto "([^"]+)" l'esposizione massima per direzione a (\d+)%$/,
  async ({ dashboard }, account: string, name: string, percent: number) => {
    // The scenario names no account beforehand: the user sets the limit on one of hers.
    fakePlatform.giveAccountTo(account, name, 2000);
    await dashboard.openAccounts();
    await dashboard.signInAs(account);
    await dashboard.openAccount(name, 'Impostazioni');
    const section = dashboard.page.getByRole('region', {
      name: `Esposizione per direzione del conto ${name}`,
    });
    await section
      .getByLabel('Esposizione massima per direzione (% del saldo)', { exact: true })
      .fill(String(percent));
    await section.getByRole('button', { name: 'Imposta il limite', exact: true }).click();
    await expect(section.getByRole('status')).toHaveText(`Limite impostato: ${percent}% del saldo`);
  },
);

Then(
  /^il conto "([^"]+)" ha esposizione massima per direzione (\d+)%$/,
  async ({}, name: string, percent: number) => {
    expect(fakePlatform.accountNamed(name).maxDirectionExposurePercent).toBe(String(percent));
  },
);

When(
  /^"([^"]+)" accende nel modulo di "([^"]+)" l'esposizione del conto nel contesto dell'agente$/,
  async ({ dashboard }, account: string, flow: string) => {
    // The scenario names no flow beforehand: the user edits one of hers.
    fakePlatform.ensureUser(account);
    fakePlatform.addFlow(account, flow);
    await dashboard.openFlowEditor(flow);
    await dashboard.signInAs(account);
    await dashboard.page
      .getByRole('checkbox', {
        name: "Esposizione degli altri flussi del conto nel contesto dell'agente",
      })
      .check();
    await dashboard.button(SAVE).click();
    await expect(dashboard.message('Modifiche salvate: versione 2')).toBeVisible();
  },
);

Then(
  /^"([^"]+)" ha l'esposizione del conto nel contesto dell'agente accesa$/,
  async ({}, flow: string) => {
    expect(configurationOf(fakePlatform.flowNamed(flow)).account_exposure_for_agent).toBe(true);
  },
);
