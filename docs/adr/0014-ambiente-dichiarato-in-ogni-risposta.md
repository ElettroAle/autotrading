# ADR 0014 — Ambiente dell'installazione validato all'avvio e dichiarato in ogni risposta

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.1.4

## Contesto

R0.1.4 chiede che ogni risposta della piattaforma riporti il nome dell'ambiente (`dev` o `prod`), e
che l'installazione non parta se l'ambiente manca o non è uno dei due. Le risposte sono di forme
diverse: JSON di un caso d'uso, errori di validazione, 404 di un percorso inesistente, 405 di un
metodo non ammesso. Un campo nel corpo non arriva in tutte, e il corpo degli errori lo genera in
parte FastAPI.

## Decisione

- **Intestazione HTTP `X-Autotrading-Environment`** aggiunta a ogni risposta da un middleware
  dell'adapter FastAPI. Il middleware avvolge anche gli errori generati dal framework, quindi nessuna
  risposta esce senza ambiente. `/health` lo riporta anche nel corpo, come già faceva.
- **Validazione all'avvio in `bootstrap.py`**, unico punto che legge la configurazione:
  `APP_ENVIRONMENT` assente o vuoto solleva `UndeclaredEnvironmentError` ("ambiente non dichiarato");
  un valore diverso da `dev` e `prod` solleva `UnsupportedEnvironmentError` ("ambiente non ammesso:
  sono ammessi dev e prod"). Il valore è confrontato esattamente, dopo aver tolto gli spazi ai bordi.
- L'ambiente resta una stringa di configurazione dell'installazione: nessun contesto di dominio nuovo.

## Alternative scartate

- **Campo `environment` nel corpo di ogni risposta**: non copre le risposte generate dal framework e
  obbliga ogni schema di risposta a portarlo.
- **Ambiente nel solo `/health`**: non soddisfa "ogni risposta".
- **Contesto di dominio `installation`**: un contesto nuovo richiede la decisione del proprietario, e
  oggi l'ambiente non ha regole di business oltre ai due valori ammessi.

## Conseguenze

- La pagina OpenAPI e qualunque client vedono l'ambiente nell'intestazione di ogni risposta.
- Un errore di configurazione ferma il container all'avvio: il controllo di salute del rilascio
  fallisce e il rilascio si interrompe, invece di servire un'installazione ambigua.
