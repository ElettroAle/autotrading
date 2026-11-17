import { listed } from './listed';

describe('listed', () => {
  it.each([
    [[], ''],
    [['asset'], 'asset'],
    [['conto', 'asset'], 'conto e asset'],
    [['conto', 'capitale allocato', 'asset'], 'conto, capitale allocato e asset'],
  ])('says %j as «%s»', (parts, sentence) => {
    expect(listed(parts)).toBe(sentence);
  });
});
