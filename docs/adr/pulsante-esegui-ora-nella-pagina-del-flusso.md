# ADR pulsante-esegui-ora-nella-pagina-del-flusso — Pulsante «Esegui ora» tra i comandi del flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.2 (Task 517)
- Collegate: ADR comando-del-ciclo-su-richiesta-nell-api, ADR viste-e-comandi-della-pagina-del-flusso, ADR 0116,
  ADR icone-con-lucide-react-e-comandi-condivisi (R6.5.3, in parallelo)

## Contesto e problema

La pagina del flusso ha i comandi di stato (Avvia, Pausa, Riprendi, Stop) nella funzionalità `flow-commands`. Serve
«Esegui ora» per i soli flussi attivi, che mostri l'attesa durante il ciclo, il motivo di un rifiuto e il ciclo nuovo
alla fine.

## Fattori decisionali

- Direttiva del proprietario (16/11/2026): regole architetturali e componenti riusabili.
  - I comandi usano l'aspetto condiviso di `src/components/ui/commands.ts`, oppure il componente condiviso di
    R6.5.3 se è già integrato.
  - Il rifiuto si mostra con il `CommandRefusal` esistente.
  - Le chiamate passano dal client di `src/lib/api-client.ts`.
- `.claude/rules/tech-dashboard.md`: nessuna logica di business. La disponibilità del comando segue lo stato che
  l'API restituisce; il rifiuto lo decide l'API.

## Opzioni considerate

1. **Comando nella funzionalità `flow-commands`.**
   - Una nuova `api/run-cycle-now.ts`, una mutazione TanStack Query su `POST /flows/{flow_id}/cycles`.
   - «Esegui ora» compare accanto ai comandi di stato solo se il flusso è attivo. Non chiede conferma, perché non
     distrugge nulla.
   - Durante la richiesta il pulsante è disabilitato e dice «Ciclo in corso…».
   - Alla fine si invalidano le query dei cicli, dello stato, della panoramica e dell'equity del flusso.
   - L'elenco dei cicli (`features/cycles`) mostra l'etichetta «su richiesta» per `trigger = on_demand`, nel riassunto
     e nel dettaglio.
   - Se R6.5.3 è già integrato, il pulsante usa il suo componente condiviso dei comandi; altrimenti
     `SECONDARY_COMMAND`, e il ramo che integra per secondo allinea.
2. **Pagina o dialogo a parte**: scartata, perché è un comando di stato come gli altri.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test di disponibilità, attesa, rifiuto mostrato e invalidazione.
- Scenari Playwright di R6.5.2 con i finti MSW: la piattaforma finta accetta il ciclo su richiesta e simula un ciclo
  già in corso.

### Conseguenze

- I finti MSW ricevono la rotta nuova e il campo `trigger`.
