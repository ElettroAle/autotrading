import { render, screen } from '@testing-library/react';

import { SessionExpiredError } from '@/lib/auth';

import { ErrorMessage } from './error-message';

describe('ErrorMessage', () => {
  it('tells why the data could not be read', () => {
    render(<ErrorMessage error={new Error('piattaforma non raggiungibile')} />);

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Impossibile leggere i dati: piattaforma non raggiungibile',
    );
  });

  it('tells why a command failed with the lead the caller gives', () => {
    render(
      <ErrorMessage error={new Error('nessuna chat collegata')} prefix="Operazione non riuscita" />,
    );

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Operazione non riuscita: nessuna chat collegata',
    );
  });

  it('says nothing about an expired session, as the user is back at the sign-in', () => {
    render(<ErrorMessage error={new SessionExpiredError()} />);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
