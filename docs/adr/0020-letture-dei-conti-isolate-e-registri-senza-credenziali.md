# ADR 0020 — Letture dei conti isolate tra tenant e registri senza credenziali

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.1.3, R0.2.3

## Contesto

R0.1.3 chiede che un utente non veda né modifichi i conti di un altro tenant, e che un conto di un altro
tenant risulti inesistente senza rivelare che esiste. R0.2.3 chiede che dettaglio, registri, dati salvati
ed errori dell'exchange non contengano mai le credenziali. ADR 0018 ha messo la row level security sulla
tabella `accounts` e oscurato il messaggio dell'exchange nella sola rotta di registrazione.

## Decisione

- **Elenco e dettaglio**: `ListAccountsUseCase` e `GetAccountUseCase` leggono dal repository legato al
  tenant della richiesta. Un id che il repository non vede, inesistente o di un altro tenant, produce lo
  stesso `AccountNotFoundError` "non trovato", senza attributi: le due risposte sono identiche (404).
  La row level security resta la difesa nel database; il caso d'uso non filtra per tenant da sé.
- **Dettaglio senza credenziali**: `AccountDetails` riporta id, nome, exchange e `has_credentials`. Non
  porta il testo cifrato né l'impronta del conto dell'exchange. Rotte `GET /accounts` (ordinato per nome)
  e `GET /accounts/{id}`.
- **Errori dell'exchange oscurati nel caso d'uso**: `read_balance_proving` sostituisce indirizzo e chiave,
  in qualunque maiuscola, con `***` nel messaggio dell'exchange e rilancia senza causa concatenata, perché
  l'eccezione originale conserva ancora il testo in chiaro. Vale per registrazione e sostituzione, e per
  ogni ingresso futuro oltre l'API.
- **Registri**: le operazioni sui conti si registrano sul logger `autotrading.accounts` con il solo id del
  conto (`conto registrato`, `credenziali sostituite`). Le credenziali non entrano mai in un record.

## Alternative scartate

- **403 per un conto di un altro tenant**: dice che il conto esiste, contro R0.1.3.
- **Filtro per tenant nel caso d'uso oltre alla row level security**: duplica la regola in due posti e
  non protegge da una query scritta male; la row level security la applica a ogni query.
- **Oscuramento nel solo adapter Hyperliquid**: ogni adapter futuro dovrebbe ricordarsene; il caso d'uso
  conosce le credenziali della richiesta e le toglie una volta per tutti.

## Conseguenze

- Un id non valido nella rotta (non un UUID) risponde 422 dalla validazione, prima di qualunque lettura:
  non rivela nulla su alcun conto.
