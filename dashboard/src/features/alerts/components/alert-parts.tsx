import { Link } from 'react-router';

import { Icon } from '@/components/ui/icons/icon';
import { paths } from '@/config/paths';
import { formatInstant } from '@/utils/format-instant';

import type { Alert, AlertSeverity } from '../api/get-alerts';

type SeverityLook = { readonly label: string; readonly look: string };

// The text names the severity and the colour only underlines it (ADR icone-con-lucide-react-e-comandi-condivisi).
const SEVERITIES: Readonly<Record<AlertSeverity, SeverityLook>> = {
  critical: { label: 'Critica', look: 'text-red-700' },
  warning: { label: 'Attenzione', look: 'text-amber-700' },
};

export const SEVERITY_LABELS: Readonly<Record<AlertSeverity, string>> = {
  critical: SEVERITIES.critical.label,
  warning: SEVERITIES.warning.label,
};

/** The severity of an alert: an icon and its word, red when critical, amber when it asks for attention. */
export const AlertSeverityLabel = ({ severity }: { readonly severity: AlertSeverity }) => {
  const { label, look } = SEVERITIES[severity];
  return (
    <span className={`inline-flex items-center gap-1 font-medium ${look}`}>
      <Icon name="triangle-alert" />
      {label}
    </span>
  );
};

const RESOURCE_KINDS: Readonly<Record<Alert['resource']['kind'], string>> = {
  account: 'Conto',
  flow: 'Flusso',
  key: 'Chiave',
};

export const RESOURCE_KIND_LABELS = RESOURCE_KINDS;

// The page where the user acts on the resource: the box of the account, the page of the flow, the keys.
const resourceHrefOf = (resource: Alert['resource']): string => {
  if (resource.kind === 'flow') {
    return paths.flow.getHref(resource.id);
  }
  if (resource.kind === 'key') {
    return paths.providerKeys.getHref();
  }
  return paths.accounts.getHref();
};

/** The resource the alert is about, with the link to where the user acts on it. */
export const AlertResourceLink = ({ resource }: { readonly resource: Alert['resource'] }) => (
  <Link to={resourceHrefOf(resource)} className="text-blue-800 underline wrap-anywhere">
    {`${RESOURCE_KINDS[resource.kind]} ${resource.name}`}
  </Link>
);

/** The state of an alert: open, or when it was resolved. */
export const alertStateOf = (alert: Pick<Alert, 'resolved_at'>): string =>
  alert.resolved_at === null ? 'Aperto' : `Risolto il ${formatInstant(alert.resolved_at)}`;
