---
paths:
  - "src/autotrading/*/cycles/**"
  - "tests/**/cycles/**"
  - "specs/E1-flussi-autonomi/F1.2-ciclo-decisionale/**"
  - "specs/E1-flussi-autonomi/F1.7-registrazione-e-consultazione/R1.7.1-*"
  - "specs/E1-flussi-autonomi/F1.7-registrazione-e-consultazione/R1.7.3-*"
---

# Contesto cycles

Il ciclo decisionale: quando parte, che passi esegue, come fallisce e che cosa ne resta.

## Glossario

- **Cycle**: un'esecuzione del ciclo decisionale di un flusso, con istante previsto ed effettivo, esito
  (`completed`, `failed`, `skipped`) e versione della configurazione in vigore (R1.2.1, R1.7.1).
- **Schedule**: primo ciclo all'avvio o alla ripresa del flusso, poi ogni intervallo da quell'istante; un
  ciclo è puntuale se parte entro 60 secondi dall'istante previsto, altrimenti il ritardo si registra.
- **Steps**, nell'ordine: lettura dello stato del flusso, raccolta delle fonti, composizione del contesto,
  decisione dell'agente, controllo del rischio, esecuzione degli ordini, aggiornamento dello stato,
  registrazione.
- **Transient error**: può non ripetersi al ciclo successivo (rete, fornitore o exchange indisponibile,
  timeout). Fa fallire solo il ciclo (R1.2.3).
- **Permanent error**: si ripete finché l'utente non interviene (credito esaurito, chiave IA o credenziali
  revocate). Fa fallire il ciclo e mette in pausa i flussi coinvolti (R1.2.4).
- **Cycle record**: tutto ciò che il ciclo ha prodotto fino all'ultimo passo eseguito (R1.7.1).

## Regole

- **Fail fast**: un passo che non riesce solleva un errore tipizzato; il ciclo si interrompe in quel punto,
  senza nuovi tentativi e senza ordini successivi. Un solo gestore centrale degli errori del ciclo
  registra il ciclo fallito e, per un errore permanente, mette in pausa i flussi e rilancia comunque
  (ADR della gestione degli errori).
- La natura transitoria o permanente è una proprietà del tipo di errore, non del punto che lo intercetta.
- **Nessuna sovrapposizione**: due cicli dello stesso flusso non sono mai in corso insieme, anche tra più
  processi; il ciclo previsto durante uno in corso è saltato e registrato (R1.2.2).
- **Flussi indipendenti**: un flusso lento o in errore non ritarda gli altri.
- Una fonte che non risponde non fa fallire il ciclo (R1.2.5): è assente e dichiarata.
- Il ciclo gira solo nel `worker`, l'unico che decifra le credenziali (ADR 0007).
- Le credenziali non compaiono mai nella registrazione del ciclo.

## Porte del contesto

Repository dei cicli; orologio; esclusione per flusso; i passi del ciclo verso `flows`, `sources`,
`agent`, `orders` e `notifications`, ciascuno con una porta propria collegata in `bootstrap.py`.
