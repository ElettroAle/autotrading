import { useId, type Ref, type SelectHTMLAttributes } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';

import { FORM_CONTROL, FormField } from './form-field';

/** An option of the list: one that cannot be chosen says why in its note. */
export type SelectOption = {
  readonly value: string;
  readonly label: string;
  readonly disabled?: boolean;
  readonly note?: string;
};

/** Options shown together under the label of their group. */
export type SelectOptionGroup = {
  readonly label: string;
  readonly options: readonly SelectOption[];
};

export type SelectChoice = SelectOption | SelectOptionGroup;

/** What failed reading the list, and why: the field cannot be used without it. */
export type UnavailableList = { readonly prefix: string; readonly error: Error };

/** A reason of a refusal, as the form state keeps it. */
type Reason = { readonly message?: string } | undefined;

type SelectFieldProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> & {
  readonly label: string;
  /** The text of the info button of the field (R5.5.7). */
  readonly info: string;
  /** The first option, which leaves the field empty. */
  readonly placeholder: string;
  readonly choices: readonly SelectChoice[];
  readonly error?: Reason;
  readonly loading?: boolean;
  readonly unavailable?: UnavailableList | undefined;
  readonly ref?: Ref<HTMLSelectElement>;
};

const textOf = ({ label, note }: SelectOption): string =>
  note === undefined ? label : `${label} · ${note}`;

const OptionOf = ({ option }: { readonly option: SelectOption }) => (
  <option value={option.value} disabled={option.disabled}>
    {textOf(option)}
  </option>
);

const isGroup = (choice: SelectChoice): choice is SelectOptionGroup => 'options' in choice;

/**
 * A single choice from a list the API gives, as a native drop-down that suits a phone (ADR 0153): while the list is
 * read, or once it could not be read, the field cannot be used and the form waits for it.
 */
export const SelectField = ({
  label,
  info,
  placeholder,
  choices,
  error,
  loading = false,
  unavailable,
  id,
  disabled = false,
  ...select
}: SelectFieldProps) => {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  return (
    <FormField id={selectId} label={label} info={info} error={error?.message}>
      {(control) => (
        <>
          <select
            {...control}
            className={FORM_CONTROL}
            {...select}
            disabled={disabled || loading || unavailable !== undefined}
          >
            <option value="">{loading ? 'Caricamento…' : placeholder}</option>
            {choices.map((choice) =>
              isGroup(choice) ? (
                <optgroup key={choice.label} label={choice.label}>
                  {choice.options.map((option) => (
                    <OptionOf key={option.value} option={option} />
                  ))}
                </optgroup>
              ) : (
                <OptionOf key={choice.value} option={choice} />
              ),
            )}
          </select>
          {unavailable !== undefined && (
            <ErrorMessage error={unavailable.error} prefix={unavailable.prefix} />
          )}
        </>
      )}
    </FormField>
  );
};
