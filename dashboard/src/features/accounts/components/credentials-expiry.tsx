import { useState } from 'react';
import { Link } from 'react-router';

import { CommandButton } from '@/components/ui/command-button';
import { ExpiringKeysNotice, ExpiryDateForm, KeyExpiryStatus } from '@/components/ui/key-expiry';
import { paths } from '@/config/paths';

import type { Account } from '../api/get-accounts';
import { useSetAccountKeyExpiry } from '../api/set-account-key-expiry';

// A date the exchange reads is shown as read (R6.2.2).
const READ_BY = "dall'exchange";

/** The expiry of the credentials of the account, as the API reads it today (R6.2.2). */
export const CredentialsExpiryStatus = ({ account }: { readonly account: Account }) => (
  <KeyExpiryStatus expiry={account} readBy={READ_BY} />
);

/**
 * The expiry of the credentials with the command to give it, only where the exchange does not read it (R6.2.2, ADR
 * scadenza-nelle-pagine-chiavi-e-conti).
 */
export const CredentialsExpiry = ({ account }: { readonly account: Account }) => {
  const [dating, setDating] = useState(false);
  const setting = useSetAccountKeyExpiry();
  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-2">
        <CredentialsExpiryStatus account={account} />
        {account.expiry_editable && !dating && (
          <CommandButton tone="secondary" onClick={() => setDating(true)}>
            Indica scadenza
          </CommandButton>
        )}
      </div>
      {dating && (
        <ExpiryDateForm
          subject={account.name}
          current={account.expiry?.expires_on}
          pending={setting.isPending}
          error={setting.error}
          onSave={(expiresOn) =>
            setting.mutate(
              { accountId: account.id, expiresOn },
              { onSuccess: () => setDating(false) },
            )
          }
          onCancel={() => setDating(false)}
        />
      )}
    </div>
  );
};

/**
 * At the head of the page, as long as the credentials of an account expire within 30 days or expired: each account with
 * the way to the replacement of its credentials (R6.2.2, ADR scadenza-nelle-pagine-chiavi-e-conti).
 */
export const ExpiringCredentialsNotice = ({
  accounts,
}: {
  readonly accounts: readonly Account[];
}) => (
  <ExpiringKeysNotice
    keys={accounts.map((account) => ({
      name: account.name,
      expiry: account,
      renewal: (
        <Link
          to={paths.accountSettings.getHref(account.id)}
          className="text-blue-800 underline wrap-anywhere"
        >
          Sostituisci le credenziali di {account.name}
        </Link>
      ),
    }))}
  />
);
