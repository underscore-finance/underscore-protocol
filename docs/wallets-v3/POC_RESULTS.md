# User Wallet v3 Lean PoC Results

**Contract:** Implementation Guide v2.4 and Architecture v11.4

**Evidence classification:** Final acceptance runs are from this file's clean containing commit. Raw JSON remains under `/tmp` and is not committed.

**Environment:** Vyper 0.4.3; titanoboa 0.2.7; py-evm 0.12.1b1; v3 `optimizer=gas`, `evm_version=cancun`; v2 source setting `optimizer=codesize`, implicit EVM target; Prague execution VM.

**Scope deviations:** None.

## Architecture questions

### Q1 · PASS

Evidence ids: S1-E5, S3-E6, S3-E7, S4-E8.

Test node ids:

- `tests/walletsV3/test_transfer_and_config.py::test_s1_e5_broken_config_can_be_replaced_without_moving_assets`
- `tests/walletsV3/test_extender_lifecycle.py::test_s3_e6_and_e7_debt_position_survives_successor_and_old_exact_exits`
- `tests/walletsV3/test_mpp.py::test_s4_e8_commitments_survive_config_and_payment_successor`

Measurements: The wallet address, balances, wallet-keyed debt position, attachment history, reservations, and commitments remain at the same core address through Config replacement and extender succession.

Residual risks/limitations: The proof uses representative mock debt/payment integrations. It does not prove migration compatibility for a production ABI or storage layout.

Disposition: **KEEP** the permanent custody address, direct Config replacement, and append-only typed attachment model.

### Q2 · PASS

Evidence ids: S1-E3, S1-E5, S3-E6.

Test node ids:

- `tests/walletsV3/test_transfer_and_config.py::test_s1_e3_rejects_invalid_config_candidates`
- `tests/walletsV3/test_transfer_and_config.py::test_s1_e3_reviewed_config_has_no_initializer_or_rebinding`
- `tests/walletsV3/test_transfer_and_config.py::test_s1_e3_zero_beneficiary_is_not_a_zero_consumer_exemption`
- `tests/walletsV3/test_transfer_and_config.py::test_s1_e5_broken_config_can_be_replaced_without_moving_assets`
- `tests/walletsV3/test_extender_lifecycle.py::test_s3_e6_and_e7_debt_position_survives_successor_and_old_exact_exits`

Measurements: A Config whose operational authorizers always revert is replaced directly while wallet-owned economic state remains unchanged. Wrong marker, wrong wallet, no code, revert, isolated 31-/33-byte marker return, and probe-gas exhaustion are rejected. Every reviewed Config function is view/pure, and a zero consumer does not exempt a zero beneficiary.

Residual risks/limitations: Runtime probes cannot prove that arbitrary bytecode lacks a hidden rebinding path. Constructor immutability and absence of an initializer are properties of the reviewed PoC Config source.

Disposition: **KEEP** the IDLE-only owner escape path and exact 33-byte bounded probes; require source/governance controls in production.

### Q3 · PASS

Evidence ids: S2-E1 through S2-E6, S3-E6, S5-E1 through S5-E4.

Test node ids:

- `tests/walletsV3/test_yield_session.py::test_s2_e1_routed_extender_opens_once_and_direct_calls_fail`
- `tests/walletsV3/test_yield_session.py::test_s2_e2_empty_session_has_no_effect_or_approval`
- `tests/walletsV3/test_yield_session.py::test_s2_e3_and_e8_semantic_hash_binds_full_yield_action`
- `tests/walletsV3/test_yield_session.py::test_s2_e4_and_e5_exact_approval_cleanup_and_direct_beneficiary`
- `tests/walletsV3/test_yield_session.py::test_s2_e4_nested_dispatch_during_approval_rolls_back`
- `tests/walletsV3/test_yield_session.py::test_s2_e6_attachment_bounds_declarations_and_dependencies`
- `tests/walletsV3/test_extender_lifecycle.py::test_s3_e6_and_e7_debt_position_survives_successor_and_old_exact_exits`
- `tests/walletsV3/test_security.py::test_s5_e1_none_route_cannot_consume_named_core_primitives`
- `tests/walletsV3/test_security.py::test_s5_e1_hostile_active_extender_cannot_mutate_core_effect_fields`
- `tests/walletsV3/test_security.py::test_s5_e2_capability_reuse_cross_action_and_stale_session_fail`
- `tests/walletsV3/test_security.py::test_s5_e2_unconsumed_spend_session_cannot_settle`
- `tests/walletsV3/test_security.py::test_s5_e3_malicious_extender_cannot_use_primitives_or_general_authority`
- `tests/walletsV3/test_security.py::test_s5_e4_config_reentrancy_and_approval_cleanup_failure_revert_cleanly`
- `tests/walletsV3/test_security.py::test_s5_e4_malformed_erc20_return_fails_closed`

