import { Icon, type IconName } from './icons/icon';

type Look = { readonly icon: IconName; readonly colour: string };

// The directions the API writes (R6.5.3): the colour is a sign more, the icon and the text are always there.
const DIRECTIONS: ReadonlyMap<string, Look> = new Map([
  ['long', { icon: 'arrow-up', colour: 'text-green-700' }],
  ['short', { icon: 'arrow-down', colour: 'text-red-700' }],
]);

/** The direction of a position or an opening, with its icon; a direction it does not know shows as the API wrote it. */
export const DirectionLabel = ({ value }: { readonly value: string }) => {
  const look = DIRECTIONS.get(value);
  if (look === undefined) {
    return <span>{value}</span>;
  }
  return (
    <span className={`inline-flex items-center gap-1 ${look.colour}`}>
      <Icon name={look.icon} />
      {value}
    </span>
  );
};
