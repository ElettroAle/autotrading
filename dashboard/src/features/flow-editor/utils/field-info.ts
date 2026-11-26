import type { Source, SourceAdapter } from '../api/get-sources';

/**
 * The texts of the info buttons of the form of the flow, all in one place, each in the order the requirement fixes:
 * what the field does, the values it admits, its default or what leaving it empty means (R5.5.7, ADR
 * informazioni-sui-campi-di-configurazione). The parameters of models and adapters show the description the API
 * declares, never a text of the dashboard.
 */
export const FLOW_FIELD_INFO = {
  name: 'Nome con cui riconosci il flusso nella dashboard e nelle notifiche. Testo, diverso da quello degli altri flussi. Obbligatorio.',
  account:
    'Conto di trading su cui il flusso apre e chiude le posizioni. Uno dei tuoi conti. Obbligatorio; dopo la creazione non cambia.',
  assets:
    "Asset su cui il flusso opera: l'agente decide per ciascuno a ogni ciclo. Gli asset che l'exchange negozia, non già usati da un altro flusso dello stesso conto. Almeno uno.",
  cycleMinutes:
    "Minuti tra un ciclo decisionale e il successivo: a ogni ciclo l'agente legge le fonti e decide. Da 1 a 1440. Predefinito: 15.",
  model:
    'Modello IA che decide per il flusso. Uno dei modelli del catalogo di un fornitore di cui hai registrato la chiave. Obbligatorio.',
  instructions:
    "Istruzioni all'agente: strategia, stile, vincoli da rispettare. Testo libero. Vuoto: l'agente segue solo le regole operative del system prompt.",
  systemPrompt:
    'Testo di sistema che il modello riceve a ogni ciclo, con i segnaposti elencati sotto sostituiti dai valori del flusso. Testo libero. Predefinito: quello della piattaforma, finché non lo modifichi.',
  maxLeverage:
    "Leva più alta che il flusso usa in un'apertura: una decisione con leva maggiore si riduce a questa. Intero da 1 al massimo dell'exchange per l'asset. Obbligatoria.",
  maxMarginExposure:
    "Margine massimo di una singola apertura, in percentuale dei soldi del flusso: un'apertura più grande si riduce. Maggiore di 0 e fino a 100. Vuoto: nessun limite sul margine, ma serve almeno uno tra margine e valore.",
  maxValueExposure:
    "Valore massimo di una singola apertura (dimensione per prezzo), in percentuale dei soldi del flusso: un'apertura più grande si riduce. Maggiore di 0 e fino a 100. Vuoto: nessun limite sul valore, ma serve almeno uno tra margine e valore.",
  maxTotalMarginExposure:
    'Margine massimo di tutte le posizioni aperte del flusso insieme, in percentuale dei soldi del flusso. Da 0,1 a 1000. Vuoto: nessun limite complessivo sul margine.',
  maxTotalValueExposure:
    'Valore massimo di tutte le posizioni aperte del flusso insieme, in percentuale dei soldi del flusso. Da 0,1 a 1000. Vuoto: nessun limite complessivo sul valore.',
  maxConsecutiveFailures:
    'Cicli falliti di fila dopo i quali il flusso va in pausa. Intero da 1 a 100. Vuoto: nessun massimo, il flusso riprova a ogni ciclo.',
  maxDailyLoss:
    'Perdita del giorno, in percentuale dei soldi del flusso, oltre la quale le aperture si sospendono. Da 0,1 a 100. Vuoto: nessun limite.',
  maxDrawdown:
    'Perdita dal valore più alto raggiunto dai soldi del flusso, in percentuale, oltre la quale le aperture si sospendono. Da 0,1 a 100. Vuoto: nessun limite.',
  openingsResume:
    'Come riprendono le aperture sospese da una perdita massima: quando le riprendi tu, o da sole alla mezzanotte UTC successiva. Manuale o il giorno dopo. Predefinito: manuale.',
  maxConsecutiveLosses:
    'Chiusure in perdita di fila dopo le quali le riaperture si bloccano per la durata del blocco. Intero da 1 in su, insieme a finestra e durata. Vuote tutte e tre: nessun blocco.',
  lossWindow:
    'Ore entro cui le chiusure in perdita contano per il blocco: le più vecchie non contano. Intero da 1 in su. Vuota con le altre due: nessun blocco.',
  blockDuration:
    "Minuti di blocco delle riaperture, dall'ultima perdita contata. Intero da 1 in su. Vuota con le altre due: nessun blocco.",
  lossCountScope:
    'Dove si contano e si bloccano le perdite consecutive: su ogni asset da solo o su tutti gli asset del flusso. Per singolo asset o su tutto il flusso. Predefinito: per singolo asset.',
  defaultStopLoss:
    "Distanza dello stop loss dal prezzo d'ingresso, in percentuale, per ogni apertura in cui l'agente non indica uno stop. Da 0,1 a 50. Predefinito: 5.",
  defaultTakeProfit:
    "Distanza dell'obiettivo dal prezzo d'ingresso, in percentuale, per ogni apertura in cui l'agente non indica un obiettivo. Maggiore di 0. Vuoto: nessun take profit.",
  trailingDistance:
    'Distanza in percentuale a cui lo stop segue il miglior prezzo raggiunto dalla posizione. Da 0,1 a 50. Vuota: lo stop non segue il prezzo.',
  trailingActivation:
    "Guadagno in percentuale dal prezzo d'ingresso da cui lo stop comincia a seguire il prezzo. Maggiore di 0, solo con la distanza. Vuota: lo stop segue dall'apertura.",
  trailingBreakeven:
    "Guadagno in percentuale dal prezzo d'ingresso raggiunto il quale lo stop va al prezzo d'ingresso. Maggiore di 0. Vuoto: lo stop non va al pareggio.",
  maxProfitInContext:
    "Lo stato inviato all'agente riporta il massimo profitto raggiunto da ogni posizione aperta; ha effetto solo con la distanza o il pareggio. Accesa o spenta. Predefinita: spenta.",
  minimumConfidence:
    "Confidenza, da 0 a 100, sotto la quale un'apertura decisa dall'agente non viene eseguita. Vuoto: ogni apertura passa.",
  allocatedCapital:
    'Parte del saldo del conto assegnata al flusso: base delle quote e dei limiti in percentuale. Maggiore di 0, entro il capitale libero del conto. Obbligatorio.',
  bringToMinimum:
    "Un'apertura sotto l'importo minimo dell'exchange sale al minimo, se il minimo rispetta i limiti di esposizione e la liquidità del flusso; spenta, si blocca. Accesa o spenta. Predefinita: spenta.",
  memoryActive:
    "L'agente riceve a ogni ciclo le decisioni precedenti del flusso su ogni asset, con il loro esito. Accesa o spenta. Predefinita: spenta.",
  memoryDecisions:
    "Quante decisioni precedenti per asset riceve l'agente, le più recenti. Intero da 1 a 50, solo con la memoria attiva. Predefinito: 10.",
  memoryDays:
    "Giorni indietro da cui l'agente riceve le decisioni precedenti. Intero da 1 a 365, solo con la memoria attiva. Predefinito: 30.",
  memoryTextLength:
    'Caratteri del motivo di ogni decisione ricordata: un motivo più lungo si tronca. Intero da 1 in su, solo con la memoria attiva. Predefinito: 160.',
  memoryUnlimitedLength:
    "Il motivo di ogni decisione ricordata arriva intero all'agente, senza limite di caratteri. Accesa o spenta, solo con la memoria attiva. Predefinita: spenta.",
  memoryAllDecisions:
    'La memoria ricorda anche gli aggiornamenti e le decisioni di mantenere, oltre ad aperture, chiusure e inversioni. Accesa o spenta, solo con la memoria attiva. Predefinita: spenta.',
  memorySummary:
    'In testa alla memoria di ogni asset, una riga per direzione con le posizioni chiuse nei giorni della memoria. Accesa o spenta, solo con la memoria attiva. Predefinita: spenta.',
  memoryOtherAssets:
    'Nella memoria di ogni asset, le righe di riepilogo degli altri asset del flusso, senza le loro decisioni. Accesa o spenta, solo con la memoria attiva. Predefinita: spenta.',
  accountExposureForAgent:
    "Lo stato inviato all'agente riporta il valore long e short delle posizioni degli altri flussi dello stesso conto. Accesa o spenta. Predefinita: spenta.",
  feesForAgent:
    "Lo stato inviato all'agente riporta il costo di andata e ritorno di una posizione: la commissione del conto per un ordine a mercato, contata per l'apertura e per la chiusura. Accesa o spenta. Predefinita: spenta.",
} as const;

/** The info of a source of the catalog: what it gives the agent, as the API describes it. */
export const sourceInfoOf = (source: Source): string =>
  `Dà all'agente la fonte ${source.name}: ${source.description} Accesa con almeno un adapter, o spenta. Predefinita: spenta.`;

/** The info of an adapter of a source: what it reads, as it declares itself. */
export const adapterInfoOf = (source: Source, adapter: SourceAdapter): string =>
  `Legge la fonte ${source.name} da ${adapter.name}: ${adapter.description} Scelto o no, anche insieme ad altri adapter della fonte. Predefinito: non scelto.`;

/** The info of the weight of an adapter chosen for a source. */
export const weightInfoOf = (source: Source, adapter: SourceAdapter): string =>
  `Quanto l'agente deve contare sui dati di ${source.name} da ${adapter.name} rispetto alle altre fonti. Intero da 1 a 10. Predefinito: 5.`;
