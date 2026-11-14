import { useSearchParams } from 'react-router';

import { PageLayout } from '@/components/layouts/page-layout';
import { returnPathOf, useSignIn } from '@/lib/auth';

export const LoginRoute = () => {
  const signIn = useSignIn();
  const [searchParameters] = useSearchParams();
  const returnTo = returnPathOf(searchParameters.get('returnTo'));
  return (
    <PageLayout title="Accesso alla dashboard">
      <p className="mb-4">Entra con il tuo account per gestire i tuoi flussi.</p>
      <button
        type="button"
        onClick={() => void signIn(returnTo)}
        className="rounded bg-blue-800 px-4 py-2 font-medium text-white hover:bg-blue-900"
      >
        Accedi
      </button>
    </PageLayout>
  );
};
