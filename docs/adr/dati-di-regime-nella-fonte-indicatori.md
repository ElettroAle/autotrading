# ADR dati-di-regime-nella-fonte-indicatori — Estremi, variazioni a ore e serie delle chiusure nella fonte indicatori

- Stato: accettata (26 novembre 2026)
- Requisiti: US 760 R5.5.4 (Task 761)
- Collegate: ADR 0032 (calcoli di pivot e indicatori), ADR 0057 (dati di mercato e lettura degli indicatori), ADR
  indicatori-estesi-nel-domain, ADR parametri-delle-fonti-come-liste-libere, ADR fonti-provate-su-risposte-registrate;
  `.claude/rules/context-sources.md`, `.claude/rules/tech-hyperliquid.md`
- Verifica: prova

## Contesto e problema

R5.5.4 chiede tre parametri nuovi dell'adapter Hyperliquid della fonte indicatori: `estremi_ore` (elenco di interi da 1
a 720), `variazione_ore` (elenco di interi da 1 a 720) e `serie_chiusure` (0 oppure 1, predefinito 0). Vuoti o a zero,
la fonte dà gli stessi valori di oggi.

## Fattori decisionali

- Requisito R5.5.4: formule, nomi delle chiavi, sole candele chiuse, valori non calcolabili tra i dati mancanti senza far
  fallire il ciclo; motivi di rifiuto letterali.
- I parametri di una fonte li dichiara il suo adapter, con validazione e predefiniti, e compaiono così in API, MCP e
  dashboard (ADR parametri-delle-fonti-come-liste-libere).
- I calcoli degli indicatori stanno nel domain (ADR indicatori-estesi-nel-domain); l'adapter legge le candele.
- Le fonti si provano su risposte registrate (ADR fonti-provate-su-risposte-registrate).
- Ordine del proprietario per F5.5: impostazioni facoltative, vuote di default, nessuna versione nuova dei flussi
  esistenti.
- Ambiguità risolta: il requisito dice la distanza dal minimo «zero o positiva» e dal massimo «zero o negativa», ma il
  prezzo corrente può uscire dall'intervallo delle candele chiuse (la candela in corso non conta). Vale la formula del
  requisito, senza riportare a zero: una distanza dal minimo negativa dice all'agente che il prezzo ha rotto il minimo.
- Ambiguità risolta: «la chiusura di N ore fa» è la chiusura della candela oraria N candele prima dell'ultima chiusa,
  come la variazione a giorni; minimo e massimo sono il minimo e il massimo delle candele, non le chiusure.

## Decisione

- **Parametri dichiarati dall'adapter.** L'adapter Hyperliquid degli indicatori dichiara `estremi_ore` e
  `variazione_ore` come liste libere di interi da 1 a 720 (motivo «<parametro> va da 1 a 720») e `serie_chiusure` come
  valore 0 oppure 1 (motivo «serie_chiusure vale 0 oppure 1»), tutti con predefinito vuoto o 0. Un flusso esistente li
  legge con il predefinito senza versione nuova.
- **Calcoli nel domain.** Accanto agli indicatori estesi, funzioni pure calcolano dalle candele orarie chiuse il minimo
  e il massimo delle ultime N, le distanze percentuali del prezzo (formule del requisito) e la variazione rispetto alla
  chiusura di N ore fa; la serie delle chiusure è quella delle candele dei due timeframe, lunga quanto la lunghezza
  della serie già configurata, dalla più vecchia alla più recente. Chiavi: `estremi.minimo_Nh`, `estremi.massimo_Nh`,
  `estremi.dal_minimo_Nh`, `estremi.dal_massimo_Nh`, `tendenza.variazione_Nh`, `breve.chiusura.serie`,
  `lungo.chiusura.serie`.
- **Candele orarie.** L'adapter legge le candele orarie necessarie (la più lunga delle N richieste) solo quando
  `estremi_ore` o `variazione_ore` hanno valori; la candela in corso non conta.
- **Dati mancanti.** Un valore che lo storico non permette di calcolare entra tra i dati mancanti del ciclo; gli altri
  valori restano.
- Prove su risposte registrate dell'exchange.

## Alternative scartate

- **Calcoli nell'adapter**: regole di business fuori dal domain.

## Conseguenze

- Con i parametri vuoti nessuna chiamata in più all'exchange.
