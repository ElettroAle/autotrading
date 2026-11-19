import { DETAILS_GRID, DETAIL_VALUE } from '@/components/ui/details-list';
import { Icon } from '@/components/ui/icons/icon';
import { formatInstant } from '@/utils/format-instant';

import type { SourceTrial } from '../api/try-source-adapter';

const ReadValues = ({ trial }: { readonly trial: SourceTrial }) => (
  <>
    {trial.values.map((value, index) => (
      <dl key={`${value.reference_at}-${String(index)}`} className={`${DETAILS_GRID} text-sm`}>
        {Object.entries(value.values).map(([key, read]) => (
          <div key={key} className="contents">
            <dt className="text-slate-600">{key}</dt>
            <dd className={DETAIL_VALUE}>{read}</dd>
          </div>
        ))}
      </dl>
    ))}
  </>
);

const Succeeded = ({ trial }: { readonly trial: SourceTrial }) => (
  <>
    <p className="inline-flex items-center gap-1 font-semibold text-green-800">
      <Icon name="circle-check" />
      riuscita
    </p>
    <ReadValues trial={trial} />
    <dl className={`${DETAILS_GRID} text-sm`}>
      <dt className="text-slate-600">Istante dei dati</dt>
      <dd className={DETAIL_VALUE}>
        {trial.data_at === null ? 'nessun dato' : formatInstant(trial.data_at)}
      </dd>
      <dt className="text-slate-600">Tempo di risposta</dt>
      <dd className={DETAIL_VALUE}>{trial.response_milliseconds} ms</dd>
    </dl>
  </>
);

const Failed = ({ trial }: { readonly trial: SourceTrial }) => (
  <>
    <p className="inline-flex items-center gap-1 font-semibold text-red-800">
      <Icon name="circle-alert" />
      errore
    </p>
    <dl className={`${DETAILS_GRID} text-sm`}>
      <dt className="text-slate-600">Motivo</dt>
      <dd className={DETAIL_VALUE}>{trial.reason}</dd>
      <dt className="text-slate-600">Tipo</dt>
      <dd className={DETAIL_VALUE}>{trial.permanent ? 'permanente' : 'transitorio'}</dd>
      <dt className="text-slate-600">Tempo di risposta</dt>
      <dd className={DETAIL_VALUE}>{trial.response_milliseconds} ms</dd>
    </dl>
  </>
);

/**
 * The last outcome of the trial of a source, in text and icon, announced as it arrives; it stays until the user tries
 * again (ADR pagina-fonti-con-la-prova).
 */
export const SourceTrialOutcome = ({
  source,
  trial,
}: {
  readonly source: string;
  readonly trial: SourceTrial | undefined;
}) => (
  <section aria-live="polite" aria-label={`Esito della prova di ${source}`} className="space-y-2">
    {trial !== undefined &&
      (trial.outcome === 'succeeded' ? <Succeeded trial={trial} /> : <Failed trial={trial} />)}
  </section>
);
