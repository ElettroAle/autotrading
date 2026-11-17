import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';

import { Icon } from '@/components/ui/icons/icon';
import { useSignedInUserName } from '@/lib/auth';

import { SignOutButton } from './sign-out-button';

/**
 * The area of the signed-in user, on the right of the bar on top: the name opens a menu that holds «Esci». The menu
 * closes with Esc, giving the focus back to the name, and with a click outside it (ADR area-utente-in-alto-a-destra).
 */
export const UserMenu = () => {
  const name = useSignedInUserName();
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const area = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLUListElement>(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    menu.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();
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

  if (name === undefined) {
    return null;
  }

  const closeOnEscape = (event: KeyboardEvent) => {
    if (event.key !== 'Escape' || !open) {
      return;
    }
    setOpen(false);
    trigger.current?.focus();
  };

  return (
    <div ref={area} className="relative min-w-0">
      <button
        ref={trigger}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((wasOpen) => !wasOpen)}
        onKeyDown={closeOnEscape}
        className="flex min-h-11 max-w-full min-w-11 items-center gap-1 rounded px-2 text-sm hover:bg-slate-100"
      >
        <Icon name="user" />
        <span className="max-w-28 min-w-0 truncate md:max-w-48">{name}</span>
        <Icon name="chevron-down" />
      </button>
      {open ? (
        <ul
          ref={menu}
          id={menuId}
          role="menu"
          aria-label={name}
          onKeyDown={closeOnEscape}
          className="absolute right-0 z-10 mt-1 min-w-32 rounded border border-slate-200 bg-white p-1 shadow-md"
        >
          <li role="none">
            <SignOutButton />
          </li>
        </ul>
      ) : null}
    </div>
  );
};
