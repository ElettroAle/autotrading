import { expect } from '@playwright/test';

import type { DashboardPages } from './dashboard-pages';
import type { ScenarioMemory } from './fixtures';

/** Signs in once per scenario: the later steps act on the page the user is already on. */
export const onFlowPage = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
  flow: string,
): Promise<void> => {
  if (memory.account !== account) {
    memory.account = account;
    await dashboard.openFlowAs(account, flow);
  }
  await expect(dashboard.flowName()).toHaveText(flow);
};

/** Signs in once per scenario on the list of the flows, where the user imports a strategy. */
export const onFlowsPage = async (
  dashboard: DashboardPages,
  memory: ScenarioMemory,
  account: string,
): Promise<void> => {
  if (memory.account !== account) {
    memory.account = account;
    await dashboard.openAndSignInAs(account);
  }
  await expect(dashboard.importForm()).toBeVisible();
};
