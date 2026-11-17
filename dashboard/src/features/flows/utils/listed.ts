/** The parts of a list as a sentence says them: «conto, capitale allocato e asset». */
export const listed = (parts: readonly string[]): string => {
  const last = parts.at(-1) ?? '';
  return parts.length <= 1 ? last : `${parts.slice(0, -1).join(', ')} e ${last}`;
};
