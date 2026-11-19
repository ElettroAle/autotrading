import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { useTradableAssets } from '@/hooks/use-tradable-assets';

import { useTrialSources } from '../api/get-trial-sources';

import { SourceTrialForm, type TrialAssets } from './source-trial-form';

const UNREADABLE_ASSETS = 'Impossibile leggere gli asset';

/**
 * The sources of the catalog, a card each, stacked at full width so the page holds on a phone; every adapter of a
 * new source appears here without code of the dashboard (ADR pagina-fonti-con-la-prova).
 */
export const SourceTrialsList = () => {
  const sources = useTrialSources();
  const tradable = useTradableAssets();
  if (sources.isPending) {
    return <Loading />;
  }
  if (sources.isError) {
    return <ErrorMessage error={sources.error} />;
  }
  if (sources.data.length === 0) {
    return <p className="text-slate-600">Nessuna fonte nel catalogo.</p>;
  }
  const assets: TrialAssets = {
    names: tradable.data ?? [],
    loading: tradable.isPending,
    unavailable: tradable.isError
      ? { prefix: UNREADABLE_ASSETS, error: tradable.error }
      : undefined,
  };
  return (
    <ul className="space-y-4">
      {sources.data.map((source) => (
        <li key={source.name}>
          <article
            aria-labelledby={`source-trial-${source.name}`}
            className="space-y-3 rounded border border-slate-200 p-4"
          >
            <header>
              <h2
                id={`source-trial-${source.name}`}
                className="text-lg font-semibold wrap-anywhere"
              >
                {source.name}
              </h2>
              <p className="text-sm text-slate-600">{source.description}</p>
            </header>
            <SourceTrialForm source={source} assets={assets} />
          </article>
        </li>
      ))}
    </ul>
  );
};
