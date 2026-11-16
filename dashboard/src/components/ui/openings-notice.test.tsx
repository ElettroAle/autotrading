import { render, screen } from '@testing-library/react';

import { OpeningsSuspendedNotice } from './openings-notice';

describe('OpeningsSuspendedNotice', () => {
  it('says that the openings of the flow are suspended, and why', () => {
    render(<OpeningsSuspendedNotice reason="perdita dal picco 11% oltre il 10%" />);

    expect(screen.getByRole('status')).toHaveTextContent(
      'aperture sospese: perdita dal picco 11% oltre il 10%',
    );
  });
});
