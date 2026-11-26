import type { ReactNode } from 'react';

import { InfoButton } from '@/components/ui/info-button';

/** What a control needs to be named by its label and described by the reason its value was refused. */
export type ControlProps = {
  readonly id: string;
  readonly 'aria-describedby'?: string;
  readonly 'aria-invalid'?: true;
};

const CONTROL_LOOK = 'w-full max-w-full min-w-0 rounded border border-slate-300 px-2 py-1';

/** The look of a control of a form: as wide as the form, never wider, a long value cut short (ADR 0146). */
export const FORM_CONTROL = `${CONTROL_LOOK} truncate`;

/** The look of a control of a form that holds lines of text: as wide as the form, never wider (ADR 0146). */
export const FORM_TEXT_AREA = CONTROL_LOOK;

export const errorIdOf = (id: string): string => `${id}-error`;

const hintIdOf = (id: string): string => `${id}-hint`;

/** The props that describe a control, or a group, by the reason its value was refused, if any. */
export const describedBy = (id: string, error: string | undefined) =>
  error === undefined ? {} : { 'aria-describedby': errorIdOf(id), 'aria-invalid': true as const };

export const FieldError = ({ id, error }: { id: string; error: string | undefined }) =>
  error === undefined ? null : (
    <p id={errorIdOf(id)} className="text-sm text-red-700">
      {error}
    </p>
  );

/**
 * The label of a field with its info button beside it, the text of the button on a line of its own below (R5.5.7,
 * ADR informazioni-sui-campi-di-configurazione): the label itself goes in as children, so a checkbox keeps its own.
 */
export const LabelRow = ({
  label,
  info,
  children,
}: {
  readonly label: string;
  readonly info: string;
  readonly children: ReactNode;
}) => (
  <div className="flex min-w-0 flex-wrap items-center gap-1">
    {children}
    <InfoButton label={label} text={info} />
  </div>
);

type FormFieldProps = {
  readonly id: string;
  readonly label: string;
  /** What the field does, the values it admits, its default or what leaving it empty means: never missing (R5.5.7). */
  readonly info: string;
  readonly error: string | undefined;
  // What the control admits, when its label alone does not say it (ADR parametri-delle-fonti-come-liste-libere).
  readonly hint?: string;
  readonly children: (control: ControlProps) => ReactNode;
};

const controlOf = (
  id: string,
  error: string | undefined,
  hint: string | undefined,
): ControlProps => {
  const described = [
    hint === undefined ? '' : hintIdOf(id),
    error === undefined ? '' : errorIdOf(id),
  ]
    .filter((each) => each !== '')
    .join(' ');
  return {
    id,
    ...(described === '' ? {} : { 'aria-describedby': described }),
    ...(error === undefined ? {} : { 'aria-invalid': true as const }),
  };
};

/** A labelled control with its info button, what it admits and the reason of a refusal beside it (R2.3.3, R5.5.7). */
export const FormField = ({ id, label, info, error, hint, children }: FormFieldProps) => (
  <div className="flex min-w-0 flex-col gap-1">
    <LabelRow label={label} info={info}>
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
    </LabelRow>
    {children(controlOf(id, error, hint))}
    {hint !== undefined && (
      <p id={hintIdOf(id)} className="text-xs text-slate-600">
        {hint}
      </p>
    )}
    <FieldError id={id} error={error} />
  </div>
);
