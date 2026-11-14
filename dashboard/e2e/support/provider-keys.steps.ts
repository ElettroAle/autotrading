import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given } from './fixtures';

const ACCOUNT_NAME = 'principale';
const REGISTERED_AT = '2026-11-14T09:00:00+00:00';

// The user starts with a trading account, so that the forms that need one (a new flow) open as well.
const ensureUser = (account: string): void => {
  if (!fakePlatform.hasUser(account)) {
    fakePlatform.giveAccountTo(account, ACCOUNT_NAME, 500);
  }
};

// Shared by the requirements that depend on which providers have a key (R2.3.7, R2.3.8).
Given(
  'che {string} ha registrato la chiave del fornitore {string}',
  async ({}, account: string, provider: string) => {
    ensureUser(account);
    fakePlatform.saveProviderKey(account, provider, REGISTERED_AT);
    expect(fakePlatform.providerKeyOf(account, provider)).toBeDefined();
  },
);

Given(
  'che {string} non ha registrato la chiave del fornitore {string}',
  async ({}, account: string, provider: string) => {
    ensureUser(account);
    expect(fakePlatform.providerKeyOf(account, provider)).toBeUndefined();
  },
);
