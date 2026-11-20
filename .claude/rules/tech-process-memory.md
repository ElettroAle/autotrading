---
paths:
  - "src/autotrading/adapters/outbound/process_memory/**"
  - "tests/unit/adapters/process_memory/**"
---

# Adapter in uscita: memoria del processo

- Il sistema integrato è la memoria del processo: archivi in RAM, persi al riavvio. Nessuna libreria esterna.
- Una cache è un decorator della porta che decora: la dichiara tra le basi e la riceve nel costruttore, e un errore
  della porta decorata passa invariato e non si salva (ADR cache-delle-letture-del-conto-come-decorator-in-memoria).
- `ProcessMemoryAccountActivityAdapter` decora `AccountActivityPort` nel solo processo `api`, legato al tenant della
  richiesta: una lettura del conto resta valida 10 secondi (`_ProcessMemorySettings`) dall'istante in cui è arrivata;
  chiave tenant e conto, così tenant e conti diversi non condividono letture. Il `worker` non la monta: i cicli
  leggono sempre l'exchange (Bug 635).
- L'archivio è privato della cartella, uno per processo, creato da `process_memory_adapters()` in `composition.py`, che
  restituisce la funzione che decora una porta per un tenant; un lock lo protegge dalle richieste concorrenti e le voci
  scadute si tolgono alla scrittura.
- Le scadenze si misurano con un orologio monotono passato come funzione: nei test un orologio finto, mai un'attesa.
