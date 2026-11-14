const STYLE_BY_ENVIRONMENT: Readonly<Record<string, string>> = {
  prod: 'bg-red-700 text-white',
};
const OTHER_ENVIRONMENT = 'bg-amber-300 text-amber-950';

/** The installation is always recognisable, on every page (R0.1.4). */
export const EnvironmentBadge = ({ environment }: { environment: string }) => (
  <p
    aria-label="Ambiente dell'installazione"
    className={`rounded px-2 py-1 text-sm font-semibold uppercase ${STYLE_BY_ENVIRONMENT[environment] ?? OTHER_ENVIRONMENT}`}
  >
    {environment}
  </p>
);
