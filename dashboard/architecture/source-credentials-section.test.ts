// ADR sezione-fonti-nella-pagina-chiavi (R4.1.2): the credentials of the adapters of the sources are the feature
// source-credentials, apart from the keys of the AI providers; the route of the page of the keys shows its section «Fonti»
// under those keys; the section grows from the shared components (commands, confirmation, expiry, declared fields) and
// draws no button and no input of its own; the editor of the flow shows the reason the API gives, without reading it.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCE = fileURLToPath(new URL('../src', import.meta.url));
const FEATURE = join(SOURCE, 'features', 'source-credentials');
const ROUTE = join(SOURCE, 'app', 'routes', 'app', 'provider-keys.tsx');
const EDITOR = join(SOURCE, 'features', 'flow-editor');

const SHARED = [
  "from '@/components/ui/command-button'",
  "from '@/components/ui/confirmation-dialog'",
  "from '@/components/ui/key-expiry'",
  "from '@/components/ui/form/declared-fields'",
] as const;

const filesOf = (folder: string): string[] =>
  readdirSync(folder, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? filesOf(join(folder, entry.name)) : [join(folder, entry.name)],
  );

const productionOf = (folder: string): string =>
  filesOf(folder)
    .filter((path) => !/\.test\.tsx?$/.test(path))
    .map((path) => readFileSync(path, 'utf8'))
    .join('\n');

/** What the feature of the section breaks of the decision. */
const featureBreaches = (source: string): string[] => [
  ...(source.includes('@/features/provider-keys')
    ? ['la funzionalità importa quella delle chiavi dei fornitori IA']
    : []),
  ...SHARED.filter((shared) => !source.includes(shared)).map(
    (shared) => `la sezione non usa il componente condiviso ${shared}`,
  ),
  ...(/<button|<input/.test(source) ? ['la sezione disegna comandi o campi propri'] : []),
];

/** What the route of the page of the keys breaks: the section «Fonti» under the keys of the AI providers. */
const routeBreaches = (source: string): string[] => {
  const keys = source.indexOf('<ProviderKeysList />');
  const sources = source.indexOf('<SourceCredentialsSection />');
  if (sources === -1) {
    return ['la pagina delle chiavi non mostra la sezione Fonti'];
  }
  return keys === -1 || sources < keys
    ? ['la sezione Fonti non sta sotto le chiavi dei fornitori IA']
    : [];
};

const CONFORMING_FEATURE =
  SHARED.join(';\n') + '\n<CommandButton tone="secondary">Configura</CommandButton>';
const CONFORMING_ROUTE =
  '<ProviderKeysList />\n<RegisterProviderKeyForm />\n<SourceCredentialsSection />';

describe('ADR sezione-fonti-nella-pagina-chiavi: the section Fonti of the page of the keys', () => {
  it('is red when the section draws its own button and reads the keys of the AI providers', () => {
    expect(
      featureBreaches(
        `${CONFORMING_FEATURE}\nimport { useProviderKeys } from '@/features/provider-keys/api/get-provider-keys';\n<button type="button">Configura</button>`,
      ),
    ).toEqual([
      'la funzionalità importa quella delle chiavi dei fornitori IA',
      'la sezione disegna comandi o campi propri',
    ]);
  });

  it('is red when the section stands above the keys of the AI providers or is missing', () => {
    expect(routeBreaches('<SourceCredentialsSection />\n<ProviderKeysList />')).toEqual([
      'la sezione Fonti non sta sotto le chiavi dei fornitori IA',
    ]);
    expect(routeBreaches('<ProviderKeysList />')).toEqual([
      'la pagina delle chiavi non mostra la sezione Fonti',
    ]);
  });

  it('is silent on a section and a route that follow the decision', () => {
    expect(featureBreaches(CONFORMING_FEATURE)).toEqual([]);
    expect(routeBreaches(CONFORMING_ROUTE)).toEqual([]);
  });

  it('holds for the feature source-credentials and the route of the page of the keys', () => {
    expect([
      ...featureBreaches(productionOf(FEATURE)),
      ...routeBreaches(readFileSync(ROUTE, 'utf8')),
    ]).toEqual([]);
  });

  it('holds for the editor of the flow, which shows the reason of the API without the feature', () => {
    const editor = productionOf(EDITOR);
    expect(editor).toContain('adapter.unavailable_reason');
    expect(editor).not.toContain('@/features/source-credentials');
  });
});
