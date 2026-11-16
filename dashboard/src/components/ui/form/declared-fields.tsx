import type { UseFormRegisterReturn } from 'react-hook-form';

import { InputField, NOT_FOR_PASSWORD_MANAGERS, SecretField } from './input-field';

/** A datum an exchange or a provider asks, as its adapter declares it to the API (R2.3.9, ADR 0158, ADR 0159). */
export type DeclaredField = {
  readonly name: string;
  readonly label: string;
  readonly secret: boolean;
};

type DeclaredFieldsProps = {
  readonly fields: readonly DeclaredField[];
  readonly registerField: (name: string) => UseFormRegisterReturn;
  readonly reasonOf: (name: string) => string | undefined;
};

/**
 * The inputs of the fields the API declares, in its order: the form knows no exchange and no provider, and a secret
 * is never shown while typed (R2.3.9).
 */
export const DeclaredFields = ({ fields, registerField, reasonOf }: DeclaredFieldsProps) =>
  fields.map((field) => {
    const reason = reasonOf(field.name);
    const error = reason === undefined ? undefined : { message: reason };
    return field.secret ? (
      <SecretField
        key={field.name}
        label={field.label}
        error={error}
        {...registerField(field.name)}
      />
    ) : (
      <InputField
        key={field.name}
        label={field.label}
        error={error}
        autoComplete="off"
        {...NOT_FOR_PASSWORD_MANAGERS}
        {...registerField(field.name)}
      />
    );
  });

/** The field the API names in a refusal, when it is one of those declared. */
export const declaredFieldOf = (
  fields: readonly DeclaredField[],
  name: string,
): DeclaredField | undefined => fields.find((field) => field.name === name);
