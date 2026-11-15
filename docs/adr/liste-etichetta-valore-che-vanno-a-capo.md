# ADR liste-etichetta-valore-che-vanno-a-capo — Liste etichetta-valore che vanno a capo e prova a 360 pixel

- Stato: proposta (15 novembre 2026)
- Requisiti: R6.4.1 (412), Task T6.4.1.1 (413)
- Collegate: ADR 0146 (campi dei moduli entro la larghezza), ADR 0116 (struttura e controlli della dashboard)

## Contesto e problema

Nella pagina del flusso il nome del modello `openrouter/~deepseek/deepseek-flash-latest` esce dal riquadro su un
telefono e la pagina diventa larga 410 pixel su uno schermo di 360 (analisi UI/UX del 15/11/2026). La causa è la
griglia `grid-cols-[max-content_1fr]` di `flow-details.tsx`: una colonna `1fr` ha come minimo la parola più lunga, e
una parola senza spazi la allarga oltre lo schermo. Le altre liste etichetta-valore (statistiche, conti, cicli) usano
schemi simili. La prova di layout a larghezza di telefono copre oggi solo il modulo del flusso (ADR 0146).

## Fattori decisionali

- R6.4.1: nessuna pagina scorre in orizzontale a 360 pixel; il disegno attuale resta (decisione del proprietario,
  15/11/2026).
- `.claude/rules/tech-dashboard.md`: Tailwind per lo stile, prove Playwright con la piattaforma finta.
- ADR 0146: stesso problema sui campi dei moduli, risolto con un vincolo di larghezza e una prova a larghezza di
  telefono.

## Opzioni considerate

1. Colonna dei valori `minmax(0,1fr)` e a capo dentro le parole (`overflow-wrap: anywhere`) in ogni lista
   etichetta-valore, con una prova di layout a 360 pixel su tutte le pagine.
2. Troncare i testi lunghi con i puntini e il testo completo al passaggio del puntatore: nasconde dati su un
   telefono, dove il passaggio del puntatore non c'è.

## Esito della decisione

Opzione 1. Ogni lista etichetta-valore della dashboard limita la colonna dei valori a `minmax(0,1fr)` e manda a capo
dentro le parole lunghe; dove le classi si ripetono si estraggono in un'unica costante condivisa, come i campi
dell'ADR 0146, senza cambiare l'aspetto su schermi larghi. La prova di layout (`e2e/layout/`, progetto `telefono`)
apre ogni pagina della dashboard a 360 pixel con dati che contengono parole lunghe e verifica che la larghezza del
documento non superi lo schermo e che nessun elemento esca dal proprio riquadro. Gli scenari di R6.4.1 girano con
`playwright-bdd` come quelli di E2: la configurazione include il `.feature` di F6.4.

Verifica: prova (prova di layout a 360 pixel su tutte le rotte; scenari di R6.4.1).

### Conseguenze

- Nessuna pagina scorre in orizzontale su un telefono, anche con nomi di modelli o indirizzi lunghi.
- Una pagina nuova entra nella prova di layout quando entra nelle rotte.
