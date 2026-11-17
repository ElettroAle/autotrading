// ADR-area-utente-in-alto-a-destra (Bug 567): «Esci» is only the item of the menu of the user, which the bar on top of
// every page shows; the navigation no longer holds it, and the name of the user comes from the sign-in of the
// dashboard, never from the API.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

const isTest = (path: string): boolean => /\.test\.tsx?$/.test(path);

const sourcesOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { recursive: true, encoding: 'utf8' })
    .filter((path) => /\.tsx?$/.test(path) && !isTest(path))
    .map((path) => relative(directory, join(directory, path)).split(sep).join('/'))
    .filter((path) => !path.startsWith('testing/') && !path.endsWith('.d.ts'))
    .map((path) => ({ path, source: readFileSync(join(directory, path), 'utf8') }));

const USER_MENU = 'components/layouts/user-menu.tsx';
const APP_HEADER = 'components/layouts/app-header.tsx';
const LAYOUT = 'components/layouts/dashboard-layout.tsx';
const SIGN_OUT_IMPORT = /from '(?:\.\/|@\/components\/layouts\/)sign-out-button'/;
const USER_MENU_IMPORT = /from '(?:\.\/|@\/components\/layouts\/)user-menu'/;
const NAME_FROM_SIGN_IN = /\buseSignedInUserName\b[^;]*from '@\/lib\/auth'/;

const signOutOutsideTheMenu = (files: readonly SourceFile[]): string[] =>
  files
    .filter((file) => file.path !== USER_MENU && SIGN_OUT_IMPORT.test(file.source))
    .map((file) => `${file.path}: «Esci» fuori dal menu dell'utente`);

const headerWithoutTheMenu = (files: readonly SourceFile[]): string[] => {
  const header = files.find((file) => file.path === APP_HEADER);
  return header !== undefined && USER_MENU_IMPORT.test(header.source)
    ? []
    : [`${APP_HEADER}: non mostra il menu dell'utente`];
};

const menuProblems = (files: readonly SourceFile[]): string[] => {
  const menu = files.find((file) => file.path === USER_MENU);
  if (menu === undefined) {
    return [`${USER_MENU}: mancante`];
  }
  return [
    ...(SIGN_OUT_IMPORT.test(menu.source) ? [] : [`${USER_MENU}: non contiene «Esci»`]),
    ...(NAME_FROM_SIGN_IN.test(menu.source)
      ? []
      : [`${USER_MENU}: il nome non viene dall'accesso`]),
  ];
};

/** Each file that breaks the decision, with the reason. */
const misplacedUserArea = (files: readonly SourceFile[]): string[] => [
  ...signOutOutsideTheMenu(files),
  ...headerWithoutTheMenu(files),
  ...menuProblems(files),
];

const file = (path: string, source: string): SourceFile => ({ path, source });

const conforming = (): SourceFile[] => [
  file(
    USER_MENU,
    "import { useSignedInUserName } from '@/lib/auth';\nimport { SignOutButton } from './sign-out-button';",
  ),
  file(APP_HEADER, "import { UserMenu } from './user-menu';"),
  file(LAYOUT, "import { AppHeader } from './app-header';"),
];

const replaced = (files: readonly SourceFile[], path: string, source: string): SourceFile[] =>
  files.map((each) => (each.path === path ? file(path, source) : each));

describe('ADR-area-utente-in-alto-a-destra: «Esci» in the menu of the user, on top of every page', () => {
  it('is red when the navigation offers «Esci» again', () => {
    const files = replaced(
      conforming(),
      LAYOUT,
      "import { SignOutButton } from './sign-out-button';",
    );

    expect(misplacedUserArea(files)).toEqual([`${LAYOUT}: «Esci» fuori dal menu dell'utente`]);
  });

  it('is red when the bar on top does not show the menu of the user', () => {
    const files = replaced(conforming(), APP_HEADER, "import { BackButton } from './back-button';");

    expect(misplacedUserArea(files)).toEqual([`${APP_HEADER}: non mostra il menu dell'utente`]);
  });

  it('is red when the menu reads the name elsewhere and loses «Esci»', () => {
    const files = replaced(conforming(), USER_MENU, "api.GET('/me')");

    expect(misplacedUserArea(files)).toEqual([
      `${USER_MENU}: non contiene «Esci»`,
      `${USER_MENU}: il nome non viene dall'accesso`,
    ]);
  });

  it('is red when the menu of the user is missing', () => {
    const files = conforming().filter((each) => each.path !== USER_MENU);

    expect(misplacedUserArea(files)).toEqual([`${USER_MENU}: mancante`]);
  });

  it('is silent when only the menu of the user, in the bar on top, offers «Esci»', () => {
    expect(misplacedUserArea(conforming())).toEqual([]);
  });

  it('finds «Esci» only in the menu of the user of the dashboard', () => {
    expect(misplacedUserArea(sourcesOf(SOURCES))).toEqual([]);
  });
});
