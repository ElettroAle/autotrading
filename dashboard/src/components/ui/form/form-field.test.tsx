import { render, screen } from '@testing-library/react';

import { FormField } from './form-field';

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
});
