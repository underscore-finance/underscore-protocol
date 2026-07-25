# Archived User Wallet Proof of Concept

**Status:** Paused historical experiment. This directory is evidence and
background, not the current Wallet v3 architecture or implementation
authorization.

The proof of concept tested a greenfield permanent-wallet/extender model. Its
contracts and tests now live under:

- [`contracts/poc/userWallet/`](../../../contracts/poc/userWallet/)
- [`tests/poc/userWallet/`](../../../tests/poc/userWallet/)

The main historical artifacts are:

- [`user-wallet.md`](user-wallet.md): experimental architecture
- [`implementation-guide.md`](implementation-guide.md): experiment contract and
  evidence plan
- [`POC_RESULTS.md`](POC_RESULTS.md): recorded results and dispositions
- [`BUILDLOG.md`](BUILDLOG.md): implementation history
- [`user-wallet-visual.html`](user-wallet-visual.html) and
  [`user-wallet-flows-claude.html`](user-wallet-flows-claude.html): visual
  explanations
- [`production-design-plan.md`](production-design-plan.md) and
  [`phase-0-d4a-d2.md`](phase-0-d4a-d2.md): the superseded PoC-derived
  production track

Current Wallet v3 work is separate:

- [`docs/wallets-v3/`](../../wallets-v3/README.md)
- [`contracts/walletsV3/`](../../../contracts/walletsV3/)
- [`tests/walletsV3/`](../../../tests/walletsV3/)

Historical filenames and internal `V3` contract names are intentionally
preserved so prior evidence remains traceable. Renaming those archived symbols
would be a separate owner-directed evidence rewrite, not part of the folder
separation.

## Revalidating the archived evidence

The normal local selection includes the archived security and lifecycle suite;
the gas test skips unless explicitly enabled, and Base-only tests are
deselected:

```sh
python -m pytest --fork=local tests/poc/userWallet -q
python -m pytest --fork=base tests/poc/userWallet/test_x402.py -q
```

The gas harness binds paired artifacts to the source commit, dirty flag,
complete worktree-state digest, and local artifact bytes. An artifact produced
before the directory move will therefore fail binding by design. With the
repository's normal fork credentials already available, regenerate the local
artifact first and then run the Base profile without changing the commit or
worktree between commands:

```sh
GAS_PROFILE=1 WALLET_V3_GAS_OUTPUT=/tmp/wallet-v3-poc-local.json python -m pytest --fork=local tests/poc/userWallet/gas/test_poc_gas.py -q -s
GAS_PROFILE=1 WALLET_V3_GAS_OUTPUT=/tmp/wallet-v3-poc-base.json python -m pytest --fork=base tests/poc/userWallet/gas/test_poc_gas.py -q -s
```

The preserved gas numbers in [`POC_RESULTS.md`](POC_RESULTS.md) remain the
historical pre-archive measurements and are not freshly bound to the final
archived source. That status remains until both profiles are regenerated from
the same archived repository state.
