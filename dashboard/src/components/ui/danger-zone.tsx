import type { ReactNode } from 'react';

const TITLE = 'Zona di emergenza';

/**
 * The box at the bottom of a page that holds only its emergency commands, away from the commands of every day, so
 * that none is touched by mistake (ADR zona-di-emergenza-in-fondo-alla-pagina).
 */
export const DangerZone = ({ children }: { readonly children: ReactNode }) => (
  <section aria-label={TITLE} className="mt-12 rounded border-2 border-red-300 bg-white p-4">
    <h2 className="mb-3 text-lg font-semibold text-red-800">{TITLE}</h2>
    <div className="flex flex-wrap gap-4">{children}</div>
  </section>
);
