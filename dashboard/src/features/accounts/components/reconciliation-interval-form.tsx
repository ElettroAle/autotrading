import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { Card } from '@/components/ui/card';
import { CommandButton } from '@/components/ui/command-button';
import { FormAlert, InputField } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';

import type { Account } from '../api/get-accounts';
import {
  intervalInputSchema,
  useSetReconciliationInterval,
  type IntervalInput,
} from '../api/set-reconciliation-interval';
import { ACCOUNT_SETTING_INFO } from '../utils/setting-info';

// The name the API gives to the field of the request, as its refusals report it.
const MINUTES = 'minutes';

/**
 * How often the periodic check reconciles the account while its flows hold open positions, starting from the interval
 * in force, the default included; the API checks it and its reason stays at the head of the form (Bug 778, ADR
 * intervallo-di-riconciliazione-del-conto).
 */
export const ReconciliationIntervalForm = ({ account }: { readonly account: Account }) => {
  const setInterval = useSetReconciliationInterval(account.id);
  const [saved, setSaved] = useState<number | undefined>(undefined);
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors },
  } = useForm<IntervalInput>({
    resolver: zodResolver(intervalInputSchema),
    defaultValues: { minutes: String(account.reconciliation_interval_minutes) },
  });

  const onSubmit = handleSubmit((input) => {
    const minutes = Number(input.minutes);
    setInterval.mutate(minutes, {
      onSuccess: () => {
        reset({ minutes: String(minutes) });
        setSaved(minutes);
      },
      onError: (error) =>
        showRefusal(error, setError, (field) => (field === MINUTES ? MINUTES : undefined)),
    });
  });

  return (
    <Card
      as="section"
      aria-label={`Riconciliazione periodica del conto ${account.name}`}
      className="space-y-2"
    >
      <h2 className="text-lg font-semibold">Riconciliazione periodica</h2>
      <form onSubmit={(event) => void onSubmit(event)} noValidate className="space-y-3">
        <InputField
          label="Intervallo di riconciliazione (minuti)"
          info={ACCOUNT_SETTING_INFO.reconciliationInterval}
          inputMode="numeric"
          error={errors.minutes}
          {...register(MINUTES)}
        />
        <FormAlert error={errors.root?.server} />
        <CommandButton tone="primary" type="submit" disabled={setInterval.isPending}>
          Salva l&apos;intervallo
        </CommandButton>
      </form>
      {saved !== undefined && (
        <p role="status" className="text-green-800">
          Intervallo di riconciliazione: {saved} minuti
        </p>
      )}
    </Card>
  );
};
