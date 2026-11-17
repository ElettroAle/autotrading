import { useQueryClient } from '@tanstack/react-query';

import { useSignOut } from '@/lib/auth';

/**
 * «Esci»: the data the dashboard read go first, then the identity provider ends its session and the browser keeps no
 * token (ADR accesso-persistente-con-cache-msal-in-localstorage).
 */
export const SignOutButton = () => {
  const queryClient = useQueryClient();
  const signOut = useSignOut();
  const leave = () => {
    queryClient.clear();
    void signOut();
  };
  return (
    <button
      type="button"
      onClick={leave}
      className="inline-flex min-h-11 min-w-11 items-center justify-center rounded border border-slate-300 px-2 text-sm"
    >
      Esci
    </button>
  );
};
