import { shortenText } from './shorten-text';

// The reasoning of a decision, shortened on a word boundary (ADR riquadro-dell-ultima-decisione-nella-panoramica).

describe('shortenText', () => {
  it('keeps a text within the limit as it is', () => {
    expect(shortenText('apro long', 160)).toBe('apro long');
    expect(shortenText('a'.repeat(160), 160)).toBe('a'.repeat(160));
  });

  it('cuts a longer text at the last word that fits and adds an ellipsis', () => {
    expect(shortenText('apro una posizione long', 12)).toBe('apro una…');
  });

  it('cuts at the limit when the word that crosses it ends exactly there', () => {
    expect(shortenText('apro una posizione', 8)).toBe('apro una…');
  });

  it('drops the spaces before the ellipsis', () => {
    expect(shortenText('apro  una posizione', 6)).toBe('apro…');
  });

  it('cuts a single word longer than the limit at the limit', () => {
    expect(shortenText('supercalifragilistico', 5)).toBe('super…');
  });

  it('shortens to 160 characters unless told otherwise', () => {
    const shortened = shortenText(`${'parola '.repeat(30)}fine`);

    expect(shortened.endsWith('parola…')).toBe(true);
    expect(shortened.length).toBeLessThanOrEqual(161);
  });
});
