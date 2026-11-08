# AutoTrading: documento dei requisiti funzionali

**Stato:** bozza 0.2, con le decisioni dell'intervista del 7-8 novembre 2026 (sezione 11)
**Data:** 8 novembre 2026
**Ambito:** solo requisiti funzionali e di comportamento. Le scelte di architettura e tecnologia sono escluse; gli spunti tecnologici emersi dalle fonti sono raccolti in [`tech-notes.md`](tech-notes.md).

---

## 1. Fonti e convenzioni

Il documento è ricavato dalle trascrizioni di una serie di cinque video YouTube in italiano e dalle decisioni prese con il proprietario del progetto:

| Rif. | Fonte |
|------|-------|
| V1 | "Abbiamo dato 60.000$ alle AI per fare trading… ecco cosa è successo" (analisi del benchmark Alpha Arena) |
| V2 | "Creo il mio Trading AI Agent, pt1: da Hyperliquid a Python" |
| V3 | "Creo il mio Trading AI Agent, pt2: dalla teoria all'Agent" |
| V4 | "Creo il mio Trading AI Agent, pt3: il lancio" |
| V5 | "Creo il mio Trading AI Agent, pt4: i primi risultati e le migliorie dopo 7 giorni" |
| D | Decisione del proprietario (intervista, sezione 11) |

Convenzioni usate nel testo:

- **RF-xx.yy**: requisito funzionale. **RNF-xx**: requisito non funzionale.
- **Priorità**: **M** (Must, necessario per la prima versione operativa su testnet), **S** (Should, atteso a breve), **C** (Could, evoluzione futura).
- **[Vn] / [D]**: provenienza del requisito.
- **[PROPOSTA]**: requisito non presente nei video, aggiunto perché necessario a rendere il sistema sicuro o completo.
- **[ASSUNZIONE]**: interpretazione di un punto non esplicito, da confermare.

---

## 2. Contesto e obiettivi

### 2.1 Contesto

Le fonti partono dal benchmark pubblico **Alpha Arena**, nel quale sei modelli linguistici di frontiera ricevono ciascuno un capitale reale e operano in autonomia su criptovalute, con lo stesso prompt e gli stessi dati numerici [V1]. Lo scopo della serie è replicare quell'esperimento con un agente proprio e poi **migliorarlo**, fornendo all'agente un contesto più ricco (notizie, sentiment, previsioni, livelli di supporto e resistenza, movimenti di grandi investitori), aggiungendo controlli sul rischio e uno strumento di monitoraggio [V1, V2, V3].

AutoTrading è un progetto **personale**: un solo proprietario, che è anche l'unico operatore e l'unico utente [D].

### 2.2 Obiettivo del prodotto

Realizzare una piattaforma che:

1. Fa operare in parallelo uno o più **flussi di trading** indipendenti, ciascuno guidato da un agente di intelligenza artificiale con la propria configurazione, per confrontarli [V1, D].
2. Esegue in autonomia, a intervalli regolari e senza intervento umano, il ciclo di analisi del mercato e di decisione di ogni flusso [V1, V4, D].
3. Esegue le decisioni su un exchange di contratti perpetui su criptovalute, sia al rialzo (long) sia al ribasso (short), con leva [V2, V4].
4. Punta a generare profitto **indipendentemente dalla direzione del mercato** [V5].
5. Protegge il capitale con regole di rischio indipendenti dall'agente, a difesa da errori e "allucinazioni" del modello [V3, V5].
6. Registra ogni decisione con il contesto completo che l'ha generata, per spiegarla, verificarla e migliorare il sistema nel tempo [V4, V5].
7. Permette di rigiocare i flussi su dati storici, per iterare più in fretta sulle configurazioni [D].
8. Offre una dashboard privata per configurare i flussi e seguirne in tempo reale andamento, posizioni e ragionamento [V4, V5, D].

### 2.3 Strategia di adozione

- **Fase di sperimentazione**: per alcuni mesi la piattaforma opera **solo con fondi virtuali** sull'ambiente di test dell'exchange, per testare e iterare [D].
- **Eventuale passaggio al reale**: solo dopo la sperimentazione e per scelta esplicita del proprietario, eventualmente con capitale limitato [D].

### 2.4 Principi guida

- **Approccio incrementale**: partire semplice, mettere in funzione, osservare, aggiungere funzionalità e dati solo dopo averli verificati [V4].
- **Fonti dati ortogonali**: ogni fonte di informazione è una capacità indipendente, attivabile o disattivabile per singolo flusso. Se una fonte si rivela non praticabile, il suo requisito si chiude senza effetti sul resto [D].
- **Trasparenza delle decisioni**: ogni azione dell'agente è accompagnata dal suo ragionamento ed è ricostruibile [V1, V4].
- **Tutto per flusso**: ogni parametro operativo (asset, intervallo, modello, pesi, regole di rischio, istruzioni, capitale) appartiene a un flusso [D].
- **Scopo sperimentale**: i risultati iniziali, positivi o negativi, possono dipendere dal caso e vanno valutati su periodi lunghi [V1].

