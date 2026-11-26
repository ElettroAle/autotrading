# ADR informazioni-sui-campi-di-configurazione — Pulsante info condiviso e testi dei campi del flusso e del conto

- Stato: accettata (26 novembre 2026)
- Requisiti: US 772 R5.5.7 (Task 773)
- Collegate: ADR 0116, ADR 0131 (editor della configurazione guidato dai campi), ADR 0146 (controlli larghi quanto il
  modulo); `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

R5.5.7 chiede accanto all'etichetta di ogni campo del modulo del flusso (creazione e modifica) e di ogni impostazione
della pagina del conto un pulsante info con un testo in italiano: che cosa fa il campo, i valori ammessi, il predefinito
o che cosa succede lasciandolo vuoto. Vale anche per ogni campo aggiunto dopo: un campo senza testo non è ammesso.

## Fattori decisionali

- Regole di R5.5.7: attivazione con clic, tocco, Invio o Spazio; chiusura con Esc, clic fuori o nuova attivazione; un
  solo testo aperto; nome accessibile «Informazioni su <etichetta>»; un componente solo, condiviso. Testi letterali dei
  criteri per i quattro campi di esempio.
- Regole dei componenti riusabili della dashboard (bulletproof-react, `src/components/ui`); ogni campo passa dal
  componente di campo condiviso (`FormField`).
- I campi aggiunti dai requisiti F5.5 e R5.3.7 precedenti sono campi di oggi per questo requisito.
- Ambiguità risolta: l'elenco «campi di oggi» del requisito è stato scritto prima di R5.5.1-R5.5.6 e R5.3.7. Si legge
  come elenco minimo: ricevono il pulsante anche lo stop che segue il prezzo, il limite di perdite consecutive, le
  opzioni del riepilogo e degli altri asset della memoria, l'esposizione degli altri flussi e le commissioni nel
  contesto dell'agente, e nella pagina del conto l'esposizione massima per direzione.

## Decisione

- **Componente.** `InfoButton` in `src/components/ui/`: pulsante con nome accessibile «Informazioni su <etichetta>»,
  `aria-expanded`, testo a comparsa collegato con `aria-controls`; si chiude con Esc, clic fuori o nuova attivazione;
  un solo testo aperto in tutta la pagina attraverso un contesto condiviso.
- **Ogni campo lo riceve.** `FormField` e le etichette delle caselle prendono un testo info obbligatorio nel tipo:
  un campo senza testo non compila. I campi costruiti dalle dichiarazioni (parametri di adapter e di modello) usano la
  descrizione dichiarata (ADR descrizioni-dei-parametri-di-fonti-e-modelli).
- **Testi in un solo punto.** Un modulo della funzionalità del flusso e uno del conto tengono i testi di tutti i campi,
  ciascuno nell'ordine: che cosa fa, valori ammessi, predefinito o vuoto.
- **Prova.** Una prova della dashboard apre il modulo di creazione, quello di modifica e la pagina del conto, trova ogni
  controllo con etichetta e fallisce se gli manca il pulsante o il testo.

## Alternative scartate

- **Attributo `title`**: non accessibile da tastiera e tocco.
- **Testi accanto a ogni campo nel suo componente**: sparsi, non verificabili in un punto.

## Conseguenze

- Ogni campo futuro deve portare il suo testo per compilare.
