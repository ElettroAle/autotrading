import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { CheckboxField } from './checkbox-field';

const INFO = 'Ricorda le decisioni precedenti del flusso. Accesa o spenta. Predefinita: spenta.';

describe('CheckboxField', () => {
  it('names the box by its label and puts the info button of the option beside it (R5.5.7)', async () => {
    render(<CheckboxField label="Memoria attiva" info={INFO} name="memory" />);

    expect(screen.getByRole('checkbox', { name: 'Memoria attiva' })).not.toBeChecked();
    await userEvent.click(screen.getByRole('button', { name: 'Informazioni su Memoria attiva' }));
    expect(screen.getByText(INFO)).toBeVisible();
    expect(screen.getByRole('checkbox', { name: 'Memoria attiva' })).not.toBeChecked();
  });

  it('describes the box by the line that says what the option adds', () => {
    render(
      <CheckboxField
        id="flow-fees"
        label="Commissioni"
        info={INFO}
        hint="lo stato riporta il costo di andata e ritorno"
      />,
    );

    const box = screen.getByRole('checkbox', { name: 'Commissioni' });
    expect(box).toHaveAccessibleDescription('lo stato riporta il costo di andata e ritorno');
    expect(box).toHaveAttribute('aria-describedby', 'flow-fees-hint');
  });

  it('describes nothing without a line', () => {
    render(<CheckboxField label="Memoria attiva" info={INFO} />);

    expect(screen.getByRole('checkbox', { name: 'Memoria attiva' })).not.toHaveAttribute(
      'aria-describedby',
    );
  });
});