---

## 3. Glossario

| Termine | Significato |
|---------|-------------|
| Flusso di trading | Unità operativa indipendente: un agente IA con la propria configurazione (asset, intervallo, modello, pesi, rischio, istruzioni) e il proprio capitale, che opera in parallelo agli altri flussi [D]. |
| Agente IA | Componente che riceve il contesto di mercato e restituisce le decisioni operative strutturate di un flusso, basato su un modello linguistico (LLM). |
| Ciclo decisionale | Esecuzione completa per un flusso di raccolta dati, decisione, controllo, esecuzione e registrazione. Tra un ciclo e l'altro l'agente "dorme". |
| Intervallo di ciclo | Tempo tra due cicli dello stesso flusso (15 minuti nella configurazione di V4, 3 minuti in Alpha Arena [V1]). |
| Asset / ticker | Criptovaluta su cui un flusso può operare (es. BTC, ETH, SOL). |
| Perpetuo con leva | Contratto derivato senza scadenza che replica il prezzo di un asset, con esposizione moltiplicata dalla leva. Non si possiede la criptovaluta. |
| Spot | Acquisto effettivo della criptovaluta, senza leva; guadagna solo se il prezzo sale. |
| Copy-trading | Replica automatica delle operazioni di un trader o agente esterno. |
| Long / Short | Posizione che guadagna se il prezzo sale / se il prezzo scende. |
| Leva | Moltiplicatore dell'esposizione rispetto al margine impegnato; amplifica guadagni e perdite. |
| Liquidazione | Chiusura forzata della posizione da parte dell'exchange quando la perdita esaurisce il margine. |
| Stop loss / Take profit | Livelli di prezzo ai quali una posizione viene chiusa automaticamente per limitare la perdita / incassare il guadagno. |
| Exit plan | Piano di uscita dichiarato all'apertura: obiettivo di prezzo, stop e condizione di invalidazione [V1]. |
| Hold | Decisione di mantenere la situazione invariata su un asset. |
| Equity / equity curve | Valore complessivo del capitale di un flusso nel tempo e relativo grafico. |
| PnL | Profitto o perdita (realizzato o non realizzato). |
| Win rate | Percentuale di operazioni chiuse in guadagno sul totale delle chiuse. |
| Pivot point | Livelli calcolati dai prezzi precedenti: punto centrale (PP), resistenze (R1, R2) e supporti (S1, S2) [V3]. |
| Sentiment (Fear & Greed) | Indice sintetico dell'umore del mercato, con valore numerico e classificazione (es. paura, neutrale, avidità) [V3]. |
| Whale | Grande investitore i cui movimenti possono influenzare il prezzo [V3]. |
| Order book | Elenco degli ordini di acquisto e vendita in attesa di esecuzione [V3]. |
| Forecast | Previsione del prezzo futuro di un asset su un orizzonte dato, prodotta da un modello statistico o di machine learning [V2, V3]. |
| Fonte dati | Capacità indipendente che fornisce al contesto un tipo di informazione (indicatori, pivot, forecast, sentiment, notizie, whale, volumi) [D]. |
| Pesi dei segnali | Importanza relativa assegnata a ciascuna fonte dati nel contesto dell'agente [V3]. |
| Ambiente di test | Ambiente dell'exchange con fondi virtuali che riproduce il comportamento reale senza rischio economico [V3, V4]. |
| Replay storico | Esecuzione simulata di un flusso su un periodo passato, più veloce del tempo reale [D]. |
| Fee | Commissione pagata per ciascuna operazione [V1]. |

---

## 4. Attori

| Attore | Descrizione |
|--------|-------------|
| **Proprietario / operatore** | Unico utente della piattaforma. Crea e configura i flussi, li avvia e li ferma, lancia i replay, analizza i risultati [D]. |
| **Agente IA** | Prende le decisioni operative di un flusso a ogni ciclo, entro i limiti imposti dalla configurazione e dal modulo di rischio. |
| **Exchange** | Sistema esterno su cui si eseguono gli ordini e da cui si leggono prezzi, saldo e posizioni. Exchange di riferimento: Hyperliquid [V1, V2, D]. |
| **Fonti dati esterne** | Servizi che forniscono notizie, sentiment, movimenti delle whale, volumi e order book. |
| **Pianificatore** | Meccanismo che avvia i cicli decisionali di ogni flusso al suo intervallo [V4]. |
| **Canali di notifica** | Telegram ed email, per gli avvisi al proprietario [D]. |

---

## 5. Ambito

### 5.1 Incluso

