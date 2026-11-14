import { useState, type KeyboardEvent, type Ref } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';
import { useTradableAssets } from '@/hooks/use-tradable-assets';

import { FORM_CONTROL, FormField } from './form-field';

const matchesOf = (tradable: readonly string[], chosen: readonly string[], search: string) => {
  const wanted = search.trim().toUpperCase();
  return wanted === ''
    ? []
    : tradable.filter((asset) => !chosen.includes(asset) && asset.toUpperCase().includes(wanted));
};

// Enter picks the asset typed in full, or the only one left: it never sends the form from here.
const pickedBy = (matches: readonly string[], search: string): string | undefined =>
  matches.find((asset) => asset.toUpperCase() === search.trim().toUpperCase()) ??
  (matches.length === 1 ? matches[0] : undefined);

type AssetPickerProps = {
  readonly id: string;
  readonly chosen: readonly string[];
  readonly onChange: (assets: string[]) => void;
  /** The reason the API or the form refused the assets, shown beside the field. */
  readonly error: string | undefined;
  readonly onBlur?: () => void;
  readonly inputRef?: Ref<HTMLInputElement>;
};

/**
 * The assets of a flow, chosen among those the API says the exchange trades now: typing filters the list, each
 * chosen asset is a label the user can remove. No list of assets lives in the dashboard (ADR 0147).
 */
export const AssetPicker = ({
  id,
  chosen,
  onChange,
  error,
  onBlur,
  inputRef,
}: AssetPickerProps) => {
  const tradable = useTradableAssets();
  const [search, setSearch] = useState('');
  const matches = matchesOf(tradable.data ?? [], chosen, search);
  const offeredId = `${id}-offered`;

  const choose = (asset: string) => {
    onChange([...chosen, asset]);
    setSearch('');
  };
  const remove = (asset: string) => onChange(chosen.filter((other) => other !== asset));
  const pickOnEnter = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Enter') {
      return;
    }
    event.preventDefault();
    const picked = pickedBy(matches, search);
    if (picked !== undefined) {
      choose(picked);
    }
  };

  return (
    <FormField id={id} label="Asset" error={error}>
      {(control) => (
        <div className="min-w-0 space-y-2">
          {chosen.length > 0 && (
            <ul aria-label="Asset scelti" className="flex min-w-0 flex-wrap gap-2">
              {chosen.map((asset) => (
                <li
                  key={asset}
                  className="flex max-w-full items-center gap-1 rounded bg-slate-100 px-2 py-0.5"
                >
                  <span className="truncate">{asset}</span>
                  <button
                    type="button"
                    aria-label={`Togli ${asset}`}
                    onClick={() => remove(asset)}
                    className="px-1 text-slate-600 hover:text-red-700"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
          <input
            {...control}
            type="search"
            ref={inputRef}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onBlur={onBlur}
            onKeyDown={pickOnEnter}
            disabled={tradable.isError}
            autoComplete="off"
            placeholder="Cerca un asset"
            aria-controls={offeredId}
            className={FORM_CONTROL}
          />
          {tradable.isError && (
            <ErrorMessage
              error={tradable.error}
              prefix="Impossibile leggere gli asset negoziabili"
            />
          )}
          {matches.length > 0 && (
            <ul
              id={offeredId}
              aria-label="Asset negoziabili"
              className="max-h-48 min-w-0 overflow-y-auto rounded border border-slate-200"
            >
              {matches.map((asset) => (
                <li key={asset}>
                  <button
                    type="button"
                    onClick={() => choose(asset)}
                    className="w-full truncate px-2 py-1 text-left hover:bg-slate-100"
                  >
                    {asset}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </FormField>
  );
};
