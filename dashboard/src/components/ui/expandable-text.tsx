import { useId, useState } from 'react';

import { shortenText } from '@/utils/shorten-text';

/**
 * A long text shortened, which «Leggi tutto» opens whole in place and «Riduci» closes again; a short text is shown
 * whole, without a command. The command declares whether the text is open, for screen readers too (ADR
 * testo-lungo-espandibile).
 */
export const ExpandableText = ({ text }: { readonly text: string }) => {
  const textId = useId();
  const [expanded, setExpanded] = useState(false);
  const shortened = shortenText(text);
  if (shortened === text) {
    return <span>{text}</span>;
  }
  return (
    <span>
      <span id={textId}>{expanded ? text : shortened}</span>{' '}
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={textId}
        className="text-blue-800 hover:underline"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? 'Riduci' : 'Leggi tutto'}
      </button>
    </span>
  );
};
