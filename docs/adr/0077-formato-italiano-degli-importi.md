# ADR 0077 — Formato italiano degli importi e dei numeri nei messaggi

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.1.7, R1.5.1-R1.5.4, R1.6.2; Bug 162
- Collegate: ADR 0018 (importi nell'API come stringhe con il punto decimale), che resta valida per l'API

## Contesto

I messaggi in italiano per l'utente (notifiche Telegram, motivi di rifiuto del controllo del rischio, differenze
di configurazione, errori di capitale e di riconciliazione) scrivevano gli importi con tre funzioni diverse,
sparse in contesti diversi: una toglieva gli zeri finali e usava la virgola, una usava il punto, una lasciava le
cifre come arrivavano dal `Decimal`. Lo stesso importo poteva comparire come `25,5 USDC` in una notifica e
`250.5` in una differenza di configurazione. Gli scenari approvati scrivono invece `PnL 2 USDC`, `0,04 USDC`,
`4,20 USDC`, `398 USDC`: virgola decimale, nessuna cifra decimale per un importo intero, i centesimi quando ci
sono decimali.

## Decisione

Un solo modulo del dominio, `domain/italian_text.py`, importabile da ogni contesto come gli altri moduli alla
radice del dominio, con due regole:

- **Importo di denaro** (`money_text`): virgola decimale; un importo intero si scrive senza decimali (`2`,
  `398`); altrimenti almeno due cifre decimali (`4,20`, `-25,50`) e tutte quelle significative oltre la seconda
  (`0,0123`), perché un importo piccolo non deve diventare zero in un messaggio.
- **Numero** (`number_text`) per percentuali, quantità e soglie: virgola decimale, nessuno zero finale inutile
  (`12,5`), mai in notazione esponenziale; lo zero negativo si scrive `0`.

L'API non cambia: gli importi restano stringhe con il punto decimale (ADR 0018), con l'unica funzione
`amount_text` dell'adapter FastAPI.

## Alternative scartate

- **Sempre due decimali**: arrotonda gli importi piccoli (commissioni, PnL di frazioni di centesimo) e
  contraddice gli scenari che scrivono `PnL 2 USDC`.
- **Solo togliere gli zeri finali anche per il denaro**: `4,2 USDC` non è come si legge un importo in italiano e
  contraddice `4,20 USDC` degli scenari.
- **Formattare con `locale`**: dipende dalla configurazione del sistema operativo del container e porta una
  libreria di piattaforma nel dominio.

## Conseguenze

- Tutti i messaggi italiani scrivono lo stesso importo nello stesso modo; cambiano i testi che prima usavano il
  punto o toglievano i centesimi (`-25,5` diventa `-25,50`, `250.5` diventa `250,50`, `12.5%` diventa `12,5%`).
- Un nuovo messaggio con un importo usa `money_text`; un nuovo campo dell'API usa `amount_text`.
- I parametri del modello di IA nelle differenze di configurazione restano scritti come il fornitore li riceve.
