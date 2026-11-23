import { useId, type HTMLAttributes, type ReactNode } from 'react';

type CardElement = 'div' | 'section' | 'article' | 'fieldset' | 'li';

// A box of state keeps the colour it already had, always apart from the background of the page.
type CardTone = 'neutral' | 'error';

type CardProps = HTMLAttributes<HTMLElement> & {
  readonly as?: CardElement;
  readonly tone?: CardTone;
  /** The heading that names the card. */
  readonly title?: string;
  /** A line under the title. */
  readonly description?: string;
  readonly children: ReactNode;
};

// The card is white on the slate background of the pages, with a soft shadow: it stands apart by its colour, not only
// by its thin border (Bug 726).
const BOX = 'rounded-lg border p-4 shadow-sm';

const COLOURS_BY_TONE: Readonly<Record<CardTone, string>> = {
  neutral: 'border-slate-200 bg-white',
  error: 'border-red-300 bg-red-50',
};

const CardHeader = ({
  id,
  title,
  description,
}: {
  id: string;
  title: string;
  description?: string;
}) => (
  <header className="mb-3">
    <h2 id={id} className="text-lg font-semibold wrap-anywhere">
      {title}
    </h2>
    {description !== undefined && <p className="text-sm text-slate-600">{description}</p>}
  </header>
);

/**
 * Every box of the dashboard, the same on every page: features and routes give it only their layout (margins, gaps),
 * never border, padding or background (ADR card-condivisa-distinta-dallo-sfondo).
 */
export const Card = ({
  as: Element = 'div',
  tone = 'neutral',
  title,
  description,
  className,
  children,
  ...attributes
}: CardProps) => {
  const titleId = useId();
  const labelled = title === undefined ? {} : { 'aria-labelledby': titleId };
  return (
    <Element
      {...attributes}
      {...labelled}
      className={[BOX, COLOURS_BY_TONE[tone], className].filter(Boolean).join(' ')}
    >
      {title !== undefined && <CardHeader id={titleId} title={title} description={description} />}
      {children}
    </Element>
  );
};
