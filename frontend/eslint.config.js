import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // Los `cva(...)` de los componentes de interfaz son constantes, no componentes, y
      // Fast Refresh sabe convivir con ellas. Sin esta opcion habria que sacarlas a un
      // fichero aparte por nada (issue #47).
      'react-refresh/only-export-components': ['error', { allowConstantExport: true }],
      // El guión bajo delante ya es la convención de este código para decir «esto se declara
      // y no se usa **a propósito**»: el `_omitida` de `payloadDeProveedor`, que existe para
      // quitar una clave del objeto, o el `_failure_kind` de una firma que tiene que aceptar
      // el argumento aunque no lo mire. Sin este patrón, la forma de callar al linter sería
      // reescribir un idioma correcto, que es peor que configurar la regla (issue #47).
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
    },
  },
])
