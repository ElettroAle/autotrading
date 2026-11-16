import { expect } from '@playwright/test';

import { paths } from '@/config/paths';
import { fakePlatform } from '@/testing/mocks/platform';

import { Then } from './fixtures';

// Shared by the ways to a cycle (R6.4.3, R6.4.4): the page of the cycle the user chose, with what it tells.
Then('vede il dettaglio di quel ciclo', async ({ dashboard, memory }) => {
  const chosen = memory.chosenCycle;
  expect(chosen, 'the scenario chose a cycle').toBeDefined();
  const flowId = fakePlatform.flowNamed(memory.flow).id;
  await expect(dashboard.page).toHaveURL(
    (url) => url.pathname === `/dashboard${paths.cycle.getHref(flowId, chosen?.planned_at ?? '')}`,
  );
  await expect(dashboard.pageHeading()).toHaveText('Dettaglio del ciclo');
  await expect(dashboard.failure()).toContainText(chosen?.failure?.message ?? '');
});
