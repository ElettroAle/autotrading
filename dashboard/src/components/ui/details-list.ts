/**
 * A list of labels and values in two columns: the labels as wide as they need, the values in what is left and never
 * wider, so a long value cannot push the page past the screen (ADR liste-etichetta-valore-che-vanno-a-capo).
 */
export const DETAILS_GRID = 'grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-1';

/**
 * A value of a list of labels and values: it shrinks with its box and breaks a word with no space, as the name of a
 * model or an address, only where the word would not fit (ADR liste-etichetta-valore-che-vanno-a-capo).
 */
export const DETAIL_VALUE = 'min-w-0 wrap-anywhere';
