import type { StepDocument } from '../api/get-cycle';
import {
  contextOf,
  decisionLabelOf,
  decisionsOf,
  sourcesOf,
  type AgentDecision,
  type ContextMessage,
  type SourceReading,
} from '../utils/cycle-documents';

import { CycleSection } from './cycle-section';
import { RecordedText, RecordedValue } from './recorded-text';

// The steps by the names the API gives them (R1.2.1).
const COLLECT_SOURCES = 'raccolta dei dati delle fonti';
const COMPOSE_CONTEXT = 'composizione del contesto';
const AGENT_DECISION = "decisione dell'agente";

const SOURCES_TITLE = 'Dati delle fonti';
const CONTEXT_TITLE = 'Contesto inviato';
const DECISIONS_TITLE = 'Decisioni e ragionamento';

const TITLE_OF_STEP: Readonly<Record<string, string>> = {
  'lettura dello stato del flusso': "Flusso all'avvio",
  'controllo del rischio': 'Controllo del rischio',
  'esecuzione degli ordini': 'Esecuzione degli ordini',
  'aggiornamento dello stato del flusso': 'Flusso alla fine',
};

const RecordedSection = ({ title, value }: { title: string; value: unknown }) => (
  <CycleSection title={title}>
    <RecordedValue value={value} />
  </CycleSection>
);

const SourcesSection = ({ readings }: { readings: SourceReading[] }) => (
  <CycleSection title={SOURCES_TITLE}>
    {readings.map((reading) => (
      <div key={reading.fonte}>
        <h3 className="font-medium">{reading.fonte}</h3>
        <RecordedValue value={reading.dati} />
      </div>
    ))}
  </CycleSection>
);

const ContextSection = ({ messages }: { messages: ContextMessage[] }) => (
  <CycleSection title={CONTEXT_TITLE}>
    {messages.map((message, index) => (
      // The messages have no identity of their own: their order is the context.
      <div key={index}>
        <h3 className="font-medium">{message.ruolo}</h3>
        <RecordedText text={message.contenuto} />
      </div>
    ))}
  </CycleSection>
);

const DecisionSections = ({ decision }: { decision: AgentDecision }) => (
  <>
    <CycleSection title={DECISIONS_TITLE}>
      {decision.decisioni.length === 0 && <p>Nessuna decisione valida.</p>}
      {decision.decisioni.map((each) => (
        <div key={each.asset}>
          <h3 className="font-medium">{decisionLabelOf(each)}</h3>
          <RecordedText text={each.reasoning} />
        </div>
      ))}
      {decision.scartate.length > 0 && (
        <div>
          <h3 className="font-medium">Decisioni scartate</h3>
          <RecordedValue value={decision.scartate} />
        </div>
      )}
      {decision.mancanti.length > 0 && <p>Asset senza decisione: {decision.mancanti.join(', ')}</p>}
    </CycleSection>
    <CycleSection title="Risposta integrale dell'agente">
      <RecordedText text={decision.risposta} />
    </CycleSection>
  </>
);

/** What one step produced; a document of a shape it does not know is shown as it is. */
export const StepDocumentView = ({ document }: { document: StepDocument }) => {
  const { step, content } = document;
  if (step === COLLECT_SOURCES) {
    const readings = sourcesOf(content);
    return readings === undefined ? (
      <RecordedSection title={SOURCES_TITLE} value={content} />
    ) : (
      <SourcesSection readings={readings} />
    );
  }
  if (step === COMPOSE_CONTEXT) {
    const messages = contextOf(content);
    return messages === undefined ? (
      <RecordedSection title={CONTEXT_TITLE} value={content} />
    ) : (
      <ContextSection messages={messages} />
    );
  }
  if (step === AGENT_DECISION) {
    const decision = decisionsOf(content);
    return decision === undefined ? (
      <RecordedSection title={DECISIONS_TITLE} value={content} />
    ) : (
      <DecisionSections decision={decision} />
    );
  }
  return <RecordedSection title={TITLE_OF_STEP[step] ?? step} value={content} />;
};