Measurements: Attachment/route bounds, active-family collision rejection, dependency codehash checks, one transient capability, semantic binding, exact approval cleanup, nested-session rejection, stale/reuse rejection, and attached-extender containment all pass. Inside an ACTIVE session, every common envelope field and every external-exact/reserved-transfer field is independently mutated and rejected; valid controls reach each named primitive. A consume-capable hostile extender whose only envelope mutation is `consumer != record.lego` cannot open, consume, or pull the exact authorized amount, while the same routed path with the pinned Lego succeeds and delivers vault shares to the wallet. Removing only the consumer-binding assertion was verified to make this node fail because the hostile pull succeeds. `NONE` cannot consume, and an unconsumed LEGO/CORE route cannot settle.

Residual risks/limitations: A reviewed typed extender remains trusted to preserve caller intent among requests that policy would independently allow. Legos are trusted adapters and malicious Lego behavior is outside this PoC.

Disposition: **KEEP** typed selector routing, pinned dependencies, one-capability containment, and automatic DRAIN_ONLY succession. Do not generalize into an arbitrary executor.

### Q4 · PASS

Evidence ids: S2-E3 through S2-E5, S3-E1 through S3-E4.

Test node ids:

- `tests/walletsV3/test_yield_session.py::test_s2_e3_and_e8_semantic_hash_binds_full_yield_action`
- `tests/walletsV3/test_yield_session.py::test_s2_e4_and_e5_exact_approval_cleanup_and_direct_beneficiary`
- `tests/walletsV3/test_yield_session.py::test_s2_e4_nested_dispatch_during_approval_rolls_back`
- `tests/walletsV3/test_debt_and_operator.py::test_s3_e1_non_allowance_effects_are_semantically_bounded`
- `tests/walletsV3/test_debt_and_operator.py::test_s3_e2_borrowed_and_released_assets_go_to_wallet`
- `tests/walletsV3/test_debt_and_operator.py::test_s3_e3_fixed_operator_target_and_lego_only`
- `tests/walletsV3/test_debt_and_operator.py::test_s3_e4_operator_use_outside_active_session_fails`
- `tests/walletsV3/test_security.py::test_s5_e1_hostile_active_extender_cannot_mutate_core_effect_fields`
- `tests/walletsV3/test_security.py::test_s5_e2_unconsumed_spend_session_cannot_settle`

Measurements: SPEND is bounded by exact approval, required consumption, reservation invariance, and final token loss; LIABILITY and ASSET_RELEASE are bounded by action-specific semantic hashes and direct wallet beneficiary state; AUTHORITY is bounded by a named core primitive. Wrong action ids and wrong action-data hashes are directly tested.

Residual risks/limitations: Representative mocks prove the containment mechanisms, not every protocol-specific semantic or postcondition.

Disposition: **KEEP** the split between token-loss, semantic-effect, and fixed-authority mechanisms; require action-by-action adapter review.

### Q5 · PASS

Evidence ids: S3-E3, S3-E4, S3-E5, S3-E7.

Test node ids:

- `tests/walletsV3/test_debt_and_operator.py::test_s3_e3_fixed_operator_target_and_lego_only`
- `tests/walletsV3/test_debt_and_operator.py::test_s3_e4_operator_use_outside_active_session_fails`
- `tests/walletsV3/test_debt_and_operator.py::test_s3_e5_active_revoke_after_config_replacement`
- `tests/walletsV3/test_extender_lifecycle.py::test_s3_e6_and_e7_debt_position_survives_successor_and_old_exact_exits`
- `tests/walletsV3/test_security.py::test_s5_e1_none_route_cannot_consume_named_core_primitives`
- `tests/walletsV3/test_security.py::test_s5_e1_hostile_active_extender_cannot_mutate_core_effect_fields`

