# Agent Guidance for `html/`

This directory is the web root for the public HTML UI and API discovery assets for `mod_mynativeplant`.

If you are trying to use the webservice API, read [`openapi.json`](openapi.json) first. It documents the available JSON handlers, required query parameters, and the response envelope used by the module.

The module exposes these handlers under `/webservice`:

- `/webservice/list-families`
- `/webservice/list-genera?family=...`
- `/webservice/list-plants?family=...[&genera=...|&genus=...]`
- `/webservice/search?string=...`

Practical notes:

- `list-genera` requires `family`.
- `list-plants` requires `family` and accepts `genera` or the singular alias `genus`.
- If both `genera` and `genus` are present, they must match.
- `search` requires `string`.
- Successful responses include `result`, `creator`, `compile_time`, `run_time`, and endpoint-specific fields.
- A non-success response still uses JSON and includes an `error` field.

The HTML pages in this directory are UI consumers of the same handlers. When in doubt, use the API contract in `openapi.json` and the module notes in [`../module/README.md`](../module/README.md).
