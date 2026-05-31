# Security Audit Handoff: Underscore Protocol — Payment Subsystem

> **Paste everything below the line into a fresh agent.** It is self-contained. It assumes the agent has read access to this repository and can run shell commands and write test files.

---

## 0. Your mission

You are a senior smart-contract security auditor. Your job is to perform a **full, adversarial security audit of the Underscore Protocol payment subsystem** — every way that value can leave a user's wallet. Hunt for bugs, exploits, logic errors, weaknesses, and economic vulnerabilities. Assume a motivated attacker who will read every line, chain multiple weak primitives together, and abuse edge cases (timing, rounding, reentrancy, role confusion, oracle manipulation, struct/ABI mismatches).

This code is **not yet deployed**. It lives on a feature branch (`cheque-enhance`) that significantly reworked the payment paths. The goal is to make sure money cannot leave a wallet except exactly as the owner intended, and that every limit, timelock, and permission is sound. **Funds are at stake.** Bias toward over-reporting: a plausible-but-unconfirmed issue is worth surfacing.

This is a **review and analysis task, not a remediation task.** Do not modify protocol contracts. You may (and should) write throwaway test files to prove or disprove findings. Report what you find; do not "fix" it unless explicitly asked afterward.

---

## 1. Environment setup (do this first)

```bash
cd /Users/wigglez/dev/underscore-protocol
git status --short --branch
git fetch origin
git branch --show-current   # expect: cheque-enhance
git diff --stat origin/master...HEAD
```

If `git branch --show-current` is not `cheque-enhance`, stop and report that
the audit is not running on the intended branch.

- **Language:** Vyper `0.4.3`. Test harness: `titanoboa` + `pytest` (+ `hypothesis` available but unused for payments). See `requirements.txt` (pinned) / `requirements.in`.
- **Contracts:** `contracts/**/*.vy`. Interfaces/structs: `interfaces/*.vyi`. These `.vyi` files are the source of truth for struct layouts and the ABI cutover.
- **There is no `pytest.ini`/`pyproject.toml`.** All test config lives in `tests/conftest.py` → `tests/conf_*.py` plugins.

### Running tests

```bash
cd /Users/wigglez/dev/underscore-protocol
# GOTCHA 1: tests/conf_env.py reads os.environ["ETHERSCAN_API_KEY"] at import time (lines 18 & 26),
# so even LOCAL runs fail at collection if it is unset. Export a dummy value:
export ETHERSCAN_API_KEY=dummy
export WEB3_ALCHEMY_API_KEY=dummy

# GOTCHA 2: invoke via `python -m pytest`, NOT bare `pytest`. Bare `pytest` does not put the repo
# root on sys.path, so collection fails with `ModuleNotFoundError: No module named 'config.BluePrint'`.
# `python -m pytest` (or `PYTHONPATH=. pytest`) fixes it. Always run from the repo root.
python -m pytest tests/core/walletBackpack/chequeBook/test_cheque_mgmt.py -q      # one file
python -m pytest tests/core/ -q                                                   # all unit tests (local mock EVM, no RPC needed)
python -m pytest tests/core/agent/test_agent_batch_actions.py::test_batch_create_and_pay_cheque -s   # single test
```

- Default `--fork=local` uses an in-memory boa EVM with mock tokens — **no RPC/keys needed** (the dummy env vars above are only to satisfy the import). Always run from the repo root via `python -m pytest` so imports (`config.BluePrint`, `constants`, `conf_utils`) resolve.
- Base-mainnet fork tests (`python -m pytest --fork=base`) are **Earn-Vault only** and need `anvil` (foundry) + real Alchemy/Etherscan keys. **No payment test runs against a real fork** — note this as a coverage limitation, not something you must run.
- Time travel through timelocks in tests via `boa.env.time_travel(blocks=N)`.

### Starter payment-suite command
Run or extend this focused suite before finalizing the report:

```bash
python -m pytest \
  tests/core/test_billing.py \
  tests/core/userWallet/test_user_wallet.py \
  tests/core/userWallet/test_user_wallet_config.py \
  tests/core/userWallet/test_user_wallet_owner_bypass.py \
  tests/core/userWallet/test_user_wallet_swap.py \
  tests/core/userWallet/test_action_data_provider.py \
  tests/core/walletBackpack/kernel/test_whitelist.py \
  tests/core/walletBackpack/paymaster/test_payee_mgmt.py \
  tests/core/walletBackpack/paymaster/test_payee_mgmt_validation.py \
  tests/core/walletBackpack/chequeBook/test_cheque_mgmt.py \
  tests/core/walletBackpack/chequeBook/test_cheque_mgmt_validation.py \
  tests/core/walletBackpack/sentinel/test_payee_validation.py \
  tests/core/walletBackpack/sentinel/test_cheque_validation.py \
  tests/core/walletBackpack/sentinel/test_manager_validation.py \
  tests/core/walletBackpack/sentinel/test_approved_yield_validation.py \
  tests/core/walletBackpack/highCommand/test_manager_mgmt.py \
  tests/core/walletBackpack/highCommand/test_manager_mgmt_val.py \
  tests/core/walletBackpack/migrator/test_migrate_config.py \
  tests/core/walletBackpack/migrator/test_migrate_funds.py \
  tests/core/agent/ \
  -q
```

If this is too slow, run the smallest relevant subset first, but the final report
must state exactly what was run and what was not run.

### Test-writing toolkit (use this to build PoCs)
`tests/conf_utils.py` has tuple-builders for every payment struct: `createChequeSettings`, `createCheque`, `createPayeeSettings`, `createPayeeLimits`, `createGlobalPayeeSettings`, `createManagerSettings`, `createManagerLimits`, `createTransferPerms`, `createWhitelistPerms`, plus helpers `set_live_cheque_settings` (handles pending+confirm), `set_user_instant_action_settings`, `fresh_user_wallet`, `filter_logs`. `tests/conf_mock.py` gives accounts (`bob`=owner, `alice`, `charlie`, `sally`, `whale`), `user_wallet`/`user_wallet_config`, `starter_agent` (AgentWrapper) + `starter_agent_sender` (AgentSenderGeneric), and mock ERC20s. `tests/conf_core.py` deploys the whole protocol (incl. all backpack modules) as session fixtures.

