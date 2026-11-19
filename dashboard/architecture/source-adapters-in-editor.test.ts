// ADR scelta-degli-adapter-nell-editor-del-flusso (R4.1.1): in the editor of the flow an active source lists its
// adapters, each with its choice, and an adapter chosen shows its weight and its parameters labelled «<fonte> · <adapter>»;
// an adapter without configuration fields says «nessuna configurazione necessaria»; the values of the form are
// sources.<fonte>.adapters.<adapter>. Everything comes from the catalog of the API: no adapter is named in the code of
// the dashboard, only in its fakes.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import { FAKE_SOURCES } from '../src/testing/mocks/catalogs';

const SOURCE = fileURLToPath(new URL('../src', import.meta.url));
const FIELDS = join(SOURCE, 'features', 'flow-editor', 'components', 'source-fields.tsx');
const OUTSIDE_THE_RULE = /(^testing\/|\.test\.tsx?$|^lib\/api-schema\.d\.ts$)/;

const RULES: readonly { readonly breach: string; readonly holds: (source: string) => boolean }[] = [
  {
    breach: 'gli adapter non si elencano dal catalogo sotto la fonte',
    holds: (source) => /source\.adapters\.map\(/.test(source),
  },
  {
    breach: 'il peso non è etichettato «Peso di <fonte> · <adapter>»',
    holds: (source) =>
      /`\$\{source\.name\} · \$\{adapter\.name\}`/.test(source) &&
      /`Peso di \$\{label\}`/.test(source),
  },
  {
    breach: 'un adapter senza campi di configurazione non dice «nessuna configurazione necessaria»',
    holds: (source) =>
      source.includes("'nessuna configurazione necessaria'") &&
      /configuration_fields\.length === 0/.test(source),
  },
  {
    breach: 'i valori del modulo non sono sources.<fonte>.adapters.<adapter>',
    holds: (source) => /`sources\.\$\{source\.name\}\.adapters\.\$\{key\}/.test(source),
  },
];

/** The rules of the ADR the source of the editor of the sources breaks. */
const breachesOf = (source: string): string[] =>
  RULES.filter((rule) => !rule.holds(source)).map((rule) => rule.breach);

const withoutComments = (source: string): string =>
  source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/.*$/gm, '$1');

const filesOf = (folder: string): string[] =>
  readdirSync(folder, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? filesOf(join(folder, entry.name)) : [join(folder, entry.name)],
  );

const ADAPTER_NAMES = FAKE_SOURCES.flatMap((source) =>
  source.adapters.map((adapter) => adapter.name),
);

/** The adapters a file of the dashboard names, which only the catalog of the API may name. */
const adaptersNamedIn = (source: string): string[] =>
  ADAPTER_NAMES.filter((name) => withoutComments(source).includes(`'${name}'`));

const CONFORMING = `
  const label = \`\${source.name} · \${adapter.name}\`;
  <FormField label={\`Peso di \${label}\`}>{register(\`sources.\${source.name}.adapters.\${key}.weight\`)}</FormField>
  const configuration = adapter.configuration_fields.length === 0 ? 'nessuna configurazione necessaria' : labels;
  {source.adapters.map((adapter) => <AdapterChoice adapter={adapter} />)}`;

describe('ADR scelta-degli-adapter-nell-editor-del-flusso: the adapters of a source in the editor of the flow', () => {
  it('is red when the source keeps one weight of its own', () => {
    expect(
      breachesOf(
        '<FormField label={`Peso di ${source.name}`}>{register(`sources.${source.name}.weight`)}</FormField>',
      ),
    ).toEqual(RULES.map((rule) => rule.breach));
  });

  it('is red when an adapter without configuration says nothing', () => {
    expect(breachesOf(CONFORMING.replace("'nessuna configurazione necessaria'", "''"))).toEqual([
      'un adapter senza campi di configurazione non dice «nessuna configurazione necessaria»',
    ]);
  });

  it('is silent on the editor that follows the decision', () => {
    expect(breachesOf(CONFORMING)).toEqual([]);
  });

  it('holds for the editor of the sources of the dashboard', () => {
    expect(breachesOf(readFileSync(FIELDS, 'utf8'))).toEqual([]);
  });

  it('is red when the dashboard names an adapter', () => {
    expect(adaptersNamedIn("const PREFERRED = 'CoinMarketCap';")).toEqual(['CoinMarketCap']);
    expect(
      adaptersNamedIn("// as 'CoinMarketCap' declares\nconst preferred = adapter.name;"),
    ).toEqual([]);
  });

  it('names no adapter outside the fakes of the dashboard', () => {
    const named = filesOf(SOURCE)
      .map((path) => relative(SOURCE, path).replaceAll('\\', '/'))
      .filter((path) => !OUTSIDE_THE_RULE.test(path))
      .flatMap((path) =>
        adaptersNamedIn(readFileSync(join(SOURCE, path), 'utf8')).map((name) => `${path}: ${name}`),
      );
    expect(named).toEqual([]);
  });
});
