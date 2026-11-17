import { useId, type ReactNode } from 'react';

import { CommandButton } from './command-button';
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
        <CommandButton tone="stop" onClick={onConfirm} disabled={pending}>
          {confirmLabel}
        </CommandButton>
        <CommandButton tone="secondary" onClick={onCancel}>
          Annulla
        </CommandButton>
      </div>
      {error && <ErrorMessage error={error} prefix="Operazione non riuscita" />}
    </div>
  );
};
