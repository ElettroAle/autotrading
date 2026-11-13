# ADR 0085 — Tipi di supporto e contratti interni degli adapter

- Stato: accettata (13 novembre 2026)
- Requisiti: Bug 175 (B0.0.2); Task T0.0.1 (test di architettura)
- Collegate: ADR 0018 (SDK ufficiale di Hyperliquid), ADR 0042 (pianificazione dei cicli)

## Contesto

I test di architettura del Task T0.0.1 fanno valere tre regole che il codice violava in 17 punti, tutti elencati
sotto il Bug 175:

- un `Protocol` vive solo in `application/<contesto>/ports.py`;
- una classe pubblica di `adapters/outbound/<tecnologia>/` è un `<Tecnologia><Ruolo>Adapter` o un `*Error`;
- domain e application non nominano tecnologie, e un `*Command` è una dataclass frozen.

I casi erano di quattro tipi: contratti interni scritti come `Protocol` (il parametro di un modello nel domain, i
cicli in background del worker, l'SDK di Hyperliquid), classi di supporto degli adapter pubbliche, un enum chiamato
come un comando, e "Telegram" nei messaggi degli errori di application.

## Decisione

- **Un insieme chiuso si scrive come unione, non come `Protocol`.** `ModelParameter` è
  `RangeParameter | ChoiceParameter`; `BackgroundLoop` è `BotPolling | CyclePolling`. I tipi sono quelli che
  esistono: un tipo nuovo entra nell'unione, e mypy controlla ogni uso.
- **L'SDK di Hyperliquid è un adapter concreto.** `HyperliquidSdkAdapter` incapsula `Exchange` e `Info`
  dell'SDK ufficiale ed è l'unico punto che li costruisce. Gli adapter della cartella lo ricevono nel costruttore. Un
  test passa una sottoclasse che risponde al posto dell'exchange, invece di un oggetto che soddisfa un `Protocol`.
- **Le classi di supporto di un adapter sono private.** Il prefisso `_` le nasconde a `bootstrap.py` e alle altre
  cartelle. Restano visibili ai moduli della stessa cartella di tecnologia che le condividono: è il caso dello stato
  letto da Hyperliquid (`_UserState`, `_UserPosition`), che l'adapter dei conti e quello dell'attività traducono
  ciascuno nel proprio tipo di dominio.
- **La configurazione del database è l'adapter del database.** `SqlAlchemyDatabaseAdapter` conosce dove sta il
  database e chi si collega, e costruisce l'engine con `engine()`. La password resta fuori dalla sua
  rappresentazione testuale.
- **Un tipo restituito da una porta vive con la porta.** `TenantScheduledFlow` passa da `sqlalchemy/scheduling.py` a
  `application/cycles/ports.py`, accanto a `ScheduledFlow`.
- **Un enum di azioni non si chiama Command.** `FlowCommand` diventa `FlowAction`: il suffisso `Command` resta ai
  comandi dei casi d'uso.
- **I messaggi di application non nominano il canale.** Diventano "nessuna chat collegata", "messaggio non
  consegnato alla chat" e "bot non raggiungibile". Il canale si legge dal contesto delle notifiche.

## Alternative scartate

- **Elencare i casi come eccezioni permanenti dei test.** Scartata: l'elenco delle violazioni note può solo scendere,
  e ogni voce ha un Bug che la elimina.
- **Spostare i `Protocol` interni in `application/*/ports.py`.** Scartata: non sono porte. Il ciclo in background
  usa `threading.Event`, che application non può importare. L'SDK è un dettaglio di una sola tecnologia.
- **Funzioni o tuple al posto dei record privati condivisi.** Scartata: perde i nomi dei campi e la verifica di mypy
  senza togliere nessuna dipendenza.

## Conseguenze

- I test di architettura non hanno più voci del Bug 175.
- Chi scrive un fake dell'SDK lo deriva da `HyperliquidSdkAdapter`.
- Una nuova classe di supporto in un adapter nasce privata, oppure è un adapter.
- Il dettaglio della risposta 404 sotto `/telegram` per la chat non collegata cambia testo: "nessuna chat collegata".
