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
  /** The text of the info button of a declared field, which its declaration does not carry (R5.5.7). */
  readonly infoOf: (field: DeclaredField) => string;
  readonly registerField: (name: string) => UseFormRegisterReturn;
  readonly reasonOf: (name: string) => string | undefined;
};

/**
 * The inputs of the fields the API declares, in its order: the form knows no exchange and no provider, and a secret
 * is never shown while typed (R2.3.9).
 */
export const DeclaredFields = ({ fields, infoOf, registerField, reasonOf }: DeclaredFieldsProps) =>
  fields.map((field) => {
    const reason = reasonOf(field.name);
    const error = reason === undefined ? undefined : { message: reason };
    return field.secret ? (
      <SecretField
        key={field.name}
        label={field.label}
        info={infoOf(field)}
        error={error}
        {...registerField(field.name)}
      />
    ) : (
      <InputField
        key={field.name}
        label={field.label}
        info={infoOf(field)}
        error={error}
        autoComplete="off"
        {...NOT_FOR_PASSWORD_MANAGERS}
        {...registerField(field.name)}
      />
    );
  });

/**
 * The info of the declared fields of one asker, from what they are for and who gives their values: a secret never
 * shows again once saved (R5.5.7). The declarations carry no description, so the form that asks them says it.
 */
export const declaredInfoOf =
  (purpose: string, giver: string) =>
  (field: DeclaredField): string =>
    field.secret
      ? `${field.label}: dato segreto ${purpose}, conservato cifrato e mai più mostrato. Il valore che ti dà ${giver}. Obbligatorio.`
      : `${field.label}: dato ${purpose}, conservato in chiaro. Il valore che ti dà ${giver}. Obbligatorio.`;

/** The field the API names in a refusal, when it is one of those declared. */
export const declaredFieldOf = (
  fields: readonly DeclaredField[],
  name: string,
): DeclaredField | undefined => fields.find((field) => field.name === name);
