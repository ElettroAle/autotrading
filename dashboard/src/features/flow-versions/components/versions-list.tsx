import { formatInstant } from '@/utils/format-instant';

import type { Version } from '../api/get-flow-versions';

export const VersionsList = ({ versions }: { versions: Version[] }) => (
  <ol
    aria-label="Versioni"
    className="divide-y divide-slate-200 rounded border border-slate-200 bg-white"
  >
    {versions.map((version) => (
      <li key={version.version} className="px-4 py-3">
        {`Versione ${version.version} · `}
        <time dateTime={version.created_at} className="text-slate-600">
          {formatInstant(version.created_at)}
        </time>
      </li>
    ))}
  </ol>
);
