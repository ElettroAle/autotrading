import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { Card } from '@/components/ui/card';
import { CommandButton } from '@/components/ui/command-button';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { FormAlert, InputField } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';

import type { Account } from '../api/get-accounts';
import {
  useResetVirtualBalance,
  virtualBalanceInputSchema,
  type VirtualBalanceInput,
} from '../api/reset-virtual-balance';
import { ACCOUNT_SETTING_INFO } from '../utils/setting-info';

// The name the API gives to the field of the request, as its refusals report it.
const BALANCE = 'balance';
const RESET = 'Azzera il conto';

/**
 * The virtual balance of an account of the simulated exchange, which the user starts the account again from once the
 * reset is confirmed: it closes the open positions and cancels the orders (R6.3.2).
 */
export const VirtualBalanceForm = ({ account }: { readonly account: Account }) => {
  const reset = useResetVirtualBalance(account.id);
  const [asked, setAsked] = useState<VirtualBalanceInput | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<VirtualBalanceInput>({
    resolver: zodResolver(virtualBalanceInputSchema),
    defaultValues: { balance: '' },
  });

  const onSubmit = handleSubmit((input) => {
    setDone(null);
    setAsked(input);
  });

  const confirm = (input: VirtualBalanceInput) =>
    reset.mutate(input, {
      onSuccess: () => setDone(input.balance.trim()),
      onError: (error) =>
        showRefusal(error, setError, (field) => (field === BALANCE ? BALANCE : undefined)),
      onSettled: () => setAsked(null),
    });

  return (
    <Card
      as="section"
      aria-label={`Saldo virtuale del conto ${account.name}`}
      className="space-y-2"
    >
      <h2 className="text-lg font-semibold">Saldo virtuale</h2>
      <form onSubmit={(event) => void onSubmit(event)} noValidate className="space-y-3">
        <FormAlert error={errors.root?.server} />
        <InputField
          label={`Nuovo saldo virtuale (${account.currency})`}
          info={ACCOUNT_SETTING_INFO.newVirtualBalance}
          inputMode="decimal"
          error={errors.balance}
          {...register(BALANCE)}
        />
        <CommandButton tone="secondary" type="submit" disabled={asked !== null}>
          {RESET}
        </CommandButton>
      </form>
      {asked !== null && (
        <ConfirmationDialog
          title="Azzeramento del conto"
          confirmLabel={RESET}
          onConfirm={() => confirm(asked)}
          onCancel={() => setAsked(null)}
          pending={reset.isPending}
        >
          <p>
            Le posizioni aperte del conto si chiudono, gli ordini si cancellano e il conto riparte
            da {asked.balance.trim()} {account.currency}
          </p>
        </ConfirmationDialog>
      )}
      {done !== null && (
        <p role="status" className="text-green-800">
          Conto {account.name} azzerato con saldo {done} {account.currency}
        </p>
      )}
    </Card>
  );
};
