import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { PRIMARY_COMMAND, SECONDARY_COMMAND } from '@/components/ui/commands';
import { FormAlert, InputField } from '@/components/ui/form/input-field';
import { showRefusal } from '@/lib/form-errors';
import { formatAmount } from '@/utils/format-amount';

import type { Account } from '../api/get-accounts';
import {
  thresholdInputSchema,
  useSetDeviationThreshold,
  type ThresholdInput,
} from '../api/set-deviation-threshold';

// The name the API gives to the field of the request, as its refusals report it.
const PERCENT = 'percent';

type DeviationThresholdFormProps = {
  readonly account: Account;
  /** The threshold in force, as the API writes it. */
  readonly threshold: string;
  readonly onSaved: () => void;
  readonly onCancel: () => void;
};

/** The threshold of the balance deviation of the account; the API checks its range and says why it refuses it. */
export const DeviationThresholdForm = ({
  account,
  threshold,
  onSaved,
  onCancel,
}: DeviationThresholdFormProps) => {
  const setThreshold = useSetDeviationThreshold(account.id);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<ThresholdInput>({
    resolver: zodResolver(thresholdInputSchema),
    defaultValues: { percent: formatAmount(threshold) },
  });

  const onSubmit = handleSubmit((input) =>
    setThreshold.mutate(input, {
      onSuccess: onSaved,
      onError: (error) =>
        showRefusal(error, setError, (field) => (field === PERCENT ? PERCENT : undefined)),
    }),
  );

  return (
    <form
      aria-label={`Soglia di scostamento del conto ${account.name}`}
      onSubmit={(event) => void onSubmit(event)}
      noValidate
      className="space-y-3"
    >
      <FormAlert error={errors.root?.server} />
      <InputField
        label="Soglia di scostamento (%)"
        inputMode="decimal"
        error={errors.percent}
        {...register('percent')}
      />
      <div className="flex gap-2">
        <button type="submit" disabled={setThreshold.isPending} className={PRIMARY_COMMAND}>
          Salva la soglia
        </button>
        <button type="button" onClick={onCancel} className={SECONDARY_COMMAND}>
          Annulla
        </button>
      </div>
    </form>
  );
};
