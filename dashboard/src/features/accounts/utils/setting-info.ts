import { declaredInfoOf } from '@/components/ui/form/declared-fields';

/**
 * The texts of the info buttons of the settings of an account, all in one place, each in the order the requirement
 * fixes: what the setting does, the values it admits, its default or what leaving it empty means (R5.5.7, ADR
 * informazioni-sui-campi-di-configurazione).
 */
export const ACCOUNT_SETTING_INFO = {
  name: 'Nome con cui riconosci il conto nella dashboard. Testo, diverso da quello degli altri tuoi conti. Obbligatorio.',
  exchange:
    'Exchange su cui sta il conto: decide quali credenziali servono e su quale rete opera il conto. Uno degli exchange supportati. Obbligatorio; dopo la registrazione non cambia.',
  virtualBalance:
    "Saldo da cui parte il conto dell'exchange simulato. Un importo maggiore di 0. Obbligatorio.",
  newVirtualBalance:
    'Saldo da cui riparte il conto: azzerarlo chiude le posizioni aperte e cancella gli ordini. Un importo maggiore di 0. Obbligatorio.',
  maxDirectionExposure:
    "Valore massimo delle posizioni long, e separatamente di quelle short, di tutti i flussi del conto, in percentuale del saldo letto dall'exchange: un'apertura che lo supera si blocca. Maggiore di 0. Vuoto: nessun limite.",
  deviationThreshold:
    "Scostamento del saldo letto dall'exchange da quello atteso, in percentuale, oltre il quale la riconciliazione del conto segnala un allarme. Da 0,1 a 100. Predefinito: 1.",
} as const;

/** The info of a datum the exchange of the account asks (R2.3.9). */
export const credentialInfoOf = declaredInfoOf(
  "che l'exchange chiede per collegare il conto",
  "l'exchange",
);
