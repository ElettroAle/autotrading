import type { PageData } from '@/hooks/use-page-data';
import { formatTimeOfDay } from '@/utils/format-instant';

/** When the data of the page was read, the command to reread it and the warning when a rereading failed (RF-23.10). */
export const RefreshBar = ({ pageData }: { pageData: PageData }) => (
  <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
    <button
      type="button"
      onClick={() => void pageData.refresh()}
      className="rounded border border-slate-300 bg-white px-3 py-1 font-medium hover:bg-slate-100"
    >
      Aggiorna
    </button>
    {pageData.updatedAt > 0 && (
      <p className="text-slate-600">
        Ultimo aggiornamento:{' '}
        <time dateTime={new Date(pageData.updatedAt).toISOString()}>
          {formatTimeOfDay(new Date(pageData.updatedAt).toISOString())}
        </time>
      </p>
    )}
    {pageData.stale && (
      <p role="alert" className="rounded bg-amber-100 px-2 py-1 font-medium text-amber-900">
        Dati non aggiornati
      </p>
    )}
  </div>
);
