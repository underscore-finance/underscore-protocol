# Mutability Cleanup Scope

This branch keeps the scoped mutability changes that were retained on `cheque-enhance`.
It is not the full zero-violation cleanup from the original handoff.

The scanner and policy docs remain useful for auditing and future cleanup work, but this
branch should not claim:

- zero `view-revert` violations,
- a final empty scanner inventory,
- final gas baseline comparison,
- or completed status-code/sentinel refactors for every scanner finding.

Current known intentional scope:

- low-risk `@view` to `@pure` promotions retained by the branch owner,
- local interface mutability updates that match those retained promotions,
- `Appraiser.calculateYieldProfits` promoted to `@view`. Permission failures and
  other off-path conditions return the zero tuple `(0, 0, 0)`. The mutating
  wallet path treats this as no realized yield and does not assert on it.
- some local third-party interface declarations are marked `pure` where retained
  branch code and local mocks compile that way. These declarations are local
  call-surface metadata and should not be treated as authoritative statements
  about the upstream Aave, Compound, Euler, Morpho, or Sky contracts.

Before presenting this branch as a full mutability-policy cleanup, regenerate scanner
inventory and gas data from the actual branch state.