- Trading automatizzato di **criptovalute** tramite **contratti perpetui con leva**, long e short [V1, V2, D].
- Più **flussi** in parallelo, ciascuno con configurazione e capitale propri [D].
- Asset configurabili per flusso; insieme iniziale suggerito **BTC, ETH, SOL** [V4].
- Esecuzione sull'**ambiente di test** dell'exchange; ambiente reale come opzione successiva e deliberata [D].
- **Replay storico** dei flussi [D].
- Raccolta e arricchimento del contesto, decisione IA, controllo del rischio, esecuzione, registrazione, monitoraggio, configurazione da dashboard, analisi delle prestazioni e notifiche.

### 5.2 Escluso

- Uso da parte di più utenti o gestione di capitale di terzi [D].
- Mercati tradizionali (azioni, ETF, forex). La scelta delle cripto è motivata da mercato aperto 24/7 e abbondanza di dati [V1].
- Trading ad altissima frequenza: le decisioni avvengono su intervalli di minuti od ore, non di microsecondi [V1].
- Approvazione manuale delle singole operazioni: i flussi operano in piena autonomia [D].
- Accesso alla dashboard da parte di terzi [D].

### 5.3 Backlog proposto (fuori dalla prima versione)

Funzionalità registrate come candidate, con priorità bassa, da non sviluppare ora [D]:

- **BL-01. Trading spot**: i flussi possono anche comprare e vendere criptovalute spot.
- **BL-02. Copy-trading**: un flusso può replicare le operazioni di un trader o agente esterno (es. quelli di Alpha Arena) [V1].

---

## 6. Requisiti funzionali

### 6.1 Flussi di trading

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-01.01 | Il proprietario può creare più flussi di trading, ciascuno con: nome, asset, intervallo di ciclo, modello IA, fonti dati attive e relativi pesi, istruzioni dell'agente, regole di rischio, capitale iniziale, ambiente (test o reale). | M | V1, D |
| RF-01.02 | I flussi operano in parallelo e in modo indipendente: il comportamento, gli errori o le pause di un flusso non influenzano gli altri. | M | D |
| RF-01.03 | Capitale, posizioni e risultati di ogni flusso sono **isolati**: le operazioni di un flusso non modificano saldo e posizioni di un altro, e i risultati sono attribuibili al singolo flusso senza ambiguità. | M | D |
| RF-01.04 | Il proprietario può avviare, mettere in pausa, riprendere e archiviare ogni flusso. | M | D |
| RF-01.05 | Il proprietario può duplicare un flusso esistente per crearne una variante e confrontarla. | S | [PROPOSTA] |
| RF-01.06 | Una classifica confronta i flussi su: rendimento %, PnL, commissioni, win rate, numero di operazioni, drawdown massimo, costo del modello IA. | S | V1, D |

### 6.2 Ciclo decisionale autonomo

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-02.01 | Ogni flusso attivo esegue automaticamente il proprio ciclo decisionale al proprio intervallo, 24 ore su 24, 7 giorni su 7, senza intervento umano. | M | V1, V4, D |
| RF-02.02 | L'intervallo di ciclo è configurabile per flusso; valore iniziale suggerito 15 minuti. | M | V4, D |
| RF-02.03 | Ogni ciclo esegue, nell'ordine: (1) lettura dello stato del capitale del flusso, (2) raccolta dei dati delle fonti attive, (3) composizione del contesto, (4) decisione dell'agente, (5) controllo del modulo di rischio, (6) esecuzione degli ordini risultanti, (7) registrazione completa del ciclo. | M | V1, V4 |
| RF-02.04 | La raccolta dati di un ciclo si conclude in un tempo nettamente inferiore all'intervallo; le fonti indipendenti vengono interrogate in parallelo, non in sequenza. | S | V3 |
| RF-02.05 | Se una fonte dati non risponde, il ciclo prosegue con le fonti disponibili, il contesto indica all'agente quali dati mancano e il problema viene registrato. | M | [PROPOSTA] |
| RF-02.06 | Il fallimento di un ciclo (errore dell'agente, dell'exchange o di rete) non impedisce l'esecuzione dei cicli successivi. | M | [PROPOSTA] |
| RF-02.07 | Due cicli dello stesso flusso non si sovrappongono: se un ciclo è ancora in corso allo scadere dell'intervallo, il successivo viene saltato e l'evento registrato. | M | [PROPOSTA] |
| RF-02.08 | Il contesto di ogni ciclo include l'ora corrente e il tempo trascorso dall'avvio del flusso. | S | V1 |
| RF-02.09 | Dati di mercato comuni a più flussi (es. indicatori dello stesso asset nello stesso istante) possono essere riutilizzati, purché ogni ciclo registri esattamente i dati che ha usato. | C | [PROPOSTA] |

### 6.3 Fonti dati: requisiti comuni

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-03.01 | Ogni fonte dati (indicatori tecnici, pivot point, forecast, sentiment, notizie, whale, volumi e order book) è una capacità **indipendente** dalle altre. | M | D |
| RF-03.02 | Per ogni flusso il proprietario sceglie quali fonti sono attive. | M | D |
| RF-03.03 | Aggiungere, sostituire o rimuovere una fonte non richiede modifiche al funzionamento delle altre fonti né del ciclo decisionale. | M | D |
| RF-03.04 | Ogni fonte si applica automaticamente a tutti gli asset configurati nel flusso. | M | V3 |
| RF-03.05 | Ogni valore raccolto viene registrato con il suo istante di riferimento, così da poterlo riutilizzare nei replay storici e nelle analisi. | M | V4, D |

