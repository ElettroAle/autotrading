# AutoTrading: documento dei requisiti funzionali

**Stato:** bozza 0.3, con le decisioni dell'intervista e della revisione del 7-8 novembre 2026 (sezione 11)
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
| D | Decisione del proprietario (intervista e revisione, sezione 11) |

Convenzioni usate nel testo:

- **RF-xx.yy**: requisito funzionale. **RNF-xx**: requisito non funzionale.
- **Priorità**: **M** (Must, necessario per la fase indicata), **S** (Should, atteso a breve), **C** (Could, evoluzione futura).
- **Fase**: fase di rilascio in cui il requisito è previsto (sezione 8).
- **[Vn] / [D]**: provenienza del requisito.
- **[PROPOSTA]**: requisito non presente nei video, aggiunto perché necessario a rendere il sistema sicuro o completo.
- **[ASSUNZIONE]**: interpretazione di un punto non esplicito, da confermare.

Le sezioni dei requisiti (sezione 6) sono ordinate secondo l'ordine di realizzazione: prima ciò che serve a far operare e testare i flussi (agente, fonti, exchange, configurazione), poi la dashboard e le funzioni di analisi.

---

## 2. Contesto e obiettivi

### 2.1 Contesto

Le fonti partono dal benchmark pubblico **Alpha Arena**, nel quale sei modelli linguistici di frontiera ricevono ciascuno un capitale reale e operano in autonomia su criptovalute, con lo stesso prompt e gli stessi dati numerici [V1]. Lo scopo della serie è replicare quell'esperimento con un agente proprio e poi **migliorarlo**, fornendo all'agente un contesto più ricco (notizie, sentiment, previsioni, livelli di supporto e resistenza, movimenti di grandi investitori), aggiungendo controlli sul rischio e uno strumento di monitoraggio [V1, V2, V3].

AutoTrading nasce come progetto **personale**: il primo e, inizialmente, unico utente è il proprietario. La piattaforma è però strutturata fin dall'inizio per **più utenti**: ogni utente è un **tenant** indipendente, con i propri conti, i propri flussi, i propri dati e le proprie notifiche, invisibili agli altri utenti [D].

### 2.2 Obiettivo del prodotto

Realizzare una piattaforma che:

1. Fa operare in parallelo, per ogni utente, uno o più **flussi di trading** indipendenti, ciascuno guidato da un agente di intelligenza artificiale con la propria configurazione, per confrontarli [V1, D].
2. Esegue in autonomia, a intervalli regolari e senza intervento umano, il ciclo di analisi del mercato e di decisione di ogni flusso [V1, V4, D].
3. Esegue le decisioni su un exchange di contratti perpetui su criptovalute, sia al rialzo (long) sia al ribasso (short), con leva [V2, V4].
4. Punta a generare profitto **indipendentemente dalla direzione del mercato** [V5].
5. Protegge il capitale con regole di rischio indipendenti dall'agente, a difesa da errori e "allucinazioni" del modello [V3, V5].
6. Registra ogni decisione con il contesto completo che l'ha generata, per spiegarla, verificarla e migliorare il sistema nel tempo [V4, V5].
7. Permette di rigiocare i flussi su dati storici, per iterare più in fretta sulle configurazioni [D].
8. Permette all'utente di incassare i profitti quando lo desidera, senza perdere il controllo del capitale [D].
9. Offre una dashboard privata per configurare i flussi e seguirne in tempo reale andamento, posizioni e ragionamento [V4, V5, D].

### 2.3 Strategia di adozione

- **Fase di sperimentazione**: per alcuni mesi la piattaforma opera **solo con fondi virtuali** sull'ambiente di test dell'exchange, per testare e iterare [D].
- **Prima i flussi, poi la dashboard**: la priorità è poter avviare e testare i flussi il prima possibile. La configurazione è quindi disponibile tramite interfaccia programmatica prima e indipendentemente dalla dashboard, che arriva in una fase successiva [D].
- **Eventuale passaggio al reale**: solo dopo la sperimentazione e per scelta esplicita dell'utente, eventualmente con capitale limitato [D].

### 2.4 Principi guida

- **Approccio incrementale**: partire semplice, mettere in funzione, osservare, aggiungere funzionalità e dati solo dopo averli verificati [V4].
- **Capacità ortogonali e configurabili**: fonti dati, modelli IA ed exchange sono capacità indipendenti, integrate attraverso un'interfaccia comune. Aggiungerne una, sostituirla o rimuoverla non tocca le altre né il ciclo decisionale; sceglierne una diversa per un flusso è solo questione di configurazione. Se una capacità si rivela non praticabile, il suo requisito si chiude senza effetti sul resto [D].
- **Trasparenza delle decisioni**: ogni azione dell'agente è accompagnata dal suo ragionamento ed è ricostruibile [V1, V4].
- **Tutto per flusso**: ogni parametro operativo (conto, asset, intervallo, modello, fonti attive e pesi, regole di rischio, istruzioni, capitale) appartiene a un flusso [D].
- **Tutto per tenant**: ogni dato, conto, flusso, configurazione e notifica appartiene a un utente e non è visibile agli altri [D].
- **Scopo sperimentale**: i risultati iniziali, positivi o negativi, possono dipendere dal caso e vanno valutati su periodi lunghi [V1].

---

## 3. Glossario

| Termine | Significato |
|---------|-------------|
| Utente / tenant | Persona registrata sulla piattaforma. Ogni utente è un tenant: uno spazio isolato che contiene i suoi conti, flussi, dati e impostazioni [D]. |
| Conto di trading | Collegamento a un exchange: exchange, credenziali e ambiente (test o reale). Appartiene a un utente; uno o più flussi vi operano [D]. |
| Flusso di trading | Unità operativa indipendente: un agente IA con la propria configurazione (conto, asset, intervallo, modello, fonti e pesi, rischio, istruzioni) e il proprio capitale allocato, che opera in parallelo agli altri flussi [D]. |
| Capitale allocato | Parte del saldo di un conto assegnata a un flusso; il flusso può impegnarne al massimo quella quota [D]. |
| Capitale libero | Parte del saldo di un conto non allocata ad alcun flusso; è l'unica parte prelevabile [D]. |
| Contabilità virtuale | Registro, tenuto dalla piattaforma, di capitale, posizioni, PnL e commissioni di ciascun flusso, indipendente da come l'exchange separa (o non separa) i fondi [D]. |
| Riconciliazione | Verifica che la somma delle contabilità virtuali dei flussi di un conto coincida con il saldo reale del conto sull'exchange [D]. |
| Agente IA | Componente che riceve il contesto di mercato e restituisce le decisioni operative strutturate di un flusso, basato su un modello linguistico (LLM). |
| Modello IA / fornitore | Il modello linguistico usato da un agente e il servizio che lo eroga. Configurabili per flusso [D]. |
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
| Pesi dei segnali | Importanza relativa assegnata a ciascuna fonte dati attiva nel contesto dell'agente [V3, D]. |
| Interfaccia programmatica | Modo di configurare e comandare la piattaforma senza interfaccia grafica, usato prima della dashboard e poi dalla dashboard stessa [D]. |
| Ambiente di test | Ambiente dell'exchange con fondi virtuali che riproduce il comportamento reale senza rischio economico [V3, V4]. |
| Replay storico | Esecuzione simulata di un flusso su un periodo passato, più veloce del tempo reale [D]. |
| Fee | Commissione pagata per ciascuna operazione [V1]. |

