/** A channel of the platform, by the name the user reads (R3.5.3). */
export type FakeChannel = 'Telegram' | 'email';

/** The channels of a type of event, in the order of the channels; none for no notification. */
export type FakeChoice = readonly FakeChannel[];

/** A type of event in the order the API lists it, whether a flow may except it, and its channels by default. */
type FakeEventType = {
  readonly event: string;
  readonly ofFlow: boolean;
  readonly byDefault: FakeChoice;
};

const TELEGRAM_ONLY: FakeChoice = ['Telegram'];
const SILENT: FakeChoice = [];

const flowEvent = (event: string, byDefault: FakeChoice = TELEGRAM_ONLY): FakeEventType => ({
  event,
  ofFlow: true,
  byDefault,
});

const accountEvent = (event: string): FakeEventType => ({
  event,
  ofFlow: false,
  byDefault: TELEGRAM_ONLY,
});

/** The types of event of R1.8.2 and R3.5.1, as the API lists them. */
export const FAKE_EVENT_TYPES: readonly FakeEventType[] = [
  flowEvent('apertura di una posizione'),
  flowEvent('chiusura di una posizione'),
  flowEvent('stop loss attivato'),
  flowEvent('take profit attivato'),
  flowEvent('liquidazione di una posizione'),
  flowEvent('ciclo fallito'),
  flowEvent('ordine rifiutato'),
  flowEvent('pausa automatica di un flusso'),
  flowEvent('perdita massima raggiunta'),
  flowEvent('decisione ridotta dal rischio', SILENT),
  flowEvent('decisione bloccata dal rischio', SILENT),
  accountEvent('posizione non attribuibile'),
  accountEvent('esecuzione non attribuibile'),
  accountEvent('allarme di riconciliazione'),
  flowEvent('incasso eseguito'),
  accountEvent('chiusura di emergenza eseguita'),
  accountEvent('scadenza di una chiave'),
  accountEvent('credenziali di una fonte rifiutate'),
];

/** Every channel of the platform, in its order (ADR canali-delle-notifiche-come-insieme). */
export const FAKE_CHANNELS: readonly FakeChannel[] = ['Telegram', 'email'];

/** The channels given, once each and in the order of the channels, as the API keeps a set. */
export const choiceOf = (channels: readonly FakeChannel[]): FakeChoice =>
  FAKE_CHANNELS.filter((channel) => channels.includes(channel));

type FakeChoices = Map<string, FakeChoice>;

type FakeChannelPreferences = {
  readonly general: FakeChoices;
  readonly exceptions: Map<string, FakeChoices>;
};

const preferences = new Map<string, FakeChannelPreferences>();

const preferencesOf = (account: string): FakeChannelPreferences => {
  const known = preferences.get(account);
  if (known !== undefined) {
    return known;
  }
  const created = {
    general: new Map<string, FakeChoice>(),
    exceptions: new Map<string, FakeChoices>(),
  };
  preferences.set(account, created);
  return created;
};

/** The channels each user of the fake platform chose, with the exceptions of their flows (R3.5.3). */
export const fakeNotificationChannels = {
  reset(): void {
    preferences.clear();
  },

  channelsOf(account: string, event: string): FakeChoice {
    const chosen = preferencesOf(account).general.get(event);
    return (
      chosen ?? FAKE_EVENT_TYPES.find((type) => type.event === event)?.byDefault ?? TELEGRAM_ONLY
    );
  },

  choose(account: string, event: string, channels: readonly FakeChannel[]): void {
    preferencesOf(account).general.set(event, choiceOf(channels));
  },

  exceptionsOf(account: string, flowId: string): ReadonlyMap<string, FakeChoice> {
    return preferencesOf(account).exceptions.get(flowId) ?? new Map<string, FakeChoice>();
  },

  except(account: string, flowId: string, event: string, channels: readonly FakeChannel[]): void {
    const { exceptions } = preferencesOf(account);
    exceptions.set(
      flowId,
      new Map([...(exceptions.get(flowId) ?? []), [event, choiceOf(channels)]]),
    );
  },

  removeException(account: string, flowId: string, event: string): void {
    preferencesOf(account).exceptions.get(flowId)?.delete(event);
  },
};
