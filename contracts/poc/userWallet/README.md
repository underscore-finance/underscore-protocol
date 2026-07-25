# User Wallet Proof of Concept

This directory contains the paused user-wallet proof of concept. Its contracts
remain executable evidence for the experiments documented in
[`docs/poc/user-wallet/`](../../../docs/poc/user-wallet/README.md), but they are
not the current Wallet v3 implementation and are not production contracts.

Historical contract and interface names retain the `V3` suffix so the archived
evidence, test node identities, and recorded results remain recognizable. The
folder boundary—not a source-code rename—separates this experiment from new
Wallet v3 work. Renaming these symbols would be a separate owner-directed
evidence rewrite.

Future repository-wide production build or deployment globs should exclude
`contracts/poc/` unless the archived experiment is being validated explicitly.

New Wallet v3 contracts belong in [`contracts/walletsV3/`](../../walletsV3/).
