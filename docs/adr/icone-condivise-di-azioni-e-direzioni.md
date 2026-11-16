# ADR icone-condivise-di-azioni-e-direzioni — Etichette condivise con icona per azioni dell'agente e direzioni

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.3 (Task 520)
- Collegate: ADR icone-con-lucide-react-e-comandi-condivisi, ADR tabella-condivisa-senza-sforamento-e-con-filtri

## Contesto e problema

Azioni (`apri`, `chiudi`, `mantieni`, `aggiorna`, i valori di `TradeAction`) e direzioni (`long`, `short`) compaiono
come testo semplice in più punti:
- dettaglio del ciclo;
- posizioni aperte e chiuse;
- storico;
- in futuro, l'ultima decisione (R6.5.4) e lo storico delle decisioni (R6.5.5).

## Fattori decisionali

- Decisione del proprietario (16/11/2026): icone che fanno capire long, short, mantieni, apri e chiudi; una UI più
  intuitiva.
- Direttiva del proprietario (16/11/2026): componenti riusabili. Un componente per ruolo in `src/components/ui`,
  usato da tutte le funzionalità.
- R6.5.3, scenario «Direzioni e azioni con icona»: long freccia in su, short freccia in giù, apri più, chiudi x,
  mantieni pausa, aggiorna frecce circolari. Il testo resta accanto all'icona e il lettore di schermo legge il nome.

## Opzioni considerate

1. **`DirectionLabel` e `ActionLabel` in `src/components/ui/`.**
   - Ognuno riceve il valore dell'API e mostra icona più testo: `ArrowUp`, `ArrowDown`, `Plus`, `X`, `Pause` e
     `RefreshCw`, dalle icone di `src/components/ui/icons`.
   - Long in verde e short in rosso come segno in più, mai unico.
   - Un valore sconosciuto mostra il testo senza icona: l'API resta la fonte dei valori.
   - Li usano il dettaglio del ciclo (decisioni e ordini), le posizioni aperte e chiuse e lo storico.
2. **Icone dentro ogni funzionalità**: scartata dalla direttiva sui componenti riusabili.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test dei due componenti: ogni valore, il valore sconosciuto, il nome accessibile.
- Scenari di R6.5.3 sulle pagine che li usano.

### Conseguenze

- R6.5.4 e R6.5.5 usano questi componenti.
