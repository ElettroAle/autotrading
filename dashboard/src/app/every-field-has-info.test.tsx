// ADR informazioni-sui-campi-di-configurazione (R5.5.7): the form that creates a flow, the one that edits it and the
// settings of the page of an account give every labelled control an info button named «Informazioni su <label>» that
// shows a text that is not empty; a control without it is red here, whatever form adds it.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { FormField } from '@/components/ui/form/form-field';
import { fakePlatform } from '@/testing/mocks/platform';
import { renderApp } from '@/testing/test-utils';

/** The labels of the labelled controls of the region. */
const labelsOf = (region: HTMLElement): string[] =>
  within(region)
    .queryAllByLabelText(/\S/)
    .map((control) => (control as HTMLInputElement).labels?.[0]?.textContent.trim() ?? '')
    .filter((label) => label !== '');

/**
 * The labels of the controls of the region that have no info button, or whose button controls no note with a text:
 * buttons and notes are read once, open or closed, and matched by the note the button controls.
 */
const withoutInfo = (region: HTMLElement): string[] => {
  const notes = within(region).queryAllByRole('note', { hidden: true });
  const buttons = within(region).queryAllByRole('button', { name: /^Informazioni su / });
  const textOf = (label: string): string => {
    const button = buttons.find(
      (each) => each.getAttribute('aria-label') === `Informazioni su ${label}`,
    );
    const controlled = button?.getAttribute('aria-controls');
    return notes.find((note) => note.id === controlled)?.textContent.trim() ?? '';
  };
  return labelsOf(region).filter((label) => textOf(label) === '');
};

const form = () => screen.findByRole('form', { name: 'Configurazione del flusso' });

describe('ADR informazioni-sui-campi-di-configurazione: every field has its info', () => {
  beforeEach(() => {
    fakePlatform.addUser('anna', { hasUserRole: true });
    fakePlatform.giveAccountTo('anna', 'principale', 500);
    fakePlatform.saveProviderKey('anna', 'openrouter', '2026-11-14T09:00:00+00:00');
  });

  it('is red on a labelled control without the info button', () => {
    render(
      <section aria-label="Prova">
        <label htmlFor="bare">Campo senza info</label>
        <input id="bare" />
        <FormField id="with" label="Campo con info" info="Che cosa fa." error={undefined}>
          {(control) => <input {...control} />}
        </FormField>
      </section>,
    );

    expect(withoutInfo(screen.getByRole('region', { name: 'Prova' }))).toEqual([
      'Campo senza info',
    ]);
  });

  it('is red on an info button with an empty text', () => {
    render(
      <section aria-label="Prova">
        <FormField id="empty" label="Campo vuoto" info=" " error={undefined}>
          {(control) => <input {...control} />}
        </FormField>
      </section>,
    );

    expect(withoutInfo(screen.getByRole('region', { name: 'Prova' }))).toEqual(['Campo vuoto']);
  });

  it('finds the info of every field of the form that creates a flow, sources and model chosen', async () => {
    await renderApp({ account: 'anna', url: '/flows/new' });
    const creation = await form();
    await userEvent.click(within(creation).getByRole('checkbox', { name: 'indicatori' }));
    await userEvent.selectOptions(
      within(creation).getByLabelText('Modello'),
      'openrouter/deepseek-chat',
    );

    expect(within(creation).getByLabelText('temperatura')).toBeInTheDocument();
    expect(withoutInfo(creation)).toEqual([]);
  });

  it('finds the info of every field of the form that edits a flow', async () => {
    fakePlatform.addConfiguredFlow('anna', 'alfa', {
      account_id: 'account-principale',
      sources: [
        { name: 'indicatori', adapters: [{ name: 'Hyperliquid', weight: 5, parameters: {} }] },
      ],
    });
    await renderApp({ account: 'anna', url: '/flows/flow-alfa/edit' });
    const edit = await form();

    expect(
      await within(edit).findByLabelText('rsi periodi di indicatori · Hyperliquid'),
    ).toBeInTheDocument();
    expect(withoutInfo(edit)).toEqual([]);
  });

  it('finds the info of every setting of the page of an account', async () => {
    await renderApp({ account: 'anna', url: '/accounts/account-principale/settings' });
    await userEvent.click(
      await screen.findByRole('button', { name: 'Sostituisci le credenziali' }),
    );
    const page = screen.getByRole('main');

    expect(
      within(page).getByLabelText('Esposizione massima per direzione (% del saldo)'),
    ).toBeInTheDocument();
    expect(
      within(page).getByLabelText('Intervallo di riconciliazione (minuti)'),
    ).toBeInTheDocument();
    expect(withoutInfo(page)).toEqual([]);
  });
});
