# ADR 0089 — Un adapter, una tecnologia; test di architettura senza eccezioni di regola

- Stato: accettata (13 novembre 2026)
- Requisiti: Task T0.0.1 (174), Bug B0.0.3 (177)
- Supera: le parti «ponte» (bridge in `bootstrap.py` tra contesti) delle ADR 0023, 0024, 0029, 0031, 0041, 0042,
  0046, 0047, 0048, 0050, 0051, 0052, 0054, 0055, 0056, 0061, 0065, 0067, 0070, 0075, 0079, 0082, 0085 e 0086
- Collegate: CLAUDE.md (Architettura, Regola delle dipendenze, Test di architettura), ADR 0027 (errori)

## Contesto

La prima batteria di test di architettura (PR #77) ha reso visibili le regole di business scritte in `bootstrap.py`,
ma lasciava due varchi: otto funzioni di lettura della configurazione esentate per nome dalla regola «bootstrap senza
decisioni», e un elenco di costanti di modulo ammesse. Inoltre non verificava che un adapter usasse una sola
tecnologia né che non orchestrasse altre porte.

Le ADR elencate sopra avevano introdotto il «ponte»: una classe in `bootstrap.py` che realizza la porta di un contesto
chiamando un altro contesto, traducendo tipi ed errori e spesso decidendo la sequenza (trova il conto, apri le
credenziali, scegli il lettore dell'exchange). Il proprietario non ha mai approvato quel concetto e CLAUDE.md non lo
cita: in `bootstrap.py` finivano orchestrazione e decisioni, e l'adapter diventava un compositore di porte.

## Decisione

- **Un adapter usa una e una sola tecnologia**: virtualmente una libreria a sé, staccabile. Ogni cartella
  `adapters/<verso>/<tecnologia>/` dichiara le librerie esterne che importa (tabella `TECHNOLOGY_LIBRARIES` in
  `tests/support/architecture.py`); una libreria appartiene a una sola cartella e fuori da quella cartella
  (`bootstrap.py` compreso) non si importa. `domain`, `application` e `bootstrap.py` non importano librerie esterne.
- **Il caso d'uso orchestra gli adapter.** Un adapter in uscita non riceve porte né casi d'uso nel costruttore e da
  `application` importa solo `ports.py` ed `errors.py`. Unica eccezione: il decorator, che riceve una sola porta e
  dichiara esplicitamente di realizzare la stessa (`class XRetryingExchangeAdapter(ExchangePort)`); prima di un
  decorator che aggiunge effetti si valuta l'outbox.
- **Niente ponti.** Il contesto che usa un dato di un altro contesto dichiara le sue porte, con i suoi errori, nel
  proprio `ports.py`; l'adapter della tecnologia che ha il dato le realizza nella sua cartella (un adapter può
  realizzare più porte e sollevare direttamente l'errore del contratto); la sequenza sta nel caso d'uso. Nessuna
  classe si chiama `*Bridge*` o `<X>From<Y>`.
- **`bootstrap.py` istanzia e collega**, come il `Program.cs` di .NET: nessuna classe, nessuna costante di modulo,
  nessuna decisione, nessuna libreria esterna o standard tecnica. La lettura e la validazione della configurazione
  stanno in un adapter.
- **Le regole non hanno eccezioni per nome.** Restano solo le violazioni note, ciascuna con il suo Bug, in
  `tests/architecture/known_violations.py`, che può solo diminuire.
- Regole aggiunte, già scritte in CLAUDE.md e prima non verificate: nomi delle porte (`Protocol` ⇔ `*Port`), errori che
  discendono da `AutotradingError`, caso d'uso nel modulo che porta il suo nome, `*Command` nel modulo del caso d'uso
  omonimo, nessuna cartella `common`/`utils`/`shared`, nessun `typing.Any`, `type: ignore` con codice e motivo.
- Ogni regola ha un esempio che la viola e uno conforme (`tests/architecture/test_architecture_rules.py`).

## Alternative scartate

- **Ponti in una cartella `adapters/bridges/`**: un adapter che compone porte di contesti diversi orchestra, cioè fa
  il lavoro del caso d'uso fuori dall'esagono.
- **Esenzioni nominali per la lettura della configurazione in `bootstrap.py`**: un'eccezione per nome cresce senza
  che si veda; la configurazione è una tecnologia (file montati, ambiente) e ha il suo adapter.
- **Verificare il decorator solo per forma del costruttore**: senza la porta dichiarata tra le basi non si distingue
  un decorator da un adapter che orchestra.

## Conseguenze

- Le violazioni esistenti delle regole nuove sono elencate con il Bug 177; quelle dei ponti già in lavorazione restano
  ai Bug 170 e 173.
- Una cartella di tecnologia nuova nasce con la sua riga nella tabella delle librerie, altrimenti il test è rosso.
- `jwt` dentro l'adapter FastAPI è una seconda tecnologia: la validazione dei token va in un adapter proprio.
