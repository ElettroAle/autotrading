import { SessionExpiredError } from '@/lib/auth';

/** The reason a read failed; an expired session says nothing here, as the user is already back at the sign-in. */
export const ErrorMessage = ({ error }: { error: Error }) => {
  if (error instanceof SessionExpiredError) {
    return null;
  }
  return (
    <p role="alert" className="text-red-700">
      Impossibile leggere i dati: {error.message}
    </p>
  );
};
