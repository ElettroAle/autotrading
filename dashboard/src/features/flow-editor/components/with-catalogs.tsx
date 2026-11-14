import type { ReactNode } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useAccounts, type Account } from '../api/get-accounts';
import { useModelCatalog, type Model } from '../api/get-model-catalog';
import { useSources, type Source } from '../api/get-sources';

export type Catalogs = {
  readonly accounts: Account[];
  readonly models: Model[];
  readonly sources: Source[];
};

/** The choices of a configuration, all from the API: accounts, models and sources (R1.3.1, R1.4.2). */
export const WithCatalogs = ({ children }: { children: (catalogs: Catalogs) => ReactNode }) => {
  const accounts = useAccounts();
  const models = useModelCatalog();
  const sources = useSources();
  const failed = accounts.error ?? models.error ?? sources.error;
  if (failed !== null) {
    return <ErrorMessage error={failed} />;
  }
  if (accounts.data === undefined || models.data === undefined || sources.data === undefined) {
    return <Loading />;
  }
  return children({ accounts: accounts.data, models: models.data.models, sources: sources.data });
};
