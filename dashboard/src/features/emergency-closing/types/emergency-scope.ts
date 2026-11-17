/** What an emergency closing covers: one flow, the flows of one account, or every flow of the user (R3.2.3). */
export type EmergencyScope =
  | { readonly kind: 'flow'; readonly flowId: string; readonly flowName: string }
  | { readonly kind: 'account'; readonly accountId: string; readonly accountName: string }
  | { readonly kind: 'all' };
