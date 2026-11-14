import { PageLayout } from '@/components/layouts/page-layout';
import { LinkCodePanel } from '@/features/notifications/components/link-code-panel';
import { LinkedChatPanel } from '@/features/notifications/components/linked-chat-panel';

export const NotificationsRoute = () => (
  <PageLayout title="Notifiche Telegram">
    <div className="space-y-4">
      <LinkedChatPanel />
      <LinkCodePanel />
    </div>
  </PageLayout>
);
