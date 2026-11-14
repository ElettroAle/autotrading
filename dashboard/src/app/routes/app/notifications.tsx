import { DashboardLayout } from '@/components/layouts/dashboard-layout';
import { LinkCodePanel } from '@/features/notifications/components/link-code-panel';
import { LinkedChatPanel } from '@/features/notifications/components/linked-chat-panel';

const SECTION_HEADING_ID = 'telegram-notifications-heading';

export const NotificationsRoute = () => (
  <DashboardLayout title="Notifiche">
    <section aria-labelledby={SECTION_HEADING_ID} className="space-y-4">
      <h2 id={SECTION_HEADING_ID} className="text-lg font-semibold">
        Notifiche Telegram
      </h2>
      <LinkedChatPanel />
      <LinkCodePanel />
    </section>
  </DashboardLayout>
);
