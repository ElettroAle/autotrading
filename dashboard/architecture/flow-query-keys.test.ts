// ADR-chiavi-delle-letture-del-flusso-con-l-id (Bug 574): the commands of a flow read again every query whose key has
// the id of the flow as one of its elements. A reading of a flow keeps the id as an element of its key, never only
// inside a path, or the command leaves it stale.
import { readdirSync, readFileSync } from 'node:fs';
import { join, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const SOURCES = fileURLToPath(new URL('../src', import.meta.url));

/** The paths of the API that read a single flow. */
const FLOW_PATH = '/flows/{flow_id}';

type SourceFile = { readonly path: string; readonly source: string };

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

const visit = (node: ts.Node, onNode: (node: ts.Node) => void): void => {
  onNode(node);
  node.forEachChild((child) => visit(child, onNode));
};

const isNamed = (node: ts.ObjectLiteralElementLike, name: string): node is ts.PropertyAssignment =>
  ts.isPropertyAssignment(node) && ts.isIdentifier(node.name) && node.name.text === name;

/** The elements of the key an options object declares, as `queryKey: [...]` or `...pageDataQuery(...)`. */
const keyOf = (options: ts.ObjectLiteralExpression): readonly ts.Expression[] | undefined => {
  for (const property of options.properties) {
    if (isNamed(property, 'queryKey') && ts.isArrayLiteralExpression(property.initializer)) {
      return property.initializer.elements;
    }
    if (
      ts.isSpreadAssignment(property) &&
      ts.isCallExpression(property.expression) &&
      ts.isIdentifier(property.expression.expression) &&
      property.expression.expression.text === 'pageDataQuery'
    ) {
      return property.expression.arguments;
    }
  }
  return undefined;
};

const isFlowCall = (node: ts.Node): node is ts.CallExpression => {
  if (!ts.isCallExpression(node)) {
    return false;
  }
  const [path] = node.arguments;
  return path !== undefined && ts.isStringLiteralLike(path) && path.text.startsWith(FLOW_PATH);
};

/** The expressions that give the id of the flow to the calls of the API inside the options. */
const flowIdsReadBy = (options: ts.ObjectLiteralExpression): string[] => {
  const flowIds: string[] = [];
  visit(options, (node) => {
    if (!isFlowCall(node)) {
      return;
    }
    visit(node, (inner) => {
      if (ts.isObjectLiteralExpression(inner)) {
        inner.properties
          .filter((property) => isNamed(property, 'flow_id'))
          .forEach((property) => flowIds.push(property.initializer.getText()));
      }
    });
  });
  return flowIds;
};

/** Each reading of a flow whose key lacks, as an element, the id the reading sends: file and key. */
const readingsWithoutFlowId = (files: readonly SourceFile[]): string[] =>
  files.flatMap((file) => {
    const syntax = ts.createSourceFile(
      file.path,
      file.source,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const violations: string[] = [];
    visit(syntax, (node) => {
      if (!ts.isObjectLiteralExpression(node)) {
        return;
      }
      const key = keyOf(node);
      if (key === undefined) {
        return;
      }
      const elements = key.map((element) => element.getText());
      flowIdsReadBy(node)
        .filter((flowId) => !elements.includes(flowId))
        .forEach(() => violations.push(`${file.path}: [${elements.join(', ')}]`));
    });
    return violations;
  });

const reading = (key: string): SourceFile => ({
  path: 'features/flows/api/get-flow-equity.ts',
  source:
    'const path = equityPath(flowId, period);\n' +
    `useQuery({ ${key}, queryFn: async () => api.GET('/flows/{flow_id}/equity', ` +
    '{ params: { path: { flow_id: flowId } } }) });\n',
});

describe('ADR-chiavi-delle-letture-del-flusso-con-l-id: the id of the flow in the key of its readings', () => {
  it('finds no reading of a flow without its id in the key', () => {
    expect(readingsWithoutFlowId(productionFiles())).toEqual([]);
  });

  it('red: a reading of a flow with the id only inside the path of the key', () => {
    expect(readingsWithoutFlowId([reading("...pageDataQuery('flow-equity', path)")])).toEqual([
      "features/flows/api/get-flow-equity.ts: ['flow-equity', path]",
    ]);
  });

  it('red: a reading of a flow whose queryKey lacks the id', () => {
    expect(readingsWithoutFlowId([reading("queryKey: ['compared-equity', path]")])).toEqual([
      "features/flows/api/get-flow-equity.ts: ['compared-equity', path]",
    ]);
  });

  it('silent: a reading of a flow with the id as an element of the key', () => {
    expect(
      readingsWithoutFlowId([reading("...pageDataQuery('flow-equity', flowId, path)")]),
    ).toEqual([]);
  });

  it('silent: a reading that is not of a single flow', () => {
    const flows = {
      path: 'features/flows/api/get-flows.ts',
      source: "useQuery({ ...pageDataQuery('flows'), queryFn: async () => api.GET('/flows') });\n",
    };

    expect(readingsWithoutFlowId([flows])).toEqual([]);
  });
});
