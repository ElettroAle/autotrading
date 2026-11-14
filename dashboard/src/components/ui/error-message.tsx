import { SessionExpiredError } from '@/lib/auth';

type ErrorMessageProps = {
  readonly error: Error;
  /** What failed, before the reason: a read unless the caller says otherwise. */
  readonly prefix?: string;
};

/** The reason a read failed; an expired session says nothing here, as the user is already back at the sign-in. */
export const ErrorMessage = ({
  error,
  prefix = 'Impossibile leggere i dati',
}: ErrorMessageProps) => {
  if (error instanceof SessionExpiredError) {
    return null;
  }
  return (
    <p role="alert" className="text-red-700">
      {prefix}: {error.message}
    </p>
  );
};
