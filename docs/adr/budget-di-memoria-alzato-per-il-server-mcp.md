# ADR budget-di-memoria-alzato-per-il-server-mcp — Budget di memoria dei servizi alzato a 2816 MiB per il server MCP

- Stato: proposta (24 novembre 2026)
- Requisiti: US 527 R6.6.1 (Task 529)
- Collegate: sostituisce, per la sola somma dei limiti, ADR 0165 (limiti di memoria dei servizi); ADR
  server-mcp-in-un-container-proprio-con-accesso-entra; ADR 0144 (tipo d'istanza `d2-4`, 4 GiB)
- Verifica: prova

## Contesto e problema

ADR 0165 vuole un `mem_limit` per ogni servizio e la somma dei limiti dei servizi a lunga vita entro 2560 MiB. Oggi la
somma è 2432 MiB. Il nuovo servizio `mcp` carica lo stesso bootstrap di `api`: circa 190 MiB a riposo, misurati
importando il bootstrap e il server. Con il metodo di ADR 0165 (circa due volte e mezzo il riposo) il limite è
`384m`, e la somma diventa 2816 MiB.

## Fattori decisionali

- Decisione del proprietario (24 novembre 2026, in chat): alzare il budget a 2816 MiB, senza togliere memoria agli
  altri servizi e senza cambiare macchina (nessun costo).
- I limiti sono tetti, non memoria riservata: a riposo i servizi usano circa 820 MiB in tutto (misura di ADR 0165 più
  il server MCP).

## Decisione

- Servizio `mcp` in `deploy/compose.yaml` con `mem_limit: 384m`.
- La somma dei limiti dei servizi a lunga vita resta entro **2816 MiB** (era 2560); la prova di ADR 0165 controlla il
  nuovo valore. Il resto di ADR 0165 (un limite per servizio, metodo di calcolo, limiti degli altri servizi) resta.

## Alternative scartate

- **Togliere memoria a worker e forecaster** (da 768 a 640 MiB): rischio di riavvii nei cicli pesanti e negli
  addestramenti.
- **Limite stretto a `mcp` (256 MiB)**: rischio di riavvio su una richiesta pesante dello storico o della classifica.
- **Macchina più grande**: costo nuovo.

## Conseguenze

- Su 4 GiB restano circa 1,2 GiB per sistema, Docker, Tailscale e il pull delle immagini, invece di circa 1,5 GiB.
- Il consumo misurato a ogni rilascio (ADR 0162) dice se il limite di `mcp` va rivisto.
