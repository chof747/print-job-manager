# Scheduling API client

Run `pnpm generate:scheduling-client` from the repository root after changing
the backend scheduling API. The command uses the backend's FastAPI OpenAPI
schema and the locked `openapi-typescript-codegen` version to regenerate
`scheduling/`. Commit the generated files alongside API changes. The script
selects only the scheduling operation and its referenced schemas; it strips
the `/api/v1` prefix because the runtime API base URL already includes it.

`job-import-api-client.ts` wraps the generated operation to retain the
feature's error messages. Do not edit generated files directly.
