# Valutazione di DeepFund e di altri framework di trading multi-agente

**Data:** 8 novembre 2026
**Scopo:** capire se DeepFund (HKUST) vale come base o come fonte di idee per AutoTrading, e censire le alternative autorevoli. Le fonti sono state lette il giorno indicato; stelle e date cambiano.
**Nota:** la conversazione condivisa da Google AI Mode (`share.google/aimode/...`) non è raggiungibile da qui: il link reindirizza a una pagina di consenso Google. La valutazione si basa su repository, paper e documentazione.

---

## 1. Sintesi

| Domanda | Risposta breve |
|---------|----------------|
| DeepFund è aggiornato? | Poco. Ultimo commit 18 marzo 2026, nessuna release, 0 issue aperte, 303 stelle. Attività concentrata tra marzo e novembre 2025. |
| È autorevole? | Sì sul piano accademico: HKUST Guangzhou, paper a NeurIPS 2025 (Datasets & Benchmarks, poster) e IJCAI 2025 FinLLM Workshop (oral award). Poco sul piano del codice: adozione bassa, documentazione scarna. |
| Fa quello che ci serve? | No. È un **benchmark di ricerca** per azioni, con cadenza giornaliera, dati Alpha Vantage e Yahoo Finance, senza esecuzione reale ("it DOES NOT TRADE"), senza cripto, senza modulo di rischio, senza leva. |
| Cosa aggiunge al nostro sistema? | Tre idee, non codice: (1) analisti specializzati con **schema di segnale unificato** (Bullish/Bearish/Neutral + motivazione); (2) **planner** che sceglie quali analisti attivare a ogni ciclo; (3) il principio "time travel is cheating": valutare i modelli solo su dati successivi al loro cutoff di addestramento. |
| Alternativa più autorevole? | **TradingAgents** (TauricResearch): 121k stelle, attivo a novembre 2026, Apache-2.0, cripto supportate via Yahoo (BTC-USD, ETH-USD), struttura analisti → dibattito rialzista/ribassista → trader → rischio → gestore. Anche questo solo simulazione. |
| Qualcuno fa trading reale su Hyperliquid? | **nofx** (NoFxAiOS): sì, con Hyperliquid, Binance, OKX, Bitget e altri; 13k stelle, attivo. Ma AGPL-3.0, gateway IA a pagamento in USDC, link referral, gestione di chiavi private: da trattare con cautela. |

**Raccomandazione:** non adottare DeepFund né altri framework come base. Il nostro requisito "capacità ortogonali e configurazione per flusso" è più semplice e più adatto a perpetui con leva su Hyperliquid. Recuperare invece, come feature avanzata, il modello "analisti specialisti + dibattito + gestore" di DeepFund e TradingAgents, descritto nella sezione 5 e inserito nei requisiti come sezione 6.28.

---

## 2. DeepFund nel dettaglio

**Repository:** https://github.com/HKUSTDial/DeepFund (MIT)
**Paper:** arXiv 2505.11065, "Time Travel is Cheating: Going Live with DeepFund for Real-Time Fund Investment Benchmarking", NeurIPS 2025 D&B; arXiv 2503.18313, paper di visione, IJCAI 2025 FinLLM Workshop.
**Autori:** Changlun Li, Yao Shi, Nan Tang, Yuyu Luo e altri, HKUST Guangzhou. Da marzo 2026 collaborazione con la startup Paradoox AI, che ospita l'arena pubblica (https://deepfund.paradoox.ai/).

### 2.1 Cosa fa

- Valuta la capacità di trading di diversi LLM in un ambiente unificato, con un'**arena** pubblica che confronta i modelli su dati di mercato successivi al loro cutoff di addestramento (per evitare che "ricordino" il futuro).
- Architettura multi-agente: sei **analisti** (notizie aziendali, fondamentali, insider, macroeconomia, politica, tecnico), ciascuno con lo stesso output: `Signal ∈ {Bullish, Bearish, Neutral}` più una motivazione. Un **planner** opzionale sceglie quali analisti eseguire; altrimenti girano tutti in parallelo. Un **manager** prende la decisione finale di portafoglio.
- Workflow su LangGraph; modelli via LangChain (OpenAI, DeepSeek, Anthropic, Grok, Fireworks, Ollama); dati da Alpha Vantage e Yahoo Finance; persistenza su Supabase o SQLite (tabelle Config, Portfolio, Decision, Signal).
- Esecuzione giornaliera per data di trading, da rigiocare in ordine cronologico.

### 2.2 Stato e manutenzione

| Indicatore | Valore (8 nov 2026) |
|------------|---------------------|
| Stelle / fork | 303 / 48 |
| Ultimo commit | 18 marzo 2026 (aggiornamento README e versioni dipendenze) |
| Commit precedenti | 11 novembre 2025, 28-30 ottobre 2025, 19 settembre 2025 |
| Release | nessuna |
| Issue aperte | 0 |
| Maturità dichiarata | TRL 4 su 9, "research purposes only, it DOES NOT TRADE" |

