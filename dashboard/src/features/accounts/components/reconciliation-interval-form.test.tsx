import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderInApp } from '@/testing/test-utils';

import { AccountSettings } from './account-settings';

const FIELD = 'Intervallo di riconciliazione (minuti)';
const SAVE = "Salva l'intervallo";

const intervalOfTheAccount = () =>
  fakePlatform.user('anna').accounts[0]?.reconciliationIntervalMinutes;

const openSection = async (): Promise<HTMLElement> => {
  await renderInApp(<AccountSettings accountId="account-principale" />, { account: 'anna' });
  return screen.findByRole('region', { name: 'Riconciliazione periodica del conto principale' });
};

const typeInterval = async (section: HTMLElement, minutes: string): Promise<void> => {
  const field = within(section).getByLabelText(FIELD);
  await userEvent.clear(field);
  await userEvent.type(field, minutes);
  await userEvent.click(within(section).getByRole('button', { name: SAVE }));
};

// Bug 778, ADR intervallo-di-riconciliazione-del-conto: the interval of the account on the page of the account, the
// default shown as such; the API checks its range and says why it refuses it.
describe('ReconciliationIntervalForm', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
  });

  it('starts from the interval in force, the default of an account that set none', async () => {
    const section = await openSection();

    expect(within(section).getByLabelText(FIELD)).toHaveValue('5');
    expect(
      within(section).getByRole('button', { name: `Informazioni su ${FIELD}` }),
    ).toBeInTheDocument();
  });

  it('sets the interval of the account', async () => {
    const section = await openSection();

    await typeInterval(section, '15');

    expect(await within(section).findByRole('status')).toHaveTextContent(
      'Intervallo di riconciliazione: 15 minuti',
    );
    expect(intervalOfTheAccount()).toBe(15);
    expect(within(section).getByLabelText(FIELD)).toHaveValue('15');
  });

  it('shows the reason of a refusal of the API', async () => {
    const section = await openSection();

    await typeInterval(section, '1441');

    expect(await within(section).findByRole('alert')).toHaveTextContent(
      'intervallo di riconciliazione da 1 a 1440 minuti',
    );
    expect(intervalOfTheAccount()).toBeUndefined();
  });

  it('refuses a text that is not a whole number before asking the API', async () => {
    const section = await openSection();

    await typeInterval(section, '2,5');

    expect(await within(section).findByLabelText(FIELD)).toHaveAccessibleDescription(
      /scrivi i minuti come numero intero, per esempio 15/,
    );
    expect(intervalOfTheAccount()).toBeUndefined();
  });
});
