# language: it
@R5.5.4
Funzionalità: R5.5.4 Dati di regime nella fonte indicatori
  Come utente
  Voglio poter dare all'agente la distanza del prezzo dal minimo e dal massimo delle ultime ore, la variazione a ore e
  la serie dei prezzi di chiusura
  Perché l'agente riconosca il passaggio da discesa a rimbalzo e viceversa

  La fonte indicatori (R1.3.3 Fonte indicatori tecnici, R5.1.4 Indicatori estesi) dà all'agente medie, RSI, MACD,
  volumi e la variazione a giorni, ma nessun dato che dica dove sta il prezzo rispetto ai minimi e ai massimi recenti,
  né la serie dei prezzi. Il 25 novembre 2026 un agente ha letto come eccesso da vendere un rimbalzo del 7% dal minimo
  della giornata, che nessun dato gli mostrava.

  Parametri nuovi dell'adapter Hyperliquid della fonte indicatori, facoltativi e vuoti di default, configurabili come
  gli altri parametri dell'adapter. Con i tre vuoti la fonte dà gli stessi valori di oggi.
  - estremi_ore: elenco di interi da 1 a 720. Per ogni N la fonte aggiunge estremi.minimo_Nh ed estremi.massimo_Nh
    (minimo e massimo delle ultime N candele orarie chiuse: la candela in corso non conta, come per ogni altro
    indicatore della fonte), estremi.dal_minimo_Nh ed estremi.dal_massimo_Nh (distanza percentuale del prezzo dal
    minimo, zero o positiva, e dal massimo, zero o negativa).
  - variazione_ore: elenco di interi da 1 a 720. Per ogni N la fonte aggiunge tendenza.variazione_Nh: variazione
    percentuale del prezzo rispetto alla chiusura di N ore fa.
  - serie_chiusure: 0 oppure 1, predefinito 0. Con 1 la fonte aggiunge breve.chiusura.serie e lungo.chiusura.serie: i
    prezzi di chiusura delle candele dei due timeframe, tanti quanti la lunghezza della serie già configurata.

  Regole.
  - Distanza dal minimo: (prezzo − minimo) / minimo × 100. Distanza dal massimo: (prezzo − massimo) / massimo × 100.
    Variazione: (prezzo − chiusura di N ore fa) / chiusura di N ore fa × 100.
  - Un valore che l'exchange non permette di calcolare (storico più corto di N ore) compare tra i dati mancanti e non
    fa fallire il ciclo.

  Fuori ambito: altri adapter della fonte indicatori, indicatori nuovi diversi da questi.

  Scenario: Parametri nel modulo delle fonti
    Quando "anna" apre nel modulo di "alfa" l'adapter "Hyperliquid" della fonte indicatori
    Allora vede i parametri estremi_ore, variazione_ore e serie_chiusure con i valori in vigore
    E può impostare estremi_ore a [24, 72]
