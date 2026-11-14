import type { ReactNode } from 'react';

/** A field of a form, with its label and, below it, why its value is refused. */
export const FormField = ({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error: string | undefined;
  children: ReactNode;
}) => (
  <div className="flex flex-col gap-1">
    <label htmlFor={id} className="text-sm text-slate-700">
      {label}
    </label>
    {children}
    {error === undefined ? null : (
      <p id={`${id}-error`} className="text-sm text-red-700">
        {error}
      </p>
    )}
  </div>
);

export const FORM_CONTROL = 'rounded border border-slate-300 px-2 py-1';
