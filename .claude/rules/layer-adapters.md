---
paths:
  - "src/autotrading/adapters/**"
  - "src/autotrading/bootstrap.py"
  - "tests/unit/adapters/**"
  - "tests/integration/**"
---

# Livello adapters e composition root

Qui vivono le tecnologie. Ogni tecnologia è incapsulata in una sola cartella, e ogni adapter usa una e
una sola tecnologia: virtualmente una libreria a sé, staccabile.

## Adapter in uscita

- `adapters/outbound/<tecnologia>/`: implementano le porte di application. Un adapter può realizzare più
  porte, anche di contesti diversi, purché con la sola tecnologia della sua cartella.
- Le librerie esterne che la cartella importa sono dichiarate in `TECHNOLOGY_LIBRARIES`
  (`tests/support/architecture.py`); una libreria appartiene a una sola cartella.
- Un adapter non orchestra: non riceve porte né casi d'uso nel costruttore e da `application` importa solo
  `ports.py` ed `errors.py`. La sequenza tra adapter è del caso d'uso. Unica eccezione il decorator, che
  riceve la stessa porta che dichiara tra le sue basi; se aggiunge effetti si valuta l'outbox.
- Niente ponti tra contesti: il contesto che usa un dato di un altro dichiara la sua porta e l'adapter della
  tecnologia che ha il dato la realizza qui, sollevando direttamente l'errore del contratto.
- Nome `<Tecnologia><Ruolo>Adapter` (es. `SodiumCredentialSealerAdapter`); rispetta la porta
  strutturalmente, verificato da mypy.
- Le eccezioni della libreria si catturano qui e si traducono subito nell'errore tipizzato del
  contratto della porta. Nessuna eccezione di libreria esce dall'adapter.
- La traduzione tra tipi della libreria e tipi del dominio sta in funzioni private piccole,
  testabili senza la tecnologia.
- Una cartella di tecnologia non importa un'altra cartella di tecnologia.
- Il costruttore di un adapter riceve impostazioni tipizzate o client, mai la `ConfigurationSource`, e
  non legge variabili d'ambiente né file di configurazione.

## Configurazione

Modello di `IConfiguration` in .NET: una sorgente unica, ogni libreria legge la sua sezione.

- `adapters/configuration/source.py`: `ConfigurationSource` è l'unico punto che legge l'ambiente del
  processo e i file dei segreti. `value(nome)` (obbligatorio), `optional(nome)`, `secret(nome)` e
  `optional_secret(nome)` (leggono il file montato indicato da `<nome>_FILE`), `environment()`
  (l'installazione, validata dal domain). Errori `MissingConfigurationError` e
  `InvalidConfigurationError` in `adapters/configuration/errors.py`, col nome della variabile.
- Ogni cartella `adapters/<verso>/<tecnologia>/` che ha configurazione ha:
  - `configuration.py`: dataclass frozen privata `_<Tecnologia>Settings` (segreti con `repr=False`) e la
    funzione privata `_settings_of(source)` che legge, applica i default e valida forma e presenza
    (porta fuori intervallo, base64, numero). Lo importa solo il `composition.py` della stessa cartella.
  - `composition.py`: funzioni pubbliche `<tecnologia>_adapters(source, ...)` che leggono le impostazioni,
    creano client e adapter e li restituiscono pronti. Sono l'equivalente di
    `services.Add<X>(configuration)`.
- Le regole di business sui valori (slippage ammessa, ambienti ammessi, rete dell'installazione) restano
  nel domain; l'adapter le invoca.
- I segreti arrivano solo da file montati in sola lettura; nessuna impostazione in variabili di modulo.

## Adapter in ingresso

`adapters/inbound/api/`: traduce una richiesta esterna in un comando, chiama il caso d'uso, traduce
esito ed errori tipizzati nella risposta. Nessuna logica di business.

## bootstrap.py

- Unico punto che conosce sia le porte sia gli adapter: istanzia e collega, come un `Program.cs`.
- Nessuna classe, nessuna costante di modulo, nessuna decisione, nessuna libreria esterna o standard
  tecnica.
- Crea la `ConfigurationSource` dall'ambiente del processo (`PROCESS_ENVIRONMENT`, sostituibile nei test
  con un dizionario) e la passa solo alle funzioni `*_adapters`; ne legge al più `environment()`. Nessun
  nome di variabile, nessun default, nessuna decisione sulla configurazione.
- `for_tenant(tenant_id)` costruisce, per ogni richiesta, adapter legati al tenant e casi d'uso.
- Nei test gli stessi casi d'uso si costruiscono con gli adapter finti al posto di quelli veri.

## Test

- Unit test delle funzioni di traduzione in `tests/unit/adapters/<tecnologia>/`.
- Test di integrazione contro la tecnologia vera in `tests/integration/<tecnologia>/`
  (vedi `tests.md`).
