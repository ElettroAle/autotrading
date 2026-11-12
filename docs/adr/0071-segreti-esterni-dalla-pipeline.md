# ADR 0071 — Segreti esterni dalla pipeline: il token del bot Telegram

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.8.1, R1.8.2
- Collegate: ADR 0015 (segreti generati sulla macchina), di cui fa eccezione per i segreti creati fuori dalla
  macchina; ADR 0035 (bot Telegram nel worker), di cui supera solo la scrittura a mano del token; ADR 0013
  (Tailscale SSH)

## Contesto

L'ADR 0015 genera i segreti dei servizi sulla macchina stessa, così nessuna persona e nessun log di GitHub li vede.
Il token del bot Telegram non si può generare sulla macchina: lo crea il proprietario con BotFather. L'ADR 0035
chiedeva quindi di scriverlo a mano nel file `secrets/telegram_bot_token` entrando in SSH, un passo manuale fuori
dalla pipeline, ripetuto per ogni installazione e a ogni rotazione del token. Il proprietario ha deciso che il token
arrivi dalla pipeline, come già prevede `docs/architecture.md` §8.2 per i segreti dei servizi.

## Decisione

- **Fonte.** Il token è il segreto `TELEGRAM_BOT_TOKEN` dell'environment GitHub dell'installazione (`dev`, `prod`),
  creato dal proprietario con `gh secret set`, che lo legge senza mostrarlo. Non passa dalla chat, da una riga di
  comando o da un file del repository.
- **Trasporto.** Il job di rilascio lo passa al composite `ssh-deploy`, che lo manda sullo standard input di una
  sessione Tailscale SSH, come il token del registro. Mai su una riga di comando, mai in un file del runner, mai
  stampato.
- **Scrittura.** `deploy/install-telegram-token.sh`, eseguito sulla macchina, lo legge dallo standard input dentro
  un container senza rete e lo scrive accanto al file in uso, con proprietario l'utente dell'immagine (65532) e
  permessi 0400, poi lo rinomina sopra quello in uso: il worker non legge mai mezzo token. Il file arriva al worker
  come secret del compose, montato in sola lettura, mai come variabile d'ambiente.
- **Solo se cambia.** Un token uguale a quello in uso non tocca il file. Un token nuovo lascia un marcatore: dopo
  `docker compose up` il rilascio ricrea solo il worker, che legge il token quando parte. Il marcatore sopravvive a
  un rilascio fallito, così il successivo ricrea comunque il worker.
- **Segreto assente.** Senza il segreto il passo non parte: resta il file vuoto creato da
  `prepare-installation.sh` (ADR 0035) e il worker gira senza notifiche.
- **Regola generale.** Un segreto creato fuori dalla macchina arriva dall'environment GitHub attraverso la pipeline,
  come file in sola lettura. I segreti che la macchina sa generare restano generati sulla macchina (ADR 0015).

## Alternative scartate

- **Scrittura a mano via SSH (ADR 0035).** Passo manuale fuori dalla pipeline, da ripetere per ogni installazione e
  a ogni rotazione, contro il vincolo che il deploy passi sempre dalla pipeline.
- **Variabile d'ambiente del container.** Vietata: visibile con `docker inspect` e da `/proc`.
- **Riavvio del worker a ogni rilascio.** Interromperebbe i cicli in corso anche quando il token non cambia.

## Conseguenze

- Il token passa dal runner GitHub per la durata del job: GitHub lo maschera nei log, e il composite non lo stampa.
- Togliere il segreto da GitHub non cancella il token dalla macchina: per spegnere il bot si revoca il token con
  BotFather, che lo rende inutile ovunque.
- Ruotare il token è un `gh secret set` seguito da un rilascio.
