# ADR zona-di-emergenza-in-fondo-alla-pagina — Chiusura di emergenza da sola in una zona di emergenza in fondo alla pagina

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 545, R3.2.3 (460)
- Collegate: ADR chiusura-di-emergenza-nella-dashboard (il comando e la conferma, che restano), ADR
  viste-e-comandi-della-pagina-del-flusso, ADR icone-con-lucide-react-e-comandi-condivisi (R6.5.3, non ancora in
  main), ADR 0116 (dashboard secondo bulletproof-react)

## Contesto e problema

La chiusura di emergenza chiude a mercato tutte le posizioni dell'ambito e mette i flussi in pausa: è il comando
più pesante della dashboard. Oggi però sta vicino ai comandi di uso quotidiano:
- nella pagina del flusso, subito dopo Pausa, Riprendi e Stop (`renderCommands` di `FlowView`);
- nell'elenco dei flussi, sopra l'elenco, accanto alla barra dei comandi;
- nella pagina dei conti, tra i comandi di ogni conto (`renderCommands` di `AccountsList`).

Si può toccare per sbaglio, soprattutto sul telefono.

## Fattori decisionali

- Decisione del proprietario, 17/11/2026: «Lo stop di emergenza non può stare vicino agli altri tasti, e deve
  richiedere una conferma». All'avvio ha scelto:
  - posizione: «Riquadro separato in fondo», un riquadro «Zona di emergenza» a sé, con bordo rosso, in fondo alla
    pagina del flusso, della pagina dei conti e della home;
  - conferma: «Finestra di oggi», cioè la `ConfirmationDialog` attuale con ambito e numero di posizioni.
- Decisione del proprietario, 16/11/2026: regole architetturali e componenti riusabili dove possibile, nessun
  duplicato per pagina. Il riquadro è uno solo, condiviso dalle tre pagine.
- bulletproof-react (ADR 0116): nessun import tra funzionalità. Sono le pagine di `src/app` a comporre le
  funzionalità, e possono leggere le query delle funzionalità.
- ADR chiusura-di-emergenza-nella-dashboard: un solo `EmergencyClosingCommand`, parametrizzato dall'ambito. Questa
  ADR cambia solo dove sta, non che cosa fa.

## Opzioni considerate

1. **Un componente condiviso `DangerZone` in `src/components/ui/danger-zone.tsx`, composto in fondo a ogni pagina
   da `src/app`.**
   - È una `section` con `aria-label` e titolo «Zona di emergenza», bordo rosso, margine superiore ampio. Riceve
     come `children` soltanto i comandi di emergenza.
   - **Pagina del flusso:** `flow.tsx` toglie `EmergencyClosingCommand` da `renderCommands` di `FlowView`. Il
     riquadro va dopo `FlowView`, cioè dopo schede e contenuto. Il nome del flusso si legge da `useFlows` della
     funzionalità flows, la stessa query di `FlowView`, che non fa una seconda chiamata. Il riquadro compare solo
     per un flusso trovato che non sia una bozza.
   - **Elenco dei flussi:** `home.tsx` sposta `EmergencyClosingCommand` con ambito «tutti» in un `DangerZone`
     dopo `FlowsList`.
   - **Pagina dei conti:** `accounts.tsx` non passa più `renderCommands` ad `AccountsList`. Dopo
     `RegisterAccountForm` mette un `DangerZone` con un `EmergencyClosingCommand` per conto, letti da `useAccounts`
     della funzionalità accounts. Ogni pulsante nomina il conto, per esempio «Chiusura di emergenza del conto
     test-1». La prop facoltativa `renderCommands` di `AccountsList` si toglie se nessuno la usa più.
   - Il testo del pulsante nomina l'ambito anche nel flusso («Chiusura di emergenza del flusso alfa») e in home
     («Chiusura di emergenza di tutti i flussi»). Così la zona si legge da sola.
2. Il riquadro dentro `EmergencyClosingCommand`: scartata. Il comando di un conto andrebbe ripetuto in un riquadro
   per conto, e la posizione nella pagina la decide la pagina, non il comando.
3. Un menu «Altro» che nasconde il comando: scartata, il proprietario ha scelto il riquadro visibile in fondo.

## Esito della decisione

Opzione 1. La conferma non cambia: `ConfirmationDialog` con la domanda di oggi («Chiudere 1 posizione del flusso
alfa e metterlo in pausa?»), e nessuna chiamata prima della conferma.

**Allineamento con R6.5.3.** Il pulsante condiviso `CommandButton` con il tono `stop` non è ancora in main.
- Se R6.5.3 si integra prima di questo Bug, il pulsante della zona usa `CommandButton` con tono `stop`.
- Se si integra dopo, questo Bug resta con la classe `DESTRUCTIVE_COMMAND` di oggi, e il ramo di R6.5.3 lo porta a
  `CommandButton` quando si allinea a main.
In ogni caso il ramo integrato per secondo si allinea al primo.

Verifica: prova.
- I quattro scenari nuovi di R3.2.3 con playwright-bdd: zona in fondo alla pagina del flusso, dei conti e
  dell'elenco; conferma dalla zona.
- Unit test di `DangerZone` (titolo, ruolo, solo i figli dati).
- Unit test delle tre pagine: il comando di emergenza non sta più tra i comandi del flusso o del conto, ma è
  l'ultimo riquadro della pagina.
- Lo scenario esistente «Conferma nella dashboard» resta verde.

### Conseguenze

- Il comando di emergenza non sta più accanto ad alcun comando, e sulle tre pagine sta nello stesso posto: in fondo.
- Per raggiungerlo serve scorrere fino in fondo: è voluto, e la conferma resta l'ultima barriera.
- `.claude/rules/tech-dashboard.md` elenca `DangerZone` tra i componenti condivisi.
