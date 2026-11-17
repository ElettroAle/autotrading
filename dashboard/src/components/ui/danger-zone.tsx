import type { ReactNode } from 'react';

type DangerZoneProps = {
  /** «Zona pericolosa» where the zone holds more than the emergency closing, as in the settings of a flow (Bug 560). */
  readonly title?: string;
  readonly children: ReactNode;
};

/**
 * The box at the bottom of a page that holds only its emergency commands, away from the commands of every day, so
 * that none is touched by mistake (ADR zona-di-emergenza-in-fondo-alla-pagina).
 */
export const DangerZone = ({ title = 'Zona di emergenza', children }: DangerZoneProps) => (
  <section aria-label={title} className="mt-12 rounded border-2 border-red-300 bg-white p-4">
    <h2 className="mb-3 text-lg font-semibold text-red-800">{title}</h2>
    <div className="flex flex-wrap gap-4">{children}</div>
  </section>
);
