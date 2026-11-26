import { useId, type InputHTMLAttributes, type Ref } from 'react';

import { LabelRow } from './form-field';

type CheckboxFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  readonly label: string;
  /** The text of the info button of the option (R5.5.7). */
  readonly info: string;
  /** The line under the option that says what it adds, which describes the box. */
  readonly hint?: string;
  readonly ref?: Ref<HTMLInputElement>;
};

/**
 * An option of a form: the box inside its label, the info button beside the label and, under it, the line that says
 * what the option adds (R5.5.7, ADR informazioni-sui-campi-di-configurazione).
 */
export const CheckboxField = ({ label, info, hint, id, ...input }: CheckboxFieldProps) => {
  const generatedId = useId();
  const boxId = id ?? generatedId;
  const hintId = `${boxId}-hint`;
  return (
    <div className="min-w-0 space-y-1">
      <LabelRow label={label} info={info}>
        <label className="flex items-center gap-2">
          <input
            id={boxId}
            type="checkbox"
            {...(hint === undefined ? {} : { 'aria-describedby': hintId })}
            {...input}
          />
          {label}
        </label>
      </LabelRow>
      {hint !== undefined && (
        <p id={hintId} className="text-xs text-slate-600">
          {hint}
        </p>
      )}
    </div>
  );
};
