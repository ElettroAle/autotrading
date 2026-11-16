import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { Given, Then, When } from '../../../support/fixtures';

// R3.6.1 on the flow page; pytest-bdd runs every scenario on the use cases (ADR errore-medio-della-previsione-nell-api,
// ADR errore-della-previsione-nella-pagina-del-flusso).

const HOUR_MS = 60 * 60 * 1000;
const HOUR_MINUTES = 60;

const hoursAgo = (hours: number): Date => new Date(Date.now() - hours * HOUR_MS);

Given(
  'che {string} ha il flusso {string} con la fonte forecast su {string} a 1 ora',
  async ({ memory }, account: string, flow: string, asset: string) => {
    fakePlatform.ensureUser(account);
    fakePlatform.addFlow(account, flow, {
      assets: [asset],
      sources: [{ name: 'forecast', weight: 5, parameters: { profondita_storico_giorni: 7 } }],
    });
    memory.account = account;
    memory.flow = flow;
  },
);

Given(
  /^che le previsioni di "([^"]+)" su "([^"]+)" a 1 ora hanno errore medio assoluto \d+ e percentuale [\d,]+% su 2 previsioni$/,
  async ({}, flow: string, asset: string) => {
    const forecasts = fakePlatform.flowNamed(flow).forecasts;
    forecasts.push(
      {
        asset,
        horizonMinutes: HOUR_MINUTES,
        expiresAt: hoursAgo(2),
        predictedPrice: 60500,
        actualPrice: 60000,
      },
      {
        asset,
        horizonMinutes: HOUR_MINUTES,
        expiresAt: hoursAgo(3),
        predictedPrice: 61000,
        actualPrice: 61400,
      },
    );
  },
);

When(
  '{string} apre la pagina del flusso {string} nella dashboard',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlow(flow);
    await dashboard.signInAs(account);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);

Then(
  /^la pagina mostra per "([^"]+)" a 1 ora errore medio (\d+), ([\d,]+%), (\d+) previsioni valutate$/,
  async ({ dashboard }, asset: string, error: string, percent: string, evaluated: string) => {
    await expect(dashboard.forecastError(`${asset} · 1 ora`)).toHaveText(
      `errore medio ${error} · ${percent} · ${evaluated} previsioni valutate`,
    );
  },
);
