const ELLIPSIS = '…';
const SHORTENED_LENGTH = 160;

/**
 * A long text cut on the last word that fits in the length, with an ellipsis; a single word longer than the length is
 * cut at the length. The whole text stays where it is shown in full (ADR riquadro-dell-ultima-decisione-nella-panoramica).
 */
export const shortenText = (text: string, length = SHORTENED_LENGTH): string => {
  if (text.length <= length) {
    return text;
  }
  // The character after the length tells whether the word that crosses it ends exactly there.
  const boundary = text.slice(0, length + 1).lastIndexOf(' ');
  const kept = boundary > 0 ? text.slice(0, boundary) : text.slice(0, length);
  return `${kept.trimEnd()}${ELLIPSIS}`;
};