---

## 4. Attori

| Attore | Descrizione |
|--------|-------------|
| **Utente** | Titolare di un tenant. Collega i propri conti, crea e configura i flussi, li avvia e li ferma, incassa i profitti, lancia i replay, analizza i risultati. Vede solo ciò che gli appartiene [D]. |
| **Proprietario della piattaforma** | Il primo utente. In più gestisce la piattaforma stessa (abilitazione di altri utenti) [D]. |
| **Agente IA** | Prende le decisioni operative di un flusso a ogni ciclo, entro i limiti imposti dalla configurazione e dal modulo di rischio. |
| **Exchange** | Sistema esterno su cui si eseguono gli ordini e da cui si leggono prezzi, saldo e posizioni. Exchange di riferimento: Hyperliquid [V1, V2, D]. |
| **Fornitore del modello IA** | Servizio esterno che eroga il modello linguistico usato dall'agente [V3, V4]. |
| **Fonti dati esterne** | Servizi che forniscono notizie, sentiment, movimenti delle whale, volumi e order book. |
| **Pianificatore** | Meccanismo che avvia i cicli decisionali di ogni flusso al suo intervallo [V4]. |
| **Canali di notifica** | Telegram ed email, per gli avvisi agli utenti [D]. |

---

## 5. Ambito

### 5.1 Incluso

- Trading automatizzato di **criptovalute** tramite **contratti perpetui con leva**, long e short [V1, V2, D].
- Più **utenti**, ciascuno con il proprio spazio isolato [D].
- Più **conti** per utente e più **flussi** per conto, ciascun flusso con configurazione e capitale propri [D].
- Asset configurabili per flusso; insieme iniziale suggerito **BTC, ETH, SOL** [V4].
- Esecuzione sull'**ambiente di test** dell'exchange; ambiente reale come opzione successiva e deliberata [D].
- **Incasso** dei profitti su richiesta dell'utente [D].
- **Replay storico** dei flussi [D].
- Raccolta e arricchimento del contesto, decisione IA, controllo del rischio, esecuzione, registrazione, configurazione (prima programmatica, poi da dashboard), monitoraggio, analisi delle prestazioni e notifiche.

### 5.2 Escluso

- Gestione del capitale di terzi: ogni utente opera esclusivamente con i propri conti e le proprie credenziali [D].
- Condivisione di conti, flussi o dati tra utenti [D].
- Mercati tradizionali (azioni, ETF, forex). La scelta delle cripto è motivata da mercato aperto 24/7 e abbondanza di dati [V1].
- Trading ad altissima frequenza: le decisioni avvengono su intervalli di minuti od ore, non di microsecondi [V1].
- Approvazione manuale delle singole operazioni: i flussi operano in piena autonomia [D].
- Prelievi automatici dall'exchange: ogni uscita di fondi è un'azione manuale e confermata dell'utente [D].

### 5.3 Backlog proposto (fuori dalla prima versione)

Funzionalità registrate come candidate, con priorità bassa, da non sviluppare ora [D]:

- **BL-01. Trading spot**: i flussi possono anche comprare e vendere criptovalute spot.
- **BL-02. Copy-trading**: un flusso può replicare le operazioni di un trader o agente esterno (es. quelli di Alpha Arena) [V1].
- **BL-03. Netting tra flussi**: più flussi dello stesso conto possono operare lo stesso asset; la piattaforma mantiene posizioni virtuali per flusso e una sola posizione aggregata sull'exchange. Finché non è disponibile vale la regola di conflitto RF-02.05 [D].

---

## 6. Requisiti funzionali

