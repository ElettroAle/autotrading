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
- Configurazione e segreti arrivano dal costruttore; un adapter non legge variabili d'ambiente.

## Adapter in ingresso

`adapters/inbound/api/`: traduce una richiesta esterna in un comando, chiama il caso d'uso, traduce
esito ed errori tipizzati nella risposta. Nessuna logica di business.

## bootstrap.py

- Unico punto che conosce sia le porte sia gli adapter: istanzia e collega, come un `Program.cs`.
- Nessuna classe, nessuna costante di modulo, nessuna decisione, nessuna libreria esterna o standard
  tecnica. La configurazione la legge e la valida un adapter; `bootstrap.py` la passa ai costruttori.
- `for_tenant(tenant_id)` costruisce, per ogni richiesta, adapter legati al tenant e casi d'uso.
- Nei test gli stessi casi d'uso si costruiscono con gli adapter finti al posto di quelli veri.

## Test

- Unit test delle funzioni di traduzione in `tests/unit/adapters/<tecnologia>/`.
- Test di integrazione contro la tecnologia vera in `tests/integration/<tecnologia>/`
  (vedi `tests.md`).
