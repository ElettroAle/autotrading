import { Icon, type IconName } from './icons/icon';

// The actions of the agent as the API writes them, the values of TradeAction (R6.5.3).
const ICONS: ReadonlyMap<string, IconName> = new Map([
  ['apri', 'plus'],
  ['chiudi', 'x'],
  ['mantieni', 'pause'],
  ['aggiorna', 'refresh'],
  ['inverti', 'arrow-left-right'],
]);

/** An action of the agent, with its icon; an action it does not know shows as the API wrote it. */
export const ActionLabel = ({ value }: { readonly value: string }) => {
  const icon = ICONS.get(value);
  if (icon === undefined) {
    return <span>{value}</span>;
  }
  return (
    <span className="inline-flex items-center gap-1">
      <Icon name={icon} />
      {value}
    </span>
  );
};
