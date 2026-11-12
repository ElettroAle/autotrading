# ADR 0065 — Liquidità impegnata dalle aperture dello stesso ciclo

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.5.3, Bug 156 (B1.5.1)

## Contesto

Il controllo del rischio confrontava ogni apertura di un ciclo con la stessa liquidità disponibile letta
all'inizio del ciclo. Le aperture già approvate nello stesso ciclo non la riducevano: con liquidità 1000 e due
aperture da 600 di margine, entrambe passavano e il flusso impegnava 1200 su 1000 di capitale. Su un conto
condiviso l'exchange le accetta, perché il margine libero del conto comprende il capitale degli altri flussi.

## Opzioni considerate

### 1. Il controllo tiene la liquidità residua e ogni apertura approvata la riduce

- Pro: una sola istanza di `RiskCheck` per ciclo, già così costruita da `CheckRiskUseCase`; l'ordine è quello
  delle decisioni dell'agente, prevedibile e leggibile nel registro del ciclo.
- Contro: il controllo diventa con stato; si usa un'istanza per ciclo, mai condivisa.

### 2. Controllo complessivo: somma dei margini delle aperture approvate contro la liquidità, a fine giro

- Pro: nessuno stato tra le decisioni.
- Contro: se la somma supera la liquidità bisogna scegliere quali bloccare, cioè un ordine di priorità che il
  requisito non dà; un'apertura già "approvata" verrebbe rimessa in discussione.

### 3. Le chiusure dello stesso ciclo liberano liquidità prima delle aperture

- Pro: il flusso userebbe subito il margine che chiude.
- Contro: la liquidità di una chiusura è nota solo dopo l'esecuzione (prezzo, PnL, commissioni); una chiusura
  rifiutata lascerebbe aperture senza copertura.

## Esito della decisione

Scelta: **opzione 1**. `RiskCheck` parte dalla liquidità dello stato e, per ogni apertura approvata (anche quella
portata al minimo), sottrae il suo margine; le decisioni successive del ciclo sono confrontate con il residuo e il
motivo del blocco riporta la liquidità residua. Le chiusure non liberano liquidità prima dell'esecuzione: la
liberano al ciclo successivo, quando lo stato si rilegge.

### Conseguenze

- A parità di decisioni, l'esito dipende dal loro ordine nella risposta dell'agente: la prima apertura che sta
  nella liquidità passa, le successive vedono il residuo.
- Nessun cambio di porte o di dati: il ponte del ciclo costruisce già un solo controllo per ciclo.
