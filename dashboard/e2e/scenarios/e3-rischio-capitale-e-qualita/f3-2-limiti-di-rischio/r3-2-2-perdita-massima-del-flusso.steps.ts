import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// How the scenarios name the resume, as the API takes it (R3.2.2).
const RESUMES: Readonly<Record<string, 'manual' | 'next_day'>> = {
  manuale: 'manual',
  'il giorno dopo': 'next_day',
};

// The thresholds, the suspension and its reason come from the API: the page only shows them (ADR 0116, ADR
// perdita-massima-nella-dashboard). The cycles that suspend and resume run on the use cases with pytest-bdd.
Given(
  'che {string} ha il flusso {string} attivo con asset {string}, perdita giornaliera massima {int}%, perdita massima dal picco {int}% e ripresa {string}',
  async (
    { memory },
    account: string,
    flow: string,
    asset: string,
    daily: number,
    peak: number,
    resume: string,
  ) => {
    memory.account = account;
    memory.flow = flow;
    fakePlatform.addUser(account, { hasUserRole: true });
    fakePlatform.addFlow(account, flow, {
      assets: [asset],
      maxDailyLossPercent: String(daily),
      maxDrawdownPercent: String(peak),
      openingsResume: RESUMES[resume],
    });
  },
);

Given(
  'che le aperture di {string} sono sospese con motivo {string}',
  async ({}, flow: string, reason: string) => {
    fakePlatform.changeFlow(flow, {
      openingsSuspension: { reason, suspendedAt: new Date().toISOString() },
    });
  },
);

When(
  '{string} apre il flusso {string} nella dashboard',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlowAs(account, flow);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);

Then(
  'la pagina mostra {string} e il comando {string}',
  async ({ page }, notice: string, command: string) => {
    const suspension = page.getByRole('region', { name: 'Aperture sospese' });
    await expect(suspension.getByRole('status')).toHaveText(notice);
    await expect(suspension.getByRole('button', { name: command, exact: true })).toBeEnabled();
  },
);
