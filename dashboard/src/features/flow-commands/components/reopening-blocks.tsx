import { useReopeningBlocks } from '../api/get-openings-suspension';

/**
 * The sides of the flow whose reopenings stop after consecutive losses, beside the suspension of the openings, each
 * with the text of the API (R5.5.2, ADR blocco-delle-riaperture-nella-dashboard). Nothing without a block, or while
 * the state cannot be read: the tabs show their own errors.
 */
export const ReopeningBlocks = ({ flowId }: { readonly flowId: string }) => {
  const blocks = useReopeningBlocks(flowId).data ?? [];
  if (blocks.length === 0) {
    return null;
  }
  return (
    <section aria-label="Riaperture ferme" className="mt-3 space-y-1">
      {blocks.map((text) => (
        <p key={text} role="status" className="rounded bg-amber-50 px-2 py-1 text-amber-900">
          {text}
        </p>
      ))}
    </section>
  );
};
