import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { CompareVersionsForm } from './compare-versions-form';

const AT = '2026-11-14T10:30:00Z';

describe('CompareVersionsForm', () => {
  it('proposes the only version against itself', () => {
    render(
      <CompareVersionsForm
        versions={[{ version: 1, created_at: AT }]}
        chosen={undefined}
        onCompare={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('Prima versione')).toHaveValue('1');
    expect(screen.getByLabelText('Seconda versione')).toHaveValue('1');
  });

  it('keeps the choice already made', () => {
    render(
      <CompareVersionsForm
        versions={[
          { version: 2, created_at: AT },
          { version: 1, created_at: AT },
        ]}
        chosen={{ first: 2, second: 1 }}
        onCompare={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('Prima versione')).toHaveValue('2');
    expect(screen.getByLabelText('Seconda versione')).toHaveValue('1');
  });

  it('compares nothing while there is no version to choose', async () => {
    const onCompare = vi.fn();
    render(<CompareVersionsForm versions={[]} chosen={undefined} onCompare={onCompare} />);

    await userEvent.setup().click(screen.getByRole('button', { name: 'Confronta' }));

    expect(onCompare).not.toHaveBeenCalled();
  });
});