---

## 2. System model — read this before touching code

Underscore is a Base-native protocol of **programmable wallets**. Each user has two paired contracts:

- **`UserWallet`** (`contracts/core/userWallet/UserWallet.vy`) — holds all assets (ETH + ERC20 + ERC721).
- **`UserWalletConfig`** (`contracts/core/userWallet/UserWalletConfig.vy`) — holds all per-user settings/permissions and the authorization callbacks. Holds **no funds**.

**There is exactly ONE function through which discretionary funds leave a wallet: `UserWallet.transferFunds`** (`UserWallet.vy:144–183`). Everything you audit converges here. Its signature:

```vyper
@nonreentrant
@external
def transferFunds(_recipient, _asset=ETH, _amount=max, _isCheque=False, _isSpecialTx=False) -> (uint256, uint256)
```

The two booleans select the authorization branch. The three "money-out" paths the owner asked you to audit are **not** separate functions — they all flow through `transferFunds` and are distinguished downstream:

| Path | How it's triggered | Where it's authorized |
|---|---|---|
| **Whitelist** (trusted transfer, *unlimited*) | normal transfer (`_isCheque=False`) to a whitelisted recipient | `UserWalletConfig.checkRecipientLimitsAndUpdateData` → `Sentinel.isValidPayeeAndGetData` short-circuits to `True` |
| **Cheque** (one-off) | `transferFunds(..., _isCheque=True)` | `UserWalletConfig.validateCheque` → `Sentinel.isValidChequeAndGetData` (burns the cheque) |
| **Payee** (recurring/pull) | normal transfer to a registered payee | `checkRecipientLimitsAndUpdateData` → `Sentinel.isValidPayeeAndGetData` (per-tx/period/lifetime caps) |

**Two independent gates must BOTH pass for every non-special transfer — keep this straight, it is the core invariant:** **(1) signer authorization** — may `msg.sender` move funds at all (the owner *if* `GlobalManagerSettings.canOwnerManage`, or a manager within its limits, or the billing address)? **(2) recipient classification** — is the recipient whitelisted, a registered payee within caps, or the holder of a valid active cheque? Neither gate alone suffices: an authorized signer (including the owner) still cannot send to an unclassified recipient, and a whitelisted recipient still needs an authorized signer.

Plus a privileged escape hatch: **`_isSpecialTx=True`** — honored **only when `msg.sender == self.walletConfig`** (`UserWallet.vy:203–205`). It **skips recipient validation and manager post-tx limits entirely** and sends the full balance to the caller-chosen recipient. On this branch the **only** caller that passes `_isSpecialTx=True` into `transferFunds` is `UserWalletConfig.migrateFunds` (`UserWalletConfig.vy:875`); the code comment also cites legacy trial-fund clawback (`UserWallet.vy:202`). Two things are explicitly **not** this path and must not be conflated with it: (a) `Billing` transfers pass `_isSpecialTx=False` — its cheque/payee pulls go through normal validation; (b) `_isSpecialTx` is *also* a parameter on the separate `withdrawFromYield` function (used by `UserWalletConfig.preparePayment:897` to source funds from yield *before* a pull) — that is fund-sourcing, not egress. Treat the transfer special-tx path as the single most dangerous flag in the system, and audit `migrateFunds` as its sole gatekeeper.

