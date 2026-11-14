import type { Difference } from '../api/get-version-differences';

import type { ConfigurationRow } from './configuration-rows';

export type ComparisonRow = {
  readonly part: string;
  readonly before: string;
  readonly after: string;
  readonly changed: boolean;
};

/**
 * The two versions side by side, part by part: a part is changed only when the API says so, and shows the values
 * the API reports; a change to a part the dashboard does not list still shows, at the end.
 */
export const comparisonRows = (
  before: ConfigurationRow[],
  after: ConfigurationRow[],
  differences: Difference[],
): ComparisonRow[] => {
  const afterByPart = new Map(after.map((row) => [row.part, row.value]));
  const differenceByPart = new Map(differences.map((difference) => [difference.part, difference]));
  const listed = before.map((row) => {
    const difference = differenceByPart.get(row.part);
    return difference === undefined
      ? {
          part: row.part,
          before: row.value,
          after: afterByPart.get(row.part) ?? '',
          changed: false,
        }
      : { ...difference, changed: true };
  });
  const listedParts = new Set(before.map((row) => row.part));
  const unlisted = differences
    .filter((difference) => !listedParts.has(difference.part))
    .map((difference) => ({ ...difference, changed: true }));
  return [...listed, ...unlisted];
};