### 2.3 Limiti rispetto ad AutoTrading

- Solo azioni; nessun supporto a cripto, perpetui, leva, short.
- Nessuna esecuzione su exchange, nessun modulo di rischio, nessuna gestione del capitale.
- Cadenza giornaliera; noi lavoriamo a minuti.
- Due analisti su sei (fondamentali, macro) non supportano dati storici: il replay non è completo.
- Documentazione del flusso planner/manager e dello schema delle decisioni quasi assente.

### 2.4 Risultato scientifico utile

Il paper NeurIPS valuta nove LLM di punta in ambiente live e conclude che **anche DeepSeek-V3 e Claude 3.7 Sonnet chiudono in perdita netta**; gli LLM attuali non sono ancora efficaci nella gestione attiva di un fondo. Lo stesso emerge dalla survey "Agentic Quantitative Trading" (arXiv 2608.31041, agosto 2026, HKUST-GZ): "la capacità previsionale non si traduce in modo affidabile in prestazioni di trading live". Conferma il nostro principio "scopo sperimentale, risultati valutati su periodi lunghi".

---

## 3. Altri framework valutati

| Framework | Cos'è | Attività | Cripto | Trading reale | Licenza | Giudizio |
|-----------|-------|----------|--------|---------------|---------|----------|
| **TradingAgents** (TauricResearch) | Framework multi-agente su LangGraph: 4 analisti, dibattito ricercatori rialzista/ribassista, trader, team rischio, gestore di portafoglio. Backtest con memoria delle decisioni. Paper arXiv 2412.20138. | 121k stelle; ultimo commit 4 nov 2026; release v0.7.1 ott 2026 | Sì, tramite ticker Yahoo (BTC-USD) e `asset_type="crypto"` nel backtest | No, "simulated exchange" | Apache-2.0 | Riferimento più autorevole per la struttura a dibattito. Dati e cadenza pensati per azioni. |
| **ai-hedge-fund** (virattt) | Proof of concept educativo: agenti analisti, gestore di portafoglio, paper trading con registro, backtest. | 64.6k stelle; commit 8 nov 2026 (v2.7.1) | Non citato | No | MIT | Popolare, ma dati da Financial Datasets API (a pagamento) e nessuna cripto. |
| **ai-hedge-fund-crypto** (51bitquant) | Derivato per cripto su Binance: nodi strategia (MACD, RSI, Bollinger), rischio, gestore LLM. | 627 stelle; ultimo commit 5 set 2025 | Sì, Binance | Dichiarato ma "non ancora implementato" | MIT | Fermo da oltre un anno, link referral. Non usare. |
| **nofx** (NoFxAiOS) | Terminale di trading IA self-hosted, Go + web: modalità "Frontier" (piani approvati dall'utente) e "Autopilot" (loop automatico). Stop loss e take profit lato exchange, riconciliazione ordini. | 13.2k stelle; commit 4 nov 2026 | Sì: Binance perpetui, Hyperliquid, OKX, Bitget, Bybit, Gate, KuCoin, Aster, Lighter | **Sì** | AGPL-3.0 | Il più vicino al nostro prodotto. Rischi: AGPL, gateway IA a pagamento (USDC su Base), link referral, chiavi private del wallet gestite dal sistema. Utile come riferimento per adapter exchange e riconciliazione, non come base. |
| **Vibe-Trading** (HKUDS) | Agente di ricerca e backtest: report, 478 alpha, paper trading, team "swarm", broker live sperimentali. | 37.9k stelle; commit 8 nov 2026 | Dati da OKX, Binance, CCXT | Sperimentale, "non verificato" | MIT | Strumento di ricerca, non piattaforma di esecuzione. |
| **open-alpha-arena** (etrobot) | Replica comunitaria di Alpha Arena: paper trading con leva, dati Hyperliquid via ccxt, API compatibile OpenAI. TypeScript. | 601 stelle | Sì (dati) | No, "real trading" in TODO | MIT | Riferimento per prompt e formato decisione, come già nei video. |
| **TraceArena** (tonyhyworld) | Runtime di valutazione multi-agente con ledger simulato. | 3 stelle; ultimo commit umano lug 2026 | No | No | Apache-2.0 | Ignorare. |

**Alpha Arena (Nof1):** il benchmark reale citato nei video. Nessun repository ufficiale collegato dal sito; stato della stagione 2026 non verificato.

### Fonti accademiche di contesto

- **Survey "Agentic Quantitative Trading: A Survey of Workflows, Systems, and Evaluation"** (arXiv 2608.31041, 31 agosto 2026, HKUST-GZ, PKU, IDEA). Tassonomia: cinque stadi (factor mining, signal discovery, portafoglio, esecuzione, rischio); architetture sequenziali, iterative, gerarchiche, a orchestrazione; coordinamento diretto, per aggregazione, dibattito, selezione, gating; adattamento per memoria, riflessione, feedback, regime, reward. Avverte su leakage temporale e overfitting della memoria.
- **Look-Ahead-Bench** (arXiv 2601.13770, gennaio 2026): misura il bias di look-ahead negli LLM in finanza; i modelli open standard lo mostrano in modo significativo. Rafforza RF-25.03 (nessun dato futuro nel replay) e suggerisce di registrare il cutoff del modello usato.
- **awesome-ai-in-finance** (georgezouq): elenco curato; voci cripto rilevanti: okx/agent-trade-kit (MCP ufficiale OKX), DeepAlpha (bot cripto via CCXT su 12 exchange).

---

## 4. Cosa prendere e cosa no

**Prendere (come idee, nei requisiti):**

1. **Schema di segnale unificato** per gli analisti: direzione (rialzista, ribassista, neutrale), forza o confidenza, motivazione. Rende gli analisti intercambiabili come le fonti.
2. **Analisti specializzati** come agenti LLM distinti, ciascuno legato a un sottoinsieme di fonti (tecnico, notizie, sentiment, forecast, whale), invece di un unico prompt che riceve tutto.
3. **Dibattito** rialzista/ribassista (TradingAgents) prima della decisione, con numero di round configurabile.
4. **Planner** (DeepFund) che decide a ogni ciclo quali analisti attivare, per risparmiare chiamate.
5. **Gestore** che sintetizza i segnali in una decisione per asset nel nostro formato (RF-17).
6. **Valutazione anti-leakage**: registrare per ogni modello la data di cutoff e, nel confronto tra modelli e nei replay, segnalare i periodi precedenti al cutoff.
7. **Memoria delle decisioni** con esito (TradingAgents): l'agente riceve le sue decisioni passate sullo stesso asset e il risultato ottenuto.

**Non prendere:**

- Il codice di DeepFund (azioni, giornaliero, non manutenuto).
- Dipendenza da LangGraph o da un framework specifico: scelta di architettura, da valutare a parte.
- nofx come base: licenza AGPL e modello commerciale incompatibili con un progetto che vuole restare libero di evolvere.

---

## 5. Proposta di feature avanzata: flusso multi-analista

Inserita nei requisiti come sezione 6.28 (priorità C, fase F5). In sintesi:

- Un flusso può essere configurato in modalità **"agente unico"** (quella attuale: un prompt, una decisione per asset) o **"comitato"**.
- In modalità comitato il flusso ha un elenco configurabile di **analisti**, ciascuno con: fonti assegnate, modello IA, istruzioni, peso. Ogni analista produce per ogni asset un segnale nello schema unificato.
- Opzionale: **dibattito** tra un analista rialzista e uno ribassista sui segnali raccolti, con round configurabili.
- Opzionale: **planner** che, dato il contesto, sceglie quali analisti eseguire.
- Un **gestore** riceve i segnali (e l'esito del dibattito) e produce la decisione per asset nel formato standard; da lì in poi il ciclo prosegue come oggi (rischio, esecuzione, registrazione).
- Tutti i segnali intermedi, i round di dibattito e i costi per analista vengono registrati e sono visibili.
- Il modulo di rischio, la contabilità virtuale e tutto il resto non cambiano.

Costo: ogni ciclo moltiplica le chiamate al modello per il numero di analisti (più dibattito). Va stimato e mostrato come già previsto per il replay (RF-25.05).

---

## 6. Fonti consultate

- https://github.com/HKUSTDial/DeepFund e TECHNICAL_GUIDE.md, pyproject.toml, cronologia commit
- https://arxiv.org/abs/2505.11065 e https://arxiv.org/abs/2503.18313
- https://github.com/TauricResearch/TradingAgents e documentazione API (Context7 `/tauricresearch/tradingagents`)
- https://github.com/virattt/ai-hedge-fund
- https://github.com/51bitquant/ai-hedge-fund-crypto
- https://github.com/NoFxAiOS/nofx
- https://github.com/HKUDS/Vibe-Trading
- https://github.com/tonyhyworld/TraceArena
- https://github.com/etrobot/open-alpha-arena
- https://nof1.ai/
- https://arxiv.org/abs/2608.31041 (survey), https://arxiv.org/abs/2601.13770 (Look-Ahead-Bench)
- https://github.com/georgezouq/awesome-ai-in-finance
- https://pinggy.io/blog/best_ai_trading_agents/, https://www.flowhunt.io/blog/llm-trading-bots-comparison/ (panoramiche divulgative, usate solo per orientarsi)
