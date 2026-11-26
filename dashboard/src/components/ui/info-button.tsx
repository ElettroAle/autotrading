import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type ReactNode,
  type RefObject,
  type SetStateAction,
} from 'react';

import { Icon } from '@/components/ui/icons/icon';

/** Which text of the page is open: only one at a time (R5.5.7). */
type OpenInfo = {
  readonly openId: string | null;
  readonly open: Dispatch<SetStateAction<string | null>>;
};

const OpenInfoContext = createContext<OpenInfo | null>(null);

/** The page keeps one info text open at a time: opening one closes the other (ADR informazioni-sui-campi-di-configurazione). */
export const InfoProvider = ({ children }: { readonly children: ReactNode }) => {
  const [openId, open] = useState<string | null>(null);
  return <OpenInfoContext value={{ openId, open }}>{children}</OpenInfoContext>;
};

// Inside the dashboard the provider of the app decides which text is open; a component shown alone keeps its own.
const useOpenInfo = (): OpenInfo => {
  const shared = useContext(OpenInfoContext);
  const [openId, open] = useState<string | null>(null);
  return shared ?? { openId, open };
};

/**
 * Esc and a click outside the button and the text close the open text (R5.5.7): Esc gives the focus back to the button,
 * a click leaves it where the user put it. The click is the whole gesture, not the press: closing on the press would
 * move the fields under the pointer before it is released, and the click meant for another button would be lost.
 */
const useClosing = (
  opened: boolean,
  close: (refocus: boolean) => void,
  inside: readonly RefObject<HTMLElement | null>[],
) => {
  useEffect(() => {
    if (!opened) {
      return undefined;
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close(true);
      }
    };
    const closeOutside = (event: MouseEvent) => {
      if (!inside.some((element) => element.current?.contains(event.target as Node) === true)) {
        close(false);
      }
    };
    document.addEventListener('keydown', closeOnEscape);
    document.addEventListener('click', closeOutside);
    return () => {
      document.removeEventListener('keydown', closeOnEscape);
      document.removeEventListener('click', closeOutside);
    };
  }, [opened, close, inside]);
};

type InfoButtonProps = {
  /** The label of the field, which names the button «Informazioni su <label>». */
  readonly label: string;
  /** What the field does, the values it admits and its default or what leaving it empty means. */
  readonly text: string;
};

/**
 * The info button beside the label of a field: a click, a touch, Enter or Space open its text on a line of its own
 * under the label, Esc, a click outside or a new activation close it (R5.5.7, ADR
 * informazioni-sui-campi-di-configurazione). Its parent is a wrapping flex row, so the text takes the whole width.
 */
export const InfoButton = ({ label, text }: InfoButtonProps) => {
  const textId = useId();
  const buttonId = useId();
  const { openId, open } = useOpenInfo();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const textRef = useRef<HTMLParagraphElement>(null);
  const inside = useMemo(() => [buttonRef, textRef], []);
  const opened = openId === textId;
  const close = useCallback(
    (refocus: boolean) => {
      // Only its own text: the click that closes it may have just opened another one.
      open((current) => (current === textId ? null : current));
      if (refocus) {
        buttonRef.current?.focus();
      }
    },
    [open, textId],
  );
  useClosing(opened, close, inside);

  return (
    <>
      <button
        ref={buttonRef}
        id={buttonId}
        type="button"
        aria-label={`Informazioni su ${label}`}
        aria-expanded={opened}
        aria-controls={textId}
        onClick={() => open((current) => (current === textId ? null : textId))}
        className="rounded-full p-0.5 text-slate-500 hover:text-blue-800 focus-visible:outline-2 focus-visible:outline-blue-700"
      >
        <Icon name="info" />
      </button>
      <p
        ref={textRef}
        id={textId}
        // The note carries the name of its button, so the text of a field is found by the label of the field.
        role="note"
        aria-labelledby={buttonId}
        hidden={!opened}
        className="basis-full rounded border border-slate-200 bg-slate-50 px-2 py-1 text-sm font-normal text-slate-700"
      >
        {text}
      </p>
    </>
  );
};