Measurements: Core constructs only grant/revoke for the attachment-pinned protocol and Debt Lego. Alternate caller, extender, attachment, target, operator, and authority-use paths fail.

Residual risks/limitations: The result supports one fixed template only and is not evidence for generalized wallet-call templates.

Disposition: **KEEP** named fixed-authority primitives; **ABANDON** any inference that the PoC justifies a generic executor.

### Q6 · PASS

Evidence ids: S4-E1 through S4-E9, S5-E5 through S5-E7.

Test node ids:

- `tests/walletsV3/test_mpp.py::test_s4_e1_commitment_creation_is_active_typed_and_allowlisted`
- `tests/walletsV3/test_x402.py::test_s4_e2_base_constants_preflight_and_real_usdc_bytes_signature_pull`
- `tests/walletsV3/test_x402.py::test_s4_e3_rail_signature_exact_digest_caller_bounds_and_time`
- `tests/walletsV3/test_x402.py::test_s4_e4_and_e5_used_unsynced_expiry_unused_expiry_and_replay`
- `tests/walletsV3/test_x402.py::test_s4_e3_erc165_is_narrow`
- `tests/walletsV3/test_mpp.py::test_s4_e5_and_e6_partial_settlement_refund_and_terminal_replay`
- `tests/walletsV3/test_mpp.py::test_s4_e6_state_updates_before_transfer_and_reentrancy_rolls_back`
- `tests/walletsV3/test_mpp.py::test_s4_e7_reserved_value_blocks_transfer_yield_debt_and_double_commit`
- `tests/walletsV3/test_mpp.py::test_s4_e8_commitments_survive_config_and_payment_successor`
- `tests/walletsV3/test_mpp.py::test_s4_e9_token_and_helper_failures_preserve_commitment_state`
- `tests/walletsV3/test_security.py::test_s4_e3_and_s5_e4_non_idle_rail_answer_is_invalid`
- `tests/walletsV3/test_security.py::test_s5_e1_none_route_cannot_consume_named_core_primitives`
- `tests/walletsV3/test_security.py::test_s5_e1_hostile_active_extender_cannot_mutate_core_effect_fields`
- `tests/walletsV3/test_extender_lifecycle.py::test_s5_e7_old_route_collision_nonexit_and_codehash_mutation_fail`

Measurements: Real Base USDC exact external pull, permissionless sync, equality and strictly-past expiry boundaries, used/expired rail-signature rejection, real EIP-3009 cancellation-digest rejection, conservative reservation, representative reserved partial settlement/refund, all terminal-state non-reuse, reentrancy rollback, dependency succession, and reserved-value exclusion pass. Payment field binding is also exercised from inside an ACTIVE routed session.

Residual risks/limitations: The external branch proves only the Base USDC EIP-3009 onchain leg. The MPP branch is a reservation/settlement model, not MPP wire-protocol compliance. Payment helper and liveness remain trusted integration dependencies.

Disposition: **KEEP** wallet-held reservations and terminal non-reuse semantics. **REDESIGN** authorization cost and production rail/cancellation/liveness policy before specification.

### Q7 · PASS

Evidence ids: S3-E6, S3-E7.

Test node ids:

- `tests/walletsV3/test_extender_lifecycle.py::test_s3_e6_and_e7_debt_position_survives_successor_and_old_exact_exits`
- `tests/walletsV3/test_extender_lifecycle.py::test_s5_e7_old_route_collision_nonexit_and_codehash_mutation_fail`

Measurements: Attaching v2 removes all v1 current routes, marks v1 DRAIN_ONLY, blocks new/non-exit v1 actions, and permits only Config-authorized exact v1 close/revoke selectors against the unchanged wallet-keyed position.

Residual risks/limitations: The PoC has no detach/HARD_REVOKE or generic proof that every external position is closed.

Disposition: **KEEP** selector-bounded DRAIN_ONLY exits; design production lifecycle/governance and stuck-position policy separately.

### Q8 · PASS

Evidence ids: S1-E6.

