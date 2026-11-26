import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { fakePlatform } from '@/testing/mocks/platform';
import { renderInApp } from '@/testing/test-utils';

import { AccountSettings } from './account-settings';

const FIELD = 'Esposizione massima per direzione (% del saldo)';
const SET = 'Imposta il limite';
const REMOVE = 'Togli il limite';

const limitOfTheAccount = () => fakePlatform.user('anna').accounts[0]?.maxDirectionExposurePercent;

const openSection = async (): Promise<HTMLElement> => {
  await renderInApp(<AccountSettings accountId="account-principale" />, { account: 'anna' });
  return screen.findByRole('region', {
    name: 'Esposizione per direzione del conto principale',
  });
};

const typeLimit = async (section: HTMLElement, percent: string): Promise<void> => {
  const field = within(section).getByLabelText(FIELD);
  await userEvent.clear(field);
  await userEvent.type(field, percent);
  await userEvent.click(within(section).getByRole('button', { name: SET }));
};

// R5.5.5, ADR esposizione-del-conto-nella-dashboard: the limit of the account on the page of the account, empty
// allowed, set and removed; the API checks it and says why it refuses it.
describe('MaxDirectionExposureForm', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'principale', 1000);
  });

  it('starts empty for an account without limit, with what the limit counts', async () => {
    const section = await openSection();

    const field = within(section).getByLabelText(FIELD);
    expect(field).toHaveValue('');
    expect(field).toHaveAccessibleDescription(
      'vuoto: nessun limite; somma separatamente il valore long e short delle posizioni di tutti i flussi del conto, in percento del saldo',
    );
    expect(within(section).queryByRole('button', { name: REMOVE })).not.toBeInTheDocument();
  });

  it('sets the limit of the account, with a decimal comma', async () => {
    const section = await openSection();

    await typeLimit(section, '62,5');

    expect(await within(section).findByRole('status')).toHaveTextContent(
      'Limite impostato: 62,5% del saldo',
    );
    expect(limitOfTheAccount()).toBe('62.5');
  });

  it('starts from the limit in force and removes it', async () => {
    const section = await openSection();
    await typeLimit(section, '60');
    await within(section).findByRole('status');

    await userEvent.click(await within(section).findByRole('button', { name: REMOVE }));

    expect(await within(section).findByText('Limite tolto')).toBeInTheDocument();
    expect(limitOfTheAccount()).toBeNull();
    expect(within(section).getByLabelText(FIELD)).toHaveValue('');
  });

  it('removes the limit when the field is emptied', async () => {
    const section = await openSection();
    await typeLimit(section, '60');
    await within(section).findByRole('status');

    await userEvent.clear(within(section).getByLabelText(FIELD));
    await userEvent.click(within(section).getByRole('button', { name: SET }));

    await waitFor(() => expect(limitOfTheAccount()).toBeNull());
  });

  it('shows the reason of a refusal of the API under the field', async () => {
    const section = await openSection();

    await typeLimit(section, '0');

    expect(await within(section).findByRole('alert')).toHaveTextContent(
      "l'esposizione massima per direzione è maggiore di 0",
    );
    expect(limitOfTheAccount()).toBeUndefined();
  });

  it('refuses a text that is not a number before asking the API', async () => {
    const section = await openSection();

    await typeLimit(section, 'molto');

    expect(await within(section).findByLabelText(FIELD)).toHaveAccessibleDescription(
      /scrivi il limite in percento, per esempio 60 oppure 62,5/,
    );
  });
});
