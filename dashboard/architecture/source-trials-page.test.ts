// ADR-pagina-fonti-con-la-prova (R6.3.1): the trial of the sources is the feature source-trials, which reads the catalog
// GET /sources and imports no other feature; the page /fonti has the entry «Fonti» in the main group of the navigation,
// after «Avvisi»; the form builds its rules from the limits of the catalog, tries with the shared command and shows the
// refusals of the API on their fields; the outcome is announced in a live region with text and icon.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCE = fileURLToPath(new URL('../src', import.meta.url));
const FEATURE = join(SOURCE, 'features', 'source-trials');
const LAYOUT = join(SOURCE, 'components', 'layouts', 'dashboard-layout.tsx');
const ROUTER = join(SOURCE, 'app', 'router.tsx');
const PATHS = join(SOURCE, 'config', 'paths.ts');

const filesOf = (folder: string): string[] =>
  readdirSync(folder, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? filesOf(join(folder, entry.name)) : [join(folder, entry.name)],
  );

const productionOf = (folder: string): string =>
  filesOf(folder)
    .filter((path) => !/\.test\.tsx?$/.test(path))
    .map((path) => readFileSync(path, 'utf8'))
    .join('\n');

const REQUIRED: readonly (readonly [string, string])[] = [
  ["api.GET('/sources')", 'la funzionalità non legge il catalogo da GET /sources'],
  ["'/sources/{name}/adapters/{adapter}/trials'", "la funzionalità non chiede la prova all'API"],
  ["from '@/components/ui/command-button'", 'la prova non usa il comando condiviso'],
  ['parameter.minimum', 'le regole non vengono dai limiti del catalogo'],
  ['showRefusal(', "i rifiuti dell'API non vanno sui loro campi"],
  ['aria-live=', "l'esito non sta in una regione aria-live"],
  ['<Icon name=', "l'esito non ha un'icona accanto al testo"],
];

/** What the feature breaks of the decision. */
const featureBreaches = (source: string): string[] => [
  ...(source.includes("from '@/features/")
    ? ['la funzionalità importa un’altra funzionalità']
    : []),
  ...REQUIRED.filter(([needed]) => !source.includes(needed)).map(([, breach]) => breach),
  ...(/<button/.test(source) ? ['la funzionalità disegna comandi propri'] : []),
];

/** What the navigation breaks: «Fonti» right after «Avvisi», before the group of the settings. */
const navigationBreaches = (source: string): string[] => {
  const alerts = source.indexOf("name: 'Avvisi'");
  const sources = source.indexOf("name: 'Fonti'");
  const settings = source.indexOf("heading: 'Impostazioni'");
  if (sources === -1) {
    return ['la navigazione non ha la voce Fonti'];
  }
  return alerts !== -1 && alerts < sources && sources < settings
    ? []
    : ['la voce Fonti non segue Avvisi nel gruppo principale'];
};

const routeBreaches = (paths: string, router: string): string[] => [
  ...(/sources: \{\s*path: '\/fonti'/.test(paths) ? [] : ['il percorso della pagina non è /fonti']),
  ...(router.includes('path: paths.sources.path, element: <SourcesRoute />')
    ? []
    : ['la pagina Fonti non ha la sua rotta']),
];

const CONFORMING_FEATURE = `${REQUIRED.map(([needed]) => needed).join('\n')}\n<CommandButton>Prova</CommandButton>`;
const CONFORMING_NAVIGATION =
  "name: 'Avvisi', to: x },\n{ name: 'Fonti', to: y },\n],\n{ heading: 'Impostazioni',";

describe('ADR pagina-fonti-con-la-prova: the page Fonti with the trial of each adapter', () => {
  it('is red when the feature draws its own button, reads another feature and builds no rule from the limits', () => {
    expect(
      featureBreaches(
        `${CONFORMING_FEATURE.replace('parameter.minimum', '')}\nimport { x } from '@/features/flow-editor/api/x';\n<button>Prova</button>`,
      ),
    ).toEqual([
      'la funzionalità importa un’altra funzionalità',
      'le regole non vengono dai limiti del catalogo',
      'la funzionalità disegna comandi propri',
    ]);
  });

  it('is red when Fonti is missing or stands among the settings', () => {
    expect(navigationBreaches("name: 'Avvisi'\nheading: 'Impostazioni'")).toEqual([
      'la navigazione non ha la voce Fonti',
    ]);
    expect(navigationBreaches("name: 'Avvisi'\nheading: 'Impostazioni'\nname: 'Fonti'")).toEqual([
      'la voce Fonti non segue Avvisi nel gruppo principale',
    ]);
  });

  it('is red when the page has no route of its own', () => {
    expect(routeBreaches("sources: { path: '/sources'", '')).toEqual([
      'il percorso della pagina non è /fonti',
      'la pagina Fonti non ha la sua rotta',
    ]);
  });

  it('is silent on a feature and a navigation that follow the decision', () => {
    expect(featureBreaches(CONFORMING_FEATURE)).toEqual([]);
    expect(navigationBreaches(CONFORMING_NAVIGATION)).toEqual([]);
  });

  it('holds for the feature source-trials, the navigation and the route', () => {
    expect([
      ...featureBreaches(productionOf(FEATURE)),
      ...navigationBreaches(readFileSync(LAYOUT, 'utf8')),
      ...routeBreaches(readFileSync(PATHS, 'utf8'), readFileSync(ROUTER, 'utf8')),
    ]).toEqual([]);
  });
});
