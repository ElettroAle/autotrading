import { Link } from 'react-router';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { paths } from '@/config/paths';

import { useCycle, type Cycle } from '../api/get-cycle';

import { CycleSection } from './cycle-section';
import { CycleSummaryView } from './cycle-summary';
import { StepDocumentView } from './step-document';

type Failure = NonNullable<Cycle['failure']>;

/** Step, type and message of the error as the API gives them (ADR 0129). */
const CycleFailureView = ({ failure }: { failure: Failure }) => (
  <section
    aria-labelledby="cycle-failure"
    className="space-y-2 rounded border border-red-300 bg-red-50 p-4"
  >
    <h2 id="cycle-failure" className="text-lg font-semibold text-red-800">
      Errore del ciclo
    </h2>
    <dl className="space-y-1 text-sm">
      <div className="flex gap-2">
        <dt className="font-medium">Passo</dt>
        <dd>{failure.step}</dd>
      </div>
      <div className="flex gap-2">
        <dt className="font-medium">Tipo</dt>
        <dd>{failure.error_type}</dd>
      </div>
      <div className="flex gap-2">
        <dt className="font-medium">Motivo</dt>
        <dd className="break-words whitespace-pre-wrap">{failure.message}</dd>
      </div>
    </dl>
  </section>
);

const AbsentSources = ({ sources }: { sources: Cycle['absent_sources'] }) => (
  <CycleSection title="Fonti assenti">
    <ul className="list-inside list-disc text-sm">
      {sources.map((absent) => (
        <li key={absent.source}>
          {absent.source}: {absent.reason}
        </li>
      ))}
    </ul>
  </CycleSection>
);

/** Everything recorded about a cycle, step by step, up to where it stopped (R2.2.7). */
export const CycleView = ({ flowId, plannedAt }: { flowId: string; plannedAt: string }) => {
  const cycle = useCycle(flowId, plannedAt);
  if (cycle.isPending) {
    return <Loading />;
  }
  if (cycle.isError) {
    return <ErrorMessage error={cycle.error} />;
  }
  const { failure, absent_sources: absentSources, documents } = cycle.data;
  return (
    <div className="space-y-4">
      <Link to={paths.flowCycles.getHref(flowId)} className="text-blue-800 hover:underline">
        Tutti i cicli del flusso
      </Link>
      <CycleSummaryView cycle={cycle.data} />
      {failure !== null && <CycleFailureView failure={failure} />}
      {absentSources.length > 0 && <AbsentSources sources={absentSources} />}
      {documents.map((document) => (
        <StepDocumentView key={document.step} document={document} />
      ))}
    </div>
  );
};
