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

BL-010 · 2026-07-23 · S1-E6 Base fixture compatibility · owner approved
Decision or failed assumption: The existing v2 blueprint fixtures compile and deploy correctly on Base, but Boa's fork account prefetch later replaces their locally deployed code with the upstream empty accounts at the configured addresses. Before requesting the existing v2 wallet session fixture, the standalone gas harness restores those exact fixture blueprint bytecodes to the configured addresses in the py-evm overlay and asserts the bytecode match. The owner explicitly approved this narrow evidence shim on 2026-07-23 after independent review.
Reason: Hatchery otherwise reaches `create_from_blueprint` with zero-length template code. Restoring the already-compiled fixture bytecode is the narrowest correction that preserves the existing v2 source, fixture policy, compiler settings, Base state, and Boa transaction-isolation method.
Affected files/evidence: `tests/walletsV3/gas/test_poc_gas.py`, S1-E6, `tests/walletsV3/gas/test_poc_gas.py::test_poc_gas`.
Scope impact: None; this is Base overlay test compatibility and does not change v2, v3, benchmark semantics, or architecture.

BL-011 · 2026-07-23 · Steps 1-5 gas review
Decision or failed assumption: Accept direct-transfer gas and core runtime size; redesign the empty-session, routed-yield, and payment-authorization cost centers before production; retain the demonstrated payment lifecycle semantics without treating any PoC measurement as a production baseline.
Reason: The Base gate is 52,257 tx-equivalent gas for v3 versus 511,975 for v2, and core runtime is 11,913 bytes. The local empty session is 115,155 versus the 60,000 review target; routed yield is 288,598 versus 123,126 for the direct control; external-exact and reserved-transfer creation cost 541,257 and 349,578 respectively.
Affected files/evidence: `tests/walletsV3/gas/test_poc_gas.py`, `docs/wallets-v3/POC_RESULTS.md`, S1-E6, S2-E7, S4-E2, S5-E9.
Scope impact: None; these are required measurement dispositions.

BL-012 · 2026-07-23 · post-review contract conformance / S1-E3, S4-E1, S5-E1
Decision or failed assumption: A `NONE` route could reach the three named CORE primitives because those functions distinguished only zero versus nonzero consumer, and Config treated a zero beneficiary as exempt when the envelope consumer was also zero. Require `CORE` mode in each named primitive, require the route-appropriate consumption state at dispatch settlement, and exempt a beneficiary only when it equals a nonzero consumer.
Reason: Both behaviors deviated from §§4.3 and 4.6 even though normal reviewed extenders did not construct the invalid combinations. The PoC is intended to enforce these invariants by construction.
Affected files/evidence: `contracts/walletsV3/UserWalletV3.vy`, `contracts/walletsV3/UserWalletConfigV3.vy`, `tests/walletsV3/test_security.py::test_s5_e1_none_route_cannot_consume_named_core_primitives`, `tests/walletsV3/test_transfer_and_config.py::test_s1_e3_zero_beneficiary_is_not_a_zero_consumer_exemption`.
Scope impact: None; this restores the written consumer-mode and Config contract.

BL-013 · 2026-07-23 · post-review adversarial evidence / S1-E2, S1-E3, S2-E3, S3-E1, S4-E3..S4-E6, S5-E1..S5-E2
Decision or failed assumption: Expand negative evidence inside ACTIVE sessions, across action ids and action-data hashes, across strict and terminal rail states, and across all thirteen pre-Config mutating paths. Replace the all-zero Config return shims with selector-aware candidates whose wallet response is correct and whose marker has only the intended 31- or 33-byte length defect.
Reason: The original negative suite established most defenses by source review or failed earlier at the phase gate. The added nodes independently mutate every common and payment-specific field after a valid session opens, prove matching control calls succeed, and isolate exact-return-length behavior.
Affected files/evidence: `contracts/walletsV3/mocks/MaliciousExtender.vy`, `contracts/walletsV3/mocks/MockDebtLego.vy`, `contracts/walletsV3/mocks/MockYieldLego.vy`, `tests/walletsV3/conftest.py`, `tests/walletsV3/test_transfer_and_config.py`, `tests/walletsV3/test_yield_session.py`, `tests/walletsV3/test_debt_and_operator.py`, `tests/walletsV3/test_mpp.py`, `tests/walletsV3/test_x402.py`, `tests/walletsV3/test_security.py`.
Scope impact: None; all additions directly strengthen named evidence.

