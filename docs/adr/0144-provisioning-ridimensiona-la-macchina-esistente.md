# ADR 0144 — A ogni rilascio la macchina esistente si allinea al tipo d'istanza dichiarato

- Stato: proposta (14 novembre 2026)
- Requisiti: Bug: la macchina dev si blocca al rilascio (RNF di disponibilità dell'installazione dev)
- Collegate: ADR 0008 (installazioni OVH dalla pipeline), ADR 0013 (accesso solo Tailscale), ADR 0107 (forecaster);
  decisione del proprietario all'avvio di E1: passaggio a d2-4 pre-approvato se la misura mostra che d2-2 non basta

## Contesto e problema

Dal rilascio delle 06:05 del 14 novembre 2026 la macchina `autotrading-dev` (d2-2, 2 GB di RAM) smette di rispondere
durante il `docker compose pull` dei sette servizi (api, worker, migrate, postgres, litellm, forecaster, dashboard):
«Timeout, server not responding», poi ogni rilascio fallisce con l'SSH in timeout e l'app risponde 502. La misura che
la decisione di E1 chiedeva c'è: d2-2 non basta. Il provisioning oggi non tocca una macchina esistente, e una macchina
bloccata non si recupera dalla pipeline.

## Decisione

- La variabile `OVH_FLAVOR` dell'ambiente dev diventa `d2-4` (decisione pre-approvata, circa 11,44 €/mese).
- L'action `ovh-provision`, quando la macchina esiste già con un tipo d'istanza diverso da quello dichiarato, la
  ridimensiona (`openstack server resize --flavor`, attesa di `VERIFY_RESIZE`, conferma con `resize confirm`) e attende
  `ACTIVE`; il disco e i dati restano. Il ridimensionamento riavvia la macchina, quindi sblocca anche una macchina
  piantata. Con il tipo già giusto non fa nulla.
- Lo stesso allineamento gira a ogni rilascio, prima del deploy, oltre che nel workflow `provision`: cambiare
  `OVH_FLAVOR` ha effetto al rilascio successivo, senza esecuzioni a mano. Con il tipo già giusto costa solo una lettura.

## Alternative scartate

- **Riavvio a mano dalla console OVH**: sblocca subito, ma fuori dalla pipeline e la macchina si ripianterebbe al
  rilascio successivo.
- **Ricreare la macchina**: tipo giusto da zero, ma si perdono database e segreti generati sulla macchina (ADR 0015).
- **Togliere servizi da dev**: costo invariato, ma dev smette di essere uguale a prod.

## Conseguenze

- Costo dev da circa 5,71 a circa 11,44 €/mese, come pre-approvato.
- Cambiare tipo d'istanza in futuro è solo un cambio di variabile; il rilascio dopo lo applica.
