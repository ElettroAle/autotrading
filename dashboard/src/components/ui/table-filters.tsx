import { useTableFilters, type TableFilter } from '@/hooks/use-table-filters';

export type TableFiltering = {
  readonly filters: readonly TableFilter[];
  /** How many rows match the filters in all, as the API counts them across its pages. */
  readonly total: number;
  /** The count in words, «2 cicli». */
  readonly countOf: (total: number) => string;
};

type TableFiltersProps = TableFiltering & { readonly label: string };

// A quick choice is as tall as a finger needs (ADR viste-e-comandi-della-pagina-del-flusso).
const CHOICE = 'min-h-11 rounded-full border px-3 text-sm';
const PRESSED = 'border-blue-800 bg-blue-800 text-white';
const RELEASED = 'border-slate-300 bg-white text-slate-800 hover:bg-slate-100';

type ChoiceProps = {
  readonly label: string;
  readonly pressed: boolean;
  readonly onPress: () => void;
};

const Choice = ({ label, pressed, onPress }: ChoiceProps) => (
  <button
    type="button"
    aria-pressed={pressed}
    className={`${CHOICE} ${pressed ? PRESSED : RELEASED}`}
    onClick={onPress}
  >
    {label}
  </button>
);

/**
 * The filters a table declares, above it: each a row of quick choices, with the number of results and the command
 * that clears them; the choices live in the address (R6.4.4, ADR tabella-condivisa-senza-sforamento-e-con-filtri).
 */
export const TableFilters = ({ label, filters, total, countOf }: TableFiltersProps) => {
  const { values, choose, reset } = useTableFilters(filters);
  const chosen = Object.keys(values).length > 0;
  return (
    <div role="group" aria-label={`Filtri di ${label}`} className="mb-3 flex flex-col gap-2">
      {filters.map((filter) => (
        <fieldset key={filter.name} className="flex flex-wrap items-center gap-2">
          <legend className="float-left mr-1 text-sm font-medium text-slate-600">
            {filter.label}
          </legend>
          <Choice
            label={filter.all}
            pressed={values[filter.name] === undefined}
            onPress={() => choose(filter.name, undefined)}
          />
          {filter.options.map((option) => (
            <Choice
              key={option.value}
              label={option.label}
              pressed={values[filter.name] === option.value}
              onPress={() => choose(filter.name, option.value)}
            />
          ))}
        </fieldset>
      ))}
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <p aria-live="polite" className="text-slate-600">
          {countOf(total)}
        </p>
        {chosen && (
          <button type="button" className="min-h-11 text-blue-800 hover:underline" onClick={reset}>
            Azzera i filtri
          </button>
        )}
      </div>
    </div>
  );
};