Test node ids:

- `tests/walletsV3/gas/test_poc_gas.py::test_poc_gas`

Measurements: On pinned Base block 34,642,981, initialized independent cross-block repeat transfer is 51,337 tx-equivalent gas for v3 versus 511,975 for v2: -460,638 gas, or -89.9728%. V3 is below the hard 190,000 threshold. The modeled v3 sponsored fee is 41,660,008,930 wei at the pinned 774,425 wei Base fee, including 1,903,352,705 wei modeled L1 fee and zero operator fee.

Residual risks/limitations: Lean v3 intentionally omits v2 production policy work. The paired Base-profile transfer uses the v2 fixture's mock ERC-20 for both wallets, exactly as prescribed; 51,337 is evidence for the architecture's direct path, not a claim that a real Base USDC proxy transfer costs 51,337. Fee evidence is a deterministic fork-time model, not a receipt.

Disposition: **KEEP** the direct transfer path and its manually controlled hard threshold.

## Measurements and dispositions

All gas values below are tx-equivalent. Local values are diagnostic; Base transfer is the hard gate.

| Scenario | Profile | Gas | Comparison | Disposition |
|---|---:|---:|---:|---|
| `v2.transfer.repeat` | Base | 511,975 | paired comparator | Comparator only |
| `v3.transfer.repeat` | Base | 51,337 | -89.9728% vs v2; <190,000 | **ACCEPT** |
| `v2.transfer.repeat` | local | 419,507 | paired diagnostic | Diagnostic only |
| `v3.transfer.repeat` | local | 51,337 | -87.7625% vs v2 | Diagnostic support |
| `v3.session.empty` | local | 117,497 | 57,497 above the <60,000 review target | **REDESIGN** router/session overhead |
| `control.yield.protocol_direct` | local | 123,126 | direct initialized mock-vault control | Control only |
| `v3.session.yield_minimal` | local | 292,025 | +168,899, or +137.18%, vs direct | **REDESIGN** before production |
| `v3.x402.authorize` | Base | 543,981 | no hard target | **REDESIGN** creation cost; keep semantics |
| `v3.x402.sync` | Base | 67,410 | no hard target | **ACCEPT for PoC**, not a baseline |
| `v3.mpp.authorize` | local | 352,399 | no hard target | **REDESIGN** creation cost; keep semantics |
| `v3.mpp.partial_settle` | local | 93,491 | no hard target | **ACCEPT for PoC**, not a baseline |
| `v3.mpp.refund` | local | 51,787 | no hard target | **ACCEPT for PoC**, not a baseline |

The harness requires the exact Prague VM class, introspects all three pinned package versions, refuses xdist, front-loads the complete Base/USDC/oracle preflight, pins Boa's overlay timestamp, asserts an exact 1,233,604,915 wei deterministic oracle probe fee, and requires explicit scenario postconditions. Each profile independently asserts the transaction-boundary calibration: clearing an initialized slot costs 5,102 gross with a 4,800 raw refund; a later zero-to-nonzero clean write costs 22,217 gross with zero refund; only origin, target, and Prague precompiles begin warm; no storage slot begins warm. The Base run then verifies dictionary equality against the preceding local artifact and binds that exact artifact by derived path, source commit, dirty flag, complete worktree-state digest, and content SHA-256. That cross-file comparison proves paired-artifact identity and workflow linkage; it does not independently discover calibration values already pinned in both profiles.

Every scenario records `executionMode` and the absence of a receipt. Each artifact records both the literal requested `/tmp` output path and its resolved filesystem path, making macOS's `/tmp` → `/private/tmp` resolution explicit. The local artifact also records the yield control/candidate delta, while the Base preflight report contains observed overlay, upstream block, USDC, oracle-code, and fee-probe values rather than restating expected constants.

The `v3.x402.sync` tx-equivalent is 67,410 after its 9,600 refund, but its serialized envelope is asserted and decoded with a 77,010 `minimum_executable_gas_limit`. Deterministic `yParity=1` and full-width nonzero `r`/`s` values are included in every modeled Base envelope.

