import { SessionExpiredError } from '@/lib/auth';

/** Why the API refused a command; an expired session says nothing here, as the user is already back at the sign-in. */
export const CommandRefusal = ({ refusal, error }: { refusal: string; error: Error | null }) => {
  if (error === null || error instanceof SessionExpiredError) {
    return null;
  }
  return (
    <p role="alert" className="text-red-700">
      {refusal}: {error.message}
    </p>
  );
};
