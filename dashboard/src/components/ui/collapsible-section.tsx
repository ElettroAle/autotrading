import { useId, type ReactNode } from 'react';

/**
 * A section the user can close and reopen (ADR 0129): open when it is part of what the page is for, closed when it is
 * a detail read on demand.
 */
export const CollapsibleSection = ({
  title,
  open = true,
  children,
}: {
  title: string;
  open?: boolean;
  children: ReactNode;
}) => {
  const titleId = useId();
  return (
    <details
      open={open}
      aria-labelledby={titleId}
      className="rounded border border-slate-200 bg-white"
    >
      <summary id={titleId} className="cursor-pointer px-4 py-2 font-semibold">
        {title}
      </summary>
      <div className="space-y-3 border-t border-slate-200 px-4 py-3">{children}</div>
    </details>
  );
};
