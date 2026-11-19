import { useEffect, useId, useRef, useState } from 'react';
import { useNavigate } from 'react-router';

import { ErrorMessage } from '@/components/ui/error-message';
import { Icon } from '@/components/ui/icons/icon';
import { Loading } from '@/components/ui/loading';
import {
  useInboxNotifications,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  type InboxNotification,
} from '@/hooks/use-notification-inbox';
import { useUnreadNotificationsCount } from '@/hooks/use-unread-notifications-count';
import { formatInstant } from '@/utils/format-instant';
import { destinationOf } from '@/utils/notification-destination';

// Beyond two digits the mark would grow over the bar on a phone: the exact number stays in the name of the bell.
const MOST_SHOWN = 99;

const unreadMarkOf = (count: number): string =>
  count > MOST_SHOWN ? `${MOST_SHOWN}+` : String(count);

const NotificationItem = ({
  notification,
  onChoose,
}: {
  readonly notification: InboxNotification;
  readonly onChoose: (notification: InboxNotification) => void;
}) => {
  const unread = notification.read_at === null;
  return (
    <li className="border-b border-slate-100 last:border-b-0">
      <button
        type="button"
        onClick={() => onChoose(notification)}
        className="flex min-h-11 w-full gap-2 px-3 py-2 text-left hover:bg-slate-50"
      >
        <span aria-hidden="true">{notification.icon}</span>
        <span className="min-w-0 flex-1">
          <span
            className={`flex items-center gap-1 wrap-anywhere ${unread ? 'font-semibold' : ''}`}
          >
            {unread ? (
              <span className="inline-block size-2 shrink-0 rounded-full bg-blue-700">
                <span className="sr-only">non letta</span>
              </span>
            ) : null}
            {notification.title}
          </span>
          {notification.text === '' ? null : (
            <span className="block text-sm whitespace-pre-line text-slate-700 wrap-anywhere">
              {notification.text}
            </span>
          )}
          <span className="block text-xs text-slate-500">
            {formatInstant(notification.notified_at)}
          </span>
        </span>
      </button>
    </li>
  );
};

const NotificationList = ({
  onChoose,
}: {
  readonly onChoose: (notification: InboxNotification) => void;
}) => {
  const { data, error, isPending, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useInboxNotifications(true);
  if (isPending) {
    return <Loading />;
  }
  if (error !== null) {
    return <ErrorMessage error={error} />;
  }
  const notifications = data.pages.flatMap((page) => page.items);
  if (notifications.length === 0) {
    return <p className="px-3 py-4 text-sm text-slate-600">Nessuna notifica</p>;
  }
  return (
    <>
      <ul>
        {notifications.map((notification) => (
          <NotificationItem key={notification.id} notification={notification} onChoose={onChoose} />
        ))}
      </ul>
      {hasNextPage ? (
        <button
          type="button"
          disabled={isFetchingNextPage}
          onClick={() => void fetchNextPage()}
          className="min-h-11 w-full px-3 text-sm font-medium text-blue-800 hover:bg-slate-50"
        >
          Mostra altre
        </button>
      ) : null}
    </>
  );
};

/**
 * The bell of the bar on top, beside the name of the user: how many notifications are unread, and the panel that lists
 * them newest first (R6.2.1, ADR campanello-delle-notifiche-nella-dashboard). Choosing a notification reads it and leads
 * to its first page; the panel closes with Esc, giving the focus back to the bell, and with a click outside it.
 */
export const NotificationBell = () => {
  const { data: count = 0 } = useUnreadNotificationsCount();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const area = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const closeOutside = (event: PointerEvent) => {
      if (!(event.target instanceof Node && area.current?.contains(event.target) === true)) {
        setOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') {
        return;
      }
      setOpen(false);
      trigger.current?.focus();
    };
    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOutside);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [open]);

  const choose = (notification: InboxNotification) => {
    setOpen(false);
    markRead.mutate(notification.id);
    const destination = destinationOf(notification.targets[0]);
    if (destination !== undefined) {
      void navigate(destination);
    }
  };

  return (
    <div ref={area}>
      <button
        ref={trigger}
        type="button"
        aria-label={`Notifiche, ${count} non lette`}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((wasOpen) => !wasOpen)}
        className="relative flex min-h-11 min-w-11 items-center justify-center rounded hover:bg-slate-100"
      >
        <Icon name="bell" />
        {count === 0 ? null : (
          <span
            data-testid="unread-count"
            className="absolute top-1 right-0 rounded-full bg-red-700 px-1.5 text-xs leading-4 font-semibold text-white"
          >
            {unreadMarkOf(count)}
          </span>
        )}
      </button>
      {open ? (
        // Under the bar, as wide as the screen allows on a phone and at most 24rem elsewhere.
        <div
          id={panelId}
          role="dialog"
          aria-label="Notifiche"
          className="absolute top-full right-4 z-20 mt-1 max-h-[70vh] w-[min(24rem,calc(100vw-2rem))] overflow-y-auto rounded border border-slate-200 bg-white shadow-md md:right-6"
        >
          <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-3 py-2">
            <h2 className="font-semibold">Notifiche</h2>
            {count === 0 ? null : (
              <button
                type="button"
                onClick={() => markAllRead.mutate()}
                className="min-h-11 rounded px-2 text-sm font-medium text-blue-800 hover:bg-slate-100"
              >
                Segna tutte come lette
              </button>
            )}
          </div>
          <NotificationList onChoose={choose} />
        </div>
      ) : null}
    </div>
  );
};
