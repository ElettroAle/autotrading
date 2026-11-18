import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';

import { fakePlatform } from '@/testing/mocks/platform';
import { fakeReconciliation } from '@/testing/mocks/reconciliation';
import { server } from '@/testing/mocks/server';
import { renderApp } from '@/testing/test-utils';

const ACCOUNT_ID = 'account-test-1';
const FIELD = 'Soglia di scostamento (%)';

const openThresholdForm = async (): Promise<HTMLElement> => {
  await renderApp({ account: 'anna', url: '/accounts/account-test-1/reconciliation' });
  // The account is read first, its reconciliation after: the section has its title at once, its data once read.
  const section = await screen.findByRole('region', { name: 'Riconciliazione del conto test-1' });
  await userEvent.click(await within(section).findByRole('button', { name: 'Modifica la soglia' }));
  return section;
};

const typeThreshold = async (section: HTMLElement, percent: string): Promise<void> => {
  const field = within(section).getByLabelText(FIELD);
  await userEvent.clear(field);
  await userEvent.type(field, percent);
  await userEvent.click(within(section).getByRole('button', { name: 'Salva la soglia' }));
};

const threshold = (section: HTMLElement): HTMLElement =>
  within(section).getByLabelText('Soglia', { selector: 'dd' });

describe('DeviationThresholdForm', () => {
  beforeEach(() => {
    fakePlatform.giveAccountTo('anna', 'test-1', 1000);
  });

  it('starts from the threshold in force', async () => {
    fakeReconciliation.setThreshold(ACCOUNT_ID, '2.5');

    const section = await openThresholdForm();

    expect(within(section).getByLabelText(FIELD)).toHaveValue('2,5');
  });

  it('sets the threshold of the account and closes the form', async () => {
    const section = await openThresholdForm();

    await typeThreshold(section, '3');

    expect(await within(section).findByText('3%')).toBeInTheDocument();
    expect(within(section).queryByLabelText(FIELD)).not.toBeInTheDocument();
    expect(fakeReconciliation.thresholdOf(ACCOUNT_ID)).toBe('3');
  });

  it('reads a decimal comma as the decimal point of the API', async () => {
    const section = await openThresholdForm();

    await typeThreshold(section, '0,5');

    expect(await within(section).findByText('0,5%')).toBeInTheDocument();
    expect(fakeReconciliation.thresholdOf(ACCOUNT_ID)).toBe('0.5');
  });

  it('shows why the API refuses a threshold out of range', async () => {
    const section = await openThresholdForm();

    await typeThreshold(section, '101');

    const form = within(section).getByRole('form', {
      name: 'Soglia di scostamento del conto test-1',
    });
    expect(await within(form).findByRole('alert')).toHaveTextContent(
      'la soglia di scostamento va da 0,1 a 100',
    );
    expect(threshold(section)).toHaveTextContent('1%');
  });

  it('shows beside the field the reason of an invalid request that names it, the others at the head', async () => {
    server.use(
      http.put('*/accounts/:accountId/deviation-threshold', () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Unprocessable Content',
            status: 422,
            detail: 'richiesta non valida',
            errors: [
              { loc: ['body', 'percent'], msg: 'numero decimale non valido' },
              { loc: ['body', 'unit'], msg: 'campo non previsto' },
            ],
          },
          { status: 422, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    );
    const section = await openThresholdForm();

    await typeThreshold(section, '3');

    expect(await within(section).findByLabelText(FIELD)).toHaveAccessibleDescription(
      'numero decimale non valido',
    );
    expect(within(section).getByRole('alert')).toHaveTextContent('campo non previsto');
  });

  it('asks for a number before sending anything', async () => {
    const section = await openThresholdForm();

    await typeThreshold(section, 'molto');

    expect(within(section).getByLabelText(FIELD)).toHaveAccessibleDescription(
      'scrivi la soglia in percento, per esempio 1 oppure 0,5',
    );
    expect(fakeReconciliation.thresholdOf(ACCOUNT_ID)).toBe('1');
  });

  it('closes without changes when the user cancels', async () => {
    const section = await openThresholdForm();

    await userEvent.click(within(section).getByRole('button', { name: 'Annulla' }));

    expect(within(section).queryByLabelText(FIELD)).not.toBeInTheDocument();
    expect(threshold(section)).toHaveTextContent('1%');
  });
});
