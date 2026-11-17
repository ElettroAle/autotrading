import { useQueryClient } from '@tanstack/react-query';

import { useSignOut } from '@/lib/auth';

/**
 * «Esci», the item of the menu of the user (ADR area-utente-in-alto-a-destra): the data the dashboard read go first,
 * then the identity provider ends its session and the browser keeps no token (ADR
 * accesso-persistente-con-cache-msal-in-localstorage).
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
      role="menuitem"
      onClick={leave}
      className="inline-flex min-h-11 w-full min-w-11 items-center rounded px-3 text-left text-sm hover:bg-slate-100 focus:bg-slate-100"
    >
      Esci
    </button>
  );
};
