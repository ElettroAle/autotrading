// ADR-campanello-delle-notifiche-nella-dashboard (R6.2.1): the bell lives in the shared bar on top, between the badge of
// the installation and the menu of the user; it reads the number of the unread notifications as page data, draws only
// the shared icon, imports no feature, and leads each notification to the page config/paths builds for its kind.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const DASHBOARD = fileURLToPath(new URL('..', import.meta.url));

type SourceFile = { readonly path: string; readonly source: string };

const HEADER = 'src/components/layouts/app-header.tsx';
const BELL = 'src/components/layouts/notification-bell.tsx';
const COUNT = 'src/hooks/use-unread-notifications-count.ts';
const DESTINATION = 'src/utils/notification-destination.ts';

const read = (path: string): SourceFile => ({
  path,
  source: readFileSync(`${DASHBOARD}${path}`, 'utf8'),
});

const file = (path: string, source: string): SourceFile => ({ path, source });

/** Where the bell stands in the bar: after the badge of the installation, before the menu of the user. */
const headerViolations = ({ path, source }: SourceFile): string[] => {
  const badge = source.indexOf('<EnvironmentBadge');
  const bell = source.indexOf('<NotificationBell');
  const user = source.indexOf('<UserMenu');
  if (bell === -1) {
    return [`${path}: la barra non mostra il campanello`];
  }
  return badge < bell && bell < user
    ? []
    : [`${path}: il campanello non sta tra l'ambiente e l'utente`];
};

/** What the bell may use: the shared icon, the number and the destinations of the shared code, no feature. */
const bellViolations = ({ path, source }: SourceFile): string[] => [
  ...(source.includes("from '@/features") ? [`${path}: importa una funzionalità`] : []),
  ...(source.includes("from 'lucide-react'") ? [`${path}: disegna un'icona propria`] : []),
  ...(source.includes('<Icon name="bell"')
    ? []
    : [`${path}: non usa l'icona condivisa del campanello`]),
  ...(source.includes("from '@/hooks/use-unread-notifications-count'")
    ? []
    : [`${path}: non legge il numero delle non lette`]),
  ...(source.includes("from '@/utils/notification-destination'")
    ? []
    : [`${path}: non porta alla destinazione della notifica`]),
];

const countViolations = ({ path, source }: SourceFile): string[] => [
  ...(source.includes("'/notifications/inbox/summary'")
    ? []
    : [`${path}: il numero non viene da /notifications/inbox/summary`]),
  ...(source.includes('pageDataQuery(') ? [] : [`${path}: il numero non si rilegge con la pagina`]),
];

const destinationViolations = ({ path, source }: SourceFile): string[] =>
  source.includes("from '@/config/paths'") && !/['`]\/(?:flows|alerts)\//.test(source)
    ? []
    : [`${path}: i percorsi non vengono da config/paths`];

/** Each file that breaks the decision, with the reason. */
const misplacedBell = (
  header: SourceFile,
  bell: SourceFile,
  count: SourceFile,
  destination: SourceFile,
) => [
  ...headerViolations(header),
  ...bellViolations(bell),
  ...countViolations(count),
  ...destinationViolations(destination),
];

const CONFORMING = {
  header: file(
    HEADER,
    '<EnvironmentBadge environment={environment} />\n<NotificationBell />\n<UserMenu />',
  ),
  bell: file(
    BELL,
    [
      "import { Icon } from '@/components/ui/icons/icon';",
      "import { useUnreadNotificationsCount } from '@/hooks/use-unread-notifications-count';",
      "import { destinationOf } from '@/utils/notification-destination';",
      '<Icon name="bell" />',
    ].join('\n'),
  ),
  count: file(
    COUNT,
    "...pageDataQuery('notifications', 'summary'), api.GET('/notifications/inbox/summary')",
  ),
  destination: file(
    DESTINATION,
    "import { paths } from '@/config/paths';\npaths.flow.getHref(flowId)",
  ),
};

const conforming = (): [SourceFile, SourceFile, SourceFile, SourceFile] => [
  CONFORMING.header,
  CONFORMING.bell,
  CONFORMING.count,
  CONFORMING.destination,
];

describe('ADR-campanello-delle-notifiche-nella-dashboard: the bell in the shared bar on top', () => {
  it('is red when the bar does not show the bell, or shows it elsewhere', () => {
    const [, bell, count, destination] = conforming();

    expect(
      misplacedBell(file(HEADER, '<EnvironmentBadge />\n<UserMenu />'), bell, count, destination),
    ).toEqual([`${HEADER}: la barra non mostra il campanello`]);
    expect(
      misplacedBell(
        file(HEADER, '<UserMenu />\n<EnvironmentBadge />\n<NotificationBell />'),
        bell,
        count,
        destination,
      ),
    ).toEqual([`${HEADER}: il campanello non sta tra l'ambiente e l'utente`]);
  });

  it('is red when the bell imports a feature, draws its own icon and reads nothing of the shared code', () => {
    const [header, , count, destination] = conforming();
    const bell = file(
      BELL,
      "import { Bell } from 'lucide-react';\nimport { useAlerts } from '@/features/alerts/api/get-alerts';",
    );

    expect(misplacedBell(header, bell, count, destination)).toEqual([
      `${BELL}: importa una funzionalità`,
      `${BELL}: disegna un'icona propria`,
      `${BELL}: non usa l'icona condivisa del campanello`,
      `${BELL}: non legge il numero delle non lette`,
      `${BELL}: non porta alla destinazione della notifica`,
    ]);
  });

  it('is red when the number is not page data of the summary of the bell', () => {
    const [header, bell, , destination] = conforming();

    expect(
      misplacedBell(header, bell, file(COUNT, "useQuery({ queryKey: ['bell'] })"), destination),
    ).toEqual([
      `${COUNT}: il numero non viene da /notifications/inbox/summary`,
      `${COUNT}: il numero non si rilegge con la pagina`,
    ]);
  });

  it('is red when the destinations write their own routes', () => {
    const [header, bell, count] = conforming();

    expect(
      misplacedBell(header, bell, count, file(DESTINATION, 'const flow = `/flows/${id}`;')),
    ).toEqual([`${DESTINATION}: i percorsi non vengono da config/paths`]);
  });

  it('is silent on a bell placed and built as decided', () => {
    expect(misplacedBell(...conforming())).toEqual([]);
  });

  it('finds the bell of the dashboard placed and built as decided', () => {
    expect(misplacedBell(read(HEADER), read(BELL), read(COUNT), read(DESTINATION))).toEqual([]);
  });
});
