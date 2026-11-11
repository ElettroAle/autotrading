# ADR 0027 — Errori che dichiarano la propria risposta, handler centrale e Problem Details

- Stato: accettata (11 novembre 2026, decisione del proprietario)
- Requisiti: R1.2.3, R1.2.4 (Task T1.2.3.1); vale per tutte le risposte d'errore di API e `worker`

## Contesto

In E0 ogni errore discende da `AutotradingError`, ma lo stato HTTP vive in una mappa dell'adapter FastAPI
(`ERROR_STATUS`): aggiungere un errore significa ricordarsi di aggiungerlo alla mappa, e un errore
dimenticato diventa un 500 di Starlette senza corpo utile. Il corpo d'errore è un `{"detail": ...}`
proprio della piattaforma.

E1 aggiunge il ciclo dei flussi, dove un errore deve dire anche se è **transitorio** (fallisce solo il
ciclo, R1.2.3) o **permanente** (il ciclo fallisce e i flussi coinvolti vanno in pausa, R1.2.4).

Il proprietario ha indicato come modello il progetto Aidea.Dxp.AI: una radice degli errori nel centro
dell'esagono che dichiara lo stato della risposta, un errore definito nel livello che lo solleva, un
gestore centrale che risponde in Problem Details.

## Decisione

- **La radice dichiara la risposta.** `AutotradingError` (in `domain/errors.py`) ha tre attributi:
  - `status_code: ClassVar[int] = 400`;
  - `permanent: ClassVar[bool] = False`;
  - `details`, una proprietà che restituisce i dati che la risposta aggiunge al motivo (vuoti se l'errore
    non ne porta).

  Ogni sottoclasse ridefinisce solo ciò che differisce dal padre: per esempio
  `AccountNotFoundError.status_code = 404`, o `UnsupportedExchangeError.details` con gli exchange
  supportati.
- **Ogni errore nel livello che lo solleva**: domain, application (contratti delle porte), adapter.
  Rimane come in E0.
- **Un solo handler centrale per servizio.** `install_error_responses` registra un gestore per ciascun
  tipo di fallimento, e ogni risposta è Problem Details (RFC 9457, `application/problem+json`). Il corpo
  contiene `type` (`about:blank`), `title`, `status`, `detail`, i `details` dell'errore, `requestId` e
  `traceId`; il `traceId` viene dal `traceparent` W3C se valido, altrimenti è nuovo.
  - `AutotradingError`: lo stato dichiarato e il motivo dell'errore. Il 401 aggiunge
    `WWW-Authenticate: Bearer`.
  - `NotImplementedError`: 501.
  - Ogni altra eccezione: 500 con `detail` generico ("errore interno"). È registrata nel log con
    `requestId` e `traceId`, e non rivela nulla al chiamante.
  - Una richiesta non valida: 422 con `errors` (dove e perché), mai con l'input (R0.2.3).
- **La mappa `ERROR_STATUS` e la mappa `ERROR_DETAILS` spariscono.**
- **Una traduzione conserva la causa**: `raise <ErroreTipizzato> from error`, già imposto da ruff (B904).
- **Transitorio e permanente nel ciclo** (si realizza con il ciclo, R1.2.3 e R1.2.4):
  - il passo che non riesce solleva l'errore (fail fast), senza nuovi tentativi;
  - un gestore centrale del ciclo registra il ciclo fallito;
  - se l'errore è `permanent`, il gestore mette in pausa i flussi coinvolti e rilancia comunque l'errore,
    così il fallimento resta visibile a chi esegue il ciclo.

  Un errore non tipizzato nel ciclo è transitorio: non si conosce il motivo, e un'eccezione inattesa non
  deve fermare un flusso.

## Alternative scartate

- **Mappa nell'adapter (E0)**: lo stato vive lontano dall'errore, e un errore nuovo senza voce nella mappa
  diventa un 500.
- **Stato HTTP solo negli errori dell'adapter**: un errore del domain o di una porta dovrebbe essere
  tradotto due volte per avere uno stato; il proprietario vuole lo stato dichiarato dall'errore stesso.
- **Corpo proprio `{"detail": ...}`**: Problem Details è lo standard, ha già `detail`, e i client esistenti
  (gli adapter `httpx` verso il `worker`) continuano a leggere `detail` e i dati aggiuntivi allo stesso
  livello.
- **Errore transitorio come predefinito per i soli errori tipizzati, permanente per gli altri**: un errore
  inatteso fermerebbe il flusso senza che l'utente possa capire che cosa risolvere.

## Conseguenze

- Il domain conosce un numero che coincide con uno stato HTTP. È una scelta esplicita del proprietario: il
  numero dice quale tipo di risposta merita l'errore, e il domain non importa nulla di HTTP.
- Le risposte d'errore cambiano forma. Il 422 di validazione porta i dettagli in `errors`, non più in
  `detail`, che diventa il motivo "richiesta non valida".
- Le prove leggono il motivo con `tests/support/problems.py`, che toglie i membri comuni a ogni problema.