Core runtime is 12,055 bytes under Cancun/gas, 4,329 bytes below the 16,384-byte review target: **ACCEPT for PoC**. The post-review core checkpoint at commit `397a1cf` has source SHA-256 `d71ea665405494b0d9f4186e3a45e78104aaf0e97b7dcb0786c9dc1fb5f68039` and runtime keccak `f8aba82adac1b070be7ab8df6f82e588fd319c09572c9d7f2383a7a72a9834b4`. The later evidence commit proves both remain unchanged through:

- `tests/walletsV3/test_future_action.py::test_s5_e8_future_asset_release_needs_no_core_change`
- `tests/walletsV3/test_security.py::test_s5_e9_core_runtime_size_and_compiler_settings`

Historical limitation: the original implementation arrived as one squashed commit, so git cannot independently date the original Step-4 hash record before the future-action files. BL-008 is therefore an implementation attestation, not repository-verifiable temporal proof. The post-review `397a1cf` checkpoint and later evidence commit provide that temporal proof from the hardening point forward.

## Evidence coverage

The exact node ids above cover every required evidence record:

- S1-E1 through S1-E5: all seven nodes in `test_transfer_and_config.py`; S1-E6: `tests/walletsV3/gas/test_poc_gas.py::test_poc_gas`.
- S2-E1 through S2-E6 and S2-E8: all six nodes in `test_yield_session.py`; S2-E7: standalone gas node.
- S3-E1 through S3-E5: all five nodes in `test_debt_and_operator.py`; S3-E6 and S3-E7: both nodes in `test_extender_lifecycle.py`.
- S4-E1 and S4-E5 through S4-E9: all six nodes in `test_mpp.py`; S4-E2 through S4-E5: all four Base nodes in `test_x402.py`; S4 gas review: standalone gas node.
- S5-E1: `tests/walletsV3/test_security.py::test_s5_e1_none_route_cannot_consume_named_core_primitives` and `tests/walletsV3/test_security.py::test_s5_e1_hostile_active_extender_cannot_mutate_core_effect_fields`.
- S5-E2: `tests/walletsV3/test_security.py::test_s5_e2_capability_reuse_cross_action_and_stale_session_fail` and `tests/walletsV3/test_security.py::test_s5_e2_unconsumed_spend_session_cannot_settle`.
- S5-E3: `tests/walletsV3/test_security.py::test_s5_e3_malicious_extender_cannot_use_primitives_or_general_authority`.
- S5-E4: `tests/walletsV3/test_security.py::test_s4_e3_and_s5_e4_non_idle_rail_answer_is_invalid`, `tests/walletsV3/test_security.py::test_s5_e4_config_reentrancy_and_approval_cleanup_failure_revert_cleanly`, and `tests/walletsV3/test_security.py::test_s5_e4_malformed_erc20_return_fails_closed`.
- S5-E5: `tests/walletsV3/test_x402.py::test_s4_e3_rail_signature_exact_digest_caller_bounds_and_time`, `tests/walletsV3/test_x402.py::test_s4_e4_and_e5_used_unsynced_expiry_unused_expiry_and_replay`, and `tests/walletsV3/test_mpp.py::test_s4_e7_reserved_value_blocks_transfer_yield_debt_and_double_commit`.
- S5-E6: `tests/walletsV3/test_mpp.py::test_s4_e5_and_e6_partial_settlement_refund_and_terminal_replay` and `tests/walletsV3/test_mpp.py::test_s4_e6_state_updates_before_transfer_and_reentrancy_rolls_back`.
- S5-E7: `tests/walletsV3/test_extender_lifecycle.py::test_s5_e7_old_route_collision_nonexit_and_codehash_mutation_fail`.
- S5-E8: `tests/walletsV3/test_future_action.py::test_s5_e8_future_asset_release_needs_no_core_change`.
- S5-E9: `tests/walletsV3/test_security.py::test_s5_e9_core_runtime_size_and_compiler_settings`.

## Unresolved security and integration risks

