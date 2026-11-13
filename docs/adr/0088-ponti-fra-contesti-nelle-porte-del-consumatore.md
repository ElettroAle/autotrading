# ADR 0088 — Ponti fra contesti: porte del consumatore, adapter della tecnologia, sequenza nel caso d'uso

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.1.3, R0.2.3, R1.6.1, R1.6.2, R1.7.1; Bug 170
- Collegate: ADR 0082 (regole del ciclo nell'esagono), ADR 0042 (ponti in bootstrap, di cui supera la parte "ponti"),
  ADR 0023 (credenziali aperte solo nel worker), ADR 0007 (chiave privata solo nel worker)

## Contesto e problema

`bootstrap.py` conteneva classi ponte che realizzavano la porta di un contesto con i casi d'uso e le porte di un
altro: trovavano il conto, lo aprivano, sceglievano il lettore dell'exchange e traducevano gli errori. Il test di
architettura `bootstrap-senza-decisioni` (Task 174) vieta in bootstrap qualsiasi decisione, e il contratto di
indipendenza vieta che un contesto di application importi gli errori di un altro.

## Decisione (del proprietario)

- **Nessuna cartella nuova** e CLAUDE.md invariato: gli adapter stanno solo in `adapters/outbound/<tecnologia>/`.
- **Il contesto consumatore dichiara le porte che gli servono** nel proprio `application/<contesto>/ports.py`, con i
  propri errori nel contratto (es. orders: `OrderAccountPort.sealed_access`, che solleva
  `OrderAccountNotFoundError`; `AccessOpenerPort.open_access`, che solleva `OrderCredentialsNotOpenedError`).
- **Un adapter è una sola tecnologia e non orchestra altre porte.** L'adapter della tecnologia che ha già quei dati
  realizza anche la porta del consumatore nella sua cartella e solleva direttamente l'errore del contratto (es.
  `SqlAlchemyAccountRepositoryAdapter.sealed_access`, `SodiumCredentialOpenerAdapter.open_access`). Un adapter non
  riceve altre porte nel costruttore, salvo un decorator della stessa porta.
- **La sequenza sta nel caso d'uso del consumatore**, che riceve le singole porte: trovare il conto, aprire le
  credenziali, scegliere il lettore per exchange, leggere (es. `OpenTradingAccessUseCase`).
- **Il giornale JSON del ciclo** è un adapter di una porta di `cycles` in `adapters/outbound/json/`.
- **bootstrap** resta istanziazione e collegamento.

## Alternative scartate

- **Cartella `adapters/bridges/`** per i ponti: scartata dal proprietario, gli adapter si organizzano per
  tecnologia.
- **Porte che restituiscono tuple vuote per evitare l'`if` in bootstrap**: piegano i contratti per aggirare il test.
- **Errori condivisi fra contesti**: accoppierebbero i contesti attraverso il dominio.

## Conseguenze

- Un adapter di persistenza o di cifratura cresce di un metodo per ogni contesto che ne usa i dati; ogni metodo ha
  il nome della porta che realizza, così le porte di contesti diversi non si sovrappongono.
- Il valore sigillato attraversa il confine come tipo del consumatore (`SealedAccess`), mai come `Account` del
  contesto `accounts`.
- Il test architetturale che verificherà "un adapter non riceve altre porte" trova già conformi gli adapter toccati.
