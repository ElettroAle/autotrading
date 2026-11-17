/** The two tabs of the page of the notifications: what the user chooses, and the channels it reaches (ADR
 * pagina-notifiche-a-schede). */
export const NOTIFICATION_TABS = ['preferences', 'channels'] as const;

export type NotificationTab = (typeof NOTIFICATION_TABS)[number];

// The tab lives in the query string, so a link opens it and a reload keeps it.
export const TAB_PARAMETER = 'tab';

/** The query string that opens the tab. */
export const searchOfTab = (tab: NotificationTab): string => `?${TAB_PARAMETER}=${tab}`;

/** The tab the query string asks for, undefined when it asks for none the page knows. */
export const tabOf = (params: URLSearchParams): NotificationTab | undefined => {
  const asked = params.get(TAB_PARAMETER);
  return NOTIFICATION_TABS.find((tab) => tab === asked);
};

/** The query string with the tab, the other parameters kept. */
export const withTab = (current: URLSearchParams, tab: NotificationTab): URLSearchParams => {
  const next = new URLSearchParams(current);
  next.set(TAB_PARAMETER, tab);
  return next;
};
