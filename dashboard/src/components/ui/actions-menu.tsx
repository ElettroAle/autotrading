import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';

import { SECONDARY_COMMAND } from './commands';
import { Icon } from './icons/icon';

/** An action of the menu: its name, what it does, and whether it destroys something. */
export type MenuAction = {
  readonly name: string;
  readonly onSelect: () => void;
  readonly destructive?: boolean;
};

type ActionsMenuProps = {
  /** The name of the menu, which starts with what it shows: «Azioni del conto principale». */
  readonly label: string;
  readonly actions: readonly MenuAction[];
};

const ITEM = 'block min-h-11 w-full rounded px-3 text-left whitespace-nowrap hover:bg-slate-100';
const DESTRUCTIVE_ITEM = `${ITEM} text-red-800`;

// The arrows move among the actions round the ends, as a menu does (WAI-ARIA menu button pattern).
const STEPS: Readonly<Record<string, number>> = { ArrowDown: 1, ArrowUp: -1 };

/**
 * The actions of an element of a list behind one command «Azioni», so the element stays one line long: the menu
 * focuses its first action, moves with the arrows, and closes with Esc, giving the focus back to «Azioni», with a click
 * outside it or once an action is chosen (ADR elenco-dei-conti-e-pagina-del-conto).
 */
export const ActionsMenu = ({ label, actions }: ActionsMenuProps) => {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const area = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const items = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    items.current[0]?.focus();
    const closeOutside = (event: PointerEvent) => {
      if (!(event.target instanceof Node && area.current?.contains(event.target) === true)) {
        setOpen(false);
      }
    };
    document.addEventListener('pointerdown', closeOutside);
    return () => {
      document.removeEventListener('pointerdown', closeOutside);
    };
  }, [open]);

  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && open) {
      close();
      return;
    }
    const step = STEPS[event.key];
    if (step === undefined || !open) {
      return;
    }
    event.preventDefault();
    const focused = items.current.findIndex((item) => item === document.activeElement);
    items.current[(focused + step + actions.length) % actions.length]?.focus();
  };

  const choose = (action: MenuAction) => {
    setOpen(false);
    action.onSelect();
  };

  return (
    <div ref={area} className="relative">
      <button
        ref={trigger}
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((wasOpen) => !wasOpen)}
        onKeyDown={onKeyDown}
        className={SECONDARY_COMMAND}
      >
        Azioni
        <Icon name="chevron-down" />
      </button>
      {open ? (
        <ul
          id={menuId}
          role="menu"
          aria-label={label}
          onKeyDown={onKeyDown}
          className="absolute right-0 z-20 mt-1 min-w-48 rounded border border-slate-200 bg-white p-1 shadow-md"
        >
          {actions.map((action, position) => (
            <li key={action.name} role="none">
              <button
                ref={(item) => {
                  items.current[position] = item;
                }}
                type="button"
                role="menuitem"
                onClick={() => choose(action)}
                className={action.destructive === true ? DESTRUCTIVE_ITEM : ITEM}
              >
                {action.name}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
};
