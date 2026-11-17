// ADR-perdita-massima-nella-dashboard: the suspension of the openings is said by one shared notice, the same on the list
// of the flows and on the page of the flow, never written again by a page; only the feature of the commands of the flow
// resumes the openings, and the suspension comes from the API, never computed by the dashboard (ADR 0116).
import { readdirSync, readFileSync } from 'node:fs';
import { join, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

// The generated client of the API declares every path: it calls none.
const isProduction = (path: string): boolean =>
  /\.tsx?$/.test(path) &&
  !/\.test\.tsx?$/.test(path) &&
  !path.startsWith('testing/') &&
  path !== 'lib/api-schema.d.ts';

const productionFiles = (): SourceFile[] =>
  readdirSync(SOURCES, { recursive: true, encoding: 'utf8' })
    .map((path) => path.split(sep).join('/'))
    .filter(isProduction)
    .map((path) => ({ path, source: readFileSync(join(SOURCES, path), 'utf8') }));

const NOTICE_TEXT = 'aperture sospese:';
const NOTICE = 'components/ui/openings-notice.tsx';
const RESUME_PATH = '/flows/{flow_id}/openings/resume';
const COMMANDS = 'features/flow-commands/';
// Thresholds of the losses compared in the dashboard would be the rule of the API computed again; an arrow function that
// returns a field is no comparison.
const COMPUTED_SUSPENSION =
  /max_(daily_loss|drawdown)_percent\s*[<>]|(?<!=)[<>]=?\s*[\w.]*max_(daily_loss|drawdown)_percent/;

const filesWith = (files: SourceFile[], matches: (source: string) => boolean): string[] =>
  files
    .filter((file) => matches(file.source))
    .map((file) => file.path)
    .sort();

const noticeWriters = (files: SourceFile[]): string[] =>
  filesWith(files, (source) => source.includes(NOTICE_TEXT));

const resumers = (files: SourceFile[]): string[] =>
  filesWith(files, (source) => source.includes(RESUME_PATH)).filter(
    (path) => !path.startsWith(COMMANDS),
  );

const suspensionComputers = (files: SourceFile[]): string[] =>
  filesWith(files, (source) => COMPUTED_SUSPENSION.test(source));

describe('ADR-perdita-massima-nella-dashboard', () => {
  const files = productionFiles();

  it('says the suspension only through the shared notice', () => {
    expect(noticeWriters(files)).toEqual([NOTICE]);
  });

  it('red: a page that writes the notice again', () => {
    const page = {
      path: 'features/flows/components/flow-view.tsx',
      source: '<p>aperture sospese: {r}</p>',
    };

    expect(noticeWriters([page])).toEqual(['features/flows/components/flow-view.tsx']);
  });

  it('resumes the openings only from the commands of the flow', () => {
    expect(filesWith(files, (source) => source.includes(RESUME_PATH))).toEqual([
      'features/flow-commands/api/resume-flow-openings.ts',
    ]);
    expect(resumers(files)).toEqual([]);
  });

  it('red: another feature that resumes the openings', () => {
    const elsewhere = {
      path: 'features/flows/api/resume.ts',
      source: "api.POST('/flows/{flow_id}/openings/resume')",
    };

    expect(resumers([elsewhere])).toEqual(['features/flows/api/resume.ts']);
  });

  it('never compares the losses with their thresholds', () => {
    expect(suspensionComputers(files)).toEqual([]);
  });

  it('silent: a function that only returns the field', () => {
    const sorter = {
      path: 'features/ranking/utils/sort.ts',
      source: 'const by = (row) => row.max_drawdown_percent;',
    };

    expect(suspensionComputers([sorter])).toEqual([]);
  });

  it('red: a feature that decides the suspension from the thresholds', () => {
    const computed = {
      path: 'features/flows/utils/suspended.ts',
      source: 'const suspended = loss > flow.max_daily_loss_percent;',
    };

    expect(suspensionComputers([computed])).toEqual(['features/flows/utils/suspended.ts']);
  });
});
