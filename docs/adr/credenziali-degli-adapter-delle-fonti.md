# ADR credenziali-degli-adapter-delle-fonti — Credenziali degli adapter delle fonti cifrate per tenant

- Stato: proposta (19 novembre 2026)
- Requisiti: US 314 R4.1.2, Task 315; US 383 R6.2.2 (scenario «Scadenza sconosciuta»)
- Collegate: ADR 0007 (credenziali leggibili solo dal worker), ADR 0029 (chiavi dei fornitori IA), ADR
  fonti-con-adapter-dichiarati, ADR scadenza-delle-chiavi-letta-o-indicata, ADR controllo-giornaliero-delle-scadenze,
  ADR 0105 (fonti assenti); `.claude/rules/context-sources.md`, `.claude/rules/context-tenancy.md`,
  `.claude/rules/tech-libsodium.md`, `.claude/rules/tech-sqlalchemy.md`
- Verifica: prova

## Contesto e problema

Con R4.1.1 un adapter di fonte dichiara i campi di configurazione che richiede (`SourceConfigurationField(name,
label, secret)`). R4.1.2 vuole che l'utente inserisca una volta per tenant quei valori, con i segreti cifrati e letti
solo dal worker; un adapter che richiede configurazione e non ce l'ha non è attivabile nel flusso; una credenziale
rifiutata dal fornitore nel ciclo rende l'adapter assente e avvisa l'utente una volta. R6.2.2 vuole anche per queste
credenziali la scadenza.

## Fattori decisionali

- Vincoli del proprietario: segreti leggibili solo da identità di servizio, cifrati nel database, decifrabili solo dal
  `worker` (ADR 0007); ogni dato appartiene a un tenant con RLS.
- Precedente: chiavi dei fornitori IA (`RegisteredProviderKey`, sealer nel tenant, opener solo nel worker).
- Ogni contesto possiede le sue chiavi (ADR scadenza-delle-chiavi-letta-o-indicata): niente tipi condivisi con
  `agent`.
- Una fonte che fallisce è assente, mai un errore del ciclo (context-sources).

## Decisione

- **Domain `sources`**: `SourceCredentials` (`TenantOwned`: `tenant_id`, `adapter`, `public_values` per i campi non
  segreti, `sealed: SealedSourceSecrets(key_version, ciphertext)` per i segreti, `expiry: KeyExpiry | None` del
  contesto, `rejected_at | None`). I valori si validano contro i campi dichiarati dall'adapter (campo mancante o non
  dichiarato rifiutato con il nome del campo); repr mascherato.
- **Porte** in `application/sources/ports.py`: `SourceSecretsSealerPort` (legata al tenant), `SourceSecretsOpenerPort`
  (solo worker), `SourceCredentialsRepositoryPort` (elenco, lettura, aggiunta, sostituzione, rimozione, marcatura del
  rifiuto).
- **Adapter**: `SodiumSourceSecretsSealerAdapter` e `SodiumSourceSecretsOpenerAdapter` in `libsodium/` come quelli
  delle chiavi IA (testo cifrato con `tenant_id` e `adapter`, verificati all'apertura); tabella `source_credentials`
  (PK `tenant_id`, `adapter`; `public_values` JSON, `key_version`, `ciphertext`, `expires_on`, `expiry_source`,
  `rejected_at`, `created_at`, `updated_at`) con RLS forzata, nell'adapter SQLAlchemy. L'opener è collegato solo nel
  worker.
- **Casi d'uso e API** (`/source-credentials`): elenco degli adapter che richiedono configurazione con stato
  configurato, valori non segreti, data di registrazione e scadenza (`expiry_status`, `days_left`, `expiry_editable`
  come le altre chiavi); `PUT /{adapter}` inserisce o sostituisce (la sostituzione azzera `rejected_at`), `DELETE`
  rimuove, `PUT /{adapter}/expiry` indica la scadenza. I segreti non tornano mai nelle risposte.
- **Attivabilità**: `GET /sources` porta per ogni adapter che richiede configurazione `configured` e, se manca, il
  motivo «configura l'adapter <adapter> in Impostazioni › Chiavi»; la configurazione del flusso che sceglie un
  adapter non configurato è rifiutata con lo stesso motivo (la verifica sta nel caso d'uso del flusso, che riceve la
  porta delle credenziali dichiarata in `flows`).
- **Ciclo**: il worker apre le credenziali dell'adapter e le passa al lettore nella `SourceRequest`; credenziali
  assenti al momento del ciclo = adapter assente col motivo. Un rifiuto del fornitore (401/403) è un errore tipizzato
  della porta: l'adapter è assente col motivo; se `rejected_at` è vuoto si imposta e parte una notifica «credenziale
  della fonte rifiutata» per il tenant, una sola volta fino alla sostituzione.
- **Scadenza**: le credenziali entrano nel controllo giornaliero (ADR controllo-giornaliero-delle-scadenze) con la data
  indicata dall'utente (nessun adapter di fonte la legge oggi); senza data «scadenza sconosciuta» e nessun avviso. Lo
  scenario R6.2.2 «Scadenza sconosciuta» si lega qui e perde `@wip`.

## Alternative scartate

- Cifrare anche i campi non segreti: la dashboard non potrebbe mostrarli, e non sono segreti per dichiarazione.
- Riusare la tabella delle chiavi IA: mescola due contesti.

## Conseguenze

- Le fonti a pagamento di F5.1 (LunarCrush, Arkham) dichiarano la chiave come campo segreto e diventano attivabili
  solo quando il tenant la inserisce.
