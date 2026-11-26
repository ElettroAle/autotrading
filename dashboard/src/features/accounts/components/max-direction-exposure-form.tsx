import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { Card } from '@/components/ui/card';
import { CommandButton } from '@/components/ui/command-button';
import { FormAlert, InputField } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';
import { formatAmount } from '@/utils/format-amount';

import type { Account } from '../api/get-accounts';
import {
  exposureLimitInputSchema,
  exposureLimitOf,
  useSetMaxDirectionExposure,
  type ExposureLimitInput,
} from '../api/set-max-direction-exposure';

// The name the API gives to the field of the request, as its refusals report it.
const PERCENT = 'percent';

const HINT =
  'vuoto: nessun limite; somma separatamente il valore long e short delle posizioni di tutti i flussi del conto, in percento del saldo';

const savedText = (percent: string | null): string =>
  percent === null ? 'Limite tolto' : `Limite impostato: ${formatAmount(percent)}% del saldo`;

/**
 * The limit of the exposure of the flows of the account on one side, empty allowed, with the commands to set it and to
 * take it away; the API checks it and its reason stays under the field (R5.5.5, ADR
 * esposizione-del-conto-nella-dashboard).
 */
export const MaxDirectionExposureForm = ({ account }: { readonly account: Account }) => {
  const setLimit = useSetMaxDirectionExposure(account.id);
  const [saved, setSaved] = useState<string | null | undefined>(undefined);
  const inForce = account.max_direction_exposure_percent;
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors },
  } = useForm<ExposureLimitInput>({
    resolver: zodResolver(exposureLimitInputSchema),
    defaultValues: { percent: inForce === null ? '' : formatAmount(inForce) },
  });

  const save = (percent: string | null) =>
    setLimit.mutate(percent, {
      onSuccess: () => {
        reset({ percent: percent === null ? '' : formatAmount(percent) });
        setSaved(percent);
      },
      onError: (error) =>
        showRefusal(error, setError, (field) => (field === PERCENT ? PERCENT : undefined)),
    });

  const onSubmit = handleSubmit((input) => save(exposureLimitOf(input)));

  return (
    <Card
      as="section"
      aria-label={`Esposizione per direzione del conto ${account.name}`}
      className="space-y-2"
    >
      <h2 className="text-lg font-semibold">Esposizione per direzione</h2>
      <form onSubmit={(event) => void onSubmit(event)} noValidate className="space-y-3">
        <InputField
          label="Esposizione massima per direzione (% del saldo)"
          inputMode="decimal"
          hint={HINT}
          error={errors.percent}
          {...register(PERCENT)}
        />
        <FormAlert error={errors.root?.server} />
        <div className="flex gap-2">
          <CommandButton tone="primary" type="submit" disabled={setLimit.isPending}>
            Imposta il limite
          </CommandButton>
          {inForce !== null && (
            <CommandButton
              tone="secondary"
              disabled={setLimit.isPending}
              onClick={() => save(null)}
            >
              Togli il limite
            </CommandButton>
          )}
        </div>
      </form>
      {saved !== undefined && (
        <p role="status" className="text-green-800">
          {savedText(saved)}
        </p>
      )}
    </Card>
  );
};