### 6.4 Fonte: dati di mercato e indicatori tecnici

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-04.01 | Per ogni asset sono disponibili il prezzo corrente e lo storico dei prezzi necessario al calcolo degli indicatori. | M | V2 |
| RF-04.02 | Per ogni asset vengono calcolati almeno: EMA20, MA20, MACD, RSI a 7 e a 14 periodi, mid price, open interest, funding rate, volume. | M | V1, V3 |
| RF-04.03 | Gli indicatori sono forniti come valori correnti e come serie recenti, su un timeframe di breve (allineato all'intervallo del flusso) e su uno di lungo periodo (es. 4 ore, con medie a 20 e 50 periodi). | M | V1, V3 |
| RF-04.04 | L'insieme degli indicatori è estendibile; candidati futuri: livelli di Fibonacci, linee di Gann, analisi ciclica. | C | V4 |

### 6.5 Fonte: pivot point

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-05.01 | Per ogni asset vengono calcolati i pivot point PP, R1, R2, S1, S2. | M | V3 |
| RF-05.02 | All'agente vengono forniti la posizione del prezzo rispetto al PP (sopra o sotto, come indicazione di tendenza) e la distanza dal supporto e dalla resistenza più vicini. | M | V3 |

### 6.6 Fonte: previsione dei prezzi (forecast)

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-06.01 | Per ogni asset viene prodotta una previsione del prezzo su più orizzonti; quelli iniziali sono 15 minuti e 1 ora. | M | V3, V4 |
| RF-06.02 | Ogni previsione riporta ultimo prezzo, prezzo previsto, variazione percentuale prevista e orizzonte. | M | V3, V4 |
| RF-06.03 | La profondità dello storico usato per la previsione è configurabile. | S | V5 |
| RF-06.04 | Ogni previsione viene registrata per il confronto con il prezzo effettivo allo scadere dell'orizzonte (vedi 6.18). | M | V4, V5 |
| RF-06.05 | Orizzonti più lunghi (giorni, settimane), necessari a un agente strategico (vedi 6.20). | C | V5 |

### 6.7 Fonte: sentiment di mercato

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-07.01 | A ogni ciclo viene rilevato l'indice di sentiment del mercato cripto (Fear & Greed), con valore numerico e classificazione testuale. | M | V3 |

### 6.8 Fonte: notizie

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-08.01 | A ogni ciclo vengono raccolte le notizie cripto più recenti (titolo, data e ora, sintesi o testo) e incluse nel contesto. | M | V1, V3 |
| RF-08.02 | Il numero e l'età massima delle notizie incluse sono configurabili per flusso. | S | [PROPOSTA] |
| RF-08.03 | Evoluzione: messaggi social di persone influenti per il mercato, anche specifici per asset. | C | V3 |

### 6.9 Fonte: movimenti delle whale

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-09.01 | Vengono rilevati i grandi trasferimenti di criptovalute (data e ora, asset, quantità, controvalore, descrizione) e inclusi nel contesto. | S | V3 |

### 6.10 Fonte: volumi globali e order book

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-10.01 | All'agente vengono fornite informazioni su volumi e ordini aggregati di più exchange, non solo di quello su cui si opera, per capire se prevalgono acquisti o vendite. Quale dato dell'order book usare è da definire. | C | V3 |

### 6.11 Stato del capitale e delle posizioni

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-11.01 | A ogni ciclo vengono letti, per il flusso: saldo, liquidità disponibile, valore complessivo e posizioni aperte. | M | V1, V4 |
| RF-11.02 | Per ogni posizione aperta sono noti: asset, direzione, dimensione, leva, prezzo di ingresso, PnL non realizzato, prezzo di liquidazione, exit plan dichiarato. | M | V1 |
| RF-11.03 | Il contesto dell'agente include il rendimento percentuale del flusso dal suo avvio. | M | V1 |
| RF-11.04 | Lo stato del capitale e delle posizioni del flusso viene salvato come istantanea a ogni ciclo. | M | V4, V5 |

### 6.12 Pesi dei segnali

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-12.01 | Per ogni flusso il proprietario assegna un peso di importanza a ciascuna fonte attiva. | S | V3, V4 |
| RF-12.02 | I pesi vengono comunicati all'agente nel contesto, perché ne tenga conto nel ragionamento. | S | V3 |
| RF-12.03 | I pesi in vigore a ogni ciclo vengono registrati con le decisioni. | S | V3 |

### 6.13 Istruzioni dell'agente

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-13.01 | Le istruzioni dell'agente (ruolo, obiettivo, strategia, regole operative, formato della risposta) sono definite per flusso e modificabili dalla dashboard. | M | V3, D |
| RF-13.02 | Le istruzioni includono le regole operative vigenti: al massimo una posizione per asset, azioni consentite, intervallo di leva ammesso, formato obbligatorio della risposta. | M | V3, V4 |

### 6.14 Decisione dell'agente

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-14.01 | A ogni ciclo l'agente riceve il contesto completo del flusso (istruzioni, stato del capitale, dati per asset dalle fonti attive, pesi) e restituisce le decisioni in forma **strutturata** e leggibile dalla macchina. | M | V1, V3 |
| RF-14.02 | A ogni ciclo l'agente restituisce **una decisione per ciascun asset** del flusso. | M | V1, D |
| RF-14.03 | Le azioni ammesse per ogni asset sono: **apri** (long o short), **chiudi**, **mantieni** (hold). | M | V1, V4 |
| RF-14.04 | Per un'apertura la decisione contiene: direzione, quota di capitale da impegnare (frazione del saldo), leva, ragionamento. | M | V3, V4 |
| RF-14.05 | Per un'apertura la decisione contiene anche l'exit plan: prezzo obiettivo (take profit), prezzo di stop (stop loss), condizione di invalidazione. | S | V1, V5 |
| RF-14.06 | Ogni decisione contiene un **punteggio di confidenza**. | S | V1 |
| RF-14.07 | Per una decisione "mantieni" i campi operativi vengono ignorati. | M | V4 |
| RF-14.08 | La chiusura è totale. La chiusura parziale è un'evoluzione futura. | M / C | V4 |
| RF-14.09 | Il ragionamento dell'agente viene sempre conservato e reso visibile, anche per le decisioni "mantieni". | M | V1, V4 |
| RF-14.10 | Una risposta non conforme al formato atteso viene scartata senza eseguire nulla e l'evento viene registrato. Se solo alcune decisioni sono malformate, si scartano quelle e si valutano le altre [ASSUNZIONE]. | M | V3 |

### 6.15 Gestione del rischio e del capitale

Il modulo di rischio è **indipendente dall'agente** e filtra ogni decisione prima dell'esecuzione, per proteggere il capitale da errori del modello [V3]. Tutti i limiti sono **parametri configurabili per flusso**, senza valori imposti dal sistema [D].

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-15.01 | Esposizione massima per singola operazione, come percentuale del capitale del flusso (esempio citato: 5%). Un'apertura oltre il limite viene **ridotta al limite** ed eseguita. | M | V3, D |
| RF-15.02 | Leva massima. Una leva superiore viene **ridotta al massimo** consentito. | M | V3, V4, D |
| RF-15.03 | Esposizione complessiva massima del flusso (somma delle posizioni aperte). Un'apertura che la supererebbe viene ridotta al margine residuo, o non eseguita se il margine residuo è nullo. | S | [PROPOSTA] |
| RF-15.04 | Vengono bloccate le decisioni incoerenti con lo stato reale: apertura su un asset con posizione già aperta, chiusura di una posizione inesistente, asset fuori dal flusso, liquidità insufficiente. | M | V3, V4 |
| RF-15.05 | Le aperture sotto l'importo minimo dell'exchange vengono gestite in modo deterministico (portate al minimo o non eseguite, secondo configurazione) e registrate. | M | V2 |
| RF-15.06 | Ogni apertura ha stop loss e take profit attivi sull'exchange, così da proteggere la posizione anche tra un ciclo e l'altro. Se l'agente non li indica, si applicano valori predefiniti del flusso. | S | V5 |
| RF-15.07 | Confidenza minima: le decisioni operative sotto soglia non vengono eseguite. | S | V1 |
| RF-15.08 | Perdita massima: superata una soglia configurata (giornaliera e/o dal picco), il flusso sospende le nuove aperture e il proprietario viene avvisato. | S | [PROPOSTA], D |
| RF-15.09 | Il proprietario può chiudere con un unico comando tutte le posizioni di un flusso, o di tutti i flussi. | S | [PROPOSTA] |
| RF-15.10 | Ogni decisione ridotta o bloccata viene registrata con la decisione originale, quella eseguita e il motivo. | M | V3 |

### 6.16 Esecuzione degli ordini

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-16.01 | Il sistema apre posizioni long e short con la leva e la dimensione approvate dal modulo di rischio. | M | V2, V4 |
| RF-16.02 | Il sistema chiude le posizioni su decisione dell'agente o su comando del proprietario. | M | V4 |
| RF-16.03 | Dopo ogni ordine il sistema verifica sull'exchange l'esito effettivo (posizione aperta o chiusa, prezzo, quantità, commissione) e registra l'esito reale, non quello atteso. | M | V4 |
| RF-16.04 | Gli errori dell'exchange (importo minimo, saldo insufficiente, rifiuto) vengono gestiti senza interrompere il sistema e registrati con il messaggio originale. | M | V2 |
| RF-16.05 | Una procedura di verifica esercita sull'ambiente di test apertura, lettura dello stato e chiusura di una posizione; va eseguita prima di collegare un agente e dopo ogni modifica all'esecuzione. | M | V4 |
| RF-16.06 | Le commissioni di ogni operazione vengono registrate. | M | V1 |
| RF-16.07 | L'ambiente di ogni flusso (test o reale) è sempre ben visibile. Impostare un flusso sull'ambiente reale richiede una conferma esplicita. | M | [PROPOSTA] |

### 6.17 Registrazione e tracciabilità

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-17.01 | Per ogni ciclo vengono conservati: flusso, data e ora, ambiente, modello IA, versione della configurazione, tutti i dati raccolti, il contesto completo inviato all'agente, la risposta integrale, le decisioni interpretate, l'esito del modulo di rischio, l'esito dell'esecuzione e l'istantanea del capitale. | M | V4 |
| RF-17.02 | Ogni operazione eseguita è collegata al ciclo e al contesto che l'hanno generata. | M | V4 |
| RF-17.03 | Lo storico delle posizioni chiuse conserva: asset, direzione, leva, prezzo di apertura e di chiusura, durata, PnL in valore e percentuale, commissioni, motivo della chiusura (agente, stop loss, take profit, liquidazione, comando manuale). | M | V5 |
| RF-17.04 | Lo storico è interrogabile per flusso, periodo, asset e configurazione. | S | V5 |
| RF-17.05 | Il costo di ogni chiamata al modello IA viene registrato e accumulato per flusso. | S | V4 |

### 6.18 Dashboard

La dashboard è **privata**: accessibile solo al proprietario, previa autenticazione [D].

**Monitoraggio**

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-18.01 | Equity curve di ogni flusso, con linea e area in **verde** sopra il capitale iniziale e in **rosso** sotto. | M | V4 |
| RF-18.02 | Capitale iniziale, capitale attuale e rendimento complessivo in percentuale. | M | V5 |
| RF-18.03 | Posizioni aperte: asset, direzione, leva, dimensione, prezzo di ingresso, PnL corrente, exit plan. | M | V4 |
| RF-18.04 | Storico delle posizioni chiuse con prezzo di apertura e di chiusura, PnL in valore e in percentuale. | M | V5 |
| RF-18.05 | Statistiche: operazioni vinte e perse, win rate, PnL medio di vincenti e perdenti, commissioni totali, numero di operazioni, costo del modello IA. | M | V1, V5 |
| RF-18.06 | Elenco dei cicli recenti; per ciascuno si consultano decisioni, ragionamento completo, contesto inviato e risposta integrale dell'agente, con gli indicatori e le previsioni che le hanno motivate. | M | V4 |
| RF-18.07 | Stato di ogni flusso: attivo o in pausa, ultima esecuzione, prossima esecuzione prevista, esito degli ultimi cicli, ambiente, modello. | S | V4 |
| RF-18.08 | Vista comparativa dei flussi (classifica, vedi RF-01.06) con le equity curve sovrapposte. | S | V1, D |
| RF-18.09 | I dati sono aggiornati a ogni ciclo e la dashboard può essere aggiornata su richiesta. | M | V5 |

**Configurazione e comandi**

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-18.10 | Dalla dashboard il proprietario crea, modifica, duplica, avvia, mette in pausa e archivia i flussi. | M | D |
| RF-18.11 | Ogni modifica alla configurazione di un flusso è **versionata**: si sa sempre quale versione era in vigore in ogni ciclo e si può confrontare con le precedenti. | M | D |
| RF-18.12 | Una modifica alla configurazione ha effetto dal ciclo successivo, mai su un ciclo in corso. | M | [PROPOSTA] |
| RF-18.13 | Dalla dashboard il proprietario lancia la chiusura di emergenza (RF-15.09) e la procedura di verifica dell'esecuzione (RF-16.05). | S | [PROPOSTA] |

### 6.19 Replay storico

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-19.01 | Il proprietario può eseguire un flusso, o una sua variante, su un periodo passato, simulando i cicli senza attendere il tempo reale. | S | D |
| RF-19.02 | Il replay usa i dati registrati dai cicli reali (RF-03.05) e, dove mancano, dati storici delle fonti che li rendono disponibili. Le fonti senza storico vengono segnalate come assenti nel contesto. | S | D |
| RF-19.03 | Nel replay l'agente vede solo i dati disponibili fino all'istante simulato, mai dati successivi. | M (per il replay) | [PROPOSTA] |
| RF-19.04 | Le esecuzioni simulate applicano commissioni, importo minimo e un'ipotesi di scostamento di prezzo (slippage) configurabile; stop loss e take profit scattano sulla base dei prezzi storici. | S | [PROPOSTA] |
| RF-19.05 | Prima di avviare un replay il sistema stima il numero di chiamate al modello IA e il relativo costo, e chiede conferma. | S | [PROPOSTA] |
| RF-19.06 | I risultati di un replay sono presentati con le stesse metriche e viste dei flussi live e sono confrontabili tra loro e con i flussi live, ma sempre distinti da questi. | S | D |

### 6.20 Analisi delle prestazioni

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-20.01 | **Valutazione del forecast**: per ogni asset e orizzonte si confronta la previsione con il prezzo effettivo allo scadere dell'orizzonte e si calcola l'errore medio assoluto. | S | V4, V5 |
| RF-20.02 | Grafico previsione e prezzo reale nel tempo, correttamente allineati sullo stesso istante, con medie mobili e volumi. | S | V5 |
| RF-20.03 | Individuazione degli scostamenti anomali tra previsione e realtà, con data e ora esatte, per correlarli a eventi esterni (notizie, whale). | S | V5 |
| RF-20.04 | Analisi dei picchi di volatilità dell'equity: ricostruzione delle decisioni e dei movimenti di prezzo tra due cicli. | S | V5 |
| RF-20.05 | **Valutazione dei segnali**: dai dati registrati si valuta a posteriori quali fonti avevano capacità predittiva, per orientare pesi e fonti attive. | C | V3 |
| RF-20.06 | Metriche di comportamento per flusso: proporzione long/short, frequenza delle operazioni, durata media delle posizioni, esposizione, incidenza delle commissioni. | S | V1 |

### 6.21 Modelli IA

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-21.01 | Il modello IA è configurabile per flusso e sostituibile senza modifiche al resto del sistema. | M | V3, V4 |
| RF-21.02 | Il costo del modello è visibile per flusso, accumulato nel tempo e confrontabile tra flussi (vedi RF-17.05). | S | V4 |

### 6.22 Evoluzione multi-livello

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-22.01 | Un flusso può essere guidato da due agenti: uno **strategico** a bassa frequenza, che analizza il mercato su finestre lunghe (es. settimanali) e produce una "narrativa" o un indirizzo di fondo, e uno **esecutivo** a frequenza più alta che opera tenendone conto. | C | V4, V5 |

### 6.23 Notifiche

| ID | Requisito | Pri. | Fonte |
|----|-----------|------|-------|
| RF-23.01 | Il proprietario riceve notifiche su **Telegram** e via **email**. | S | D |
| RF-23.02 | Eventi notificabili: apertura e chiusura di posizioni, attivazione di stop loss o take profit, liquidazioni, decisioni ridotte o bloccate dal rischio, cicli falliti, raggiungimento della perdita massima, fine di un replay. | S | [PROPOSTA], D |
| RF-23.03 | Per ogni flusso e per ogni tipo di evento il proprietario sceglie il canale (Telegram, email, entrambi, nessuno). | S | [PROPOSTA] |
| RF-23.04 | Riepilogo periodico (es. giornaliero) dei risultati di tutti i flussi via email. | C | [PROPOSTA] |

---

## 7. Requisiti non funzionali (comportamentali)

| ID | Requisito | Fonte |
|----|-----------|-------|
| RNF-01 | **Continuità**: i flussi attivi operano 24/7; i cicli partono puntuali rispetto all'intervallo. | V1, V4 |
| RNF-02 | **Robustezza**: l'errore di una fonte, dell'agente o dell'exchange non blocca il sistema né lascia posizioni prive di protezione. | [PROPOSTA] |
| RNF-03 | **Sicurezza delle credenziali**: chiavi del wallet e chiavi dei servizi non sono mai visibili nella dashboard, nei log o nel contesto inviato all'agente. | V4 |
| RNF-04 | **Minimo privilegio sui fondi**: le credenziali di trading non hanno facoltà di prelievo [ASSUNZIONE, da verificare sull'exchange]. | [PROPOSTA] |
| RNF-05 | **Accesso riservato**: dashboard e comandi sono accessibili solo al proprietario autenticato. | D |
| RNF-06 | **Tracciabilità completa**: ogni decisione è ricostruibile a posteriori con il suo contesto e la sua configurazione. | V4, D |
| RNF-07 | **Configurabilità**: tutti i parametri dei flussi sono modificabili dalla dashboard, senza interventi sul funzionamento interno. | V3, D |
| RNF-08 | **Controllo dei costi**: i costi ricorrenti (modello IA, fonti dati, commissioni) sono misurati e visibili per flusso. | V3, V4 |
| RNF-09 | **Prestazioni**: raccolta dati e decisione si concludono entro una frazione dell'intervallo di ciclo. | V3 |
| RNF-10 | **Estendibilità delle fonti**: una nuova fonte dati si aggiunge senza modificare quelle esistenti (vedi 6.3). | D |

---

## 8. Fasi di rilascio

Tutte le fasi fino a F4 operano solo su **testnet** [D].

| Fase | Contenuto |
|------|-----------|
| **F0. Esecuzione verificata** | Lettura di prezzi, saldo e posizioni; apertura e chiusura di posizioni; procedura di verifica (RF-16.05). |
| **F1. Primo flusso autonomo** | Un flusso con ciclo pianificato, fonti indicatori, pivot, forecast, sentiment e notizie, decisione per asset, modulo di rischio di base (RF-15.01-05, 15.10), registrazione completa. |
| **F2. Dashboard e multi-flusso** | Dashboard privata con monitoraggio e configurazione versionata; più flussi in parallelo con capitali isolati e classifica. |
| **F3. Rischio e qualità** | Stop loss e take profit, confidenza minima, perdita massima, chiusura di emergenza, pesi dei segnali, valutazione del forecast, notifiche Telegram ed email. |
| **F4. Replay e analisi** | Replay storico, analisi delle prestazioni, valutazione dei segnali. |
| **F5. Evoluzioni** | Fonti whale e volumi globali, agente multi-livello, chiusure parziali. |
| **F6. Reale (opzionale)** | Dopo alcuni mesi di sperimentazione e per scelta esplicita: uno o più flussi sull'ambiente reale con capitale limitato. |
| **Backlog** | BL-01 spot, BL-02 copy-trading. |

---

## 9. Criteri di accettazione principali

- **CA-01 (F0)**: sull'ambiente di test la procedura di verifica apre una posizione long con leva 2 su BTC, ne legge lo stato e la chiude; saldo e posizioni letti dopo ogni passo coincidono con quanto mostrato dall'exchange.
- **CA-02 (F1)**: un flusso esegue almeno 7 giorni consecutivi di cicli pianificati in test, con meno dell'1% di cicli falliti [ASSUNZIONE sulla soglia] e nessuna sovrapposizione.
- **CA-03 (F1)**: per un qualsiasi ciclo scelto a caso si ricostruiscono contesto completo, configurazione in vigore, risposta dell'agente, esito del rischio e dell'esecuzione.
- **CA-04 (F1)**: una risposta malformata non produce mai ordini; una leva o un'esposizione oltre i limiti produce sempre un ordine ridotto ai limiti, registrato come tale.
- **CA-05 (F2)**: con almeno due flussi attivi sugli stessi asset, saldo, posizioni e risultati di ciascuno restano separati e coincidono con quanto registrato.
- **CA-06 (F2)**: una modifica di configurazione fatta dalla dashboard ha effetto dal ciclo successivo e crea una nuova versione consultabile.
- **CA-07 (F3)**: ogni posizione aperta ha stop loss e take profit attivi sull'exchange entro il ciclo in cui viene aperta.
- **CA-08 (F3)**: superata la perdita massima configurata, il flusso non apre nuove posizioni e arriva una notifica su Telegram ed email.
- **CA-09 (F4)**: un replay di un periodo passato non usa mai dati successivi all'istante simulato e produce le stesse metriche dei flussi live.

---

## 10. Assunzioni da confermare

| # | Assunzione | Requisito |
|---|------------|-----------|
| A1 | Se solo alcune delle decisioni per asset sono malformate, si scartano quelle e si eseguono le altre (invece di scartare l'intero ciclo). | RF-14.10 |
| A2 | Soglia di cicli falliti accettabile in F1: meno dell'1%. | CA-02 |
| A3 | Le credenziali di trading possono essere limitate senza facoltà di prelievo sull'exchange scelto. | RNF-04 |
| A4 | Il primo flusso userà gli asset BTC, ETH, SOL con intervallo di 15 minuti, come nei video. | RF-01.01, RF-02.02 |

---

## 11. Decisioni prese (intervista del 7-8 novembre 2026)

| Tema | Decisione |
|------|-----------|
| Utenti | Progetto personale: un solo proprietario e utente. |
| Capitale | Alcuni mesi solo con fondi virtuali su testnet per testare e iterare; eventualmente poi capitale reale. I limiti di perdita sono parametri configurabili, non valori decisi ora. |
| Dashboard | Privata, solo per il proprietario. |
| Agenti | Multi-agente: più flussi in parallelo, ciascuno con la propria configurazione. |
| Configurazione dei flussi | Tutto per flusso: intervallo, asset, modello, pesi, rischio, istruzioni, capitale. Gestita dalla dashboard con versionamento. |
| Decisioni per ciclo | Una decisione per ciascun asset del flusso. |
| Controllo umano | Solo autonomo; restano pausa, limiti di rischio e chiusura di emergenza. |
| Fonti dati | Ogni fonte è implementata in modo ortogonale; se una fonte non è praticabile, il suo requisito si chiude. Come procurarsi i dati è una scelta tecnica. |
| Notifiche | Telegram ed email. |
| Exchange | Hyperliquid. La sostituibilità è un tema di architettura, da trattare in progettazione. |
| Filtro di rischio | Un'operazione oltre i limiti viene ridotta ai limiti ed eseguita. |
| Replay storico | Sì: si possono rigiocare i flussi su dati storici. |
| Spot e copy-trading | Fuori dalla prima versione; nel backlog come proposte a bassa priorità. |
