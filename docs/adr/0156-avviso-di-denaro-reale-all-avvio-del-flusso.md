# ADR 0156 — Avviso di denaro reale all'avvio del flusso

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: Bug 277 (Task 279), R2.3.4
- Collegate: ADR 0155 (rete dalla configurazione dell'adapter), ADR 0132 (conferme dei comandi), ADR 0116

## Contesto e problema

Un flusso su un exchange configurato sulla rete reale muove denaro vero e partiva con un clic, senza avviso.

## Opzioni considerate

### 1. Conferma nella dashboard, con la rete del conto letta da `GET /accounts`

- Pro: nessuna API nuova: l'elenco dei conti porta già `network`, ora dalla porta dell'exchange (ADR 0155), e la
  pagina del flusso legge già i conti; l'avviso è dove si clicca.
- Contro: un client diverso dalla dashboard non vede l'avviso.

### 2. Porta di rete in `flows` e `network` nella vista del flusso

- Pro: la vista del flusso basta a se stessa.
- Contro: una porta e un campo che duplicano ciò che `GET /accounts` dice già.

### 3. Blocco nel backend con un flag di conferma

- Pro: vale per ogni client.
- Contro: oltre la richiesta del proprietario, che vuole un avviso, non un blocco.

## Esito della decisione

Opzione 1. Il design approvato prevedeva l'opzione 2; durante lo sviluppo è emerso che la pagina del flusso legge già
`GET /accounts`, con la rete di ogni conto, quindi la porta in `flows` non serve. `FlowView` ricava `realMoney` dal conto
del flusso e lo passa al pulsante di avvio della bozza e ai comandi del flusso; con la rete reale l'avvio, da bozza o da
fermo, apre la conferma «Il flusso opererà con denaro reale» (`RealMoneyStartConfirmation`, condivisa in
`src/components/ui/real-money.tsx`) e parte solo dopo «Avvia con denaro reale». Sulla rete di test l'avvio resta un clic.

Verifica: prova (scenari di R2.3.4, `draft-flows.test.tsx`, `flow-commands.test.tsx`).
