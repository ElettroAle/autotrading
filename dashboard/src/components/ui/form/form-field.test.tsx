import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { FORM_CONTROL, FORM_TEXT_AREA, FormField } from './form-field';

const INFO = 'Quota del saldo del conto data al flusso. Maggiore di 0. Obbligatorio.';

describe('FormField', () => {
  it('names the control by its label and describes it by the reason of a refusal', () => {
    render(
      <FormField
        id="capital"
        label="Capitale allocato"
        error="capitale oltre il capitale libero"
        info={INFO}
      >
        {(control) => <input {...control} />}
      </FormField>,
    );

    const capital = screen.getByRole('textbox', { name: 'Capitale allocato' });
    expect(capital).toHaveAccessibleDescription('capitale oltre il capitale libero');
    expect(capital).toHaveAttribute('aria-invalid', 'true');
  });

  it('describes nothing while no refusal concerns the control', () => {
    render(
      <FormField id="capital" label="Capitale allocato" error={undefined} info={INFO}>
        {(control) => <input {...control} />}
      </FormField>,
    );

    const capital = screen.getByRole('textbox', { name: 'Capitale allocato' });
    expect(capital).not.toHaveAttribute('aria-describedby');
    expect(capital).not.toHaveAttribute('aria-invalid');
  });

  it('describes the control by what it admits, and then by the reason of a refusal', () => {
    render(
      <FormField
        id="days"
        label="tendenza giorni"
        error="valore oltre il tetto"
        hint="ogni valore tra 1 e 3650"
        info={INFO}
      >
        {(control) => <input {...control} />}
      </FormField>,
    );

    const days = screen.getByRole('textbox', { name: 'tendenza giorni' });
    expect(days).toHaveAccessibleDescription('ogni valore tra 1 e 3650 valore oltre il tetto');
    expect(days).toHaveAttribute('aria-invalid', 'true');
  });

  it('describes the control by what it admits while no refusal concerns it', () => {
    render(
      <FormField
        id="days"
        label="tendenza giorni"
        error={undefined}
        hint="ogni valore tra 1 e 3650"
        info={INFO}
      >
        {(control) => <input {...control} />}
      </FormField>,
    );

    const days = screen.getByRole('textbox', { name: 'tendenza giorni' });
    expect(days).toHaveAccessibleDescription('ogni valore tra 1 e 3650');
    expect(days).not.toHaveAttribute('aria-invalid');
  });

  it('has beside its label the info button of the field, which shows what the field does (R5.5.7)', async () => {
    render(
      <FormField id="capital" label="Capitale allocato" info={INFO} error={undefined}>
        {(control) => <input {...control} />}
      </FormField>,
    );

    await userEvent.click(
      screen.getByRole('button', { name: 'Informazioni su Capitale allocato' }),
    );

    expect(screen.getByText(INFO)).toBeVisible();
    expect(
      screen.getByRole('textbox', { name: 'Capitale allocato' }),
    ).not.toHaveAccessibleDescription();
  });

  // The width itself is proved by the browser on a phone (e2e/layout, ADR 0146): jsdom lays nothing out.
  it('keeps a control as wide as its form and never wider, cutting a long value short', () => {
    expect(FORM_CONTROL.split(' ')).toEqual(
      expect.arrayContaining(['w-full', 'max-w-full', 'min-w-0', 'truncate']),
    );
    expect(FORM_TEXT_AREA.split(' ')).toEqual(
      expect.arrayContaining(['w-full', 'max-w-full', 'min-w-0']),
    );
    expect(FORM_TEXT_AREA.split(' ')).not.toContain('truncate');
  });
});
