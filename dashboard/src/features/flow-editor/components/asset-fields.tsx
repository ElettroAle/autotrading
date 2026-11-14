import { useState, type KeyboardEvent } from 'react';
import { useController, useFormContext } from 'react-hook-form';

import { ErrorMessage } from '@/components/ui/error-message';
import { FORM_CONTROL, FormField } from '@/components/ui/form/form-field';

import { useTradableAssets } from '../api/get-tradable-assets';
import type { FlowFormValues } from '../utils/flow-form';

const ID = 'flow-assets';
const OFFERED_ID = `${ID}-offered`;

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

/**
 * The assets of the flow, chosen among those the API says the exchange trades now: typing filters the list, each
 * chosen asset is a label the user can remove. No list of assets lives in the dashboard (ADR 0147).
 */
export const AssetFields = () => {
  const {
    control,
    formState: { errors },
  } = useFormContext<FlowFormValues>();
  const { field } = useController({ control, name: 'assets' });
  const tradable = useTradableAssets();
  const [search, setSearch] = useState('');
  const chosen = field.value;
  const matches = matchesOf(tradable.data ?? [], chosen, search);

  const choose = (asset: string) => {
    field.onChange([...chosen, asset]);
    setSearch('');
  };
  const remove = (asset: string) => field.onChange(chosen.filter((other) => other !== asset));
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
    <FormField id={ID} label="Asset" error={errors.assets?.message}>
      {(props) => (
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
            {...props}
            type="search"
            ref={field.ref}
            name={field.name}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onBlur={field.onBlur}
            onKeyDown={pickOnEnter}
            disabled={tradable.isError}
            autoComplete="off"
            placeholder="Cerca un asset"
            aria-controls={OFFERED_ID}
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
              id={OFFERED_ID}
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
