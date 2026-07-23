# User Wallet v3 Lean PoC Build Log

BL-001 · 2026-07-23 · contract review / Step 1
Decision or failed assumption: Treat Implementation Guide v2.4 and Architecture v11.4 as the complete implementation contract; no earlier v3 implementation or repository-local agent instruction exists.
Reason: The requested branch begins with only the two contract documents and a clean working tree.
Affected files/evidence: `docs/wallets-v3/*`, planned `contracts/walletsV3/**`, planned `tests/walletsV3/**`.
Scope impact: None.

BL-002 · 2026-07-23 · S1-E1..S1-E5
Decision or failed assumption: Use one test-only `MockReentrantToken` as the standard exact-return token as well as the reentrancy adversary; express ABI-invalid 31-byte and 33-byte Config returns with bounded inline EVM runtime shims.
Reason: Vyper's typed external functions cannot emit deliberately malformed ABI word lengths; the guide explicitly permits documented bounded shims in `conftest.py`.
Affected files/evidence: `contracts/walletsV3/mocks/MockReentrantToken.vy`, `tests/walletsV3/conftest.py`, S1-E3, S1-E4.
Scope impact: None; both are planned test machinery.

BL-003 · 2026-07-23 · compiler control
Decision or failed assumption: All v3 artifacts deploy through `tests/walletsV3/conftest.py::deploy_v3`, which asserts optimizer `gas` and EVM target `cancun`.
Reason: Boa and Vyper otherwise default to compiler/execution settings that do not satisfy the evidence contract.
Affected files/evidence: `tests/walletsV3/conftest.py`, all v3 tests and gas evidence.
Scope impact: None.

BL-004 · 2026-07-23 · S2-E1..S2-E8
Decision or failed assumption: Store bounded attachment records and selector routes directly in the wallet; use a session-open event for independent semantic-hash evidence without persisting diagnostic session state.
Reason: The event exposes the exact authorized hash to tests while preserving transient session state and the no-effect session's lack of persistent economic changes.
Affected files/evidence: `contracts/walletsV3/UserWalletV3.vy`, `tests/walletsV3/test_yield_session.py`, S2-E1..S2-E8.
Scope impact: None.

BL-005 · 2026-07-23 · S3-E1..S3-E7
Decision or failed assumption: Model debt and collateral by wallet address in one bounded mock protocol, and implement operator grant/revoke as the two action-specific core calls over one pinned protocol and Lego.
Reason: This is the smallest representative state needed to test non-allowance effects, fixed wallet-originated authority, Config recovery, and DRAIN_ONLY succession.
Affected files/evidence: `contracts/walletsV3/extenders/DebtExtender.vy`, `contracts/walletsV3/mocks/MockDebt*.vy`, `contracts/walletsV3/mocks/MockOperatorProtocol.vy`, S3-E1..S3-E7.
Scope impact: None.

BL-006 · 2026-07-23 · Step 4 core size
Decision or failed assumption: The first full payment-core draft compiled to 31,936 runtime bytes; removing diagnostic revert strings while retaining identical assertions reduced it to 11,913 bytes under the 16,384-byte review target.
Reason: The PoC requires gas optimization and a deployable core. Revert prose is not part of the provisional ABI or required evidence and dominated generated runtime size.
Affected files/evidence: `contracts/walletsV3/UserWalletV3.vy`, S5-E9.
Scope impact: None; trust boundaries, state transitions, and callable surface are unchanged.

BL-007 · 2026-07-23 · S4-E1..S4-E9
Decision or failed assumption: Implement external-exact and representative reserved-transfer commitments directly in core with terminal non-reuse maps and stored helper codehashes.
Reason: This preserves wallet-held value, conservative reservations, old-helper settlement, and exact rail authorization across Config and extender succession.
Affected files/evidence: `contracts/walletsV3/extenders/PaymentExtender.vy`, `contracts/walletsV3/rails/X402Helper.vy`, `tests/walletsV3/test_mpp.py`, `tests/walletsV3/test_x402.py`, S4-E1..S4-E9.
Scope impact: None.

BL-008 · 2026-07-23 · S5-E8 pre-future-action record
Decision or failed assumption: Freeze the completed Step-4 core only for the future-action experiment at source SHA-256 `182126e57477419e5d1b87183ac4bfcc699d07cc7ed8356a6fd16ad134c65809` and Cancun/gas runtime keccak `f69ffc74692fd2ff6a08d94a4b1f5705b7d30fba4f97ba642c427d6ab95aa6b7` (11,913 bytes).
Reason: S5-E8 requires objective proof that action 30 was added without changing core, shared types/interfaces, or existing extenders/Legos.
Affected files/evidence: `tests/walletsV3/test_future_action.py`, S5-E8, S5-E9.
Scope impact: None; this is experiment evidence, not a production freeze artifact.

BL-009 · 2026-07-23 · S5-E1..S5-E9
Decision or failed assumption: Add only the planned future-action trio and malicious-extender/targeted test behavior after recording the core hashes.
Reason: These files complete containment, stale/reuse, reentrancy, malformed-return, dependency-mutation, and no-core-change evidence without adding production mechanisms.
Affected files/evidence: `contracts/walletsV3/extenders/FutureActionExtender.vy`, `contracts/walletsV3/mocks/MockFutureAction*.vy`, `contracts/walletsV3/mocks/MaliciousExtender.vy`, `tests/walletsV3/test_security.py`, `tests/walletsV3/test_future_action.py`.
Scope impact: None.

BL-010 · 2026-07-23 · S1-E6 Base fixture compatibility
Decision or failed assumption: The existing v2 blueprint fixtures compile and deploy correctly on Base, but Boa's fork account prefetch later replaces their locally deployed code with the upstream empty accounts at the configured addresses. Before requesting the existing v2 wallet session fixture, the standalone gas harness restores those exact fixture blueprint bytecodes to the configured addresses in the py-evm overlay and asserts the bytecode match.
Reason: Hatchery otherwise reaches `create_from_blueprint` with zero-length template code. Restoring the already-compiled fixture bytecode is the narrowest correction that preserves the existing v2 source, fixture policy, compiler settings, Base state, and Boa transaction-isolation method.
Affected files/evidence: `tests/walletsV3/gas/test_poc_gas.py`, S1-E6, `tests/walletsV3/gas/test_poc_gas.py::test_poc_gas`.
Scope impact: None; this is Base overlay test compatibility and does not change v2, v3, benchmark semantics, or architecture.

BL-011 · 2026-07-23 · Steps 1-5 gas review
Decision or failed assumption: Accept direct-transfer gas and core runtime size; redesign the empty-session, routed-yield, and payment-authorization cost centers before production; retain the demonstrated payment lifecycle semantics without treating any PoC measurement as a production baseline.
Reason: The Base gate is 52,257 tx-equivalent gas for v3 versus 511,975 for v2, and core runtime is 11,913 bytes. The local empty session is 115,155 versus the 60,000 review target; routed yield is 288,598 versus 123,126 for the direct control; external-exact and reserved-transfer creation cost 541,257 and 349,578 respectively.
Affected files/evidence: `tests/walletsV3/gas/test_poc_gas.py`, `docs/wallets-v3/POC_RESULTS.md`, S1-E6, S2-E7, S4-E2, S5-E9.
Scope impact: None; these are required measurement dispositions.
