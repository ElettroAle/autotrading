import type { Browser, BrowserContext, Page } from '@playwright/test';

import { DashboardPages } from './dashboard-pages';
import { routeToFakes } from './fake-network';

type StorageState = Awaited<ReturnType<BrowserContext['storageState']>>;

type ContextOptions = {
  readonly baseURL: string | undefined;
  readonly timezoneId: string | undefined;
};

/**
 * The browser of the user closed and opened again (R6.5.1): the new one keeps only what the first left in the local
 * storage, as the cookies of the session and the storage of the tab end with the browser.
 */
export class BrowserRestart {
  private readonly first: Page;

  private readonly browser: Browser;

  private readonly options: ContextOptions;

  private kept: StorageState | undefined;

  private readonly contexts: BrowserContext[] = [];

  private reopenedPages: DashboardPages | undefined;

  constructor(first: Page, browser: Browser, options: ContextOptions) {
    this.first = first;
    this.browser = browser;
    this.options = options;
  }

  async close(): Promise<void> {
    const { origins } = await this.first.context().storageState();
    this.kept = { cookies: [], origins };
    await this.first.goto('about:blank');
  }

  /** The dashboard in the browser opened again at the instant, routed to the same fakes. */
  async reopenAt(instant: Date): Promise<DashboardPages> {
    const context = await this.browser.newContext({ ...this.options, storageState: this.kept });
    this.contexts.push(context);
    const page = await context.newPage();
    await page.clock.install({ time: instant });
    await routeToFakes(page, new URL(this.options.baseURL ?? 'http://127.0.0.1').origin);
    this.reopenedPages = new DashboardPages(page);
    return this.reopenedPages;
  }

  /** The dashboard in the browser opened again. */
  reopened(): DashboardPages {
    if (this.reopenedPages === undefined) {
      throw new Error('the browser was not opened again');
    }
    return this.reopenedPages;
  }

  async dispose(): Promise<void> {
    await Promise.all(this.contexts.map((context) => context.close()));
  }
}
