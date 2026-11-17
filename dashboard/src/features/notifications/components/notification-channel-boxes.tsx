import type { MailServer } from '../api/get-mail-server';

import { ChannelBox } from './channel-box';
import { LinkCodePanel } from './link-code-panel';
import { LinkedChatPanel } from './linked-chat-panel';
import { MailServerPanel } from './mail-server-panel';
import { NotificationEmailPanel } from './notification-email-panel';

/** What the channels of the user reach today, as the page reads it from the API. */
export type ChannelLinks = {
  readonly chatId: number | null;
  readonly server: MailServer | null;
  readonly address: string | null;
};

/** What the Telegram channel reaches, undefined while no chat is linked. */
export const telegramLinkOf = ({ chatId }: ChannelLinks): string | undefined =>
  chatId === null ? undefined : `chat ${chatId}`;

/** What the email channel reaches: only a server and an address together send an email. */
export const emailLinkOf = ({ server, address }: ChannelLinks): string | undefined =>
  server === null || address === null ? undefined : `${server.host} · ${address}`;

/**
 * The channels side by side from `md` up, one below the other on a phone, every one in the same shape (ADR
 * pagina-notifiche-a-schede).
 */
export const NotificationChannelBoxes = ({ links }: { readonly links: ChannelLinks }) => (
  <div className="grid items-start gap-4 md:grid-cols-2">
    <ChannelBox title="Telegram" linkedTo={telegramLinkOf(links)}>
      <LinkedChatPanel />
      <LinkCodePanel />
    </ChannelBox>
    <ChannelBox title="Email" linkedTo={emailLinkOf(links)}>
      <MailServerPanel />
      <NotificationEmailPanel serverConfigured={links.server !== null} />
    </ChannelBox>
  </div>
);
