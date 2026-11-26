import { expect } from '@playwright/test';

import { configurationOf, fakePlatform } from '@/testing/mocks/platform';

import { Then, When } from '../../../support/fixtures';

// The option that gives the agent the round-trip cost of a position, in the form of the flow beside the other options
// of the context of the agent (R5.5.6, ADR costo-di-andata-e-ritorno-nel-contesto-dell-agente).

const SAVE = 'Salva le modifiche';

When(
  /^"([^"]+)" accende nel modulo di "([^"]+)" le commissioni nel contesto dell'agente$/,
  async ({ dashboard }, account: string, flow: string) => {
    // The scenario names no flow beforehand: the user edits one of hers.
    fakePlatform.ensureUser(account);
    fakePlatform.addFlow(account, flow);
    await dashboard.openFlowEditor(flow);
    await dashboard.signInAs(account);
    await dashboard.page
      .getByRole('checkbox', { name: "Commissioni nel contesto dell'agente" })
      .check();
    await dashboard.button(SAVE).click();
    await expect(dashboard.message('Modifiche salvate: versione 2')).toBeVisible();
  },
);

Then(/^"([^"]+)" ha le commissioni nel contesto dell'agente accese$/, async ({}, flow: string) => {
  expect(configurationOf(fakePlatform.flowNamed(flow)).fees_for_agent).toBe(true);
});
