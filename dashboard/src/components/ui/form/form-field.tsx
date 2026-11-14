import type { ReactNode } from 'react';

/** What a control needs to be named by its label and described by the reason its value was refused. */
export type ControlProps = {
  readonly id: string;
  readonly 'aria-describedby'?: string;
  readonly 'aria-invalid'?: true;
};

/** The look of a control of a form. */
export const FORM_CONTROL = 'rounded border border-slate-300 px-2 py-1';

export const errorIdOf = (id: string): string => `${id}-error`;

/** The props that describe a control, or a group, by the reason its value was refused, if any. */
export const describedBy = (id: string, error: string | undefined) =>
  error === undefined ? {} : { 'aria-describedby': errorIdOf(id), 'aria-invalid': true as const };

export const FieldError = ({ id, error }: { id: string; error: string | undefined }) =>
  error === undefined ? null : (
    <p id={errorIdOf(id)} className="text-sm text-red-700">
      {error}
    </p>
  );

type FormFieldProps = {
  readonly id: string;
  readonly label: string;
  readonly error: string | undefined;
  readonly children: (control: ControlProps) => ReactNode;
};

/** A labelled control with the reason of a refusal beside it (R2.3.3). */
export const FormField = ({ id, label, error, children }: FormFieldProps) => (
  <div className="flex flex-col gap-1">
    <label htmlFor={id} className="text-sm font-medium">
      {label}
    </label>
    {children({ id, ...describedBy(id, error) })}
    <FieldError id={id} error={error} />
  </div>
);
