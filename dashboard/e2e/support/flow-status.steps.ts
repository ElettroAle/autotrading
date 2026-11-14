import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Then } from './fixtures';

// Shared by the commands (R2.3.4) and the drafts (R2.4.1): the page and the platform agree on the status.
Then(
  'il flusso {string} è nello stato {string}',
  async ({ dashboard }, flow: string, status: string) => {
    await expect(dashboard.status(status)).toBeVisible();
    expect(fakePlatform.flowNamed(flow).status).toBe(status);
  },
);
