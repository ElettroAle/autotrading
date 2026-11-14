// Texts of the model and of the sources arrive from outside: React writes them as text, never as HTML (ADR 0129).

export const RecordedText = ({ text }: { text: string }) => (
  <pre className="max-h-96 overflow-auto rounded bg-slate-100 p-2 text-xs break-words whitespace-pre-wrap">
    {text}
  </pre>
);

/** A recorded value as it is, as indented JSON. */
export const RecordedValue = ({ value }: { value: unknown }) => (
  <RecordedText text={JSON.stringify(value, null, 2)} />
);
