import {
  ArrowDown,
  ArrowUp,
  CircleAlert,
  CircleCheck,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Square,
  X,
} from 'lucide-react';

// The only module that imports lucide-react: features and shared components name an icon, never draw one (ADR
// icone-con-lucide-react-e-comandi-condivisi).
const DRAWINGS = {
  pause: Pause,
  play: Play,
  square: Square,
  'arrow-up': ArrowUp,
  'arrow-down': ArrowDown,
  plus: Plus,
  x: X,
  refresh: RefreshCw,
  'circle-check': CircleCheck,
  'circle-alert': CircleAlert,
} as const;

export type IconName = keyof typeof DRAWINGS;

/** An icon beside a text: the text names what the icon marks, so screen readers skip the icon (R6.5.3). */
export const Icon = ({ name }: { readonly name: IconName }) => {
  const Drawing = DRAWINGS[name];
  return <Drawing role="img" aria-hidden="true" data-icon={name} className="size-4 shrink-0" />;
};
