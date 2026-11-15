# ADR avviso-unico-della-rete-nella-dashboard — Avviso unico della rete nella dashboard

- Stato: accettata (15 novembre 2026), decisione del proprietario
- Requisiti: R2.3.10 (US 286, Task 288), R2.3.1, R2.3.4
- Collegate: ADR nome-della-rete-dichiarato-dall-adapter (nome della rete dall'adapter), ADR 0157, ADR 0116

## Contesto e problema

La dashboard avvisava solo della rete reale (riquadro rosso alla registrazione, conferma all'avvio). Un conto o un
flusso sulla rete di test non lo diceva, e l'elenco dei conti traduceva da sé la rete in un nome.

## Opzioni considerate

### 1. Un componente di avviso unico per le due reti

- Pro: stesso aspetto ovunque, giallo per il test e rosso per il reale; testo generico con il nome della rete che
  l'API restituisce.
- Contro: tocca i punti dove oggi c'è l'avviso del reale.

### 2. Avvisi separati in ogni pagina

- Pro: modifiche locali.
- Contro: testi e stili divergenti.

## Esito della decisione

Opzione 1. `components/ui/real-money.tsx` diventa `components/ui/network-notice.tsx`: `NetworkNotice` (rosso «opererà
con denaro reale», giallo «opererà sulla rete di test <nome>, senza denaro reale»), `NetworkBadge` (`REALE · <nome>` o
`TEST · <nome>`) e la conferma di avvio su denaro reale, invariata. La registrazione mostra l'avviso dell'exchange
scelto, l'elenco dei conti il badge nella colonna Rete, la pagina del flusso l'avviso giallo quando il conto del flusso
è sulla rete di test. La dashboard non scrive alcun nome di exchange o di rete.

Verifica: prova (scenari di R2.3.10, `network-notice.test.tsx`, `accounts-list.test.tsx`,
`register-account-form.test.tsx`, `flow-view.test.tsx`).
