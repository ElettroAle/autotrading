import type { ReactNode } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useAccounts, type Account } from '../api/get-accounts';
import { useModelCatalog, type Model, type Provider } from '../api/get-model-catalog';
import { useSources, type Source } from '../api/get-sources';
import { useDefaultSystemPrompt, type DefaultSystemPrompt } from '../api/get-system-prompt';

export type Catalogs = {
  readonly accounts: Account[];
  readonly models: Model[];
  readonly providers: Provider[];
  readonly sources: Source[];
  readonly systemPrompt: DefaultSystemPrompt;
};

/**
 * The choices of a configuration, all from the API: accounts, models, sources and the default system prompt with its
 * placeholders (R1.3.1, R1.4.2, R1.4.8).
 */
export const WithCatalogs = ({ children }: { children: (catalogs: Catalogs) => ReactNode }) => {
  const accounts = useAccounts();
  const models = useModelCatalog();
  const sources = useSources();
  const systemPrompt = useDefaultSystemPrompt();
  const failed = accounts.error ?? models.error ?? sources.error ?? systemPrompt.error;
  if (failed !== null) {
    return <ErrorMessage error={failed} />;
  }
  if (
    accounts.data === undefined ||
    models.data === undefined ||
    sources.data === undefined ||
    systemPrompt.data === undefined
  ) {
    return <Loading />;
  }
  return children({
    accounts: accounts.data,
    models: models.data.models,
    providers: models.data.providers,
    sources: sources.data,
    systemPrompt: systemPrompt.data,
  });
};
