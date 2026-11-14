import { useState } from 'react';

import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { ApiError } from '@/lib/api-client';

import type { Account } from '../api/get-accounts';
import { useRemoveAccount } from '../api/remove-account';

const CONFLICT = 409;

type RemoveAccountProps = { readonly account: Account; readonly onCancel: () => void };

/**
 * The removal of an account, in the two steps of the API (ADR 0130): the first request goes unconfirmed; when the API
 * refuses it for the flows or the positions of the account, the window tells its reason and the confirmation repeats
 * the request confirmed.
 */
export const RemoveAccount = ({ account, onCancel }: RemoveAccountProps) => {
  const removal = useRemoveAccount();
  const [reasonToConfirm, setReasonToConfirm] = useState<string | null>(null);

  const remove = () => {
    removal.mutate(
      { accountId: account.id, confirmed: reasonToConfirm !== null },
      {
        onError: (error) => {
          if (error instanceof ApiError && error.status === CONFLICT && reasonToConfirm === null) {
            setReasonToConfirm(error.message);
            removal.reset();
          }
        },
      },
    );
  };

  return (
    <ConfirmationDialog
      confirmLabel="Conferma la rimozione"
      title={`Rimozione del conto ${account.name}`}
      onConfirm={remove}
      onCancel={onCancel}
      pending={removal.isPending}
      error={removal.error}
    >
      {reasonToConfirm ??
        `Il conto ${account.name} sarà rimosso: le sue credenziali vengono cancellate, lo storico resta consultabile.`}
    </ConfirmationDialog>
  );
};
