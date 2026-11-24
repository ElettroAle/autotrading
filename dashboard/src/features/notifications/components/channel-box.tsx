import { useId, type ReactNode } from 'react';

import { Card } from '@/components/ui/card';
import { Icon } from '@/components/ui/icons/icon';

type ChannelBoxProps = {
  readonly title: string;
  /** What the channel reaches once linked; undefined while it is to configure. */
  readonly linkedTo: string | undefined;
  readonly children: ReactNode;
};

const TO_CONFIGURE = 'Da configurare';

/**
 * A channel of the notifications, every one in the same shape: its state at the top, with an icon and a text, never
 * the colour alone, then what links it (ADR pagina-notifiche-a-schede).
 */
export const ChannelBox = ({ title, linkedTo, children }: ChannelBoxProps) => {
  const titleId = useId();
  const linked = linkedTo !== undefined;
  return (
    <Card as="section" aria-labelledby={titleId} className="space-y-4">
      <h2 id={titleId} className="text-xl font-semibold">
        {title}
      </h2>
      <p
        role="status"
        aria-label={`Stato di ${title}`}
        className={`flex items-center gap-2 ${linked ? 'text-green-800' : 'text-amber-800'}`}
      >
        <Icon name={linked ? 'circle-check' : 'circle-alert'} />
        {linked ? `Collegato: ${linkedTo}` : TO_CONFIGURE}
      </p>
      {children}
    </Card>
  );
};
