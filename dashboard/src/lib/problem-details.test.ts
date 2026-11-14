import { problemDetailsOf } from './problem-details';

describe('problemDetailsOf', () => {
  it('reads nothing from an answer that is not Problem Details', () => {
    expect(problemDetailsOf({ message: 'down' })).toBeUndefined();
    expect(problemDetailsOf(null)).toBeUndefined();
  });

  it('reads the reason alone when an invalid request lists no value', () => {
    expect(problemDetailsOf({ detail: 'richiesta non valida', errors: [] })).toEqual({
      detail: 'richiesta non valida',
      problems: [{ field: undefined, reason: 'richiesta non valida' }],
    });
  });

  it('reads the field of a value nested in the body as the field of the body that holds it', () => {
    expect(
      problemDetailsOf({
        detail: 'richiesta non valida',
        errors: [{ loc: ['body', 'sources', 0, 'weight'], msg: 'Input should be a valid integer' }],
      }),
    ).toEqual({
      detail: 'richiesta non valida',
      problems: [{ field: 'sources', reason: 'Input should be a valid integer' }],
    });
  });
});
