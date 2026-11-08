# AutoTrading: spunti tecnologici dalle fonti

**Stato:** raccolta di note, non decisioni.
**Data:** 7 novembre 2026

Questo documento raccoglie le tecnologie, i servizi e le scelte implementative citati nei video sorgente (V1-V5, vedi [`requirements.md`](requirements.md) §1). Nessuna voce è una decisione di architettura: servono come punto di partenza per la fase di progettazione. Dove una voce comporta rischi (costi, termini di servizio, sicurezza) è segnalato.

---

## 1. Exchange ed esecuzione

| Voce | Cosa dicono le fonti | Fonte |
|------|----------------------|-------|
| **Hyperliquid** | Exchange decentralizzato (DEX) usato sia da Alpha Arena sia dall'autore. Offre spot e perpetui con leva fino a 40x, più di 100 asset, API pubbliche e un ambiente **testnet** con fondi virtuali. | V1, V2, V4 |
| SDK Python di Hyperliquid | Una delle due vie di integrazione ufficiali. | V2 |
| **CCXT** | Libreria multi-exchange molto diffusa, usata dall'autore per leggere saldo e prezzi e piazzare ordini su Hyperliquid. | V2 |
| Ordine minimo | Hyperliquid rifiuta gli ordini sotto 10 $ di valore ("order must have minimum value $10"); servono arrotondamenti corretti. | V2 |
| Wallet | Accesso tramite wallet (MetaMask nei video). Il deposito avviene in USDC; per le transazioni e per generare le API key serve anche ETH per il gas. Le credenziali usate sono indirizzo pubblico e chiave privata del wallet (o di un API wallet generato). | V2, V4 |
| Binance | Citato solo per lo strumento di copy-trading (NO1 Tracker) che usa API key e secret Binance. | V1 |

> **Isolamento dei flussi (RF-01.03).** Con più flussi sugli stessi asset, un unico conto non basta: una sola posizione per coin per conto renderebbe i flussi interdipendenti. Opzioni da valutare in progettazione: sub-account Hyperliquid (o vault) distinti per flusso, wallet separati, oppure un registro interno che attribuisce posizioni virtuali ai flussi. Da verificare se la testnet supporta i sub-account.

> **Nota di sicurezza.** Nei video la chiave privata del wallet è passata come variabile d'ambiente al servizio. In progettazione va preferito un API wallet dedicato al trading, senza facoltà di prelievo, con i segreti in un gestore di segreti.

## 2. Modelli linguistici (agente IA)

| Voce | Cosa dicono le fonti | Fonte |
|------|----------------------|-------|
| Modelli di Alpha Arena | DeepSeek Chat V3.1, Qwen 3 Max, Claude Sonnet 4.5, Grok 4, Gemini 2.5 Pro, GPT-5. Nella prima stagione i modelli cinesi (DeepSeek, Qwen) risultavano in testa. | V1 |
| Modelli provati dall'autore | DeepSeek, Gemini 2.5 Pro (Ultra), Claude Opus 4, GPT-5 con ragionamento massimo, Qwen. Allo stesso prompt danno decisioni diverse. | V3 |
| Modello in produzione | GPT-5.1 per la prima settimana, nonostante il costo; poi passaggio previsto a un modello più economico (DeepSeek, Kimi K2 Thinking o Qwen) per un mese di test. | V4 |
| Costi | Divario di prezzo molto ampio tra modelli: GPT-5.1 molto più caro di Kimi K2 Thinking e DeepSeek. Il costo per chiamata, moltiplicato per 96 cicli al giorno a 15 minuti, va stimato prima della scelta. | V4 |
| Output strutturato | Il modello deve restituire un JSON con chiavi fisse. In V3/V4: `operation`, `symbol`, `direction`, `target_position` (frazione del saldo), `leverage`, `reason`. In Alpha Arena anche `confidence` ed exit plan (target, stop, invalidation). | V1, V3, V4 |
| Prompt | System prompt in un file di testo, con segnaposto riempiti con dati di portafoglio e di mercato, istruzioni e regole (una posizione per coin; azioni open/close/hold). | V3 |
| Open Alpha Arena | Repository pubblico che replica l'esperimento (servizio di decisione, prompt, simboli, notizie): utile come riferimento. | V1 |

## 3. Dati di mercato e indicatori

| Voce | Cosa dicono le fonti | Fonte |
|------|----------------------|-------|
| Indicatori | EMA20, MA20, MACD, RSI (7 e 14), open interest, funding rate, mid price, EMA/MA su timeframe lungo (4h, 20 e 50 periodi). Calcolati in Python a partire dai dati dell'exchange. | V1, V3 |
| Pivot point | Calcolo di PP, R1, R2, S1, S2 aggiunto allo script degli indicatori; output JSON per ticker. | V3 |
| Analisi avanzate | Fibonacci, linee di Gann e analisi ciclica citate come estensioni future. | V4 |

