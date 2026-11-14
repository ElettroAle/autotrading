import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useFlowVersion } from '../api/get-flow-version';
import { useVersionDifferences } from '../api/get-version-differences';
import { comparisonRows, type ComparisonRow } from '../utils/comparison-rows';
import { configurationRows } from '../utils/configuration-rows';

import type { ChosenVersions } from './compare-versions-form';

const Value = ({ text, changed }: { text: string; changed: boolean }) =>
  changed ? <mark className="bg-amber-200">{text}</mark> : text;

const Row = ({ row }: { row: ComparisonRow }) => (
  <tr className={row.changed ? 'bg-amber-50' : undefined}>
    <th scope="row" className="px-3 py-2 text-left font-medium">
      {row.part}
    </th>
    <td className="px-3 py-2">
      <Value text={row.before} changed={row.changed} />
    </td>
    <td className="px-3 py-2">
      <Value text={row.after} changed={row.changed} />
    </td>
  </tr>
);

type VersionsComparisonProps = { readonly flowId: string; readonly chosen: ChosenVersions };

/** The two configurations side by side, with the parts the API reports as changed highlighted (ADR 0133). */
export const VersionsComparison = ({ flowId, chosen }: VersionsComparisonProps) => {
  const first = useFlowVersion(flowId, chosen.first);
  const second = useFlowVersion(flowId, chosen.second);
  const differences = useVersionDifferences(flowId, chosen.first, chosen.second);
  const failed = [first, second, differences].find((query) => query.isError);
  if (failed?.error) {
    return <ErrorMessage error={failed.error} />;
  }
  if (!first.data || !second.data || !differences.data) {
    return <Loading />;
  }
  const rows = comparisonRows(
    configurationRows(first.data),
    configurationRows(second.data),
    differences.data,
  );
  return (
    <section className="space-y-3">
      {differences.data.length === 0 && (
        <p role="status" className="font-medium">
          Nessuna differenza
        </p>
      )}
      <table
        aria-label="Confronto delle versioni"
        className="w-full rounded border border-slate-200 bg-white text-sm"
      >
        <thead>
          <tr className="border-b border-slate-200">
            <th scope="col" className="px-3 py-2 text-left">
              Campo
            </th>
            <th scope="col" className="px-3 py-2 text-left">
              {`Versione ${chosen.first}`}
            </th>
            <th scope="col" className="px-3 py-2 text-left">
              {`Versione ${chosen.second}`}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <Row key={row.part} row={row} />
          ))}
        </tbody>
      </table>
    </section>
  );
};
