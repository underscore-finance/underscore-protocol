# Wallet v3

This directory contains the new Wallet v3 architecture work.

## Current authority

- [`simplified-user-wallet-action-architecture-codex.md`](simplified-user-wallet-action-architecture-codex.md)
  is the owner-selected governing architecture. Implementation still requires
  separate owner authorization.
- [`user-wallet-v3-implementation-plan-codex.md`](user-wallet-v3-implementation-plan-codex.md)
  translates the governing architecture into measured, independently reviewable
  work packages. It is a draft roadmap and does not authorize contract changes
  or deployment.
- [`ideal-wallet-action-architecture-codex.md`](ideal-wallet-action-architecture-codex.md)
  is a legacy filename pointer.
- [`incremental-extenders-proposal-claude.md`](incremental-extenders-proposal-claude.md)
  is preserved independent analysis, superseded as a standalone plan.
- [`user-wallet-incremental-extender-proposal-codex.md`](user-wallet-incremental-extender-proposal-codex.md)
  is the earlier Codex incremental proposal, also superseded as a standalone
  plan.
- [`permission-action-taxonomy-research-prompt-codex.md`](permission-action-taxonomy-research-prompt-codex.md)
  is a research instrument, not an architecture proposal.
- [`perms-research-summary-claude.md`](perms-research-summary-claude.md)
  synthesizes the four independent responses to that research prompt and
  reconciles them against the current contracts. It is analysis and
  recommendation only; it does not decide the taxonomy or authorize contract
  changes, and where it disagrees with the governing architecture it says so and
  leaves the call to the owner.
- [`perms-research-summary-codex.md`](perms-research-summary-codex.md)
  is a separate Codex synthesis of the same four responses. It is supporting
  analysis and owner-decision input only; it does not replace the governing
  architecture or authorize implementation.

## Separate proof of concept

The earlier greenfield experiment is paused and archived under
[`docs/poc/user-wallet/`](../poc/user-wallet/README.md), with its contracts and
tests under `contracts/poc/userWallet/` and `tests/poc/userWallet/`.

The PoC is evidence and background. It is not “Wallet v3,” and nothing in its
archive is implicitly approved for the new implementation.

## Path-history warning

Before commit `e0616f4`, `contracts/walletsV3/` and `tests/walletsV3/` contained
the PoC. They now mean the opposite: they are reserved for the new
implementation. In-flight branches and open pull requests based on the older
tree should treat this as a semantic rename conflict and must not merge the
archived PoC back into the reserved paths.
