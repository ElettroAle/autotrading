// ADR-chiavi-di-cache-distinte-per-le-letture-dei-conti (Bug 437): the cache keeps what the query function returns,
// the data already passed through the schema of the feature that read first. A reading with a schema of its own has a
// key of its own: no query key repeats between two features.
import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const FEATURES = fileURLToPath(new URL('../src/features', import.meta.url));

/** A part of a key that is not written in the source, as an identifier or a parameter, matches any value. */
const ANY_VALUE = '*';

type SourceFile = { readonly feature: string; readonly path: string; readonly source: string };

const isTest = (path: string): boolean => /\.test\.tsx?$/.test(path);

const featureFilesOf = (directory: string): SourceFile[] =>
  readdirSync(directory, { recursive: true, encoding: 'utf8' })
    .filter((path) => /\.tsx?$/.test(path) && !isTest(path))
    .map((path) => ({
      feature: relative(directory, join(directory, path)).split(sep)[0] ?? path,
      path,
      source: readFileSync(join(directory, path), 'utf8'),
    }));

const syntaxOf = (file: SourceFile): ts.SourceFile =>
  ts.createSourceFile(file.path, file.source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

const visit = (node: ts.Node, onNode: (node: ts.Node) => void): void => {
  onNode(node);
  node.forEachChild((child) => visit(child, onNode));
};

const withoutAssertion = (expression: ts.Expression): ts.Expression =>
  ts.isAsExpression(expression) || ts.isSatisfiesExpression(expression)
    ? withoutAssertion(expression.expression)
    : expression;

/** The array constants of a feature, as `ACCOUNTS_QUERY_KEY = ['accounts'] as const`, that a key can spread. */
const arrayConstantsOf = (syntaxes: ts.SourceFile[]): Map<string, ts.ArrayLiteralExpression> => {
  const constants = new Map<string, ts.ArrayLiteralExpression>();
  syntaxes.forEach((syntax) =>
    visit(syntax, (node) => {
      if (!ts.isVariableDeclaration(node) || !ts.isIdentifier(node.name) || !node.initializer) {
        return;
      }
      const value = withoutAssertion(node.initializer);
      if (ts.isArrayLiteralExpression(value)) {
        constants.set(node.name.text, value);
      }
    }),
  );
  return constants;
};

const partsOf = (
  elements: readonly ts.Expression[],
  constants: Map<string, ts.ArrayLiteralExpression>,
): string[] =>
  elements.flatMap((element) => {
    if (ts.isStringLiteralLike(element) || ts.isNumericLiteral(element)) {
      return [element.text];
    }
    if (ts.isSpreadElement(element) && ts.isIdentifier(element.expression)) {
      const spread = constants.get(element.expression.text);
      return spread === undefined ? [ANY_VALUE] : partsOf(spread.elements, constants);
    }
    return [ANY_VALUE];
  });

/** The keys of the queries of a file: the `queryKey` arrays and the arguments of `pageDataQuery`. */
const queryKeysOf = (
  syntax: ts.SourceFile,
  constants: Map<string, ts.ArrayLiteralExpression>,
): string[][] => {
  const keys: string[][] = [];
  visit(syntax, (node) => {
    if (
      ts.isPropertyAssignment(node) &&
      ts.isIdentifier(node.name) &&
      node.name.text === 'queryKey'
    ) {
      const value = withoutAssertion(node.initializer);
      if (ts.isArrayLiteralExpression(value)) {
        keys.push(partsOf(value.elements, constants));
      }
      return;
    }
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      node.expression.text === 'pageDataQuery'
    ) {
      keys.push(partsOf(node.arguments, constants));
    }
  });
  return keys;
};

/** Every query key written by more than one feature, with the features that write it. */
const repeatedQueryKeys = (files: readonly SourceFile[]): Record<string, string[]> => {
  const featuresByKey = new Map<string, Set<string>>();
  const features = new Set(files.map((file) => file.feature));
  features.forEach((feature) => {
    const syntaxes = files.filter((file) => file.feature === feature).map(syntaxOf);
    const constants = arrayConstantsOf(syntaxes);
    syntaxes
      .flatMap((syntax) => queryKeysOf(syntax, constants))
      .forEach((key) => {
        const written = JSON.stringify(key);
        featuresByKey.set(written, (featuresByKey.get(written) ?? new Set()).add(feature));
      });
  });
  return Object.fromEntries(
    [...featuresByKey]
      .filter(([, writers]) => writers.size > 1)
      .map(([key, writers]) => [key, [...writers].sort()]),
  );
};

const file = (feature: string, source: string): SourceFile => ({
  feature,
  path: `${feature}/api/get-accounts.ts`,
  source,
});

describe('ADR-chiavi-di-cache-distinte-per-le-letture-dei-conti: one key for each reading', () => {
  it('is red when two features read under the same key', () => {
    const files = [
      file(
        'accounts',
        "export const ACCOUNTS_QUERY_KEY = ['accounts'] as const;\n" +
          'useQuery({ ...pageDataQuery(...ACCOUNTS_QUERY_KEY) });\n',
      ),
      file('flows', "useQuery({ ...pageDataQuery('accounts') });\n"),
      file('flow-editor', "useQuery({ queryKey: ['accounts'] });\n"),
    ];

    expect(repeatedQueryKeys(files)).toEqual({
      '["accounts"]': ['accounts', 'flow-editor', 'flows'],
    });
  });

  it('is red when two features read under keys that differ only in their parameters', () => {
    const files = [
      file('flows', "useQuery({ ...pageDataQuery('flow-state', flowId) });\n"),
      file('flow-positions', "useQuery({ queryKey: ['flow-state', id] });\n"),
    ];

    expect(repeatedQueryKeys(files)).toEqual({
      '["flow-state","*"]': ['flow-positions', 'flows'],
    });
  });

  it('is silent when each feature names itself after the resource', () => {
    const files = [
      file(
        'accounts',
        "const ACCOUNTS_QUERY_KEY = ['accounts'];\n" +
          'useQuery({ ...pageDataQuery(...ACCOUNTS_QUERY_KEY) });\n' +
          "useQuery({ queryKey: [...ACCOUNTS_QUERY_KEY, 'catalog'] satisfies string[] });\n",
      ),
      file('flows', "useQuery({ ...pageDataQuery('accounts', 'flows') });\n"),
      file('flow-editor', "useQuery({ queryKey: ['accounts', 'flow-editor'] });\n"),
    ];

    expect(repeatedQueryKeys(files)).toEqual({});
  });

  it('is silent when one feature reads the same key twice', () => {
    const files = [
      file('flows', "useQuery({ queryKey: ['flows'] });\nuseQuery({ queryKey: ['flows'] });\n"),
    ];

    expect(repeatedQueryKeys(files)).toEqual({});
  });

  it('finds no key repeated between two features of the dashboard', () => {
    expect(repeatedQueryKeys(featureFilesOf(FEATURES))).toEqual({});
  });
});
