import { expect, type Locator, type Page } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

const BASE_PATH = '/dashboard';

/** What a user sees and does in the dashboard, so the steps read as the scenario. */
export class DashboardPages {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async open(path = '/'): Promise<void> {
    await this.page.goto(`${BASE_PATH}${path}`);
  }

  async openNotifications(): Promise<void> {
    await this.open('/notifications');
  }

  async openFlow(name: string): Promise<void> {
    await this.open(`/flows/${fakePlatform.flowNamed(name).id}`);
  }

  async openCyclesOf(flowName: string): Promise<void> {
    await this.open(`/flows/${fakePlatform.flowNamed(flowName).id}/cycles`);
  }

  /** Signs in from the sign-in page: the account is the one typed on the page of the identity provider. */
  async signInAs(account: string): Promise<void> {
    await expect(this.signInButton()).toBeVisible();
    fakePlatform.signIn(account);
    await this.signInButton().click();
    await this.page.waitForURL((url) => !url.pathname.endsWith('/login'));
  }

  async openAndSignInAs(account: string): Promise<void> {
    await this.open();
    await this.signInAs(account);
  }

  signInButton(): Locator {
    return this.page.getByRole('button', { name: 'Accedi' });
  }

  signInHeading(): Locator {
    return this.page.getByRole('heading', { name: 'Accesso alla dashboard' });
  }

  pageHeading(): Locator {
    return this.page.getByRole('heading', { level: 1 });
  }

  environment(): Locator {
    return this.page.getByLabel("Ambiente dell'installazione");
  }

  flows(): Locator {
    return this.page.getByRole('list', { name: 'Flussi' });
  }

  flowLinks(): Locator {
    return this.page.locator(`a[href^="${BASE_PATH}/flows/"]`);
  }

  flowName(): Locator {
    return this.page.getByRole('heading', { level: 2 });
  }

  cycleRows(): Locator {
    return this.page.getByRole('table', { name: 'Cicli' }).locator('tbody tr');
  }

  nextPage(): Locator {
    return this.page.getByRole('link', { name: 'Pagina successiva' });
  }

  /** A section of the detail of a cycle, by the title it shows. */
  section(title: string): Locator {
    return this.page.getByRole('group', { name: title, exact: true });
  }

  failure(): Locator {
    return this.page.getByRole('region', { name: 'Errore del ciclo' });
  }

  alert(): Locator {
    return this.page.getByRole('alert');
  }

  /** A message the dashboard tells the user, as an alert or as a status, with exactly this text. */
  message(text: string): Locator {
    return this.page
      .getByRole('alert')
      .or(this.page.getByRole('status'))
      .and(this.page.getByText(text, { exact: true }));
  }

  button(name: string): Locator {
    return this.page.getByRole('button', { name });
  }

  linkCode(): Locator {
    return this.page.getByLabel('Codice di collegamento');
  }

  linkCodeExpiry(): Locator {
    return this.page.getByLabel('Scadenza del codice');
  }

  botLink(): Locator {
    return this.page.getByRole('link', { name: 'Apri il bot e collega la chat' });
  }

  linkedChat(): Locator {
    return this.page.getByLabel('Chat collegata');
  }

  period(): Locator {
    return this.page.getByLabel('Periodo');
  }

  statistics(): Locator {
    return this.page.getByRole('region', { name: 'Statistiche' });
  }

  /** The value the statistics panel shows beside a label. */
  statistic(label: string): Locator {
    return this.statistics().getByLabel(label, { exact: true });
  }
}
