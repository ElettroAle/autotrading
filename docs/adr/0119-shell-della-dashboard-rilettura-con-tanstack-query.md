# ADR 0119 — Shell della dashboard: rilettura con TanStack Query e client dallo schema OpenAPI

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.1.2 (Task T2.1.2.1)
- Collegate: ADR 0116 (regole della dashboard), ADR 0118 (token verso l'API), RF-23.10

## Contesto e problema

Ogni pagina della dashboard deve rileggere i dati ogni 30 secondi mentre è aperta e su richiesta (decisione del
proprietario, intervista di E2), mostrare quando i dati sono vecchi ed essere usabile da telefono. Serve anche un
modo unico per chiamare l'API, con tipi coerenti con quelli che l'API dichiara.

## Decisione

- Tipi e client generati dallo schema OpenAPI di `api` (`openapi-typescript` + `openapi-fetch`) in `src/lib`,
  rigenerati da uno script; un controllo della pipeline fallisce se il client generato non corrisponde allo schema.
- Rilettura con TanStack Query: `refetchInterval` di 30 secondi solo per le query della pagina visibile
  (`refetchIntervalInBackground: false`), pulsante «Aggiorna» che invalida le query della pagina, istante
  dell'ultimo aggiornamento dal `dataUpdatedAt`, avviso «dati non aggiornati» quando una rilettura fallisce.
- Ogni chiamata passa da `api.GET`/`POST`/`PUT`/`PATCH`/`DELETE` con il percorso dello schema; le risposte si
  leggono con `readData` (schema Zod che deve leggere una parte del tipo dichiarato dall'API, Problem Details con i
  campi nei rifiuti), `readDone` (comandi senza contenuto), `readFile` (download con il nome dato dall'API) e
  `documentBody` (il testo di un file scelto dall'utente inviato così com'è, R2.5.2).
- Le query dei dati di pagina portano il segno `pageData` nei `meta` di TanStack Query, non un prefisso della
  chiave: ogni funzionalità conserva le chiavi che invalida dopo i suoi comandi. Non si rileggono da sé l'identità,
  l'editor della configurazione con i suoi cataloghi e le pagine dello storico (ADR 0139).
- Una rilettura fallita lascia sulla pagina i dati già letti: i componenti mostrano l'errore solo se non hanno dati.
- Layout responsive con Tailwind: navigazione laterale su desktop, menu a scomparsa sotto i 768 pixel; scenari
  Playwright anche con viewport di 390 pixel.

## Alternative scartate

- **Client scritto a mano**: nessuna dipendenza in più, ma i tipi divergono dall'API senza che nessun controllo lo
  dica.
- **Push dall'API (SSE o WebSocket)**: scartato dal proprietario nell'intervista.

## Conseguenze

- Un cambio di contratto dell'API rompe la compilazione della dashboard nella stessa PR. Al primo passaggio il
  controllo ha trovato schemi della dashboard che non ammettevano il conto e il capitale nulli di una bozza e una
  sostituzione delle credenziali che si aspettava dall'API campi che l'API non restituisce.
- Il capitale vuoto di un flusso nuovo resta fuori dalla richiesta anche se il contratto lo vuole: è l'API a dire
  che manca, accanto al campo (ADR 0130); è l'unico punto in cui il tipo della richiesta si forza.
