/** The channel of a type of event, by the name the user chooses it by (R3.5.3). */
export type FakeChannel = 'Telegram' | 'email' | 'entrambi' | 'nessuno';

/** A type of event in the order the API lists it, whether a flow may except it, and its channel by default. */
type FakeEventType = {
  readonly event: string;
  readonly ofFlow: boolean;
  readonly byDefault: FakeChannel;
};

const flowEvent = (event: string, byDefault: FakeChannel = 'Telegram'): FakeEventType => ({
  event,
  ofFlow: true,
  byDefault,
});

const accountEvent = (event: string): FakeEventType => ({
  event,
  ofFlow: false,
  byDefault: 'Telegram',
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
  flowEvent('decisione ridotta dal rischio', 'nessuno'),
  flowEvent('decisione bloccata dal rischio', 'nessuno'),
  accountEvent('posizione non attribuibile'),
  accountEvent('esecuzione non attribuibile'),
  accountEvent('movimento non attribuibile'),
  accountEvent('allarme di riconciliazione'),
  flowEvent('incasso eseguito'),
  accountEvent('chiusura di emergenza eseguita'),
];

export const FAKE_CHANNELS: readonly FakeChannel[] = ['Telegram', 'email', 'entrambi', 'nessuno'];

type FakeChoices = Map<string, FakeChannel>;

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
    general: new Map<string, FakeChannel>(),
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

  channelOf(account: string, event: string): FakeChannel {
    const chosen = preferencesOf(account).general.get(event);
    return chosen ?? FAKE_EVENT_TYPES.find((type) => type.event === event)?.byDefault ?? 'Telegram';
  },

  choose(account: string, event: string, channel: FakeChannel): void {
    preferencesOf(account).general.set(event, channel);
  },

  exceptionsOf(account: string, flowId: string): ReadonlyMap<string, FakeChannel> {
    return preferencesOf(account).exceptions.get(flowId) ?? new Map<string, FakeChannel>();
  },

  except(account: string, flowId: string, event: string, channel: FakeChannel): void {
    const { exceptions } = preferencesOf(account);
    exceptions.set(flowId, new Map([...(exceptions.get(flowId) ?? []), [event, channel]]));
  },

  removeException(account: string, flowId: string, event: string): void {
    preferencesOf(account).exceptions.get(flowId)?.delete(event);
  },
};
