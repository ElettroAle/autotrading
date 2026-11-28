import { expect, type Locator, type Page } from '@playwright/test';

import { FAKE_MODELS, FAKE_SOURCES } from '@/testing/mocks/catalogs';
import { fakePlatform } from '@/testing/mocks/platform';

import type { DashboardPages } from '../../../support/dashboard-pages';
import { Given, Then, When, type ScenarioMemory } from '../../../support/fixtures';

// The info button beside every field of the form of the flow and of the settings of the account (R5.5.7, ADR
// informazioni-sui-campi-di-configurazione); the texts of parameters come from the catalogs of the fake API, as the
// real API declares them (ADR descrizioni-dei-parametri-di-fonti-e-modelli).

const FORM = 'Configurazione del flusso';
const INFO = 'Informazioni su ';
const KEYS = { Esc: 'Escape', Invio: 'Enter', Spazio: ' ' } as const;
const CONTROLS = 'input:not([type="hidden"]):not([type="submit"]), select, textarea';

const flowForm = (page: Page): Locator => page.getByRole('form', { name: FORM });

/**
 * The info button of a field, by the label the scenario names: the label as the page shows it, or the key of a
 * parameter of the catalog, whose field the page names by the label the catalog gives it.
 */
const infoButton = (page: Page, field: string): Locator =>
  page
    .getByRole('button', { name: `${INFO}${field}` })
    .or(
      page
        .locator(`label[for$="-${field}"]`)
        .locator('xpath=..')
        .getByRole('button', { name: INFO }),
    );

/** The text the info button of the field opens. */
const infoText = async (page: Page, field: string): Promise<Locator> => {
  const controlled = await infoButton(page, field).getAttribute('aria-controls');
  return page.locator(`[id="${controlled ?? ''}"]`);
};

/** The labels of the visible controls of the region that have no info button named after them beside the label. */
const withoutInfoBeside = (region: Locator): Promise<{ labels: number; missing: string[] }> =>
  region.evaluate((element, selector) => {
    const labels = [...element.querySelectorAll<HTMLInputElement>(selector)]
      .filter((control) => control.checkVisibility())
      .map((control) => control.labels?.[0])
      .filter((label) => label !== undefined && label.textContent.trim() !== '');
    const missing = labels
      .filter((label) => {
        const name = `Informazioni su ${label?.textContent.trim() ?? ''}`;
        return ![...(label?.parentElement?.querySelectorAll('button') ?? [])].some(
          (button) => button.getAttribute('aria-label') === name,
        );
      })
      .map((label) => label?.textContent.trim() ?? '');
    return { labels: labels.length, missing };
  }, CONTROLS);

// The system prompt waits in a closed panel: its field shows once the panel is open (ADR pannello-del-system-prompt-chiuso).
const openSystemPrompt = async (form: Locator): Promise<void> => {
  const panel = form.locator('details');
  if ((await panel.getAttribute('open')) === null) {
    await panel.locator('summary').click();
  }
  await expect(form.getByLabel('System prompt', { exact: true })).toBeVisible();
};

const expectInfoBesideEveryLabel = async (region: Locator): Promise<void> => {
  const { labels, missing } = await withoutInfoBeside(region);
  expect(labels, 'campi con etichetta trovati').toBeGreaterThan(0);
  expect(missing, 'campi senza il pulsante info accanto all’etichetta').toEqual([]);
};

// Every step names the user who signed in with the form: the scenario follows one user.
const expectSignedIn = (memory: ScenarioMemory, account: string): void => {
  expect(account).toBe(memory.account);
};

const openFlowForm = async (dashboard: DashboardPages, flow: string): Promise<void> => {
  await dashboard.openFlowEditor(flow);
  await expect(dashboard.field('Nome', flowForm(dashboard.page))).toHaveValue(flow);
};

Given(
  'che {string} ha aperto il modulo di modifica del flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    fakePlatform.ensureUser(account);
    fakePlatform.addConfiguredFlow(account, flow, {
      account_id: fakePlatform.addAccount(account, 'principale').id,
    });
    memory.account = account;
    memory.flow = flow;
    await dashboard.openFlowEditor(flow);
    await dashboard.signInAs(account);
    await expect(dashboard.field('Nome', flowForm(dashboard.page))).toHaveValue(flow);
  },
);

When(
  '{string} attiva il pulsante {string}',
  async ({ dashboard, memory }, account: string, button: string) => {
    expectSignedIn(memory, account);
    const field = button.replace(INFO, '');
    memory.subject = field;
    await infoButton(dashboard.page, field).click();
  },
);

Then('vede il testo {string}', async ({ dashboard }, text: string) => {
  await expect(dashboard.page.getByText(text, { exact: true })).toBeVisible();
});

Then(
  'ogni campo del modulo ha accanto all\'etichetta un pulsante "Informazioni su" seguito dall\'etichetta del campo',
  async ({ dashboard }) => {
    const form = flowForm(dashboard.page);
    await openSystemPrompt(form);
    await expectInfoBesideEveryLabel(form);
  },
);

