import type { Version } from '../api/get-flow-versions';
import { dateTimeText } from '../utils/date-time';

export const VersionsList = ({ versions }: { versions: Version[] }) => (
  <ol
    aria-label="Versioni"
    className="divide-y divide-slate-200 rounded border border-slate-200 bg-white"
  >
    {versions.map((version) => (
      <li key={version.version} className="px-4 py-3">
        {`Versione ${version.version} · `}
        <time dateTime={version.created_at} className="text-slate-600">
          {dateTimeText(version.created_at)}
        </time>
      </li>
    ))}
  </ol>
);
