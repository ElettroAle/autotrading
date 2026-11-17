import { useState } from 'react';
import { useSearchParams } from 'react-router';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { ViewTabs } from '@/components/ui/view-tabs';
import { useSearchChange } from '@/hooks/use-search-change';

import { useLinkedChat } from '../api/get-linked-chat';
import { useMailServer } from '../api/get-mail-server';
import { useNotificationEmail } from '../api/get-notification-email';
import { tabOf, withTab, type NotificationTab } from '../utils/notification-tabs';

import {
  NotificationChannelBoxes,
  emailLinkOf,
  telegramLinkOf,
  type ChannelLinks,
} from './notification-channel-boxes';
import { NotificationChannelsPanel } from './notification-channels-panel';

/** How many channels are still to configure. */
export const toConfigureOf = (links: ChannelLinks): number =>
  [telegramLinkOf(links), emailLinkOf(links)].filter((link) => link === undefined).length;

const CHANNELS = 2;

type NotificationTabsProps = { readonly links: ChannelLinks };

const NotificationTabs = ({ links }: NotificationTabsProps) => {
  const [params] = useSearchParams();
  const changeSearch = useSearchChange();
  const toConfigure = toConfigureOf(links);
  // The page opens on the channels while none is linked; the opening stays while the user links them.
  const [opening] = useState<NotificationTab>(
    toConfigure === CHANNELS ? 'channels' : 'preferences',
  );
  const current = tabOf(params) ?? opening;
  const tabs = [
    { key: 'preferences', name: 'Preferenze' },
    { key: 'channels', name: toConfigure === 0 ? 'Canali' : `Canali (${toConfigure})` },
  ] as const;
  return (
    <>
      <ViewTabs
        label="Viste delle notifiche"
        tabs={tabs}
        current={current}
        choose={(tab) => changeSearch((search) => withTab(search, tab))}
      />
      {current === 'preferences' ? (
        <NotificationChannelsPanel />
      ) : (
        <NotificationChannelBoxes links={links} />
      )}
    </>
  );
};

/**
 * The page of the notifications in two tabs: Preferenze, the choice of the channels, by default; Canali, Telegram and
 * Email, with the number of channels still to configure (ADR pagina-notifiche-a-schede).
 */
export const NotificationsView = () => {
  const chat = useLinkedChat();
  const email = useNotificationEmail();
  const server = useMailServer();
  const failed = chat.error ?? email.error ?? server.error;
  if (failed !== null) {
    return <ErrorMessage error={failed} />;
  }
  if (!chat.isSuccess || !email.isSuccess || !server.isSuccess) {
    return <Loading />;
  }
  return (
    <NotificationTabs
      links={{ chatId: chat.data.chat_id, server: server.data, address: email.data.address }}
    />
  );
};