BL-014 · 2026-07-23 · post-review gas guard strength / S1-E6, S2-E7, S4 gas, S5-E9
Decision or failed assumption: Make the gas module itself front-load the complete Base constants/oracle preflight, assert the installed Prague VM and introspected package versions, assert exact calibration gross/refund values, machine-compare Base calibration with the preceding local JSON, refuse xdist, require scenario postconditions, and serialize deterministic nonzero full-width signature values.
Reason: The original measurements were valid, but several required guards were recorded or checked in a separate functional test rather than enforced by the standalone gas run. The stronger signature model changes modeled L1 fees but not execution or tx-equivalent gas.
Affected files/evidence: `tests/walletsV3/gas/test_poc_gas.py`, `/tmp/wallet-v3-poc-local.json`, `/tmp/wallet-v3-poc-base.json`.
Scope impact: None; measurement formulas, thresholds, scenarios, and Base pin are unchanged.

BL-015 · 2026-07-23 · post-review core surface and settlement cleanup / S2-E2, S5-E2
Decision or failed assumption: Remove the uncontracted `attachmentRoute`, `attachmentCount`, and `sessionNonce` external views; expose the already-recorded calldata hash in `SessionOpened`; fully clear transient frame/capability fields; cache the direct-transfer balance read; require consumption before every LEGO/CORE session can settle; and assert reservation invariance for Lego SPEND settlement.
Reason: These changes align the external surface and cleanup behavior with §§4.5 and 5, turn the calldata hash into observable evidence, remove duplicate work, and make “effect requires consumption” an explicit dispatch invariant.
Affected files/evidence: `contracts/walletsV3/UserWalletV3.vy`, `tests/walletsV3/test_yield_session.py`, `tests/walletsV3/test_security.py::test_s5_e2_unconsumed_spend_session_cannot_settle`.
Scope impact: None.

BL-016 · 2026-07-23 · post-review S5-E8 provenance
Decision or failed assumption: The original squashed commit cannot independently prove that the recorded Step-4 hashes predated the future-action files. Preserve that limitation and establish a new repository-verifiable post-review core checkpoint at commit `397a1cf`: source SHA-256 `d71ea665405494b0d9f4186e3a45e78104aaf0e97b7dcb0786c9dc1fb5f68039`, Cancun/gas runtime keccak `f8aba82adac1b070be7ab8df6f82e588fd319c09572c9d7f2383a7a72a9834b4`, size 12,055 bytes.
Reason: Updating the S5-E8 constants in a later evidence commit proves the core remains unchanged after the hardened checkpoint without rewriting history or overstating the original temporal evidence.
Affected files/evidence: commit `397a1cf`, `tests/walletsV3/test_future_action.py`, `tests/walletsV3/test_security.py::test_s5_e9_core_runtime_size_and_compiler_settings`, S5-E8, S5-E9.
Scope impact: None; this corrects evidence provenance.

BL-017 · 2026-07-23 · negative-test diagnostics
Decision or failed assumption: Keep runtime assertions free of revert strings and discriminate high-value negative cases with isolated one-field mutations plus post-revert state invariants rather than adding runtime revert prose.
Reason: BL-006 established that revert strings dominated bytecode size. Boa's bare `reverts()` cannot distinguish identical empty assertion data, while the new mutation matrices, successful controls, and unchanged commitment/balance/allowance/phase assertions identify the failed invariant without changing deployed bytecode.
Affected files/evidence: `contracts/walletsV3/UserWalletV3.vy`, all negative tests under `tests/walletsV3/`, especially S1-E3, S4-E3..S4-E6, S5-E1..S5-E2.
Scope impact: None; production diagnostic design remains deferred.

BL-018 · 2026-07-23 · evidence-log chronology correction
Decision or failed assumption: Restore BL-011's original Step-5 measurements verbatim and supersede them here with the post-review values: Base v3 transfer 51,337 versus v2 511,975; core runtime 12,055 bytes; local empty session 117,497; routed yield 292,025 versus direct control 123,126; external-exact creation 543,981; reserved-transfer creation 352,399.
Reason: BL-011 had been rewritten in place during hardening. An evidence log should preserve the historical observation and append its successor even when both runs occurred on the same day.
Affected files/evidence: BL-011, `docs/wallets-v3/POC_RESULTS.md`, `/tmp/wallet-v3-poc-local.json`, `/tmp/wallet-v3-poc-base.json`.
Scope impact: None; this restores append-only evidence chronology.

BL-019 · 2026-07-23 · remaining routed-consumer regression / S2-E1, S5-E2
Decision or failed assumption: Add the carried-forward negative case that executes a valid LEGO route while mutating only the session envelope consumer away from the attachment-pinned Lego.
Reason: Happy-path routing exercised the equality check, but no prior negative test would fail if the `consumer == record.lego` assertion at `openSession` regressed.
Affected files/evidence: `tests/walletsV3/test_security.py::test_s5_e2_unconsumed_spend_session_cannot_settle`.
Scope impact: None; this is a five-line mutation of an existing adversarial evidence node.

