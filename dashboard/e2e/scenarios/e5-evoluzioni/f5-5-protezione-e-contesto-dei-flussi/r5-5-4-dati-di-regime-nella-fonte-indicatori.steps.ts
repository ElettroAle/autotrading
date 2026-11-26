import { expect } from '@playwright/test';

import { configurationOf, fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Then, When } from '../../../support/fixtures';

// The regime data of the indicators in the form of the flow (R5.5.4, ADR dati-di-regime-nella-fonte-indicatori): the
// adapter of the market declares the parameters and the dashboard builds their fields from the catalog alone; the
// scenarios of the api and of the worker run in pytest-bdd.

const SOURCE = 'indicatori';
const SAVE = 'Salva le modifiche';
// The values in force of the flow, saved by an earlier version.
const IN_FORCE = { estremi_ore: [24], variazione_ore: [4], serie_chiusure: 1 };

const indicatorsOf = (flow: string) => {
  const [adapter] =
    configurationOf(fakePlatform.flowNamed(flow)).sources.find((source) => source.name === SOURCE)
      ?.adapters ?? [];
  expect(adapter, `il flusso ${flow} ha un adapter degli indicatori`).toBeDefined();
  return adapter as NonNullable<typeof adapter>;
};

const fieldOf = (dashboard: DashboardPages, flow: string, key: string) =>
  dashboard.field(`${key} di ${SOURCE} · ${indicatorsOf(flow).name}`);

When(
  "{string} apre nel modulo di {string} l'adapter {string} della fonte indicatori",
  async ({ dashboard, memory }, account: string, flow: string, adapter: string) => {
    fakePlatform.ensureUser(account);
    fakePlatform.addConfiguredFlow(account, flow, {
      account_id: fakePlatform.addAccount(account, 'principale').id,
      sources: [
        {
          name: SOURCE,
          adapters: [
            { name: adapter, weight: 5, parameters: { lunghezza_serie: 10, ...IN_FORCE } },
          ],
        },
      ],
    });
    memory.flow = flow;
    await dashboard.openFlowEditor(flow);
    await dashboard.signInAs(account);
    await expect(dashboard.field('Nome')).toHaveValue(flow);
    const adapters = dashboard.page.getByRole('list', { name: `Adapter di ${SOURCE}` });
    await expect(adapters.getByRole('checkbox', { name: adapter, exact: true })).toBeChecked();
  },
);

Then(
  'vede i parametri estremi_ore, variazione_ore e serie_chiusure con i valori in vigore',
  async ({ dashboard, memory }) => {
    await expect(fieldOf(dashboard, memory.flow, 'estremi_ore')).toHaveValue('24');
    await expect(fieldOf(dashboard, memory.flow, 'variazione_ore')).toHaveValue('4');
    await expect(fieldOf(dashboard, memory.flow, 'serie_chiusure')).toHaveValue('1');
  },
);

Then(
  'può impostare estremi_ore a [{int}, {int}]',
  async ({ dashboard, memory }, first: number, second: number) => {
    await fieldOf(dashboard, memory.flow, 'estremi_ore').fill(`${first}, ${second}`);
    await dashboard.button(SAVE).click();
    await expect
      .poll(() => indicatorsOf(memory.flow).parameters['estremi_ore'])
      .toEqual([first, second]);
  },
);
