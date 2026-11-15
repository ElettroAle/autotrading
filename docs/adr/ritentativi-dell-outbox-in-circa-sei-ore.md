# ADR ritentativi-dell-outbox-in-circa-sei-ore — Ritentativi dell'outbox in circa 6 ore

- Stato: accettata (15 novembre 2026), decisione del proprietario
- Requisiti: Bug 396; Task T6.1.1 (377)
- Collegate: sostituisce, per il solo numero di tentativi, l'ADR outbox-delle-integrazioni-esterne-con-procrastinate

## Contesto e problema

L'ADR outbox-delle-integrazioni-esterne-con-procrastinate fissa "backoff esponenziale con base 5 secondi, al massimo
8 tentativi (circa 6 ore)". I numeri sono incoerenti: con base 5 secondi le attese sono 5, 25, 125, 625, 3125, 15625 e
78125 secondi, e 8 tentativi durano circa 27 ore. Il codice ha seguito gli 8 tentativi.

## Fattori decisionali

- Decisione del proprietario (15/11/2026): ritentativi per circa 6 ore.

## Opzioni considerate

1. 7 tentativi, base 5 secondi: attese fino a 15625 secondi, 19530 secondi in tutto (circa 5 ore e mezza).
2. 8 tentativi, base 5 secondi: circa 27 ore. Scartata dal proprietario.

## Esito della decisione

Opzione 1: backoff esponenziale con base 5 secondi, al massimo 7 tentativi (il primo e 6 ritentativi), poi stato
`fallito`. Il resto dell'ADR outbox-delle-integrazioni-esterne-con-procrastinate resta valido.

Verifica: prova (unit test delle attese della strategia di ritentativo; test di integrazione: messaggio fallito dopo il
settimo tentativo).

### Conseguenze

- Un messaggio che non si consegna risulta fallito dopo circa 5 ore e mezza invece che dopo circa 27.
