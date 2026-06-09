# Server calldata fixtures

Fixtures in this directory are produced by the paired `hightop-api` branch:

```bash
node -r esbuild-register scripts/exportV7Calldata.ts --input <vectors.json>
```

Each JSON file contains raw calldata generated from the server's vendored V7
ABIs. Boa tests should load these fixtures and execute `data` against `to`
using the protocol test deployment.
