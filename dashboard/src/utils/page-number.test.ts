import { pageOf } from './page-number';

describe('pageOf', () => {
  it.each([
    ['2', 2],
    ['1', 1],
  ])('reads the page %s of the query string', (value, page) => {
    expect(pageOf(value)).toBe(page);
  });

  it.each([null, '', 'zero', '0', '-1', '1.5'])('reads %s as the first page', (value) => {
    expect(pageOf(value)).toBe(1);
  });
});
