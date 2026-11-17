import type { ButtonHTMLAttributes, ReactNode } from 'react';

import {
  DESTRUCTIVE_COMMAND,
  GO_COMMAND,
  HOLD_COMMAND,
  PRIMARY_COMMAND,
  SECONDARY_COMMAND,
  STOP_COMMAND,
} from './commands';
import { Icon, type IconName } from './icons/icon';

export type CommandTone = 'primary' | 'secondary' | 'destructive' | 'go' | 'hold' | 'stop';

const LOOKS: Readonly<Record<CommandTone, string>> = {
  primary: PRIMARY_COMMAND,
  secondary: SECONDARY_COMMAND,
  destructive: DESTRUCTIVE_COMMAND,
  go: GO_COMMAND,
  hold: HOLD_COMMAND,
  stop: STOP_COMMAND,
};

type CommandButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'className' | 'type'> & {
  readonly tone: CommandTone;
  readonly icon?: IconName;
  readonly type?: 'button' | 'submit';
  readonly children: ReactNode;
};

/**
 * A command of the dashboard, with the look of its tone and an icon beside its text: the text stays, names the command
 * and is what screen readers read; the colour is never the only sign (ADR icone-con-lucide-react-e-comandi-condivisi).
 */
export const CommandButton = ({
  tone,
  icon,
  type = 'button',
  children,
  ...button
}: CommandButtonProps) => (
  <button type={type} className={LOOKS[tone]} {...button}>
    {icon !== undefined && <Icon name={icon} />}
    {children}
  </button>
);
