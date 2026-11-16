import { pageOf, searchWithPage } from './page-number';

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

describe('searchWithPage', () => {
  it('keeps the other parameters and adds the page', () => {
    expect(searchWithPage(new URLSearchParams('outcome=fallito&page=1'), 2)).toBe(
      '?outcome=fallito&page=2',
    );
  });

  it('leaves the first page out of the address', () => {
    expect(searchWithPage(new URLSearchParams('outcome=fallito&page=2'), 1)).toBe(
      '?outcome=fallito',
    );
    expect(searchWithPage(new URLSearchParams('page=2'), 1)).toBe('');
  });
});
