import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { LinkCodePanel } from '@/features/notifications/components/link-code-panel';
import { LinkedChatPanel } from '@/features/notifications/components/linked-chat-panel';
import { NotificationChannelsPanel } from '@/features/notifications/components/notification-channels-panel';
import { NotificationEmailPanel } from '@/features/notifications/components/notification-email-panel';

const SECTION_HEADING_ID = 'telegram-notifications-heading';
const EMAIL_HEADING_ID = 'email-notifications-heading';
const CHANNELS_HEADING_ID = 'notification-channels-heading';

export const NotificationsRoute = () => (
  <DashboardLayout title="Notifiche">
    <section aria-labelledby={SECTION_HEADING_ID} className="space-y-4">
      <h2 id={SECTION_HEADING_ID} className="text-lg font-semibold">
        Notifiche Telegram
      </h2>
      <LinkedChatPanel />
      <LinkCodePanel />
    </section>
    <section aria-labelledby={EMAIL_HEADING_ID} className="mt-6 space-y-4">
      <h2 id={EMAIL_HEADING_ID} className="text-lg font-semibold">
        Notifiche email
      </h2>
      <NotificationEmailPanel />
    </section>
    <section aria-labelledby={CHANNELS_HEADING_ID} className="mt-6 space-y-4">
      <h2 id={CHANNELS_HEADING_ID} className="text-lg font-semibold">
        Scelta dei canali
      </h2>
      <NotificationChannelsPanel />
    </section>
  </DashboardLayout>
);
