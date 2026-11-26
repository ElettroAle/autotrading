import { useId, type InputHTMLAttributes, type Ref } from 'react';

import { FORM_CONTROL, FormField } from './form-field';

/** A reason of a refusal, as the form state keeps it. */
type Reason = { readonly message?: string } | undefined;

type InputFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  readonly label: string;
  /** The text of the info button of the field (R5.5.7). */
  readonly info: string;
  readonly error?: Reason;
  readonly hint?: string;
  readonly ref?: Ref<HTMLInputElement>;
};

/** A labelled text input of a form, with the reason of a refusal beside it (ADR 0130). */
export const InputField = ({ label, info, error, hint, id, ...input }: InputFieldProps) => {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <FormField id={inputId} label={label} info={info} error={error?.message} hint={hint}>
      {(control) => <input {...control} className={FORM_CONTROL} {...input} />}
    </FormField>
  );
};

/**
 * Keeps the best-known password managers from filling an input: on a password input they ignore `autocomplete="off"`
 * and may put a saved password where a key was pasted (Bug 387).
 */
export const NOT_FOR_PASSWORD_MANAGERS = {
  'data-lpignore': 'true',
  'data-1p-ignore': 'true',
  'data-bwignore': 'true',
} as const;

/**
 * A secret: never shown while typed, never filled or remembered by the browser, which honours `new-password` where it
 * ignores `off` (ADR 0130, Bug 387).
 */
export const SecretField = (props: Omit<InputFieldProps, 'type' | 'autoComplete'>) => (
  <InputField
    {...props}
    {...NOT_FOR_PASSWORD_MANAGERS}
    type="password"
    autoComplete="new-password"
  />
);

/** The reason of a refusal that concerns the whole form, at its head. */
export const FormAlert = ({ error }: { readonly error: Reason }) =>
  error?.message === undefined ? null : (
    <p role="alert" className="text-red-700">
      {error.message}
    </p>
  );
