# Documentation

The documentation tree has three distinct scopes:

- Files directly under `docs/` describe the existing production system or
  cross-cutting repository concerns. Examples include deployment, payments,
  mutability, gas profiling, and the current user-wallet implementation.
- [`wallets-v3/`](wallets-v3/README.md) contains the new Wallet v3 architecture
  track. Its governing design does not itself authorize implementation or
  deployment.
- [`poc/user-wallet/`](poc/user-wallet/README.md) contains the paused,
  historical user-wallet proof of concept and its evidence.

Keeping the current-system documents at the root is intentional: they are
neither archived PoC evidence nor new Wallet v3 design work.

## Link validation

Run the repository link checker after moving or renaming documentation:

```sh
python tools/check_doc_links.py
```

By default, the checker scans Git-tracked Markdown and HTML files, so its result
is reproducible from a clean checkout. It validates relative file targets,
verifies GitHub-style Markdown heading anchors and HTML element IDs, and checks
`#L123` source-line anchors.

To include non-ignored, untracked documentation while drafting:

```sh
python tools/check_doc_links.py --include-untracked
```
