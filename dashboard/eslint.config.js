import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import importPlugin from 'eslint-plugin-import';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import reactHooks from 'eslint-plugin-react-hooks';
import testingLibrary from 'eslint-plugin-testing-library';
import globals from 'globals';
import tseslint from 'typescript-eslint';

import architecture, { SOURCE_FILES } from './eslint.architecture.js';

export default tseslint.config(
  ...architecture,
  {
    files: SOURCE_FILES,
    extends: [js.configs.recommended, ...tseslint.configs.strict],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    plugins: { import: importPlugin },
    rules: {
      'import/order': [
        'error',
        {
          groups: ['builtin', 'external', 'internal', 'parent', 'sibling', 'index', 'object'],
          pathGroups: [{ pattern: '@/**', group: 'internal' }],
          'newlines-between': 'always',
          alphabetize: { order: 'asc', caseInsensitive: true },
        },
      ],
      'import/no-duplicates': 'error',
    },
  },
  {
    files: ['src/**/*.tsx'],
    extends: [reactHooks.configs.flat.recommended, jsxA11y.flatConfigs.recommended],
  },
  {
    files: ['src/**/*.test.{ts,tsx}'],
    extends: [testingLibrary.configs['flat/react']],
    languageOptions: { globals: globals.vitest },
  },
  {
    // Playwright reads the fixtures a step needs from the destructured first argument: a step needing none
    // destructures nothing, and an automatic fixture provides nothing.
    files: ['e2e/**/*.ts'],
    rules: { 'no-empty-pattern': 'off', '@typescript-eslint/no-invalid-void-type': 'off' },
  },
  prettier,
);