BL-020 · 2026-07-23 · gas-artifact linkage and observed preflight / S1-E6, S2-E7, S4 gas
Decision or failed assumption: Derive the required local-evidence path from the requested Base output path; reject missing, non-absolute, outside-`/tmp`, wrong-suffix, and colliding paths with explicit messages; bind the paired runs by commit, dirty flag, a digest of the complete tracked diff/status and untracked-file contents, and the exact local artifact SHA-256. Require the exact Prague VM class, pinned overlay timestamp, and exact deterministic oracle probe fee; report observed fork, USDC, oracle, execution-mode, and yield-comparison values.
Reason: Commit and dirty-state equality did not distinguish two dirty trees at one commit, a fixed local path could collide with a custom Base output, and several guard values were asserted weakly or echoed from constants rather than recorded from observation.
Affected files/evidence: `tests/walletsV3/gas/test_poc_gas.py`, `/tmp/wallet-v3-poc-local.json`, `/tmp/wallet-v3-poc-base.json`.
Scope impact: None; scenarios, gas formula, Base pin, thresholds, and state-boundary method remain unchanged.

BL-021 · 2026-07-23 · evidence interpretation
Decision or failed assumption: Describe the cross-profile calibration check as artifact/workflow linkage plus equality of values that each profile independently pins, not as an independent discovery of calibration parity. Retain the per-primitive `consumerMode == CORE` checks as redundant defense-in-depth while crediting the public regression to the composed dispatch invariant rather than claiming it isolates each internal assertion.
Reason: The prior BL-014 phrasing overstated what comparing two already-pinned calibration dictionaries proves, and the public NONE-route regression cannot reach past the stronger dispatch invariant to falsify each redundant primitive guard independently.
Affected files/evidence: `tests/walletsV3/gas/test_poc_gas.py`, `docs/wallets-v3/POC_RESULTS.md`, BL-014, S5-E1.
Scope impact: None; this narrows evidence claims and records why redundant fail-closed checks remain.

BL-022 · 2026-07-23 · explicitly reviewed scope correction / §§1, 4.5
Decision or failed assumption: Clarify in both contract documents that only a `NONE` route may settle without consumption; a `LEGO` or `CORE` route must consume before its extender returns or the entire execution reverts. The owner explicitly approved this wording correction on 2026-07-23 after reviewing its runtime meaning and compatibility tradeoff.
Reason: The existing implementation and §1 already reserve successful no-effect sessions for framework-overhead evidence, but the broader prose in implementation-guide §4.5 and architecture §4.4 could be read as allowing any route mode to return unconsumed.
Affected files/evidence: `docs/wallets-v3/implementation-guide.md`, `docs/wallets-v3/user-wallet.md`, `contracts/walletsV3/UserWalletV3.vy`, `tests/walletsV3/test_security.py::test_s5_e2_unconsumed_spend_session_cannot_settle`.
Scope impact: Explicitly reviewed documentation correction only; runtime behavior, ABI, storage, scenarios, and architecture are unchanged.

BL-023 · 2026-07-23 · round-three regression correction / S2-E1, S5-E2
Decision or failed assumption: BL-019's first wrong-consumer probe was shadowed by the later dispatch requirement that every LEGO route settle consumed: an extender that only opened and returned reverted even if the `consumer == record.lego` assertion was removed. Replace it with a consume-capable hostile path that declares itself as consumer, consumes, and pulls the exact authorized amount, plus a pinned-Lego positive control on the same routed selector and the existing unconsumed-session negative case.
Reason: With the real core the hostile path reverts before any approval or pull. In a temporary mutation that removed only the `openSession` consumer-binding assertion, the same test failed with `Did not revert` because the hostile path consumed and pulled successfully. Restoring the assertion restored the passing test, and the core source hash remained `d71ea665405494b0d9f4186e3a45e78104aaf0e97b7dcb0786c9dc1fb5f68039`.
Affected files/evidence: `contracts/walletsV3/mocks/MaliciousExtender.vy`, `tests/walletsV3/test_security.py::test_s5_e2_unconsumed_spend_session_cannot_settle`, `docs/wallets-v3/POC_RESULTS.md`, BL-019.
Scope impact: None; this corrects overstated test evidence with a mutation-sensitive planned malicious mock. Production core, ABI, storage, and architecture are unchanged.

BL-024 · 2026-07-23 · round-three gas-report polish / S1-E6, S2-E7, S4 gas
Decision or failed assumption: Record both requested and resolved output/local-evidence paths so macOS's `/tmp` → `/private/tmp` symlink resolution is explicit, and remove the prose `preflightPosition` field rather than presenting code-order self-attestation as observed evidence.
Reason: Both points were cosmetic and did not weaken the guards or measurements, but the report can express path resolution directly and rely on executable source order instead of a constant claim about that order.
Affected files/evidence: `tests/walletsV3/gas/test_poc_gas.py`, `docs/wallets-v3/POC_RESULTS.md`, `/tmp/wallet-v3-poc-local.json`, `/tmp/wallet-v3-poc-base.json`.
Scope impact: None; report observability only. Preconditions, scenarios, formulas, thresholds, and Base pin are unchanged.