### 6.1 Utenti e tenant

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-01.01 | Ogni utente dispone di uno spazio (tenant) che contiene i suoi conti, flussi, configurazioni, dati registrati, risultati e impostazioni di notifica. | M | F1 | D |
| RF-01.02 | Nessun dato di un tenant è visibile, interrogabile o modificabile da un altro utente. Ogni funzione della piattaforma opera sempre nel perimetro dell'utente autenticato. | M | F1 | D |
| RF-01.03 | Ogni accesso alla piattaforma, programmatico o da dashboard, richiede autenticazione e identifica l'utente. | M | F1 | D |
| RF-01.04 | Il proprietario della piattaforma abilita i nuovi utenti. Nella prima versione esiste un solo utente, il proprietario; la registrazione autonoma è un'evoluzione. | M / C | F1 / F5 | D |
| RF-01.05 | Le credenziali dei conti (chiavi dell'exchange) e dei servizi (fornitori IA, fonti dati) di un utente sono conservate nel suo tenant e usate solo per i suoi flussi. | M | F1 | D, [PROPOSTA] |
| RF-01.06 | Le classifiche e i confronti tra flussi (RF-03.06) riguardano solo i flussi dell'utente. | M | F2 | D |

### 6.2 Conti di trading

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-02.01 | L'utente registra uno o più **conti di trading**, ciascuno con: nome, exchange, ambiente (test o reale), credenziali. | M | F0 | D |
| RF-02.02 | Ogni flusso è assegnato a un conto. Più flussi possono condividere lo stesso conto, oppure l'utente può dedicare un conto a ciascun flusso quando l'exchange lo consente (sotto-conti, portafogli separati). La scelta è dell'utente. | M | F1 | D |
| RF-02.03 | Per ogni conto la piattaforma legge dall'exchange saldo, liquidità disponibile e posizioni aperte. | M | F0 | V2, V4 |
| RF-02.04 | Il saldo di un conto è ripartito in: capitale allocato ai flussi e capitale libero. La somma delle allocazioni non può superare il saldo. | M | F1 | D |
| RF-02.05 | **Regola di conflitto**: due flussi assegnati allo stesso conto non possono avere asset in comune. La piattaforma rifiuta la creazione o la modifica di un flusso che violerebbe la regola, indicando il flusso in conflitto. Evoluzione: BL-03 netting. | M | F1 | D |
| RF-02.06 | L'utente può collegare, modificare le credenziali e scollegare un conto. Lo scollegamento è possibile solo se nessun flusso attivo vi è assegnato. | M | F1 | [PROPOSTA] |
| RF-02.07 | L'ambiente di ogni conto (test o reale) è sempre ben visibile. Registrare un conto sull'ambiente reale richiede una conferma esplicita. | M | F0 | [PROPOSTA] |
| RF-02.08 | Il sistema verifica la validità delle credenziali di un conto al momento della registrazione e la segnala quando viene meno. | S | F1 | [PROPOSTA] |

### 6.3 Flussi di trading

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-03.01 | L'utente può creare più flussi di trading, ciascuno con: nome, conto, asset, intervallo di ciclo, fornitore e modello IA con relativi parametri, fonti dati attive e relativi pesi, istruzioni dell'agente, regole di rischio, capitale allocato. | M | F1 | V1, D |
| RF-03.02 | I flussi operano in parallelo e in modo indipendente: il comportamento, gli errori o le pause di un flusso non influenzano gli altri. | M | F1 | D |
| RF-03.03 | Capitale, posizioni e risultati di ogni flusso sono **isolati** tramite la contabilità virtuale (sezione 6.13): le operazioni di un flusso non modificano la contabilità di un altro, e i risultati sono attribuibili al singolo flusso senza ambiguità, anche quando più flussi condividono lo stesso conto. | M | F1 | D |
| RF-03.04 | L'utente può avviare, mettere in pausa, riprendere, fermare e archiviare ogni flusso. Pausa e stop sono distinti (vedi RF-22.01 e RF-22.02). | M | F1 | D |
| RF-03.05 | L'utente può duplicare un flusso esistente per crearne una variante e confrontarla. | S | F2 | [PROPOSTA] |
| RF-03.06 | Una classifica confronta i flussi dell'utente su: rendimento %, PnL, commissioni, win rate, numero di operazioni, drawdown massimo, costo del modello IA. | S | F2 | V1, D |

### 6.4 Ciclo decisionale autonomo

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-04.01 | Ogni flusso attivo esegue automaticamente il proprio ciclo decisionale al proprio intervallo, 24 ore su 24, 7 giorni su 7, senza intervento umano. | M | F1 | V1, V4, D |
| RF-04.02 | L'intervallo di ciclo è configurabile per flusso; valore iniziale suggerito 15 minuti. | M | F1 | V4, D |
| RF-04.03 | Ogni ciclo esegue, nell'ordine: (1) lettura dello stato del capitale del flusso, (2) raccolta dei dati delle fonti attive, (3) composizione del contesto, (4) decisione dell'agente, (5) controllo del modulo di rischio, (6) esecuzione degli ordini risultanti, (7) aggiornamento della contabilità virtuale, (8) registrazione completa del ciclo. | M | F1 | V1, V4 |
| RF-04.04 | La raccolta dati di un ciclo si conclude in un tempo nettamente inferiore all'intervallo; le fonti indipendenti vengono interrogate in parallelo, non in sequenza. | S | F1 | V3 |
| RF-04.05 | Se una fonte dati non risponde, il ciclo prosegue con le fonti disponibili, il contesto indica all'agente quali dati mancano e il problema viene registrato. | M | F1 | [PROPOSTA] |
| RF-04.06 | Il fallimento di un ciclo (errore dell'agente, dell'exchange o di rete) non impedisce l'esecuzione dei cicli successivi. | M | F1 | [PROPOSTA] |
| RF-04.07 | Due cicli dello stesso flusso non si sovrappongono: se un ciclo è ancora in corso allo scadere dell'intervallo, il successivo viene saltato e l'evento registrato. | M | F1 | [PROPOSTA] |
| RF-04.08 | Il contesto di ogni ciclo include l'ora corrente e il tempo trascorso dall'avvio del flusso. | S | F1 | V1 |
| RF-04.09 | Dati di mercato comuni a più flussi (es. indicatori dello stesso asset nello stesso istante) possono essere riutilizzati, anche tra utenti diversi, purché ogni ciclo registri esattamente i dati che ha usato. | C | F5 | [PROPOSTA] |

### 6.5 Fonti dati: requisiti comuni

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-05.01 | Ogni fonte dati (indicatori tecnici, pivot point, forecast, sentiment, notizie, whale, volumi e order book) è una capacità **indipendente** dalle altre, integrata attraverso un'interfaccia comune. | M | F1 | D |
| RF-05.02 | **Selezione delle fonti**: per ogni flusso l'utente attiva o disattiva singolarmente ciascuna fonte disponibile. Una fonte disattivata non viene interrogata per quel flusso e non compare nel suo contesto. | M | F1 | D |
| RF-05.03 | Aggiungere, sostituire o rimuovere una fonte non richiede modifiche al funzionamento delle altre fonti né del ciclo decisionale. Una nuova fonte diventa selezionabile nei flussi con la sola configurazione. | M | F1 | D |
| RF-05.04 | Ogni fonte può avere parametri propri (es. numero di notizie, orizzonti del forecast), configurabili per flusso. | S | F1 | D, [PROPOSTA] |
| RF-05.05 | Ogni fonte si applica automaticamente a tutti gli asset configurati nel flusso. | M | F1 | V3 |
| RF-05.06 | Ogni valore raccolto viene registrato con il suo istante di riferimento, così da poterlo riutilizzare nei replay storici e nelle analisi. | M | F1 | V4, D |
| RF-05.07 | L'elenco delle fonti disponibili, con i rispettivi parametri, è consultabile dall'utente. | M | F1 | [PROPOSTA] |

### 6.6 Fonte: dati di mercato e indicatori tecnici

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-06.01 | Per ogni asset sono disponibili il prezzo corrente e lo storico dei prezzi necessario al calcolo degli indicatori. | M | F1 | V2 |
| RF-06.02 | Per ogni asset vengono calcolati almeno: EMA20, MA20, MACD, RSI a 7 e a 14 periodi, mid price, open interest, funding rate, volume. | M | F1 | V1, V3 |
| RF-06.03 | Gli indicatori sono forniti come valori correnti e come serie recenti, su un timeframe di breve (allineato all'intervallo del flusso) e su uno di lungo periodo (es. 4 ore, con medie a 20 e 50 periodi). | M | F1 | V1, V3 |
| RF-06.04 | L'insieme degli indicatori è estendibile; candidati futuri: livelli di Fibonacci, linee di Gann, analisi ciclica. | C | F5 | V4 |

### 6.7 Fonte: pivot point

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-07.01 | Per ogni asset vengono calcolati i pivot point PP, R1, R2, S1, S2. | M | F1 | V3 |
| RF-07.02 | All'agente vengono forniti la posizione del prezzo rispetto al PP (sopra o sotto, come indicazione di tendenza) e la distanza dal supporto e dalla resistenza più vicini. | M | F1 | V3 |

### 6.8 Fonte: previsione dei prezzi (forecast)

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-08.01 | Per ogni asset viene prodotta una previsione del prezzo su più orizzonti; quelli iniziali sono 15 minuti e 1 ora. | M | F1 | V3, V4 |
| RF-08.02 | Ogni previsione riporta ultimo prezzo, prezzo previsto, variazione percentuale prevista e orizzonte. | M | F1 | V3, V4 |
| RF-08.03 | La profondità dello storico usato per la previsione è configurabile. | S | F1 | V5 |
| RF-08.04 | Ogni previsione viene registrata per il confronto con il prezzo effettivo allo scadere dell'orizzonte (vedi 6.26). | M | F1 | V4, V5 |
| RF-08.05 | Orizzonti più lunghi (giorni, settimane), necessari a un agente strategico (vedi 6.27). | C | F5 | V5 |

### 6.9 Fonte: sentiment di mercato

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-09.01 | A ogni ciclo viene rilevato l'indice di sentiment del mercato cripto (Fear & Greed), con valore numerico e classificazione testuale. | M | F1 | V3 |

### 6.10 Fonte: notizie

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-10.01 | A ogni ciclo vengono raccolte le notizie cripto più recenti (titolo, data e ora, sintesi o testo) e incluse nel contesto. | M | F1 | V1, V3 |
| RF-10.02 | Il numero e l'età massima delle notizie incluse sono configurabili per flusso. | S | F1 | [PROPOSTA] |
| RF-10.03 | Evoluzione: messaggi social di persone influenti per il mercato, anche specifici per asset. | C | F5 | V3 |

### 6.11 Fonte: movimenti delle whale

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-11.01 | Vengono rilevati i grandi trasferimenti di criptovalute (data e ora, asset, quantità, controvalore, descrizione) e inclusi nel contesto. | S | F5 | V3 |

### 6.12 Fonte: volumi globali e order book

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-12.01 | All'agente vengono fornite informazioni su volumi e ordini aggregati di più exchange, non solo di quello su cui si opera, per capire se prevalgono acquisti o vendite. Quale dato dell'order book usare è da definire. | C | F5 | V3 |

### 6.13 Stato del capitale, posizioni e contabilità virtuale

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-13.01 | La piattaforma tiene per ogni flusso una **contabilità virtuale**: capitale allocato, liquidità disponibile, posizioni aperte, PnL realizzato e non realizzato, commissioni. È sempre tenuta, sia che il flusso condivida il conto con altri sia che ne abbia uno dedicato. | M | F1 | D |
| RF-13.02 | A ogni ciclo l'agente riceve lo stato del **flusso** (dalla contabilità virtuale), non quello dell'intero conto: saldo, liquidità disponibile, valore complessivo e posizioni aperte del flusso. | M | F1 | V1, V4, D |
| RF-13.03 | Per ogni posizione aperta sono noti: asset, direzione, dimensione, leva, prezzo di ingresso, PnL non realizzato, prezzo di liquidazione, exit plan dichiarato. | M | F1 | V1 |
| RF-13.04 | Il contesto dell'agente include il rendimento percentuale del flusso dal suo avvio. | M | F1 | V1 |
| RF-13.05 | Lo stato del capitale e delle posizioni del flusso viene salvato come istantanea a ogni ciclo. | M | F1 | V4, V5 |
| RF-13.06 | **Riconciliazione**: a ogni ciclo, e comunque a intervalli regolari, la somma delle contabilità virtuali dei flussi di un conto (più il capitale libero) viene confrontata con il saldo e le posizioni reali letti dall'exchange. | M | F1 | D |
| RF-13.07 | Uno scostamento oltre una soglia configurabile per conto genera un allarme all'utente e sospende le nuove aperture di tutti i flussi del conto, finché l'utente non conferma di aver verificato. Protegge da interventi manuali sull'exchange, liquidazioni non attese ed errori. | M | F3 | D, [PROPOSTA] |
| RF-13.08 | Le posizioni trovate sull'exchange e non attribuibili ad alcun flusso vengono segnalate all'utente e non toccate dalla piattaforma. | S | F3 | [PROPOSTA] |

### 6.14 Pesi dei segnali

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-14.01 | Per ogni flusso l'utente assegna un peso di importanza a ciascuna fonte attiva. Il peso fa parte della configurazione del flusso, insieme alla selezione delle fonti (RF-05.02). | M | F1 | V3, V4, D |
| RF-14.02 | I pesi vengono comunicati all'agente nel contesto, perché ne tenga conto nel ragionamento. | M | F1 | V3, D |
| RF-14.03 | Se l'utente non indica i pesi, tutte le fonti attive hanno lo stesso peso. | M | F1 | [PROPOSTA] |
| RF-14.04 | I pesi in vigore a ogni ciclo vengono registrati con le decisioni. | M | F1 | V3 |

### 6.15 Istruzioni dell'agente

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-15.01 | Le istruzioni dell'agente (ruolo, obiettivo, strategia, regole operative, formato della risposta) sono definite per flusso e modificabili tramite la configurazione del flusso. | M | F1 | V3, D |
| RF-15.02 | Le istruzioni includono le regole operative vigenti: al massimo una posizione per asset, azioni consentite, intervallo di leva ammesso, formato obbligatorio della risposta. | M | F1 | V3, V4 |

### 6.16 Modelli IA

I modelli IA seguono lo stesso principio delle fonti dati: sono capacità ortogonali, integrate tramite un'interfaccia comune, scelte per flusso con la sola configurazione [D].

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-16.01 | Per ogni flusso l'utente sceglie il **fornitore**, il **modello** e i suoi **parametri** (es. livello di ragionamento, temperatura, limite di lunghezza della risposta) tra quelli disponibili. | M | F1 | V3, V4, D |
| RF-16.02 | Ogni fornitore di modelli è integrato attraverso un'interfaccia comune. Aggiungere un fornitore o un modello non richiede modifiche al ciclo decisionale, alle fonti, al modulo di rischio né agli altri fornitori; il nuovo modello diventa selezionabile nei flussi con la sola configurazione. | M | F1 | D |
| RF-16.03 | Cambiare modello o fornitore di un flusso è una modifica di configurazione (versionata, RF-21.03) e ha effetto dal ciclo successivo. | M | F1 | D |
| RF-16.04 | Le credenziali dei fornitori appartengono all'utente (RF-01.05). | M | F1 | D |
| RF-16.05 | L'elenco dei fornitori e dei modelli disponibili, con i parametri ammessi, è consultabile dall'utente. | M | F1 | [PROPOSTA] |
| RF-16.06 | Il costo di ogni chiamata al modello viene registrato e accumulato per flusso; è visibile e confrontabile tra flussi (vedi RF-20.05). | S | F1 | V4 |
| RF-16.07 | Un errore o una indisponibilità del fornitore fa fallire il ciclo (RF-04.06) senza eseguire ordini; l'evento è registrato. | M | F1 | [PROPOSTA] |

### 6.17 Decisione dell'agente

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-17.01 | A ogni ciclo l'agente riceve il contesto completo del flusso (istruzioni, stato del capitale del flusso, dati per asset dalle fonti attive, pesi) e restituisce le decisioni in forma **strutturata** e leggibile dalla macchina. | M | F1 | V1, V3 |
| RF-17.02 | A ogni ciclo l'agente restituisce **una decisione per ciascun asset** del flusso. | M | F1 | V1, D |
| RF-17.03 | Le azioni ammesse per ogni asset sono: **apri** (long o short), **chiudi**, **mantieni** (hold). | M | F1 | V1, V4 |
| RF-17.04 | Per un'apertura la decisione contiene: direzione, quota di capitale da impegnare (frazione del capitale del flusso), leva, ragionamento. | M | F1 | V3, V4 |
| RF-17.05 | Per un'apertura la decisione contiene anche l'exit plan: prezzo obiettivo (take profit), prezzo di stop (stop loss), condizione di invalidazione. | S | F3 | V1, V5 |
| RF-17.06 | Ogni decisione contiene un **punteggio di confidenza**. | S | F3 | V1 |
| RF-17.07 | Per una decisione "mantieni" i campi operativi vengono ignorati. | M | F1 | V4 |
| RF-17.08 | La chiusura è totale. La chiusura parziale è un'evoluzione futura. | M / C | F1 / F5 | V4 |
| RF-17.09 | Il ragionamento dell'agente viene sempre conservato e reso visibile, anche per le decisioni "mantieni". | M | F1 | V1, V4 |
| RF-17.10 | Una risposta non conforme al formato atteso viene scartata senza eseguire nulla e l'evento viene registrato. Se solo alcune decisioni sono malformate, si scartano quelle e si valutano le altre [ASSUNZIONE]. | M | F1 | V3 |

### 6.18 Gestione del rischio

Il modulo di rischio è **indipendente dall'agente** e filtra ogni decisione prima dell'esecuzione, per proteggere il capitale da errori del modello [V3]. Tutti i limiti sono **parametri configurabili per flusso**, senza valori imposti dal sistema [D]. I limiti si applicano al capitale del **flusso** (contabilità virtuale), mai all'intero conto.

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-18.01 | Esposizione massima per singola operazione, come percentuale del capitale del flusso (esempio citato: 5%). Un'apertura oltre il limite viene **ridotta al limite** ed eseguita. | M | F1 | V3, D |
| RF-18.02 | Leva massima. Una leva superiore viene **ridotta al massimo** consentito. | M | F1 | V3, V4, D |
| RF-18.03 | Esposizione complessiva massima del flusso (somma delle posizioni aperte). Un'apertura che la supererebbe viene ridotta al margine residuo, o non eseguita se il margine residuo è nullo. | S | F3 | [PROPOSTA] |
| RF-18.04 | Vengono bloccate le decisioni incoerenti con lo stato del flusso: apertura su un asset con posizione già aperta, chiusura di una posizione inesistente, asset fuori dal flusso, liquidità del flusso insufficiente. | M | F1 | V3, V4 |
| RF-18.05 | Le aperture sotto l'importo minimo dell'exchange vengono gestite in modo deterministico (portate al minimo o non eseguite, secondo configurazione) e registrate. | M | F1 | V2 |
| RF-18.06 | Ogni apertura ha stop loss e take profit attivi sull'exchange, così da proteggere la posizione anche tra un ciclo e l'altro. Se l'agente non li indica, si applicano valori predefiniti del flusso. | S | F3 | V5 |
| RF-18.07 | Confidenza minima: le decisioni operative sotto soglia non vengono eseguite. | S | F3 | V1 |
| RF-18.08 | Perdita massima: superata una soglia configurata (giornaliera e/o dal picco), il flusso sospende le nuove aperture e l'utente viene avvisato. | S | F3 | [PROPOSTA], D |
| RF-18.09 | L'utente può chiudere con un unico comando tutte le posizioni di un flusso, di un conto o di tutti i suoi flussi. | S | F3 | [PROPOSTA] |
| RF-18.10 | Ogni decisione ridotta o bloccata viene registrata con la decisione originale, quella eseguita e il motivo. | M | F1 | V3 |

### 6.19 Esecuzione degli ordini

L'exchange è integrato attraverso un'interfaccia comune, come fonti e modelli: un flusso opera sull'exchange del proprio conto e aggiungere un exchange non richiede modifiche al resto [D].

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-19.01 | Il sistema apre posizioni long e short con la leva e la dimensione approvate dal modulo di rischio, sul conto del flusso. | M | F0 | V2, V4 |
| RF-19.02 | Il sistema chiude le posizioni su decisione dell'agente o su comando dell'utente. | M | F0 | V4 |
| RF-19.03 | Dopo ogni ordine il sistema verifica sull'exchange l'esito effettivo (posizione aperta o chiusa, prezzo, quantità, commissione), registra l'esito reale, non quello atteso, e aggiorna la contabilità virtuale del flusso. | M | F1 | V4, D |
| RF-19.04 | Gli errori dell'exchange (importo minimo, saldo insufficiente, rifiuto) vengono gestiti senza interrompere il sistema e registrati con il messaggio originale. | M | F0 | V2 |
| RF-19.05 | Una procedura di verifica esercita su un conto di test apertura, lettura dello stato e chiusura di una posizione; va eseguita prima di collegare un agente e dopo ogni modifica all'esecuzione. | M | F0 | V4 |
| RF-19.06 | Le commissioni di ogni operazione vengono registrate e attribuite al flusso. | M | F1 | V1 |
| RF-19.07 | Ogni ordine inviato all'exchange è riconducibile al flusso e al ciclo che lo hanno generato. | M | F1 | D, [PROPOSTA] |

### 6.20 Registrazione e tracciabilità

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-20.01 | Per ogni ciclo vengono conservati: utente, flusso, conto, data e ora, ambiente, fornitore e modello IA, versione della configurazione, tutti i dati raccolti, il contesto completo inviato all'agente, la risposta integrale, le decisioni interpretate, l'esito del modulo di rischio, l'esito dell'esecuzione e l'istantanea della contabilità virtuale. | M | F1 | V4 |
| RF-20.02 | Ogni operazione eseguita è collegata al ciclo e al contesto che l'hanno generata. | M | F1 | V4 |
| RF-20.03 | Lo storico delle posizioni chiuse conserva: asset, direzione, leva, prezzo di apertura e di chiusura, durata, PnL in valore e percentuale, commissioni, motivo della chiusura (agente, stop loss, take profit, liquidazione, comando manuale, incasso). | M | F1 | V5 |
| RF-20.04 | Lo storico è interrogabile per flusso, conto, periodo, asset e configurazione. | S | F2 | V5 |
| RF-20.05 | Il costo di ogni chiamata al modello IA viene registrato e accumulato per flusso. | S | F1 | V4 |
| RF-20.06 | Tutti i dati registrati sono consultabili dall'utente tramite l'interfaccia programmatica, prima e indipendentemente dalla dashboard. | M | F1 | D |

### 6.21 Configurazione e comandi (interfaccia programmatica)

Per poter avviare e testare i flussi prima della dashboard, tutte le funzioni di configurazione, comando e consultazione sono esposte come **interfaccia programmatica**. La dashboard, quando arriverà, userà le stesse funzioni e non ne aggiungerà di proprie [D].

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-21.01 | Tramite l'interfaccia programmatica l'utente: registra e gestisce i conti; crea, modifica, duplica, avvia, mette in pausa, ferma e archivia i flussi; alloca e libera capitale; incassa; consulta fonti, fornitori e modelli disponibili; consulta stato, storico e dati registrati. | M | F1 | D |
| RF-21.02 | Ogni funzione agisce solo sui dati dell'utente autenticato (RF-01.02). | M | F1 | D |
| RF-21.03 | Ogni modifica alla configurazione di un flusso è **versionata**: si sa sempre quale versione era in vigore in ogni ciclo e si può confrontare con le precedenti. | M | F1 | D |
| RF-21.04 | Una modifica alla configurazione ha effetto dal ciclo successivo, mai su un ciclo in corso. | M | F1 | [PROPOSTA] |
| RF-21.05 | Una configurazione non valida (fonte o modello inesistente, conflitto di asset sul conto, allocazione oltre il saldo, limiti incoerenti) viene rifiutata con l'indicazione dell'errore, senza toccare la versione in vigore. | M | F1 | [PROPOSTA] |
| RF-21.06 | La configurazione completa di un flusso può essere esportata e importata (per duplicarla, salvarla o condividerla con sé stessi su un altro conto). | S | F2 | [PROPOSTA] |
| RF-21.07 | Tramite l'interfaccia programmatica l'utente lancia la chiusura di emergenza (RF-18.09) e la procedura di verifica dell'esecuzione (RF-19.05). | S | F3 | [PROPOSTA] |

### 6.22 Capitale e incasso

Fermare un flusso non basta a incassare: le posizioni aperte restano a mercato e il capitale resta allocato. L'incasso è quindi un'azione distinta e sempre manuale [D].

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-22.01 | **Pausa**: il flusso non prende nuove decisioni; le posizioni aperte restano a mercato con le loro protezioni (stop loss, take profit). Alla ripresa il flusso riparte dal proprio stato. | M | F1 | D |
| RF-22.02 | **Stop**: il flusso cessa di operare. Per le posizioni aperte l'utente sceglie, nella configurazione del flusso o al momento dello stop, se chiuderle subito o lasciarle gestire dalle sole protezioni sull'exchange. | M | F1 | D |
| RF-22.03 | **Riduzione del capitale allocato**: l'utente può ridurre il capitale allocato a un flusso fino alla liquidità non impegnata in posizioni; la parte ridotta diventa capitale libero del conto. Può anche aumentarlo, entro il capitale libero disponibile. | M | F3 | D |
| RF-22.04 | **Incasso dei profitti di un flusso**: con un unico comando l'utente chiude tutte le posizioni del flusso, riporta il capitale allocato al valore iniziale (o a un valore indicato) e libera la differenza. Se il flusso è in perdita il comando non libera nulla e lo segnala. | S | F3 | D |
| RF-22.05 | Il capitale libero di un conto è visibile all'utente, distinto dal capitale allocato, e corrisponde all'unica parte prelevabile dall'exchange senza toccare i flussi. | M | F3 | D |
| RF-22.06 | **Prelievo dall'exchange**: l'uscita di fondi dal conto verso un portafoglio esterno è un'azione manuale dell'utente, con conferma esplicita, mai avviata dalla piattaforma in autonomia. Può essere eseguita direttamente sull'exchange; se la piattaforma la offre, non supera mai il capitale libero. | S | F3 | D |
| RF-22.07 | Ogni variazione di capitale allocato, incasso e prelievo è registrata con data, ora, importo e motivo, e compare nello storico del flusso e del conto. | M | F3 | D |
| RF-22.08 | Le metriche di rendimento del flusso restano corrette dopo incassi e variazioni di capitale (il rendimento non cambia perché si è prelevato). | M | F3 | [PROPOSTA] |

### 6.23 Dashboard

La dashboard è **privata**: ogni utente, previa autenticazione, vede e gestisce esclusivamente il proprio tenant [D]. Usa le funzioni dell'interfaccia programmatica (sezione 6.21).

**Monitoraggio**

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-23.01 | Equity curve di ogni flusso, con linea e area in **verde** sopra il capitale iniziale e in **rosso** sotto. | M | F2 | V4 |
| RF-23.02 | Capitale iniziale, capitale attuale e rendimento complessivo in percentuale, per flusso; saldo, capitale allocato e capitale libero, per conto. | M | F2 | V5, D |
| RF-23.03 | Posizioni aperte: asset, direzione, leva, dimensione, prezzo di ingresso, PnL corrente, exit plan. | M | F2 | V4 |
| RF-23.04 | Storico delle posizioni chiuse con prezzo di apertura e di chiusura, PnL in valore e in percentuale. | M | F2 | V5 |
| RF-23.05 | Statistiche: operazioni vinte e perse, win rate, PnL medio di vincenti e perdenti, commissioni totali, numero di operazioni, costo del modello IA. | M | F2 | V1, V5 |
| RF-23.06 | Elenco dei cicli recenti; per ciascuno si consultano decisioni, ragionamento completo, contesto inviato e risposta integrale dell'agente, con gli indicatori e le previsioni che le hanno motivate. | M | F2 | V4 |
| RF-23.07 | Stato di ogni flusso: attivo, in pausa o fermo, ultima esecuzione, prossima esecuzione prevista, esito degli ultimi cicli, conto, ambiente, modello. | S | F2 | V4 |
| RF-23.08 | Vista comparativa dei flussi (classifica, vedi RF-03.06) con le equity curve sovrapposte. | S | F2 | V1, D |
| RF-23.09 | Stato della riconciliazione di ogni conto ed eventuali allarmi. | S | F3 | D |
| RF-23.10 | I dati sono aggiornati a ogni ciclo e la dashboard può essere aggiornata su richiesta. | M | F2 | V5 |

**Configurazione e comandi**

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-23.11 | Dalla dashboard l'utente esegue tutte le operazioni di configurazione e comando dell'interfaccia programmatica (RF-21.01): conti, flussi, fonti e pesi, modello, rischio, istruzioni, capitale, incasso. | M | F2 | D |
| RF-23.12 | La dashboard mostra le versioni della configurazione di un flusso e permette di confrontarle. | S | F2 | D |
| RF-23.13 | Dalla dashboard l'utente lancia la chiusura di emergenza (RF-18.09) e la procedura di verifica dell'esecuzione (RF-19.05). | S | F3 | [PROPOSTA] |

### 6.24 Notifiche

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-24.01 | L'utente riceve notifiche su **Telegram** e via **email**, sui canali che ha configurato nel proprio tenant. | S | F1 (Telegram) / F3 (email) | D |
| RF-24.02 | Notifiche essenziali, disponibili già nella fase senza dashboard: apertura e chiusura di posizioni, cicli falliti, errori dell'exchange o del fornitore IA. | S | F1 | D, [PROPOSTA] |
| RF-24.03 | Altri eventi notificabili: attivazione di stop loss o take profit, liquidazioni, decisioni ridotte o bloccate dal rischio, raggiungimento della perdita massima, allarme di riconciliazione, incasso eseguito, fine di un replay. | S | F3 | [PROPOSTA], D |
| RF-24.04 | Per ogni flusso e per ogni tipo di evento l'utente sceglie il canale (Telegram, email, entrambi, nessuno). | S | F3 | [PROPOSTA] |
| RF-24.05 | Riepilogo periodico (es. giornaliero) dei risultati di tutti i flussi dell'utente via email. | C | F5 | [PROPOSTA] |

### 6.25 Replay storico

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-25.01 | L'utente può eseguire un flusso, o una sua variante, su un periodo passato, simulando i cicli senza attendere il tempo reale. | S | F4 | D |
| RF-25.02 | Il replay usa i dati registrati dai cicli reali (RF-05.06) e, dove mancano, dati storici delle fonti che li rendono disponibili. Le fonti senza storico vengono segnalate come assenti nel contesto. | S | F4 | D |
| RF-25.03 | Nel replay l'agente vede solo i dati disponibili fino all'istante simulato, mai dati successivi. | M (per il replay) | F4 | [PROPOSTA] |
| RF-25.04 | Le esecuzioni simulate applicano commissioni, importo minimo e un'ipotesi di scostamento di prezzo (slippage) configurabile; stop loss e take profit scattano sulla base dei prezzi storici. | S | F4 | [PROPOSTA] |
| RF-25.05 | Prima di avviare un replay il sistema stima il numero di chiamate al modello IA e il relativo costo, e chiede conferma. | S | F4 | [PROPOSTA] |
| RF-25.06 | I risultati di un replay sono presentati con le stesse metriche e viste dei flussi live e sono confrontabili tra loro e con i flussi live, ma sempre distinti da questi. | S | F4 | D |

### 6.26 Analisi delle prestazioni

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-26.01 | **Valutazione del forecast**: per ogni asset e orizzonte si confronta la previsione con il prezzo effettivo allo scadere dell'orizzonte e si calcola l'errore medio assoluto. | S | F3 | V4, V5 |
| RF-26.02 | Grafico previsione e prezzo reale nel tempo, correttamente allineati sullo stesso istante, con medie mobili e volumi. | S | F4 | V5 |
| RF-26.03 | Individuazione degli scostamenti anomali tra previsione e realtà, con data e ora esatte, per correlarli a eventi esterni (notizie, whale). | S | F4 | V5 |
| RF-26.04 | Analisi dei picchi di volatilità dell'equity: ricostruzione delle decisioni e dei movimenti di prezzo tra due cicli. | S | F4 | V5 |
| RF-26.05 | **Valutazione dei segnali**: dai dati registrati si valuta a posteriori quali fonti avevano capacità predittiva, per orientare pesi e fonti attive. | C | F4 | V3 |
| RF-26.06 | Metriche di comportamento per flusso: proporzione long/short, frequenza delle operazioni, durata media delle posizioni, esposizione, incidenza delle commissioni. | S | F4 | V1 |

### 6.27 Evoluzione multi-livello

| ID | Requisito | Pri. | Fase | Fonte |
|----|-----------|------|------|-------|
| RF-27.01 | Un flusso può essere guidato da due agenti: uno **strategico** a bassa frequenza, che analizza il mercato su finestre lunghe (es. settimanali) e produce una "narrativa" o un indirizzo di fondo, e uno **esecutivo** a frequenza più alta che opera tenendone conto. | C | F5 | V4, V5 |

---

## 7. Requisiti non funzionali (comportamentali)

| ID | Requisito | Fonte |
|----|-----------|-------|
| RNF-01 | **Continuità**: i flussi attivi operano 24/7; i cicli partono puntuali rispetto all'intervallo. | V1, V4 |
| RNF-02 | **Robustezza**: l'errore di una fonte, dell'agente, del fornitore IA o dell'exchange non blocca il sistema né lascia posizioni prive di protezione. | [PROPOSTA] |
| RNF-03 | **Isolamento tra tenant**: nessuna funzione, vista o notifica espone dati di un utente a un altro. | D |
| RNF-04 | **Sicurezza delle credenziali**: chiavi dei conti e chiavi dei servizi non sono mai visibili nella dashboard, nelle risposte dell'interfaccia programmatica, nei log o nel contesto inviato all'agente. | V4 |
| RNF-05 | **Minimo privilegio sui fondi**: le credenziali di trading non hanno facoltà di prelievo [ASSUNZIONE, da verificare sull'exchange]. | [PROPOSTA] |
| RNF-06 | **Accesso riservato**: interfaccia programmatica e dashboard sono accessibili solo a utenti autenticati, ciascuno sul proprio tenant. | D |
| RNF-07 | **Tracciabilità completa**: ogni decisione è ricostruibile a posteriori con il suo contesto e la sua configurazione. | V4, D |
| RNF-08 | **Configurabilità**: tutti i parametri dei flussi sono modificabili tramite l'interfaccia programmatica e la dashboard, senza interventi sul funzionamento interno. | V3, D |
| RNF-09 | **Controllo dei costi**: i costi ricorrenti (modello IA, fonti dati, commissioni) sono misurati e visibili per flusso. | V3, V4 |
| RNF-10 | **Prestazioni**: raccolta dati e decisione si concludono entro una frazione dell'intervallo di ciclo. | V3 |
| RNF-11 | **Estendibilità**: una nuova fonte dati, un nuovo fornitore di modelli o un nuovo exchange si aggiungono senza modificare quelli esistenti e diventano utilizzabili con la sola configurazione. | D |
| RNF-12 | **Coerenza contabile**: la contabilità virtuale dei flussi e il saldo reale dei conti sono riconciliati con regolarità e ogni scostamento è segnalato. | D |

---

## 8. Fasi di rilascio

Ordine deciso con l'obiettivo di **testare i flussi il prima possibile**: prima agente, fonti ed exchange con configurazione programmatica, poi la dashboard e il resto [D]. Tutte le fasi fino a F5 operano solo su **testnet** [D].

| Fase | Contenuto |
|------|-----------|
| **F0. Esecuzione verificata** | Conti di trading su testnet (6.2); lettura di saldo e posizioni; apertura e chiusura di posizioni; procedura di verifica (RF-19.05). |
| **F1. Flussi autonomi configurabili (senza dashboard)** | Tenant con un solo utente e autenticazione (6.1); flussi (6.3) e ciclo pianificato (6.4); fonti indicatori, pivot, forecast, sentiment e notizie con selezione per flusso e pesi (6.5-6.10, 6.14); contabilità virtuale per flusso e regola di conflitto sul conto (6.13, RF-02.05); fornitori e modelli IA tramite interfaccia comune (6.16); istruzioni e decisione per asset (6.15, 6.17); modulo di rischio di base (RF-18.01, 02, 04, 05, 10); esecuzione e registrazione completa (6.19, 6.20); configurazione versionata e comandi tramite interfaccia programmatica (6.21); pausa e stop (RF-22.01, 22.02); notifiche essenziali su Telegram (RF-24.02); riconciliazione di base (RF-13.06). |
| **F2. Dashboard e confronto** | Dashboard privata con monitoraggio e configurazione (6.23); duplicazione dei flussi e classifica (RF-03.05, 03.06); interrogazione dello storico (RF-20.04); esportazione e importazione delle configurazioni. |
| **F3. Rischio, capitale e qualità** | Exit plan, confidenza, stop loss e take profit sull'exchange, esposizione complessiva, perdita massima, chiusura di emergenza (6.18); allarmi di riconciliazione (RF-13.07, 13.08); riduzione del capitale, incasso dei profitti, capitale libero, prelievo (6.22); notifiche complete e scelta dei canali, email (6.24); valutazione del forecast (RF-26.01). |
| **F4. Replay e analisi** | Replay storico (6.25); analisi delle prestazioni e valutazione dei segnali (6.26). |
| **F5. Evoluzioni** | Fonti whale e volumi globali; agente multi-livello; chiusure parziali; registrazione autonoma degli utenti; riuso dei dati di mercato tra flussi; riepiloghi periodici. |
| **F6. Reale (opzionale)** | Dopo alcuni mesi di sperimentazione e per scelta esplicita: uno o più conti sull'ambiente reale con capitale limitato. |
| **Backlog** | BL-01 spot, BL-02 copy-trading, BL-03 netting tra flussi. |

---

## 9. Criteri di accettazione principali

- **CA-01 (F0)**: su un conto di test la procedura di verifica apre una posizione long con leva 2 su BTC, ne legge lo stato e la chiude; saldo e posizioni letti dopo ogni passo coincidono con quanto mostrato dall'exchange.
- **CA-02 (F1)**: un flusso esegue almeno 7 giorni consecutivi di cicli pianificati in test, con meno dell'1% di cicli falliti [ASSUNZIONE sulla soglia] e nessuna sovrapposizione.
- **CA-03 (F1)**: per un qualsiasi ciclo scelto a caso si ricostruiscono contesto completo, configurazione in vigore, risposta dell'agente, esito del rischio e dell'esecuzione.
- **CA-04 (F1)**: una risposta malformata non produce mai ordini; una leva o un'esposizione oltre i limiti produce sempre un ordine ridotto ai limiti, registrato come tale.
- **CA-05 (F1)**: tramite la sola interfaccia programmatica, senza dashboard, si crea un flusso, si modificano fonti attive, pesi e modello, lo si avvia e si consultano i cicli registrati; la modifica crea una nuova versione e ha effetto dal ciclo successivo.
- **CA-06 (F1)**: disattivando una fonte in un flusso, dal ciclo successivo quella fonte non viene interrogata per quel flusso e non compare nel contesto; gli altri flussi non ne risentono.
- **CA-07 (F1)**: cambiando fornitore e modello IA di un flusso tramite configurazione, il ciclo successivo usa il nuovo modello senza altre modifiche; il modello usato è registrato in ogni ciclo.
- **CA-08 (F1)**: con due flussi sullo stesso conto e asset disgiunti, la contabilità virtuale di ciascuno coincide con le proprie operazioni e la somma delle due più il capitale libero coincide con il saldo del conto; un tentativo di assegnare lo stesso asset a entrambi viene rifiutato.
- **CA-09 (F2)**: ogni funzione della dashboard produce lo stesso risultato della corrispondente funzione programmatica; un utente non vede mai conti, flussi o dati di un altro utente.
- **CA-10 (F3)**: ogni posizione aperta ha stop loss e take profit attivi sull'exchange entro il ciclo in cui viene aperta.
- **CA-11 (F3)**: superata la perdita massima configurata, il flusso non apre nuove posizioni e arriva una notifica su Telegram ed email.
- **CA-12 (F3)**: il comando di incasso su un flusso in profitto chiude le posizioni, riporta il capitale allocato al valore iniziale e aumenta il capitale libero della differenza; il rendimento storico del flusso resta invariato.
- **CA-13 (F3)**: una posizione aperta a mano sull'exchange, fuori dalla piattaforma, produce un allarme di riconciliazione e sospende le nuove aperture dei flussi di quel conto.
- **CA-14 (F4)**: un replay di un periodo passato non usa mai dati successivi all'istante simulato e produce le stesse metriche dei flussi live.

---

## 10. Assunzioni da confermare

| # | Assunzione | Requisito |
|---|------------|-----------|
| A1 | Se solo alcune delle decisioni per asset sono malformate, si scartano quelle e si eseguono le altre (invece di scartare l'intero ciclo). | RF-17.10 |
| A2 | Soglia di cicli falliti accettabile in F1: meno dell'1%. | CA-02 |
| A3 | Le credenziali di trading possono essere limitate senza facoltà di prelievo sull'exchange scelto. | RNF-05 |
| A4 | Il primo flusso userà gli asset BTC, ETH, SOL con intervallo di 15 minuti, come nei video. | RF-03.01, RF-04.02 |
| A5 | Nella prima versione l'unico utente è il proprietario; l'abilitazione di altri utenti avviene a mano dal proprietario, senza registrazione autonoma. | RF-01.04 |
| A6 | Allo stop di un flusso, in assenza di scelta esplicita, le posizioni aperte vengono chiuse. | RF-22.02 |
| A7 | Le notifiche Telegram essenziali sono utili già in F1, in assenza di dashboard. | RF-24.02 |

---

## 11. Decisioni prese (intervista e revisione del 7-8 novembre 2026)

| Tema | Decisione |
|------|-----------|
| Utenti | Progetto personale, ma strutturato per crescere: ogni utente è un tenant con i propri conti, flussi, dati e notifiche. Nessuna condivisione tra utenti. |
| Capitale | Alcuni mesi solo con fondi virtuali su testnet per testare e iterare; eventualmente poi capitale reale. I limiti di perdita sono parametri configurabili, non valori decisi ora. |
| Dashboard | Privata: ogni utente vede solo il proprio tenant. Arriva dopo i flussi. |
| Ordine di realizzazione | Prima agente, fonti ed exchange, con configurazione tramite interfaccia programmatica; poi dashboard e resto. |
| Agenti | Multi-agente: più flussi in parallelo, ciascuno con la propria configurazione. |
| Configurazione dei flussi | Tutto per flusso: conto, intervallo, asset, fornitore e modello IA, fonti attive e pesi, rischio, istruzioni, capitale. Versionata. |
| Fonti dati | Ogni fonte è ortogonale, selezionabile singolarmente per flusso, con un peso per flusso. Se una fonte non è praticabile, il suo requisito si chiude. Come procurarsi i dati è una scelta tecnica. |
| Modelli IA | Come le fonti: integrati tramite interfaccia comune, scelti per flusso con la sola configurazione. |
| Decisioni per ciclo | Una decisione per ciascun asset del flusso. |
| Controllo umano | Solo autonomo; restano pausa, stop, limiti di rischio, chiusura di emergenza e incasso. |
| Incasso | Stop non basta: serve distinguere pausa, stop, riduzione del capitale allocato, incasso dei profitti e prelievo dall'exchange. Il prelievo è sempre manuale e confermato. |
| Conti e isolamento dei flussi | Concetto di conto (exchange + credenziali + ambiente) per utente; più flussi per conto o un conto per flusso, a scelta. Contabilità virtuale per flusso sempre; regola di conflitto: niente asset in comune tra flussi dello stesso conto; riconciliazione col saldo reale con allarme. Netting a backlog. |
| Notifiche | Telegram ed email. |
| Exchange | Hyperliquid. Integrato tramite interfaccia comune, sostituibile. |
| Filtro di rischio | Un'operazione oltre i limiti viene ridotta ai limiti ed eseguita. |
| Replay storico | Sì: si possono rigiocare i flussi su dati storici. |
| Spot e copy-trading | Fuori dalla prima versione; nel backlog come proposte a bassa priorità. |
