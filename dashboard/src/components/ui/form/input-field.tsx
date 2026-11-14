import { useId, type InputHTMLAttributes, type Ref } from 'react';

import { FORM_CONTROL, FormField } from './form-field';

/** A reason of a refusal, as the form state keeps it. */
type Reason = { readonly message?: string } | undefined;

type InputFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  readonly label: string;
  readonly error?: Reason;
  readonly ref?: Ref<HTMLInputElement>;
};

/** A labelled text input of a form, with the reason of a refusal beside it (ADR 0130). */
export const InputField = ({ label, error, id, ...input }: InputFieldProps) => {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <FormField id={inputId} label={label} error={error?.message}>
      {(control) => <input {...control} className={FORM_CONTROL} {...input} />}
    </FormField>
  );
};

/** A secret: never shown while typed, never remembered by the browser (ADR 0130). */
export const SecretField = (props: Omit<InputFieldProps, 'type' | 'autoComplete'>) => (
  <InputField {...props} type="password" autoComplete="off" />
);

/** The reason of a refusal that concerns the whole form, at its head. */
export const FormAlert = ({ error }: { readonly error: Reason }) =>
  error?.message === undefined ? null : (
    <p role="alert" className="text-red-700">
      {error.message}
    </p>
  );