## 4. Forecasting

| Voce | Cosa dicono le fonti | Fonte |
|------|----------------------|-------|
| **Prophet** (Meta) | Modello di serie storiche, addestrato sullo storico prezzi di ogni ticker, con previsioni a 1 minuto, 15 minuti e 1 ora. Usa solo la serie dei prezzi, senza notizie. | V2, V3, V4 |
| Limiti osservati | Molto rumore; errori ampi durante movimenti bruschi (errore medio assoluto su BTC di circa 721 $ in una settimana). Da riaddestrare su uno storico più lungo. | V5 |
| Valutazione | Script di confronto previsione/reale con grafici; attenzione allo sfasamento di un passo tra serie prevista e serie reale. | V5 |

## 5. Fonti esterne

| Voce | Cosa dicono le fonti | Rischi / note | Fonte |
|------|----------------------|---------------|-------|
| **CoinMarketCap Fear & Greed** | Endpoint API con piano gratuito (serve una API key); restituisce valore e classificazione. | Nessuno rilevante. | V3 |
| **News feed RSS** | Feed XML di notizie cripto (lo stesso usato da Open Alpha Arena, percorso `/news/feed`). | Verificare i termini d'uso del feed. | V1, V3 |
| X/Twitter | Ipotesi futura: tweet di persone influenti, anche per singolo ticker. | API di X a pagamento. | V3 |
| **Whale Alert** | API ufficiale molto costosa (circa 699 $/mese). L'autore ha usato un endpoint interno del sito, individuato analizzando il traffico di rete, per ottenere gli alert senza pagare. In V4 la fonte è stata poi disattivata. | Endpoint non ufficiale: può cambiare o sparire senza preavviso. | V3, V4 |
| **CoinGlass** | Volumi e order book aggregati multi-exchange. I dati arrivano in streaming via websocket cifrato, quindi non sono estraibili facilmente; le API sono a pagamento (order book, heatmap, large orders). | Costo; scelta del dato utile ancora aperta. | V3 |

## 6. Persistenza e registrazione

| Voce | Cosa dicono le fonti | Fonte |
|------|----------------------|-------|
| **PostgreSQL** | Database relazionale con: contesto del ciclo (collegato a notizie, sentiment, indicatori, previsioni), operazioni del bot (`bot_operations`), saldo e posizioni aperte. Forecast salvati a 15 minuti e 1 ora per ticker (last price, prediction, variazione %). | V4 |
| Scrittura | I dati vengono scritti a ogni risveglio dell'agente, cioè ogni 15 minuti. | V5 |

## 7. Esecuzione pianificata e hosting

| Voce | Cosa dicono le fonti | Fonte |
|------|----------------------|-------|
| **Railway** | Servizio deployato su Railway con **cron job** ogni 15 minuti; variabili d'ambiente: wallet, private key, OpenAI API key, database URL, CoinMarketCap API key. Dashboard pubblicata sempre su Railway con un URL pubblico. | V4 |
| Parallelizzazione | Le chiamate alle fonti dati, inizialmente sequenziali e lente, andranno parallelizzate. | V3 |

## 8. Dashboard

| Voce | Cosa dicono le fonti | Fonte |
|------|----------------------|-------|
| Backend + frontend | Backend generato a partire dallo schema del database (endpoint per posizioni aperte, saldo, operazioni), frontend generato con strumenti di "vibe coding". | V4 |
| Ricostruzione posizioni chiuse | Nella versione di V5 le posizioni chiuse sono **stimate** confrontando snapshot successivi. È più affidabile leggerle dallo storico dell'exchange o registrarle all'esecuzione (vedi RF-15.03). | V5 |

## 9. Strumenti di sviluppo citati

Strumenti usati dall'autore, non vincolanti per il progetto: Visual Studio Code con l'agente Cline, Claude, autocompletamento con Gemma, Google Antigravity con Gemini 3 Pro (agent manager e modifiche guidate da screenshot), Postman per le prove sulle API.

## 10. Riferimenti esterni citati

- **Alpha Arena** (Nof1): benchmark live, blog con il design dell'esperimento, prompt e leaderboard. [V1]
- **Open Alpha Arena**: replica open source dell'esperimento. [V1]
- **NO1 Tracker**: strumento CLI (npm) per copiare su Binance le operazioni degli agenti di Alpha Arena. [V1]
