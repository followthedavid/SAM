// @ts-check
import js from '@eslint/js';
import globals from 'globals';

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  {
    files: ['src/main.js', 'src/preload.js'],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: 'script',
      globals: globals.node
    },
    rules: {
      ...js.configs.recommended.rules,
    }
  },
  {
    files: ['src/renderer.js'],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: 'script',
      globals: {
        ...globals.browser,
        window: 'readonly',
        document: 'readonly',
        localStorage: 'readonly'
      }
    },
    rules: {
      ...js.configs.recommended.rules,
      'no-unused-vars': ['warn', { varsIgnorePattern: '^_', argsIgnorePattern: '^_' }]
    }
  }
];
