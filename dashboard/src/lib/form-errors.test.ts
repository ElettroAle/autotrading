import { ApiError } from './api-client';
import { SessionExpiredError } from './auth';
import { FORM_ERROR, reasonOf, showRefusal } from './form-errors';

type Values = { name: string; capital: string };

const FIELDS: Record<string, keyof Values> = { name: 'name', allocated_capital: 'capital' };
const fieldOf = (field: string) => FIELDS[field];

describe('reasonOf', () => {
  it('reads the reason kept for a field, and nothing for a field without one', () => {
    expect(reasonOf({ message: 'fonte ripetuta: notizie' })).toBe('fonte ripetuta: notizie');
    expect(reasonOf({ message: { message: 'nested' } })).toBeUndefined();
    expect(reasonOf(undefined)).toBeUndefined();
  });
});

describe('showRefusal', () => {
  it('shows each reason beside the field of the form the API names', () => {
    const setError = vi.fn();

    showRefusal<Values>(
      new ApiError(422, 'richiesta non valida', [
        {
          field: 'allocated_capital',
          reason: 'capitale allocato oltre il capitale libero: 500 USDC',
        },
        { field: 'name', reason: 'nome del flusso obbligatorio' },
      ]),
      setError,
      fieldOf,
    );

    expect(setError.mock.calls).toEqual([
      [
        'capital',
        { type: 'server', message: 'capitale allocato oltre il capitale libero: 500 USDC' },
      ],
      ['name', { type: 'server', message: 'nome del flusso obbligatorio' }],
    ]);
  });

  it('shows at the head of the form the reasons of no field of the form, together', () => {
    const setError = vi.fn();

    showRefusal<Values>(
      new ApiError(422, 'richiesta non valida', [
        { field: undefined, reason: 'pagina non valida' },
        { field: 'unknown', reason: 'valore non ammesso' },
      ]),
      setError,
      fieldOf,
    );

    expect(setError.mock.calls).toEqual([
      [FORM_ERROR, { type: 'server', message: 'pagina non valida; valore non ammesso' }],
    ]);
  });

  it('shows at the head of the form a refusal without problems and a failure that is not a refusal', () => {
    const setError = vi.fn();

    showRefusal<Values>(new ApiError(502, 'Bad Gateway'), setError, fieldOf);
    showRefusal<Values>(new Error('Failed to fetch'), setError, fieldOf);
    showRefusal<Values>('interrotto', setError, fieldOf);

    expect(setError.mock.calls).toEqual([
      [FORM_ERROR, { type: 'server', message: 'Bad Gateway' }],
      [FORM_ERROR, { type: 'server', message: 'Failed to fetch' }],
      [FORM_ERROR, { type: 'server', message: 'interrotto' }],
    ]);
  });

  it('shows nothing for an expired session: the user is already back at the sign-in', () => {
    const setError = vi.fn();

    showRefusal<Values>(new SessionExpiredError(), setError, fieldOf);

    expect(setError).not.toHaveBeenCalled();
  });
});
