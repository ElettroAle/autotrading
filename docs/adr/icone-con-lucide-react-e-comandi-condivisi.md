# ADR icone-con-lucide-react-e-comandi-condivisi — Icone da lucide-react e pulsante di comando condiviso con colore e icona

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.3 (Task 519)
- Collegate: ADR 0116, ADR 0121 (precedente: una libreria per ruolo, importata solo dai componenti condivisi), ADR
  viste-e-comandi-della-pagina-del-flusso, `.claude/rules/tech-dashboard.md` §Librerie

## Contesto e problema

I comandi hanno tre aspetti, primario, secondario e distruttivo, definiti come classi in
`src/components/ui/commands.ts`, e nessuna icona. Pausa, Riprendi e Stop si distinguono solo dal testo. La dashboard
non ha una libreria di icone.

## Fattori decisionali

- Decisione del proprietario (16/11/2026, intervista): «usare iconcine adatte per far capire long short mantieni apri
  e chiudi, in generale vorrei rendere più intuitiva la ui ux». Comandi di stato di colore diverso con icona: Pausa
  ambra con pausa, Riprendi verde con play, Stop rosso con quadrato, Avvia verde con play.
- Direttiva del proprietario (16/11/2026): regole architetturali e componenti riusabili. Un componente condiviso per
  ruolo, non icone sparse nelle funzionalità.
- `.claude/rules/tech-dashboard.md`: dipendenze a versione esatta; ogni libreria dichiarata nella rule; le regole di
  struttura stanno in `eslint.architecture.js` con la loro prova.
- R6.5.3: l'icona accompagna il testo e non lo sostituisce; il nome accessibile è il testo; il colore non è l'unico
  segno.

## Opzioni considerate

1. **lucide-react, importata solo da `src/components/ui/icons/`.**
   - `lucide-react` a versione esatta, ad albero (si importano solo le icone usate).
   - Una regola `import/no-restricted-paths` in `eslint.architecture.js`, come per Recharts, ammette l'import solo in
     `src/components/ui/icons/`, con la prova rossa e verde in `architecture/structure.test.ts`.
   - `src/components/ui/command-button.tsx` è il pulsante condiviso, con `tone` tra `primary`, `secondary`,
     `destructive`, `go` (verde), `hold` (ambra) e `stop` (rosso), e con un'icona facoltativa scelta per nome. Prende
     il posto delle classi di `commands.ts`, che resta solo per gli usi non pulsante.
   - Avvia e Riprendi usano `go` con play, Pausa `hold` con pausa, Stop `stop` con quadrato.
   - Le icone hanno `aria-hidden` e il testo resta visibile, quindi il nome accessibile è il testo. I colori
     rispettano il contrasto WCAG AA: verde-700, ambra-600 con testo scuro, rosso-700.
   - La rule `tech-dashboard.md` §Librerie dichiara: «Icone: lucide-react, unica libreria, importata solo da
     `src/components/ui/icons`».
2. **SVG scritti a mano**: scartata, perché è codice da mantenere senza vantaggi.
3. **Heroicons**: scartata, perché ha meno icone di trading. lucide-react ha frecce, play/pausa/quadrato e
   `RefreshCw` in uno stile uniforme.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test di `command-button`: tono, icona, nome accessibile uguale al testo, icona nascosta ai lettori di schermo.
- Prova di architettura sull'import di `lucide-react`.
- Scenari di R6.5.3.

### Conseguenze

- Ogni comando delle funzionalità (flussi, conti, chiusure) passa al pulsante condiviso nello stesso lavoro: nessuna
  copia provvisoria.
- «Esegui ora» di R6.5.2, se integrato prima, passa al pulsante condiviso nel merge.
