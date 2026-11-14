import { useId, type ReactNode } from 'react';

/** A section of the detail of a cycle the user can close and reopen (ADR 0129). */
export const CycleSection = ({ title, children }: { title: string; children: ReactNode }) => {
  const titleId = useId();
  return (
    <details open aria-labelledby={titleId} className="rounded border border-slate-200 bg-white">
      <summary id={titleId} className="cursor-pointer px-4 py-2 font-semibold">
        {title}
      </summary>
      <div className="space-y-3 border-t border-slate-200 px-4 py-3">{children}</div>
    </details>
  );
};
