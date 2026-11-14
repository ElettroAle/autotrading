import { useId, type ReactNode } from 'react';

import { ErrorMessage } from './error-message';

type ConfirmationDialogProps = {
  readonly title: string;
  readonly confirmLabel: string;
  /** What the operation does, said before the user confirms it. */
  readonly children: ReactNode;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
  readonly pending: boolean;
  readonly error?: Error | null;
};

/** Asks to confirm an operation that cannot be undone, saying what it will do. */
export const ConfirmationDialog = ({
  title,
  confirmLabel,
  children,
  onConfirm,
  onCancel,
  pending,
  error,
}: ConfirmationDialogProps) => {
  const titleId = useId();
  const descriptionId = useId();
  return (
    <div
      role="alertdialog"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      className="mt-2 space-y-2 rounded border border-red-200 bg-red-50 p-3"
    >
      <h3 id={titleId} className="font-semibold">
        {title}
      </h3>
      <div id={descriptionId} className="space-y-2">
        {children}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onConfirm}
          disabled={pending}
          className="rounded bg-red-700 px-3 py-1.5 text-white disabled:opacity-50"
        >
          {confirmLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded border border-slate-300 px-3 py-1.5"
        >
          Annulla
        </button>
      </div>
      {error && <ErrorMessage error={error} prefix="Operazione non riuscita" />}
    </div>
  );
};
