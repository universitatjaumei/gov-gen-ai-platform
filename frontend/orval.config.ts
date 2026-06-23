import { defineConfig } from 'orval';

export default defineConfig({
  govgenai: {
    input: {
      target: './openapi.json',
    },
    output: {
      mode: 'tags-split',
      target: './src/shared/api/generated',
      schemas: './src/shared/api/generated/model',
      client: 'react-query',
      override: {
        fetch: {
          includeHttpResponseReturnType: false,
        },
        mutator: {
          path: './src/shared/api/client.ts',
          name: 'customInstance',
        },
        header: (info) =>
          `// ARCHIVO AUTOGENERADO — NO EDITAR MANUALMENTE\n// Fuente: openapi.json\n// Regenerar: npm run generate:api\n`,
      },
    },
  },
});