- The owner is a fixed trusted root. There is no owner transfer, multisig, account abstraction, session-key, compromise response, freeze, or Config-bypassing emergency path.
- Extenders are contained to authorized policy/effect fields but a malicious attached extender can choose a different still-policy-authorized request than the caller intended.
- Legos and the x402 helper are trusted, reviewed adapters. Malicious Lego containment, adapter governance, and code-review provenance are not solved.
- Mock protocols are representative. Only the Base USDC EIP-3009 leg uses a real pinned integration; real Ripe/Morpho behavior and callback/reentrancy surfaces remain untested.
- Supported ERC-20 flows require standard exact boolean returns. Fee-on-transfer, rebasing, ERC-777 hooks, and no-return tokens are unsupported.
- Used-but-unsynced external pulls intentionally leave a conservative reservation until a permissionless sync occurs. Production liveness, helper failure, cancellation, and notification policy remain open.
- Narrow EIP-1271 ignores a bounded signature argument and authorizes only the stored rail digest. Wallet/tool compatibility outside the tested USDC path is not established.
- Same-address dependency code mutation is rejected, but attachment approval, adapter governance, and emergency response are deferred.
- Transient behavior is compiled for Cancun and exercised in Boa's Prague py-evm overlay. There is no live-network receipt or production deployment evidence.
- The Base transfer comparison uses the v2 fixture's mock ERC-20 for both v2 and v3. It isolates direct-path architecture cost but does not measure a real USDC proxy transfer.
- The Base gas harness must restore exact existing v2 fixture blueprint bytecode after Boa fork prefetch exposes upstream empty accounts. The report asserts byte equality; the owner explicitly approved BL-010 on 2026-07-23 after independent review. The shim should still be revisited with future Boa versions.
- Gas evidence files remain unauthenticated local files in world-writable `/tmp`. The Base run derives its paired local path and binds the exact bytes plus worktree state, preventing accidental stale/colliding evidence, but a hostile local process able to rewrite both artifacts or the running repository is outside this PoC's evidence model.
- The NONE-route regression proves the composed dispatch invariant. The additional `consumerMode == CORE` checks inside named primitives are intentionally redundant defense-in-depth and cannot be isolated through a successful public path while the stronger dispatch invariant is present.
- The original squashed commit cannot independently prove the Step-4-before-future-action chronology. The post-review checkpoint does prove unchanged core from commit `397a1cf` forward.
- Core assertions intentionally have no runtime reason strings to preserve the size result. High-value negative cases use isolated mutations and state invariants, but empty assertion data is less diagnostic than a production custom-error design.
- Tests are targeted, not a formal proof, exhaustive fuzz campaign, or audit.

## Explicitly omitted

Freeze/unfreeze and emergency drains; production ABI/storage freeze; upgrade guarantees; migration/factory/cutover tooling; owner transfer, multisig, account abstraction, relayers and session keys; timelocks/proposals/governance registries; ExtenderBook/LegoBook/ModuleBook and bundle proofs; Config state migration; general EIP-1271, callbacks, receivers and hooks; fees, pricing/USD limits, period accounting, points and yield tracking; native ETH, NFTs, swaps, liquidity and rewards; generic wallet-call templates; detach/HARD_REVOKE; production cancellation/notification policy and multi-rail adapters; real Ripe/Morpho; x402 HTTP/facilitator and MPP wire protocol; ERC-4337 gas; manifests, freeze artifacts, ratification and exhaustive audit matrices.

## Overall recommendation

- **KEEP:** stable non-proxy custody address; direct replaceable wallet-bound Config; append-only codehash-pinned typed attachments; automatic selector-bounded DRAIN_ONLY succession; one transient capability; exact approval and semantic-effect bounds; named fixed-authority primitives; wallet-held payment reservations; terminal commitment non-reuse.
- **REDESIGN:** routed-session overhead, especially the empty framework and yield path; payment commitment creation cost; production adapter/governance provenance; emergency/owner policy; payment liveness/cancellation; lifecycle behavior for irrecoverable dependencies.
- **ABANDON:** any production-readiness, ABI/storage-freeze, arbitrary-executor, general-signature, full x402, or full MPP claim derived from this PoC.

Before a production specification or audit: define owner/emergency/governance policy; optimize and remeasure routed/session and payment creation paths; specify adapter review and succession; integrate real target protocols and full payment rails; define cancellation/liveness and stuck-position behavior; add property/invariant fuzzing and formal review; support or explicitly reject token edge cases at product level; design ABI/storage/migration/deployment plans; then freeze a reviewed specification and run an independent security audit.