### The transferFunds control flow (memorize this)
1. `_validateCanTransfer` (`UserWallet.vy:186`) — resolves asset, enforces **signer** authorization. Special-tx asserts `signer==walletConfig`; otherwise `_performPreActionTasks` → `UserWalletConfig.checkSignerPermissionsAndGetBundle` → **`ActionDataProvider`** → `Sentinel.canSignerPerformActionWithConfig`. Also checks `MissionControl.isLockedSigner`, frozen/eject state. **Whitelisted recipients are rewritten to `empty(address)` here**, which is how they bypass a manager's `allowedPayees`.
2. Clamp `amount = min(_amount, balance)` (`:159–162`), assert non-zero.
3. Compute `txUsdValue` via `Appraiser` (`:166`); **returns 0 in eject mode**.
4. **Recipient validation** (`:169–173`, skipped if `_isSpecialTx`): cheque burn OR payee/whitelist limits. Effects (cheque deactivation, period-data writes) happen **before** the transfer — good CEI ordering.
5. **The actual transfer** (`:176–179`): `send(_recipient, amount)` for ETH, else `IERC20(asset).transfer(...)`. **This is the only untrusted external call / reentrancy surface.**
6. `_performPostActionTasks` (`:181`) — **manager USD-limit checks run AFTER funds leave** (the tx reverts on breach, but verify the post-check can't be skipped).

### Actor / trust model
- **Owner** — the highest-privilege signer (subject to frozen/eject) and the only role that can add a *pending* whitelist entry. **Owner authority is not unconditional, in two ways an auditor must internalize:** (a) owner *signer*-authorization is short-circuited in `Sentinel._canSignerPerformAction` only when `GlobalManagerSettings.canOwnerManage` is true (it is true by default — `HighCommand.vy:972`); (b) even an authorized owner must still pass **recipient classification** — `Sentinel.isValidPayeeAndGetData` returns `False` for any recipient that is neither whitelisted nor a registered payee (there is **no** owner special-case; `Sentinel.vy:478–483`), so the owner **cannot** send to an arbitrary address. To pay a new address the owner must first whitelist it or register it as a payee. The tests reflect this: the `valid_transfer_recipient` fixture whitelists the recipient before transferring (`tests/core/userWallet/test_user_wallet.py:39`).
- **Manager** — a delegated signer (time-bounded `[startBlock, expiryBlock)`) configured via `HighCommand`. Capabilities are the **AND** of per-manager `ManagerSettings` and `GlobalManagerSettings`. Relevant flags: `transferPerms.canTransfer` (unlocks TRANSFER **and** PAY_CHEQUE), `transferPerms.canCreateCheque`, `transferPerms.allowedPayees` (recipient allowlist; empty = unrestricted; **whitelisted recipients bypass it**), `whitelistPerms.{canConfirm,canCancel,canRemove}` (never `canAdd`), `ManagerLimits` (USD per-tx/period/lifetime, tx count, cooldown; **0 = unlimited**).
- **Payee** — a recipient allowed to receive/pull within `PayeeSettings` caps. `canPull` gates payee-initiated pulls (enforced only in `Billing`, **not** in `Sentinel`).
- **Whitelist** — fully trusted recipient: **no caps at all**. Managed by `Kernel`.
- **AgentWrapper / AgentSender** — an off-chain server signs EIP-712 payloads; the wrapper acts as a registered manager. The signer is **not** the wallet owner.
- **Switchboard** (governance) — sets protocol-level flags (incl. all the new instant-action kill-switches), starter agents, locked signers, security signers.
- **Security signer** (`MissionControl.canPerformSecurityAction`) — can freeze, cancel pendings, remove managers/payees/whitelist (veto/defensive powers; cannot grant).
- **Migrator** — extremely privileged: moves the entire balance (special-tx) and clones config (managers/payees/whitelist/settings) into a sibling wallet.

### Instant-action flags & timelocks (new on this branch — central to the audit)
Re-enabling protections is timelocked; loosening limits is either timelocked or "instant" if **both** a protocol-level switchboard flag **and** the per-wallet `InstantActionSettings` flag are enabled. The flags: `canInstantAddManager` (HighCommand), `canInstantAddPayee` / `canInstantSetGlobalPayeeSettings` (Paymaster), `canInstantSetChequeSettings` (ChequeBook), `instantMigrationEnabled` (Migrator). Each settings setter runs a **"widening detector"** (`_isChequeSettingsWidening`, `_isGlobalPayeeSettingsWidening`, etc.) that decides instant-vs-timelock. **The correctness of these detectors is load-bearing** — a misclassified loosening bypasses the timelock.

---

## 3. Scope

### In scope (audit deeply)
| Contract | Path | Role |
|---|---|---|
| `UserWallet` | `contracts/core/userWallet/UserWallet.vy` | The `transferFunds` choke point |
| `UserWalletConfig` | `contracts/core/userWallet/UserWalletConfig.vy` | Per-user settings + authorization callbacks + migration/instant/timelock state |
| `ActionDataProvider` | `contracts/core/userWallet/ActionDataProvider.vy` | **NEW.** Centralized permission/registry/privileged-addr lookups (immutable) |
| `ChequeBook` | `contracts/core/walletBackpack/ChequeBook.vy` | Cheque lifecycle (create/replace/cancel) + cheque-settings governance |
| `Paymaster` | `contracts/core/walletBackpack/Paymaster.vy` | Payee (recurring) management |
| `Sentinel` | `contracts/core/walletBackpack/Sentinel.vy` | Stateless runtime validator for transfer/cheque/payee/manager limits |
| `Kernel` | `contracts/core/walletBackpack/Kernel.vy` | Whitelist lifecycle |
| `HighCommand` | `contracts/core/walletBackpack/HighCommand.vy` | Manager model + permission structs + `allowedPayees` |
| `Migrator` | `contracts/core/walletBackpack/Migrator.vy` | Wallet-to-wallet fund + config migration |
| `Hatchery` | `contracts/core/Hatchery.vy` | Wallet factory + default payment settings |
| `Billing` | `contracts/core/Billing.vy` | Recipient-initiated pulls (`pullPaymentAsPayee`, `pullPaymentAsCheque`) |
| Agent layer | `contracts/core/agent/{AgentWrapper,AgentSenderGeneric,AgentSenderSpecial,AgentSenderSpecialAdmin,*SigHelper,UserWalletSignatureHelper}.vy`, `contracts/modules/SigHelper.vy` | Off-chain-signed payment authorization |
| Data layer | `contracts/data/MissionControl.vy`, `contracts/data/Ledger.vy` | Global config + identity registries (`isLockedSigner`, `canPerformSecurityAction`, `isUserWallet`, `isRegisteredBackpackItem`) |
| Structs/ABI | `interfaces/{WalletStructs,WalletConfigStructs,ConfigStructs,Wallet,AgentWrapperInt}.vyi` | Struct layouts & the hard ABI cutover |
| Backpack/registry wiring | `contracts/registries/WalletBackpack.vy` (+ `contracts/registries/UndyHq.vy`) | Installs/rotates the backpack module addresses — including the trust-root `ActionDataProvider` — via a pending/confirm timelock |
| Governance hooks | `contracts/config/SwitchboardAlpha.vy`, `SwitchboardBravo.vy`, `SwitchboardCharlie.vy` | Set the protocol-level instant flags / locked signers / configs (timelock semantics). `SwitchboardCharlie` is not a primary payment authorizer, but scan it for payment-relevant manager, vault, and deployment side effects and state explicitly whether it matters. |
| Fee/loot adjacency | `contracts/core/LootDistributor.vy` plus `UserWallet._payYieldFee` / `_payTransactionFee` | Adjacent value-exit path. `transferFunds` does not directly call `_payTransactionFee` on this branch; fees are charged on swap/rewards and yield-profit paths. Review for unexpected drain or accounting interactions with payment safety. |

### Deployment & wiring (in scope — this branch is deploy-sensitive and not yet deployed)
This branch changed the **constructor signatures** of the payment modules (each gained instant-flag args), so the deploy/wiring layer must be audited, not just the contract logic:
- **Constructor wiring / migration scripts** under `migrations/base-mainnet/**` — confirm every module is deployed with the correct **current** constructor args and registered into `WalletBackpack`/`UndyHq` correctly. ⚠️ **Verified lead (confirm and likely flag as a deploy blocker):** the backpack deploy scripts are stale relative to the contracts. `HighCommand` now requires `_canInstantAddManager`, `Paymaster` requires `_canInstantAddPayee` + `_canInstantSetGlobalPayeeSettings`, `ChequeBook` requires `_canInstantSetChequeSettings`, and `Migrator` requires `_instantMigrationEnabled` — but both `migrations/base-mainnet/v1.1/0008-WalletBackpack.py` **and** the newer `2026032400-Payments.py` / `2026032500-Chequebook.py` deploy them **without** these args. A deploy from these scripts fails on arg count; worse, a partially-updated script could ship a module with an instant-flag default that doesn't match the **documented** cutover (see Production defaults below). Confirm the real production deploy path and the exact boolean each module ships with.
- **Specific migration files to read:** `migrations/base-mainnet/v1.1/2026032400-Payments.py`, `migrations/base-mainnet/v1.1/2026032500-Chequebook.py`, `migrations/base-mainnet/v1.1/0008-WalletBackpack.py`, `migrations/base-mainnet/v1.1/0002-MissionControl.py`, `migrations/base-mainnet/v1.1/0004-Switchboard.py`, `migrations/base-mainnet/v1.1/2026050100-SwitchboardCharlie.py`, `migrations/base-mainnet/v1.1/2025121100-SwitchboardCharlie.py`, and `migrations/base-mainnet/v1.1/2025120900-MissionControl.py`.
- **Production defaults** — verify the deployed `defaultInstantActionSettings` (Hatchery) and the protocol-level instant flags match the **documented release plan**, not any personal preference. Per `docs/deploy-checklist.md` ("Instant Wallet Action Runbook" / "Instant Defaults Cutover") and `docs/instant-action-model.md`, the accepted cutover is **all four user/protocol instant flags TRUE** (manager-add, payee-add, global-payee-settings, cheque-settings) **with `Migrator.instantMigrationEnabled` FALSE**, cut over **simultaneously**, with the per-call instant bool as the final opt-in gate. Your job is to (a) confirm the deploy wires exactly that posture (no flag accidentally inverted), and (b) **explicitly audit and assess the residual risk** of shipping these all-true — it removes the key-action timelock on fresh wallets, so a compromised owner key can act instantly. Treat it as a documented risk to assess and confirm, **not** a misconfiguration to "fix." Cross-check `config/Defaults*.vy`, `config/BluePrint.py` PARAMS, and `tests/scripts/test_production_params.py`.
- **ABI / SDK regeneration (hard cutover)** — the branch removed `canPayOwner` / `WhitelistPerms.canAddPending` / `TransferPerms.canAddPendingPayee` / `PendingPayee`. Any off-chain encoder (dapp, multisig UI, bot, script) still using the old struct layout will revert. Confirm all generated ABIs/SDKs were regenerated (see `docs/user-wallet-payment-security.md`, "Removed Pending-Payee Fields").

### Out of scope (note, but don't deep-audit unless a payment path depends on it)
DEX/yield "lego" adapters (`contracts/legos/**`), Earn/Levg vaults (`contracts/vaults/**`), and `Appraiser`/pricing internals (treat as a trusted oracle, but DO flag where a manipulated/zero/stale USD value weakens a cap). Fee/loot accounting is only in scope as the adjacent value-exit surface described above.

### Required reading (protocol's own security notes)
- `docs/user-wallet-payment-security.md` — the intended recipient policy, role separation, and explicitly-deferred items (e.g. "same-block replacement residual remains deferred"). **Cross-check every claim here against the code; a divergence is a finding.**
- `docs/instant-action-model.md`, `docs/mutability-policy.md`, `docs/user-wallet-config-byte-budget.md`, `docs/deploy-checklist.md`.

---

## 4. What changed on this branch (focus your energy on new code)

The branch is a large hardening/refactor of all three money-exit paths. Start here:

```bash
git -C /Users/wigglez/dev/underscore-protocol log --oneline master..cheque-enhance
git -C /Users/wigglez/dev/underscore-protocol diff --stat master...cheque-enhance -- \
  contracts/core/userWallet contracts/core/walletBackpack contracts/core/Hatchery.vy \
  contracts/core/agent contracts/core/Billing.vy contracts/data interfaces
# Then read the full hunks for the high-churn files below.

# SECOND diff — the deployment / config / registry / ABI surface added to scope in §3.
# This is a MUCH larger surface (≈ 43 files / ~12k insertions vs the 25 / ~3.8k above),
# so skim it for payment-relevant wiring rather than reading every hunk:
git -C /Users/wigglez/dev/underscore-protocol diff --stat master...cheque-enhance -- \
  contracts/config contracts/registries migrations scripts/abis config
```

Highest-churn / highest-risk changes (the diff above currently reports ≈ +3,800 / −1,200 across these files — re-run it for exact figures):
1. **`ActionDataProvider.vy` is brand new** — the signer-permission assertion, `isLockedSigner` check, billing bypass, whitelist→empty recipient rewrite, and all privileged-address/registry lookups were **extracted out of `UserWalletConfig`** into this immutable helper. It cannot be rotated per-wallet. A bug here mis-authorizes everything.
2. **The three validators changed `bool` → `void`.** `transferFunds` went from `assert extcall WalletConfig(...).validateCheque(...)` to a **bare** `extcall ...` — they now `assert` internally. **Verify every reject path reverts** (a path that returns without reverting = unauthorized transfer).
3. **Sentinel now returns a third bool** (`didPay` / `didUpdate`). `UserWalletConfig` persists period data / burns the cheque / decrements `numActiveCheques` based on it instead of the old `lastTxBlock != 0` heuristic. **Verify `didPay`/`didUpdate` is always true exactly when state must change** (false-positive ⇒ double-pull; false-negative ⇒ cap bypass).
4. **Manager pending-payee flow deleted entirely** (`addPendingPayee`/`canAddPendingPayee`/`PendingPayee` removed; also `canPayOwner`, `WhitelistPerms.canAddPending`). This is a **hard ABI cutover** — old struct encoders revert. Hunt for any lingering reference or struct-offset assumption.
5. **Instant-action subsystem + widening detectors** added across ChequeBook/Paymaster/HighCommand/Migrator + per-wallet `InstantActionSettings` with asymmetric timelock.
6. **Mutual-exclusion invariants** added: an address can't be simultaneously manager/payee/whitelisted/active-cheque-recipient/privileged. Added in `addManager`/`addPayee`/`createCheque`/`addPendingWhitelistAddr`/`confirmWhitelistAddr` and the migrator. **Check they're enforced symmetrically and at both add- and confirm-time.**
7. **PAY_CHEQUE now subject to manager `allowedPayees`** (`Sentinel.vy:184`, changed from `TRANSFER` only to `TRANSFER | PAY_CHEQUE`).
8. **Migrator** gained a pending-migration timelock, `instantMigrationEnabled`, switchboard-as-caller, `@nonreentrant`, active-cheque-blocks-migration, and per-address collision validation (`_isValidMigratorConfigAddr`).
9. **Agent layer**: signed hashes now bind an **action-code byte + `_agentWrapper`** (replay/cross-action hardening); first-class `createCheque`/`payCheque`/`createAndPayCheque` with a `creationBlock` version guard; **new `AgentSenderSpecialAdmin.vy`** (cheque/whitelist admin workflows).
10. **Hatchery** became the central validator/seeder of new-wallet defaults (starter-agent types, `defaultInstantActionSettings`).

---

## 5. Threat model — concrete leads to investigate

Each lead below is a *hypothesis to confirm or refute*, with a `file:line` starting point. They came from a structural mapping pass; treat them as starting points, not a complete list. **Find more.**

### 5.1 The `transferFunds` choke point & `_isSpecialTx`
- **Special-tx authorization bypass.** `_isSpecialTx=True` skips recipient validation *and* manager post-tx limits, gated only by `msg.sender==walletConfig` (`UserWallet.vy:169,203–205; :1037`). Enumerate **every** `UserWalletConfig` path that calls `wallet.transferFunds(..., _isSpecialTx=True)` (notably `migrateFunds`, `UserWalletConfig.vy:870`) and confirm each independently authorizes recipient + amount. Any non-owner-reachable path that forwards special-tx = arbitrary drain.
- **`migrateFunds` destination not bound to `pendingMigration.toWallet`.** `migrateFunds(_toWallet, _asset)` sends `max` to an arbitrary `_toWallet`, gated only on `msg.sender==migrator`, and does **not** assert `_toWallet == pendingMigration.toWallet` here (`UserWalletConfig.vy:870–876`). All destination/timelock enforcement is assumed to live in `Migrator`. Verify there is no `Migrator` path that calls it with an attacker address.
- **Billing signer bypass.** `if ad.signer == ad.billing: return ad` skips both the lock check and Sentinel (`ActionDataProvider.vy:156–157`). Confirm `Billing` can't be induced to call `transferFunds` with an attacker-chosen recipient and `BILLING_ID` can't be spoofed.
- **Eject-mode zeroes `txUsdValue`**, disabling USD caps (`UserWallet.vy:~1311`). Cheques reject `txUsdValue==0`, but confirm payee USD caps aren't silently skipped, and that eject mode truly restricts to owner-only.
- **Post-tx manager limit runs after funds leave** (`:181` then `_performPostActionTasks`). Confirm no reentrancy/`_isSpecialTx` path skips it while funds still move.
- **Fee-on-transfer / rebasing tokens:** caps are computed on the clamped amount but the recipient may receive a different amount (`:159–163`). Check accounting tolerance.

### 5.2 Cheques (`ChequeBook` + `validateCheque` + `Sentinel.isValidChequeAndGetData`)
- **`validateCheque` doesn't assert `cheque.recipient == _recipient` or `cheque.active`** before handing to Sentinel (`UserWalletConfig.vy:524–563`). Confirm `Sentinel.isValidChequeAndGetData` (`:648–724`) enforces recipient/active/asset/exact-amount consistency — if not, funds could be diverted.
- **`didPay` consistency** — the new burn guard. If Sentinel ever returns `isValidCheque=True, didPay=False`, the cheque pays **without being burned** (double-pull). (`Sentinel.vy:700–724`, `UserWalletConfig.vy:558–563`).
- **Same-block replacement residual** (docs explicitly defer this). Replacing your own cheque skips the active-count cap but **still bumps the per-period created counters** (`ChequeBook.vy:470–472, 544–549`). Can a creator grief period caps, or can counters drift from the true active set?
- **Replace authorization uses creator identity, not current standing** — `msg.sender == existingCreator` (`ChequeBook.vy:232–233`). Can a deactivated/expired manager still replace (mutate recipient/asset/amount/flags of) a cheque they created?
- **Creation-time vs pay-time USD divergence.** `createCheque` calls a **non-view** `Appraiser.updatePriceAndGetUsdValue` (`ChequeBook.vy:237`) to set the unlock delay (expensive cheques get `max(expensiveDelayBlocks, timeLock)`); pay-time re-values independently. A manipulated/stale price at creation could make a high-value cheque unlock instantly.
- **Widening detector completeness** — `_isChequeSettingsWidening` and helpers (`ChequeBook.vy:~868–965`). Check every `ChequeSettings` field is covered and the 0-sentinel (`new==0` = uncapped = widening) and cooldown-direction semantics are right.
- **`canBePulled` enforced only in `Billing`, not in `Sentinel`/`validateCheque`.** Confirm no path lets a recipient trigger `transferFunds(_isCheque=True)` for a non-pullable cheque without going through `Billing`'s gate (i.e. the signer-gate truly blocks the recipient from self-signing a PAY_CHEQUE).
- **Pay-cooldown first-cheque guard** (`payCooldownBlocks != 0 AND lastChequePaidBlock != 0`, `Sentinel.vy:703`). Period reset (`_getLatestChequeData`) zeroes paid counts but **not** `lastChequePaidBlock` — confirm cooldown behaves correctly across period boundaries and the guard doesn't re-open a per-period bypass.

### 5.3 Payees (`Paymaster` + `checkRecipientLimitsAndUpdateData` + `Sentinel.isValidPayeeAndGetData`)
- **Instant-add bypasses start delay** — `_shouldStartInstantly` overwrites `startBlock=block.number` *after* validation assumed a delayed start (`Paymaster.vy:455–472`). A high-cap pullable payee becomes live in the add block.
- **`updatePayee` has no timelock/widening guard** (`Paymaster.vy:500–561`) — instant cap raise / `canPull` flip. Intended? Any wallet-level invariant it can exceed?
- **Unit-cap gap on non-primary assets** — `Sentinel` applies unit limits only when `asset == primaryAsset` (`Sentinel.vy:~546`). A `onlyPrimaryAsset=False` payee with only unit limits (no USD limits) could pull a *different* asset capped only by tx-count.
- **`failOnZeroPrice` only required when USD limits are set** (`Paymaster.vy:~984`). A unit-only payee with a broken/zero oracle still transacts.
- **`didUpdate` persistence gating** — same risk class as cheque `didPay`: if Sentinel returns `canPay=True, didUpdate=False` on a budget-consuming path, period/cooldown counters never advance ⇒ limit bypass via repeated pulls (`UserWalletConfig.vy:498–516`).
- **Registered user wallets are valid payees but invalid managers** (asymmetry: `Paymaster._isPrivilegedUndyAddr` does NOT call `isUserWallet`, HighCommand's does). Confirm this can't be abused for wallet-to-wallet recursive payee drains.

### 5.4 Whitelist (`Kernel` + `UserWalletConfig` + `Sentinel` + `ActionDataProvider`)
- **Whitelisting grants UNLIMITED uncapped transfers** in any asset. The *entire* safety is the owner-only add + timelock + conflict checks. Treat any way to get an address whitelisted (or to bypass the timelock) as critical.
- **Migrator timelock bypass** — `addWhitelistAddrViaMigrator` registers a whitelist entry with **no timelock**, gated only on `msg.sender==migrator` (`UserWalletConfig.vy:606–611`). Newly hardened (non-empty, not-privileged, not-already-payee/manager/cheque) — verify the hardening is complete and the migrator can only reach it via a validated clone.
- **Manager confirm → unrestricted send chain.** A manager with `whitelistPerms.canConfirm` can finalize an owner-initiated pending whitelist entry, and whitelisted recipients bypass `allowedPayees` (`Kernel.vy:130–149`; `ActionDataProvider.vy:161–163`). Is this the intended trust boundary?
- **`currentOwner` staleness** — `confirmWhitelistAddr` requires `pending.currentOwner == owner`, but the config-layer confirm does **not** re-check it (only Kernel does). Check ownership-change interleavings (`Kernel.vy:139` vs `UserWalletConfig.vy:592–599`).
- **Strict-confirm revert vs silent-remove asymmetry** — confirm hard-reverts if already whitelisted; remove returns silently if absent (`UserWalletConfig.vy:617–646`). Confirm legitimate flows don't brick and the asymmetry isn't exploitable.
- **Cross-role collision symmetry** — the branch added checks that a whitelist entry isn't a manager/payee/cheque/privileged addr. Verify the reverse is also enforced everywhere (can an already-whitelisted address later become a payee/manager, re-introducing the conflict?).

### 5.5 Managers (`HighCommand`)
- **`allowedPayees` whitelist bypass** — a manager restricted to a small `allowedPayees` list can still send to **any** owner-whitelisted address (recipient rewritten to empty; `Sentinel.vy:183–186`). Intended? Combined with manager-confirm-whitelist (5.4), can a manager self-expand its reachable recipients?
- **`updateManager` skips the add-time exclusivity checks** (payee/whitelist/active-cheque). If an address became a payee after being added as a manager, `updateManager` won't catch it (`HighCommand.vy:272–329`). Also `_newManager` is passed as `empty()` on update, so the "manager can't be its own `allowedPayee`" check is skipped — a manager could add itself to its own `allowedPayees` via update.
- **Instant-add manager skips the start delay** (`HighCommand.vy:221–237`). Check the clamped expiry math can't underflow / produce a non-expiring window.
- **`neuterStarterAgent` leaves `canClaimLoot=True` + zero window.** Verify `startBlock==0/expiryBlock==0` is truly inert in **every** consumer — note `ChequeBook._canCreateCheque` special-cases `expiryBlock != 0` (`:347–350`); make sure a neutered agent still can't create cheques.
- **0 = unlimited** everywhere in `ManagerLimits`. A fully-permissioned manager with empty limits + empty `allowedPayees` + `canTransfer` can drain to any whitelisted address with no USD cap. Confirm this requires explicit owner action.

### 5.6 Agent layer (`AgentWrapper` + `AgentSender*` + sig helpers)
- **Independent per-sender nonce spaces** — `currentNonce` lives separately in Generic/Special/SpecialAdmin. Confirm the EIP-712 domain separator (`verifyingContract = sender address`) truly prevents cross-sender replay of an identically-encoded payload, and no helper treats the nonce as global.
- **Hash-builder vs verifier drift** — `UserWalletSignatureHelper`/`AgentSenderSpecialSigHelper` must `abi_encode` **byte-identically** to the AgentSender (incl. the action-code byte and `_agentWrapper`). The branch rewrote all of these. Any mismatch could let a hash for one action validate another. Diff the encodings action-by-action.
- **`createCheque` (action 5) flag freedom** — a signed payload can set `canManagerPay=True, unlock=0, expiry=0` (an instantly-payable manager cheque). Confirm downstream Sentinel/ChequeBook caps actually bound it.
- **`harvestAndIssueCheque` (action 106) amount is NOT capped to proceeds** (its own docstring says so). Check an over-sized cheque can't drain unintended assets given pay-time `min(amount, balance)`.
- **Batch (one nonce, many money-out actions)** — `performBatchActions` consumes one nonce for ≤15 instructions including multiple transfers/cheque-pays. Verify `_assertChequeVersionMatches` (`instruction.amount2` as expected creationBlock) can't be bypassed with `amount2=0`, and create-and-pay + pay can't double-spend a cheque in one block.
- **Signature `_verify` is duplicated across all three senders** — check low-s bound, `v` normalization, and that a failed `ecrecover` (returns `0x0`) can never equal `owner`. Watch for drift between copies.
- **`addSender` is the trust root** (Switchboard-only). Check the swap-remove (index 0 reserved) can't leave a ghost approved sender, and whether missing events hurt monitoring.
- **One wrapper = one manager identity across all its wallets** — per-wallet manager limits must still bind per-wallet despite the shared wrapper. Check `removeSelfAsManager` (action 70) front-running.

### 5.7 Migration (`Migrator`)
- **Special-tx drain** (see 5.1) — migrated transfers skip all recipient/limit/whitelist/cheque checks; the only constraint is `recipient==_toWallet` (same owner + same `groupId`). Probe every assumption that makes `_toWallet` a legitimate sibling.
- **`instantMigrationEnabled` removes the timelock entirely** (`Migrator.vy:530–532`; switchboard-set). A compromised/too-fast enable defeats the migration timelock and the owner's cancel window.
- **Switchboard-as-caller widens authority beyond the owner** (`_canExecuteMigration`, `Migrator.vy:484`). Combined with the instant flag, can funds move between a victim's two wallets without the owner initiating?
- **Verbatim clone of `PayeeSettings`/`ManagerSettings` without re-running per-entry validators** — only identity/collision checks run (`Migrator.vy:371–405`). Migrated caps/flags carry over; if the source had a higher timelock or looser global config, the destination may end up over-permissioned.
- **`applyMigratedConfigSettings` bypasses all per-setter timelocks** including instant-flag re-enables (`UserWalletConfig.vy:368–389`). Confirm it's only ever called on a freshly-created, empty destination and source settings are trustworthy.
- **`_isValidMigratorConfigAddr` completeness** — for payee/whitelist slots (`isManagerSlot=False`) it skips the `isUserWallet` check (`Migrator.vy:688–710`). Can a wallet/contract be smuggled into a role that later receives normal transfers?
- **`cancelPendingMigration`** — any security-action holder can cancel any wallet's pending migration (`Migrator.vy:197–217`). DoS/griefing surface?

### 5.8 Creation & data layer (`Hatchery`, `MissionControl`, `Ledger`)
- **All-True instant-action defaults** are injected verbatim into every new wallet (`Hatchery.vy:253` → `UserWalletConfig.vy:210`; test fixtures ship `(True,True,True,True)`). The documented release plan ships these all-true (except `Migrator.instantMigrationEnabled`); see §3 "Production defaults." This is an *accepted* posture, so the task is to (a) confirm the deploy matches it and (b) assess the residual risk it carries (no key-action timelock on a fresh wallet ⇒ a compromised owner key can add a manager/payee or widen cheque/payee settings instantly) — not to treat it as a bug.
- **Starter agent installed as `managers[1]` with `canTransfer=True, canCreateCheque=True`** (`HighCommand._createHappyManagerDefaults`). Verify the starter agent can't move funds beyond intent and its expiry is enforced.
- **Validation-vs-construction divergence** — `Hatchery` validates defaults with `isValidUserWalletManagerDefaults/PayeeDefaults/ChequeDefaults` but constructs them via separate `createDefault*` functions. Confirm validated values == written values, and that "0 = no limit" defaults are acceptable for fresh wallets.
- **Config defaults are snapshotted at creation, not live-referenced** — tightening a `MissionControl` global does **not** protect already-deployed wallets. Make sure no part of the system (or the audit) assumes global config is a retroactive safety lever.
- **`isLockedSigner` bypasses** — skipped for billing and for special-tx (`ActionDataProvider.vy:155–177`). Confirm a locked owner/manager truly can't still move funds via those routes.

### 5.9 Cross-cutting / Vyper-specific
- **Reentrancy:** the global `@nonreentrant` lock in Vyper 0.4.x is shared across all `@nonreentrant` functions in a *contract*. Confirm every state-mutating external entrypoint that touches payment state holds it, and reason about **cross-contract** reentrancy (recipient → `Billing`/`Kernel`/`ChequeBook` while a transfer is mid-flight). ERC777/hook tokens and malicious registered ERC20s are in-scope as the untrusted edge.
- **Index bookkeeping:** 1-based indices with index 0 reserved (`numManagers`/`numPayees`/`numWhitelisted` init to 1). Check swap-and-pop removals don't leave stale `indexOf` entries or self-referential slots; check `numActiveCheques` underflow/desync.
- **Struct/ABI cutover:** the removed fields (`canPayOwner`, `canAddPending`, `canAddPendingPayee`, `PendingPayee`) — hunt for any place still reading those offsets, any mock/test/script encoding the old layout, and any external-facing struct returned to off-chain callers.
- **`@view`/`@pure` correctness:** the validators are stateless; confirm none secretly depend on caller-supplied config that an attacker could forge (production uses the trusted `*WithConfig`/`*AndGetData` variants — make sure the self-fetching convenience variants aren't reachable on a fund-moving path).
- **Integer/USD math:** rounding, truncation, and overflow in USD↔unit conversions and period accounting; boundary conditions at exactly `startBlock`/`expiryBlock`/`confirmBlock`/period rollover.

---

## 6. Invariants to verify (turn these into tests)

State each as a property and try to break it with a PoC test:

1. **No unauthorized egress.** Money leaves a wallet **only** via `transferFunds`, and only when **both** gates pass: an authorized **signer** (owner-with-`canOwnerManage`, or a manager within its limits, or billing) **and** a classified **recipient** (whitelisted, or a registered payee within caps, or the holder of a valid active cheque). Signer authority alone — even the owner's — is never sufficient; the recipient must be classified. The sole exception is the walletConfig-only special-tx (migration) path.
2. **Special-tx is walletConfig-only.** No path reaches `transferFunds(_isSpecialTx=True)` except via `UserWalletConfig.migrateFunds` (the only current caller) acting on a properly authorized migration — **not** Billing, which transfers with `_isSpecialTx=False`. Treat any other transfer-special path you discover as a finding to scrutinize.
3. **Cheque single-use.** A cheque pays at most once; on payment it is deactivated and `numActiveCheques` decremented, before funds move.
4. **Caps bind.** Payee per-tx/per-period/lifetime/cooldown/tx-count and manager USD limits cannot be exceeded across any sequence of transfers, pulls, batches, period rollovers, or replacements (except for whitelisted recipients, which are intentionally uncapped).
5. **Timelocks bind.** Re-enabling a disabled instant flag, lowering the timelock, widening cheque/payee/manager settings, adding a whitelist entry, and migrating all wait the required delay — unless the documented instant path (both protocol + wallet flag) is explicitly enabled.
6. **Role exclusivity.** An address is never simultaneously manager + payee + whitelisted + active-cheque-recipient, and privileged protocol/backpack addresses are none of these, at both set-time and confirm-time.
7. **Whitelist gate.** Only the owner can create a pending whitelist entry; confirm requires the timelock elapsed and the same owner.
8. **Signature soundness.** A signed agent payload authorizes exactly one action, on one wallet, via one wrapper, once (no replay across senders, actions, wallets, or nonces; no malleability).
9. **Migration safety.** Migration moves funds only to a same-owner, same-groupId, ledger-registered sibling; it cannot inject a malicious recipient/manager/payee/whitelist into the destination or carry over over-permissioned settings.
10. **Docs match code.** Every assertion in `docs/user-wallet-payment-security.md` holds in the code.

---

## 7. Methodology (suggested order)

1. **Read** `docs/user-wallet-payment-security.md` + this prompt's §2–§4. Then read `UserWallet.transferFunds` and `_validateCanTransfer` top to bottom.
2. **Read the branch diff** (`§4` commands) for the high-churn files; the newest code has the highest bug density.
3. **Trace each money-exit path end-to-end** with the `file:line` map in §3/§5, following every cross-contract call. Build a per-path call graph and note every authorization check and every state write.
4. **Per component, work the §5 leads** — confirm or refute each, then ask "what else?". Pay special attention to the `bool→void` validators, the `didPay/didUpdate` flags, the widening detectors, the instant-action flags, and the special-tx/migrator paths.
5. **Write PoC tests** for anything credible (use the §1 toolkit). A failing test that demonstrates unauthorized egress / a bypassed cap or timelock / a double-pull is the strongest possible finding. Note where existing tests are thin: there are **no adversarial-token tests** (reentrant / fee-on-transfer / non-standard-return ERC20) on the transfer edge, **no reentrancy harness** on `transferFunds`, and **no fuzz/property coverage** of cap/period/USD arithmetic (hypothesis is available but used only for vault tests). (The payee *pull* path **is** already covered end-to-end in `tests/core/test_billing.py` — `pullPaymentAsPayee` with real balance movement, vault withdrawal, partial funds, and eject mode — so don't re-prove that; aim the new tests at the adversarial gaps above.) These are prime spots to write new tests.
6. **Adversarially self-review** each finding before reporting: can you actually reach the vulnerable state given the access control? Is there an upstream check that already prevents it? Downgrade or drop findings you can't substantiate, but keep genuinely uncertain ones flagged as such.

---

## 8. Deliverable

Produce a written audit report. For **each finding**:

- **Title** — one line.
- **Severity** — Critical / High / Medium / Low / Informational (rubric below). State your confidence (Confirmed via PoC / Likely / Speculative).
- **Location** — `contract:line` (and the call path).
- **Description** — the flaw, precisely.
- **Impact** — what an attacker gains; which invariant (§6) breaks; whose funds and how much.
- **Proof of Concept** — a test (preferred) or a concrete step-by-step exploit scenario.
- **Recommendation** — the minimal fix.

**Severity rubric:**
- **Critical** — direct theft/loss of user funds, or unauthorized egress with no meaningful precondition.
- **High** — fund loss requiring a specific (but reachable) precondition; cap/timelock/whitelist bypass; signature replay.
- **Medium** — limited loss, griefing/DoS of a user's funds or controls, or a bypass needing an unusual config.
- **Low** — minor deviations, defense-in-depth gaps, unsafe defaults.
- **Informational** — code quality, doc/code divergence with no direct security impact, test-coverage gaps.

Close with: (a) an explicit **deployment recommendation** — exactly one of **Block deploy** / **Safe to deploy after fixes** / **Safe to deploy**. For **Block deploy** and **Safe to deploy after fixes**, list the named blocking findings; for **Safe to deploy**, list the residual risks and the assumptions it rests on (e.g. the accepted all-true instant-default posture). (b) an **executive summary** (overall posture, count by severity); (c) the **systemic risks** (e.g. the trust placed in `ActionDataProvider` / `Migrator` / the agent server key, the all-True instant defaults, and the deploy-script/constructor wiring); and (d) a prioritized list of **test-coverage gaps** to close before deployment. If you find **nothing** in a component after a genuine effort, say so explicitly and describe what you checked — negative results are valuable.

Do not invent findings to pad the report; a small number of real, well-substantiated issues beats a long list of speculation. But do not stop early — be exhaustive across all in-scope contracts.
