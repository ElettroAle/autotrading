import {
  apiSearchOf as periodSearchOf,
  type Period,
} from '@/components/ui/period-selector/use-period';

/** The three histories of the page, by the path of their endpoint (ADR 0138). */
export const HISTORY_TABS = [
  { kind: 'cycles', label: 'Cicli' },
  { kind: 'closed-positions', label: 'Posizioni chiuse' },
  { kind: 'orders', label: 'Ordini' },
] as const;

export type HistoryKind = (typeof HISTORY_TABS)[number]['kind'];

/** What the page asks of a history besides the period: an empty value does not narrow. */
export type HistorySearch = {
  readonly kind: HistoryKind;
  readonly flow: string;
  readonly account: string;
  readonly asset: string;
  readonly version: string;
};

const TAB = 'tab';
const FIELDS = ['flow', 'account', 'asset', 'version'] as const;

type Field = (typeof FIELDS)[number];

const isKind = (value: string | null): value is HistoryKind =>
  HISTORY_TABS.some((tab) => tab.kind === value);

/** The search of the query string; without a tab, or with one the page does not know, the cycles. */
export const searchOf = (params: URLSearchParams): HistorySearch => {
  const tab = params.get(TAB);
  const field = (name: Field) => params.get(name) ?? '';
  return {
    kind: isKind(tab) ? tab : 'cycles',
    flow: field('flow'),
    account: field('account'),
    asset: field('asset'),
    version: field('version'),
  };
};

/**
 * The query string with the change: the other parameters, the period among them, stay; empty values leave no trace.
 * A version is numbered within its flow, so choosing another flow, or none, forgets it (ADR 0139).
 */
export const withSearch = (
  current: URLSearchParams,
  change: Partial<HistorySearch>,
): URLSearchParams => {
  const next = new URLSearchParams(current);
  const flowChanged = change.flow !== undefined && change.flow !== (current.get('flow') ?? '');
  const values = { ...(flowChanged ? { version: '' } : {}), ...change };
  Object.entries(values).forEach(([name, value]) => {
    const parameter = name === 'kind' ? TAB : name;
    if (value === '') {
      next.delete(parameter);
    } else {
      next.set(parameter, value);
    }
  });
  return next;
};

const API_NAMES: Record<Field, string> = {
  flow: 'flow_id',
  account: 'account_id',
  asset: 'asset',
  version: 'version',
};

/**
 * The query string of the API: every filter as the page holds it, even a version without its flow, as the API alone
 * decides what a search means (ADR 0139).
 */
export const apiSearchOf = (search: HistorySearch, period: Period): string => {
  const params = new URLSearchParams(periodSearchOf(period));
  FIELDS.forEach((field) => {
    if (search[field] !== '') {
      params.set(API_NAMES[field], search[field]);
    }
  });
  return params.toString();
};