Then('attivando ciascun pulsante compare un testo non vuoto', async ({ dashboard }) => {
  const form = flowForm(dashboard.page);
  await openSystemPrompt(form);
  const buttons = await form.getByRole('button', { name: INFO }).all();
  expect(buttons.length).toBeGreaterThan(0);
  for (const button of buttons) {
    await button.click();
    const text = dashboard.page.locator(
      `[id="${(await button.getAttribute('aria-controls')) ?? ''}"]`,
    );
    await expect(text).toBeVisible();
    await expect(text).not.toHaveText(/^\s*$/);
  }
});

Given(
  "che il flusso {string} ha la fonte indicatori con l'adapter {string}",
  async ({ dashboard }, flow: string, adapter: string) => {
    fakePlatform.changeFlow(flow, {
      sources: [{ name: 'indicatori', adapters: [{ name: adapter, weight: 5, parameters: {} }] }],
    });
    await dashboard.page.reload();
    await openFlowForm(dashboard, flow);
    await expect(
      dashboard.page
        .getByRole('list', { name: 'Adapter di indicatori' })
        .getByRole('checkbox', { name: adapter, exact: true }),
    ).toBeChecked();
  },
);

Then(
  /^vede la descrizione che l'adapter "([^"]+)" dichiara per il parametro (\w+)$/,
  async ({ dashboard }, adapter: string, key: string) => {
    const declared = FAKE_SOURCES.flatMap((source) => source.adapters)
      .find((each) => each.name === adapter)
      ?.parameters.find((parameter) => parameter.key === key);
    expect(declared, `l'adapter ${adapter} dichiara ${key}`).toBeDefined();
    await expect(await infoText(dashboard.page, key)).toBeVisible();
    await expect(await infoText(dashboard.page, key)).toHaveText(declared?.description ?? '');
  },
);

Then(
  /^vede la descrizione che il modello di "([^"]+)" dichiara per il parametro (\w+)$/,
  async ({ dashboard }, flow: string, key: string) => {
    const declared = FAKE_MODELS.find(
      (model) => model.name === fakePlatform.flowNamed(flow).model,
    )?.parameters.find((parameter) => parameter.key === key);
    expect(declared, `il modello di ${flow} dichiara ${key}`).toBeDefined();
    await expect(await infoText(dashboard.page, key)).toBeVisible();
    await expect(await infoText(dashboard.page, key)).toHaveText(declared?.description ?? '');
  },
);

Given(
  'che {string} ha aperto il testo info di {string}',
  async ({ dashboard, memory }, account: string, field: string) => {
    expectSignedIn(memory, account);
    memory.subject = field;
    await infoButton(dashboard.page, field).click();
    await expect(await infoText(dashboard.page, field)).toBeVisible();
  },
);

When(
  /^"([^"]+)" preme (Esc|Invio|Spazio)$/,
  async ({ dashboard, memory }, account: string, key: keyof typeof KEYS) => {
    expectSignedIn(memory, account);
    await dashboard.page.keyboard.press(KEYS[key]);
  },
);

When('{string} fa clic fuori dal testo', async ({ dashboard, memory }, account: string) => {
  expectSignedIn(memory, account);
  await dashboard.pageHeading().click();
});

When(
  '{string} attiva di nuovo lo stesso pulsante info',
  async ({ dashboard, memory }, account: string) => {
    expectSignedIn(memory, account);
    await infoButton(dashboard.page, memory.subject).click();
  },
);

Then('il testo info di {string} non è più visibile', async ({ dashboard }, field: string) => {
  await expect(await infoText(dashboard.page, field)).toBeHidden();
  await expect(infoButton(dashboard.page, field)).toHaveAttribute('aria-expanded', 'false');
});

Then('vede il testo info di {string}', async ({ dashboard }, field: string) => {
  await expect(await infoText(dashboard.page, field)).toBeVisible();
  await expect(await infoText(dashboard.page, field)).not.toHaveText(/^\s*$/);
});

Given('che il pulsante {string} ha il fuoco', async ({ dashboard }, button: string) => {
  const info = infoButton(dashboard.page, button.replace(INFO, ''));
  await info.focus();
  await expect(info).toBeFocused();
});

Given(
  'che {string} ha aperto il modulo di creazione di un flusso',
  async ({ dashboard, memory }, account: string) => {
    expectSignedIn(memory, account);
    await dashboard.openNewFlow();
    await expect(dashboard.field('Nome', flowForm(dashboard.page))).toHaveValue('');
  },
);

Then(
  "ogni impostazione del conto ha accanto all'etichetta un pulsante \"Informazioni su\" seguito dall'etichetta dell'impostazione",
  async ({ dashboard }) => {
    await expectInfoBesideEveryLabel(dashboard.content());
  },
);
