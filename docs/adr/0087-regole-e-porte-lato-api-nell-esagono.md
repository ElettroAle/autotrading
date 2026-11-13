# ADR 0087 — Regole e porte lato API nell'esagono

- Stato: accettata (13 novembre 2026)
- Requisiti: B0.0.1 (Bug 173)
- Collegate: ADR 0088 (ponti fra contesti nelle porte del consumatore), ADR 0089 (un adapter, una tecnologia)

## Contesto

Il test di architettura (Task 174) ha censito in `bootstrap.py`, `application` e `domain` violazioni attribuite al
Bug 173:

- cinque porte definite in `bootstrap.py`;
- tredici decisioni di business nei ponti e nelle funzioni di composizione lato API;
- `concurrent.futures` nel nucleo, in `application/cycles/source_collector.py`;
- l'URL `https://t.me/...` nel dominio, in `domain/notifications/link_code.py`.

Bootstrap deve solo collegare; le regole stanno nel dominio o nei casi d'uso; le tecnologie dietro una porta.

## Decisione

Si applica la decisione del proprietario sui ponti (ADR 0088): il contesto consumatore dichiara le porte, l'adapter
della tecnologia che ha i dati le realizza, le sequenze stanno nel caso d'uso.

- **Conto di un flusso.** `application/flows/ports.py` dichiara `FlowAccountDirectoryPort.exchange_of`
  (realizzata da `SqlAlchemyAccountRepositoryAdapter`) e `FlowAccountBalancePort.balance_of` (realizzata da
  `HttpxAccountStateAdapter`, che traduce gli errori di `accounts` negli errori di `flows`). La sequenza è
  `read_flow_account`, usata dai casi d'uso di `flows` che ricevono le due porte in `FlowAccountPorts`.
  Sparisce `FlowAccountsFromAccounts`.
- **Uso delle chiavi dei fornitori.** `ProviderKeyUsagePort.model_uses()` restituisce i dati `ModelUse`; la regola
  «un flusso attivo usa il fornitore» sta in `RemoveProviderKeyUseCase`. Gli adapter del repository dei flussi
  realizzano `model_uses()` ed `exists()`. Spariscono `ProviderKeyUsageFromFlows` e `FlowDirectoryFromFlows`.
- **Flussi di un conto.** `Flow.runs_on` e `Flow.archivable_on` sono regole del dominio; `ListAccountFlowsUseCase` e
  `ArchiveAccountFlowsUseCase` le applicano. Il ponte in bootstrap resta solo un collegamento senza decisioni.
- **Rete dell'exchange.** `ExchangeNetwork.of_installation` nel dominio `accounts` esprime R0.2.1 (l'installazione
  `dev` opera solo sulla rete di test). Le funzioni `*_for` di bootstrap ricevono la rete invece di decidere.
- **Telegram.** `telegram_channel` (adapter `httpx`) sceglie fra canale configurato e il messaggero non configurato
  quando manca il token del bot; `bot_polling` dell'adapter in ingresso del worker decide se avviare il polling.
- **Prezzi effettivi.** `RecordActualPricesOfTenantsUseCase` scorre i tenant al posto di bootstrap.
- **Chiamate concorrenti.** `ConcurrentCallsPort.call_all` con esito tipizzato (`CallAnswered`, `CallFailed`,
  `CallUnanswered`) è realizzata da `ThreadPoolConcurrentCallsAdapter` in `adapters/outbound/threads/`;
  `SourceCollector` non usa più thread.
- **Link di avvio del bot.** `BotStartLinkPort.start_link` è realizzata da `HttpxWorkerBotIdentityAdapter`, che
  conosce il formato `t.me`; il dominio non nomina più il servizio.
- **Porte in `ports.py`.** `TenantScheduledFlowsPort`, `ActivityReaderPort`, `ExecutionsReaderPort` e
  `NotifierPort` passano nei moduli `ports.py` del loro contesto; il registratore delle chiusure manuali diventa
  un `Callable` del comando, senza porta dedicata.

## Alternative scartate

- **Rete come nuova impostazione esplicita**: aggiungerebbe una scelta di configurazione che R0.2.1 non ammette
  (`dev` non opera mai sulla rete reale); la regola sta nel dominio e deriva dall'installazione già configurata.
- **Ponti in bootstrap con le decisioni spostate in funzioni ammesse**: lascerebbe le regole fuori dall'esagono,
  senza test sul caso d'uso.
- **Esito delle chiamate con campi opzionali**: obbliga a un `type: ignore` sul valore; l'unione di tipi lo evita.

## Conseguenze

- In `tests/architecture/known_violations.py` restano del Bug 173 solo le due voci di `AccountFlowsFromFlows`
  (`bootstrap-senza-classi`, `nessun-ponte`): la classe non decide più nulla, ma collega il contesto `accounts`
  (rimozione del conto, R1.1.8) a tre casi d'uso di `flows`, fra cui `StopFlowUseCase`, che chiude le posizioni.
  Fermare un flusso è un comando su un altro contesto, non la lettura di un dato: il contratto di indipendenza vieta
  ad `application/accounts` di importare `flows`, e un adapter non può ricevere casi d'uso (ADR 0089). Dove stia la
  sequenza «ferma i flussi, rimuovi il conto, archivia i flussi» resta una decisione del proprietario.
- Il messaggero non configurato resta in bootstrap con la voce del Bug 177; `telegram_channel` lo riceve.
