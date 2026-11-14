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

  async openFlow(name: string): Promise<void> {
    await this.open(`/flows/${fakePlatform.flowNamed(name).id}`);
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

  alert(): Locator {
    return this.page.getByRole('alert');
  }
}
