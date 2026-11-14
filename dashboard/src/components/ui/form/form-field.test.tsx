import { render, screen } from '@testing-library/react';

import { FORM_CONTROL, FORM_TEXT_AREA, FormField } from './form-field';

describe('FormField', () => {
  it('names the control by its label and describes it by the reason of a refusal', () => {
    render(
      <FormField id="capital" label="Capitale allocato" error="capitale oltre il capitale libero">
        {(control) => <input {...control} />}
      </FormField>,
    );

    const capital = screen.getByRole('textbox', { name: 'Capitale allocato' });
    expect(capital).toHaveAccessibleDescription('capitale oltre il capitale libero');
    expect(capital).toHaveAttribute('aria-invalid', 'true');
  });

  it('describes nothing while no refusal concerns the control', () => {
    render(
      <FormField id="capital" label="Capitale allocato" error={undefined}>
        {(control) => <input {...control} />}
      </FormField>,
    );

    const capital = screen.getByRole('textbox', { name: 'Capitale allocato' });
    expect(capital).not.toHaveAttribute('aria-describedby');
    expect(capital).not.toHaveAttribute('aria-invalid');
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
