# Payments Audit Master Prompt

Maintainer note: this file is the authoritative payment-audit handoff. It
supersedes the prior canonical prompt and the source drafts
`docs/payments-audit1.md` / `docs/payments-audit2.md`.

> Copy everything after the next horizontal rule into a fresh audit agent.

---

## 0. Mission

You are a senior smart-contract security auditor. Perform a full, adversarial
audit of the Underscore Protocol payment subsystem on the `cheque-enhance`
branch from `/Users/wigglez/dev/underscore-protocol`.

This prompt is self-contained as an audit brief, but it intentionally directs
you to in-repo docs that must be read and cross-checked. It assumes you have
read access to this repository, can run shell commands, and may write temporary
tests or scripts to prove findings.

Audit every path where value can leave a user wallet through the payment model.
The core choke point is `UserWallet.transferFunds`; the three primary payment
categories are:

- Whitelist / trusted transfers.
- Cheques / one-off payments.
- Payees / recurring or pull payments.

Also inventory adjacent non-payment egress such as migration, fees/loot,
yield-sourcing, and NFT recovery (`UserWallet.recoverNft`,
`UserWallet.vy:1344`) so the final report can explicitly classify each as
in-scope payment risk, adjacent value-exit risk, or out of scope.

Find bugs, exploits, permission bypasses, logic errors, unsafe defaults, missing
tests, and weak assumptions before this branch is deployed. Assume a motivated
attacker who chains weak primitives, timing edges, stale pending state, rounding,
zero or stale prices, reentrancy, role collisions, signature confusion, batch
call behavior, and ABI or struct mismatches.

This is a review and analysis task, not a remediation task. Do not modify
protocol contracts unless explicitly asked later. You may and should write
small throwaway tests or scripts to prove or disprove suspected issues. Bias
toward surfacing plausible issues, but do not invent findings to pad the report.

Funds are at stake. Do not say the payment system is safe unless that claim is
defended by both code-path analysis and test evidence.

---

## 1. Start Here

Run these commands before making conclusions:

```bash
cd /Users/wigglez/dev/underscore-protocol
git status --short --branch
git fetch origin
git branch --show-current
git diff --stat origin/master...HEAD
```

Expected branch: `cheque-enhance`. If `git branch --show-current` is not
`cheque-enhance`, do not silently audit another branch. Either check out
`cheque-enhance` only if doing so will not clobber local work, or stop and report
that the audit is not running on the intended code.

Repository facts:

- Language: Vyper `0.4.3`.
- Test harness: `titanoboa` + `pytest`; `hypothesis` is available but not used
  for payments today.
- Contracts: `contracts/**/*.vy`.
- Interfaces and structs: `interfaces/*.vyi`; treat these as the source of
  truth for struct layout and ABI cutover.
- There is no `pytest.ini`, `pyproject.toml`, or Makefile test entry point. Test
  configuration is in `tests/conftest.py` and `tests/conf_*.py`.
- All `file:line` anchors are indicative snapshots from `cheque-enhance` at
  synthesis time. Re-confirm current line numbers before citing them in the
  final report.

These facts are expectations for the current branch, not permission to ignore
drift. If a path, version, command, or required doc has changed, document the
drift in the report, adjust coverage intentionally, and log a missing required
doc as Informational before proceeding.

Test setup gotchas:

```bash
cd /Users/wigglez/dev/underscore-protocol
export ETHERSCAN_API_KEY=dummy
export WEB3_ALCHEMY_API_KEY=dummy
```

`tests/conf_env.py` reads environment variables at import time, so even local
mock-EVM test collection can fail if these are unset.

Use `python -m pytest`, not bare `pytest`, unless you explicitly set
`PYTHONPATH=.`. Bare `pytest` may fail to resolve imports such as
`config.BluePrint`, `constants`, and `conf_utils`.

Local tests:

```bash
python -m pytest tests/core/walletBackpack/chequeBook/test_cheque_mgmt.py -q
python -m pytest tests/core/agent/test_agent_batch_actions.py::test_batch_create_and_pay_cheque -s
python -m pytest tests/core/ -q
```

Default `--fork=local` uses an in-memory boa EVM with mock tokens and does not
need RPC keys. Base-mainnet fork tests (`python -m pytest --fork=base`) are
Earn-Vault only and need `anvil`, Alchemy keys, and Etherscan keys. No payment
test currently runs against a real fork; note this as a coverage limitation, not
as something you must run.

Use `boa.env.time_travel(blocks=N)` for timelock tests.

Starter payment suite to run or extend before finalizing:

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

If the full suite is too slow, run the smallest relevant subset first. The final
report must state exactly what was run, what passed or failed, and what was not
run.

Useful test helpers:

- `tests/conf_utils.py`: `createChequeSettings`, `createCheque`,
  `createPayeeSettings`, `createPayeeLimits`, `createGlobalPayeeSettings`,
  `createManagerSettings`, `createManagerLimits`, `createTransferPerms`,
  `createWhitelistPerms`, `set_live_cheque_settings`,
  `set_user_instant_action_settings`, `fresh_user_wallet`, `filter_logs`.
- `tests/conf_mock.py`: accounts (`bob` owner, `alice`, `charlie`, `sally`,
  `whale`), `user_wallet`, `user_wallet_config`, `starter_agent`,
  `starter_agent_sender`, and mock ERC20s.
- `tests/conf_core.py`: deploys the protocol and backpack modules as session
  fixtures.

---

## 2. System Model

Underscore is a Base-native protocol of programmable wallets. Each user has two
paired contracts:

- `UserWallet` (`contracts/core/userWallet/UserWallet.vy`): holds ETH, ERC20s,
  ERC721s, and yield positions.
- `UserWalletConfig` (`contracts/core/userWallet/UserWalletConfig.vy`): holds
  per-user settings, roles, permissions, limits, pending actions, and
  authorization callbacks. It holds no funds.

There is exactly one discretionary payment egress function
(`contracts/core/userWallet/UserWallet.vy:146-152` as of this branch):

```vyper
@nonreentrant
@external
def transferFunds(_recipient, _asset=ETH, _amount=max, _isCheque=False, _isSpecialTx=False) -> (uint256, uint256)
```

All normal payment paths converge here:

| Path | Trigger | Authorization |
| --- | --- | --- |
| Whitelist | `transferFunds(..., _isCheque=False)` to a whitelisted recipient | `UserWalletConfig.checkRecipientLimitsAndUpdateData` -> `Sentinel.isValidPayeeAndGetData` short-circuits to valid |
| Cheque | `transferFunds(..., _isCheque=True)` | `UserWalletConfig.validateCheque` -> `Sentinel.isValidChequeAndGetData`; paying burns the cheque |
| Payee | `transferFunds(..., _isCheque=False)` to a registered payee | `checkRecipientLimitsAndUpdateData` -> `Sentinel.isValidPayeeAndGetData`; enforces payee limits |

Two independent gates must pass for every non-special transfer:

1. Signer authorization: may `msg.sender` move funds at all? Valid signers are
   the owner if `GlobalManagerSettings.canOwnerManage` allows it, a manager
   within its permissions and limits, or the billing address through its narrow
   bypass.
2. Recipient classification: is the recipient whitelisted, a registered payee
   within caps, or the holder of a valid active cheque?

Neither gate alone is enough. An authorized signer, including the owner, cannot
send to an arbitrary unclassified recipient. A whitelisted recipient still needs
an authorized signer.

Privileged exception:

- `_isSpecialTx=True` skips recipient validation and manager post-transfer
  limits. It should be honored only when `msg.sender == walletConfig`.
- The current expected transfer-special caller is
  `UserWalletConfig.migrateFunds`, which is used by `Migrator`.
- Billing pulls are not special transfers; they should call `transferFunds` with
  `_isSpecialTx=False`.
- `_isSpecialTx` is also a parameter on `withdrawFromYield`, used by
  `UserWalletConfig.preparePayment` to source funds before a pull. Do not
  confuse that fund-sourcing flag with the transfer egress special path.

`transferFunds` control flow to verify:

1. `_validateCanTransfer` resolves the asset and enforces signer authorization
   (`UserWallet.vy:187-211`). The special branch asserts the signer is
   `walletConfig` (`UserWallet.vy:203-205`); otherwise `_performPreActionTasks`
   calls `UserWalletConfig.checkSignerPermissionsAndGetBundle`
   (`UserWallet.vy:990`, `UserWalletConfig.vy:402-415`), which relies on
   `ActionDataProvider` and `Sentinel.canSignerPerformActionWithConfig`
   (`ActionDataProvider.vy:139-170`). This stage also checks locked signers,
   frozen state, and eject mode. Whitelisted recipients are rewritten to
   `empty(address)` here (`ActionDataProvider.vy:161-163`), which is how they
   bypass a manager's `allowedPayees`.
2. The amount is clamped to `min(_amount, balance)` and must be non-zero
   (`UserWallet.vy:158-164`).
3. `txUsdValue` is computed through `Appraiser` (`UserWallet.vy:166`); in eject
   mode it can be zero.
4. Recipient validation runs unless `_isSpecialTx=True` (`UserWallet.vy:169-173`).
   Cheque deactivation and payee period-data updates happen before the transfer
   (`UserWalletConfig.vy:475-516`, `UserWalletConfig.vy:525-563`).
5. The external transfer happens with native `send` or `IERC20(asset).transfer`
   (`UserWallet.vy:176-179`). This is the main untrusted external-call surface.
6. `_performPostActionTasks` runs manager USD-limit checks after funds leave
   (`UserWallet.vy:181`, `UserWallet.vy:1037-1047`). A revert should roll the
   transfer back, but verify the check cannot be skipped or bypassed.

---

## 3. Actors And Trust Boundaries

Model these actors separately:

- Wallet owner.
- Manager with full transfer permissions.
- Manager with partial transfer permissions.
- Manager with cheque-creation permission but not transfer permission.
- Manager with `allowedPayees` restrictions.
- Payee.
- Cheque recipient.
- Billing contract.
- Approved agent sender.
- Signature-based caller.
- Security actor.
- Migrator.
- Switchboard / governance.
- Malicious ERC20.
- Malicious yield lego or vault token.
- Stale pending-action beneficiary.
- Ordinary EOA or contract with no role.

Important trust-boundary details:

- Owner authority is not unconditional. The owner signer path depends on
  `GlobalManagerSettings.canOwnerManage`, which is true by default
  (`HighCommand.vy:972`), and the owner still needs recipient classification for
  normal transfers. `Sentinel.isValidPayeeAndGetData` has no owner special case:
  an unwhitelisted, unregistered recipient returns invalid
  (`Sentinel.vy:449-483`). The common test fixture whitelists the recipient
  before owner transfer (`tests/core/userWallet/test_user_wallet.py:39`).
- Managers are time-bounded by `[startBlock, expiryBlock)` and get the logical
  AND of per-manager settings and global manager settings. `0` in
  `ManagerLimits` means unlimited.
- `transferPerms.canTransfer` unlocks normal transfer and PAY_CHEQUE.
- `transferPerms.canCreateCheque` is separate from transfer authority.
- Empty `allowedPayees` means unrestricted; whitelisted recipients bypass
  `allowedPayees`.
- Payees can receive payments within settings and caps. `canPull` is enforced in
  `Billing`, not directly by `Sentinel`.
- Whitelisted recipients are fully trusted and uncapped.
- `AgentWrapper` and `AgentSender*` are off-chain signature paths. The wrapper
  acts as a registered manager; the signer is not the wallet owner.
- Security signers can freeze, cancel pending actions, and remove roles. They
  should not be able to grant new payment authority.
- Migrator is highly privileged because it can move full balances through the
  transfer-special path and clone config.

---

## 4. Instant Actions And Timelocks

The branch adds instant-action flags and widening detectors. This is central to
the audit.

Re-enabling protections is timelocked. Loosening limits is either timelocked or
"instant" only if all relevant gates are enabled:

- Protocol-level switchboard flag.
- Per-wallet `InstantActionSettings` flag.
- Per-call instant boolean.

Flags to audit:

- `canInstantAddManager` in `HighCommand` (`HighCommand.vy:139-151`,
  `HighCommand.vy:221-237`).
- `canInstantAddPayee` in `Paymaster` (`Paymaster.vy:186-193`,
  `Paymaster.vy:455-472`).
- `canInstantSetGlobalPayeeSettings` in `Paymaster` (`Paymaster.vy:186-193`,
  `Paymaster.vy:245-365`).
- `canInstantSetChequeSettings` in `ChequeBook` (`ChequeBook.vy:133-143`,
  `ChequeBook.vy:633-856`).
- `instantMigrationEnabled` in `Migrator` (`Migrator.vy:149-168`,
  `Migrator.vy:530-532`).

Each settings setter uses a widening detector such as
`_isChequeSettingsWidening` or `_isGlobalPayeeSettingsWidening`. The correctness
of these detectors is load-bearing. A misclassified loosening can bypass a
timelock.

The documented release posture is:

- All four user/protocol instant flags true for manager-add, payee-add,
  global-payee-settings, and cheque-settings.
- `Migrator.instantMigrationEnabled` false.
- The cutover happens simultaneously.
- The per-call instant bool is the final opt-in gate.

Treat this all-true posture as an accepted release decision to verify and assess,
not as an automatic bug. Explicitly evaluate the residual risk: on fresh wallets,
a compromised owner key can add a manager/payee or widen cheque/payee settings
instantly if all gates are enabled.

---

## 5. Primary Scope

Audit these deeply:

| Surface | Files | Focus |
| --- | --- | --- |
| User wallet egress | `contracts/core/userWallet/UserWallet.vy` | `transferFunds`, `_validateCanTransfer`, pre-action and post-action tasks, fee helpers |
| Wallet config | `contracts/core/userWallet/UserWalletConfig.vy` | recipient validation, cheque validation, role storage, `preparePayment`, `migrateFunds`, `deregisterAsset` |
| Action data | `contracts/core/userWallet/ActionDataProvider.vy` | billing bypass, locked signer checks, whitelist recipient rewrite, manager bundle |
| Billing | `contracts/core/Billing.vy` | `pullPaymentAsCheque`, `pullPaymentAsPayee`, `_pullPayment`, yield withdrawal before pull |
| Whitelist | `contracts/core/walletBackpack/Kernel.vy` | add, confirm, cancel, remove, manager whitelist permissions, role collision checks |
| Payees | `contracts/core/walletBackpack/Paymaster.vy` | payee add/update/remove, global payee settings, `canPull`, instant and timelock paths |
| Cheques | `contracts/core/walletBackpack/ChequeBook.vy` | cheque create/replace/cancel, cheque settings, unlock and expiry, manager-created and manager-paid flags |
| Runtime validation | `contracts/core/walletBackpack/Sentinel.vy` | manager, payee, cheque, approved-yield validation |
| Managers | `contracts/core/walletBackpack/HighCommand.vy` | manager settings, transfer permissions, `allowedPayees`, role separation |
| Migration | `contracts/core/walletBackpack/Migrator.vy` | full-balance special transfer, config clone, pending migration and instant migration |
| Creation | `contracts/core/Hatchery.vy` | wallet factory, default payment settings, starter agent |
| Agent layer | `contracts/core/agent/{AgentWrapper,AgentSenderGeneric,AgentSenderSpecial,AgentSenderSpecialAdmin,*SigHelper,UserWalletSignatureHelper}.vy`, `contracts/modules/SigHelper.vy` | off-chain-signed authorization and batch behavior |
| Data layer | `contracts/data/MissionControl.vy`, `contracts/data/Ledger.vy` | global config, locked signer, security actions, wallet registry, backpack registry |
| Structs / ABI | `interfaces/{WalletStructs,WalletConfigStructs,ConfigStructs,Wallet,AgentWrapperInt}.vyi` | struct layouts and hard ABI cutover |
| Backpack registry | `contracts/registries/WalletBackpack.vy`, `contracts/registries/UndyHq.vy` | module installation and rotation, especially `ActionDataProvider` as a trust root |
| Governance hooks | `contracts/config/SwitchboardAlpha.vy`, `contracts/config/SwitchboardBravo.vy`, `contracts/config/SwitchboardCharlie.vy` | instant flags, locked signers, configs, payment-relevant side effects |
| Fee / loot adjacency | `contracts/core/LootDistributor.vy`, `UserWallet._payYieldFee`, `UserWallet._payTransactionFee` | adjacent value-exit paths and accounting interactions |

`SwitchboardCharlie.vy` is not a primary payment authorizer, but scan it for
payment-relevant configuration, deployment wiring, manager, vault, and instant
flag side effects. State explicitly whether it matters.

`LootDistributor.vy` and fee helpers are adjacent value-exit paths. Do not claim
that `transferFunds` directly calls `_payTransactionFee` on this branch.
Transaction fees are charged on swap/rewards paths, while yield-fee behavior can
be reached through asset/yield accounting. Review whether fee/loot behavior is
in or out of scope for the payment deployment decision.

Required docs to read and cross-check:

- `docs/user-wallet-payment-security.md`
- `docs/instant-action-model.md`
- `docs/mutability-policy.md`
- `docs/user-wallet-config-byte-budget.md`
- `docs/deploy-checklist.md`

Every assertion in `docs/user-wallet-payment-security.md` should be checked
against code. A divergence is a finding.

Out of scope unless a payment path depends on it:

- DEX and yield lego internals under `contracts/legos/**`.
- Earn/Levg vault internals under `contracts/vaults/**`.
- Appraiser/pricing internals. Treat pricing as trusted for implementation
  purposes, but flag where a manipulated, zero, or stale USD value weakens a cap.

---

## 6. Deployment, Defaults, And ABI Scope

This branch is not yet deployed and changed constructor signatures for payment
modules. Audit deployment and wiring, not just contract logic.

Read these migration/config files:

- `migrations/base-mainnet/v1.1/2026032400-Payments.py`
- `migrations/base-mainnet/v1.1/2026032500-Chequebook.py`
- `migrations/base-mainnet/v1.1/0008-WalletBackpack.py`
- `migrations/base-mainnet/v1.1/0002-MissionControl.py`
- `migrations/base-mainnet/v1.1/0004-Switchboard.py`
- `migrations/base-mainnet/v1.1/2026050100-SwitchboardCharlie.py`
- `migrations/base-mainnet/v1.1/2025121100-SwitchboardCharlie.py`
- `migrations/base-mainnet/v1.1/2025120900-MissionControl.py`
- `contracts/config/DefaultsBase.vy`
- `contracts/config/DefaultsLocal.vy`
- `config/BluePrint.py`
- `tests/scripts/test_production_params.py`

Verified deployment lead to confirm; treat as a likely deploy blocker unless the
real production deploy path is different:

- `HighCommand` now requires `_canInstantAddManager`.
- `Paymaster` now requires `_canInstantAddPayee` and
  `_canInstantSetGlobalPayeeSettings`.
- `ChequeBook` now requires `_canInstantSetChequeSettings`.
- `Migrator` now requires `_instantMigrationEnabled`.
- Verified lead: both `migrations/base-mainnet/v1.1/0008-WalletBackpack.py` and
  the newer `2026032400-Payments.py` / `2026032500-Chequebook.py` deploy these
  modules without the new instant-flag constructor args. A deploy from these
  scripts should fail on argument count; a partially updated script could also
  ship the wrong instant-flag posture. Confirm the real production deploy path,
  the exact boolean each module ships with, and whether the stale scripts are
  still reachable.

Confirm production defaults match the documented release plan:

- `defaultInstantActionSettings` in Hatchery.
- Protocol-level instant flags.
- `Migrator.instantMigrationEnabled` false.
- Simultaneous cutover assumptions.

ABI / SDK cutover:

- The branch removed `canPayOwner`,
  `WhitelistPerms.canAddPending`, `TransferPerms.canAddPendingPayee`, and
  `PendingPayee`.
- Any off-chain encoder still using the old struct layout will revert or
  mis-encode.
- Confirm generated ABIs, SDKs, scripts, tests, bots, and UI/multisig encoders
  were regenerated or updated. Hunt for lingering references or old struct
  offset assumptions.

---

## 7. Branch Diff Focus

Start with these diffs:

```bash
git -C /Users/wigglez/dev/underscore-protocol log --oneline master..cheque-enhance
git -C /Users/wigglez/dev/underscore-protocol diff --stat master...cheque-enhance -- \
  contracts/core/userWallet contracts/core/walletBackpack contracts/core/Hatchery.vy \
  contracts/core/agent contracts/core/Billing.vy contracts/data interfaces

git -C /Users/wigglez/dev/underscore-protocol diff --stat master...cheque-enhance -- \
  contracts/config contracts/registries migrations scripts/abis config
```

Highest-risk changed areas:

Effort budget: read the core payment diff in detail. The deployment/config/
registry/ABI diff is much larger; skim it for payment-relevant wiring first,
then deep-read any file that touches constructor args, defaults, registries,
instant flags, struct generation, or off-chain encoders. Rerun the commands for
current churn figures rather than trusting stale counts.

1. `ActionDataProvider.vy` is new. It centralizes signer permission assertions,
   `isLockedSigner`, billing bypass, whitelist-to-empty-recipient rewrite, and
   privileged-address lookups. It is immutable per wallet. A bug here
   mis-authorizes the whole payment surface.
2. Validators changed from `bool` returns to `void` with internal asserts.
   Verify every rejection path actually reverts. A path that returns without
   reverting can become unauthorized transfer.
3. `Sentinel` now returns `didPay` / `didUpdate`. `UserWalletConfig` persists
   period data, burns cheques, and decrements active-cheque counts based on
   those flags. Verify each flag is true exactly when state must change.
4. Manager pending-payee flow and several struct fields were deleted. Treat this
   as a hard ABI cutover.
5. Instant-action subsystem and widening detectors were added across
   `ChequeBook`, `Paymaster`, `HighCommand`, and `Migrator`.
6. Mutual-exclusion invariants were added for manager/payee/whitelist/active
   cheque recipient/privileged addresses. Check symmetry and both set-time and
   confirm-time enforcement.
7. PAY_CHEQUE is now subject to manager `allowedPayees`.
8. `Migrator` gained pending-migration timelock, `instantMigrationEnabled`,
   switchboard-as-caller, `@nonreentrant`, active-cheque migration blocking, and
   per-address collision validation.
9. Agent layer now binds signed hashes to an action-code byte and
   `_agentWrapper`; it added first-class cheque actions and
   `AgentSenderSpecialAdmin.vy`.
10. `Hatchery` became the validator/seeder of new-wallet defaults, including
    starter-agent types and `defaultInstantActionSettings`.

---

## 8. Required Audit Questions

Sections 8, 9, and 10 intentionally overlap. Use this section to define the
questions the report must answer, use Section 9 as the anchored investigation
map, and use Section 10 as the invariants to prove with code-path reasoning or
PoC tests. Do not treat them as three unrelated checklists.

Answer these from code and tests:

- Can money leave a wallet through any path other than intended
  `transferFunds` calls or explicitly privileged special/migration paths?
- Does `_isSpecialTx=True` remain callable only by wallet config, and are all
  wallet-config callers sufficiently trusted and bounded?
- Do whitelisted recipients bypass only recipient-limit checks, not manager
  action permission, asset restrictions, frozen/eject mode, or accounting?
- Can an address become more than one of manager, payee, whitelisted recipient,
  and active cheque recipient when that should be forbidden?
- Can stale pending whitelist, payee, cheque settings, manager settings, owner
  changes, timelock changes, or migration state be used to confirm unsafe
  permissions later?
- Are cheque payments exact amount, single-use, active only between unlock and
  expiry, and impossible to double-pull or replay through Billing or agents?
- Can managers create, replace, or pay only the cheques they are meant to, and
  only for allowed recipients/assets?
- Do payee payments enforce global and specific limits, cooldowns, period resets,
  lifetime caps, unit caps, primary-asset restrictions, zero-price behavior, and
  partial-pull semantics?
- Does Billing's signer bypass remain safe because downstream recipient/cheque
  validation still happens in `UserWalletConfig`?
- Can Billing's yield withdrawal path over-withdraw, under-withdraw, drain an
  unrelated vault token, bypass approved-yield checks, mishandle rounding, or
  leave accounting inconsistent?
- Do instant-action paths require all intended gates: protocol flag, user wallet
  flag, and per-call instant bool?
- Do migration and config clone paths preserve or reset manager, payee,
  whitelist, cheque, and counter state safely?
- Can malicious ERC20 behavior, fee-on-transfer behavior, rebasing, native ETH,
  max-value sends, zero balances, or non-standard return values break safety?
- Is reentrancy prevented or harmless around token transfers, yield withdrawals,
  appraiser/lego calls, Billing pulls, and post-transfer accounting?
- Are fee/loot value-exit paths correctly separated from payment recipient
  authorization, and do they introduce any unexpected way to drain funds?

---

## 9. Component Leads To Confirm Or Refute

Treat these as hypotheses and starting points. Confirm, refute, or refine each;
then look for additional issues.

### 9.1 Transfer Choke Point And Special Transactions

- `_isSpecialTx=True` skips recipient validation and manager post-transfer
  limits (`UserWallet.vy:169`, `UserWallet.vy:1037-1047`), gated only by
  `msg.sender == walletConfig` (`UserWallet.vy:203-205`). Enumerate every path
  that reaches `wallet.transferFunds(..., _isSpecialTx=True)`, especially
  `UserWalletConfig.migrateFunds` (`UserWalletConfig.vy:871-877`), and confirm
  each independently authorizes recipient and amount.
- `migrateFunds(_toWallet, _asset)` sends max balance to `_toWallet`, gated on
  `msg.sender == migrator`, and appears not to assert `_toWallet` equals the
  pending migration destination itself (`UserWalletConfig.vy:871-877`). Confirm
  that behavior and verify destination and timelock enforcement in `Migrator`
  cannot be bypassed.
- Billing signer bypass in `ActionDataProvider` skips locked-signer and
  Sentinel signer checks (`ActionDataProvider.vy:155-160`). Confirm Billing
  cannot be induced to call `transferFunds` with an attacker-chosen recipient
  and that `BILLING_ID` cannot be spoofed.
- Eject mode can zero `txUsdValue`, disabling USD caps
  (`UserWallet.vy:166`; follow `_updatePriceAndGetUsdValue`). Cheques should
  reject zero USD value; confirm payee USD caps and eject-mode restrictions are
  safe.
- Manager USD-limit checks run after funds leave (`UserWallet.vy:176-181`,
  `UserWallet.vy:1037-1047`). Confirm no path skips the post-transfer check
  while still moving funds.
- Fee-on-transfer and rebasing tokens can cause the recipient to receive a
  different amount than the clamped amount used for caps. Check safety and
  accounting tolerance.

### 9.2 Cheques

- Confirm `validateCheque` and `Sentinel.isValidChequeAndGetData` enforce
  recipient, active status, asset, exact amount, unlock, expiry, creator
  authority, and manager payment rules (`UserWalletConfig.vy:525-563`,
  `Sentinel.vy:650-724`).
- Verify `didPay` consistency. If Sentinel can return valid with `didPay=False`,
  a cheque may pay without being burned (`Sentinel.vy:700-724`,
  `UserWalletConfig.vy:558-563`).
- Same-block replacement residual is explicitly deferred in docs. Replacing your
  own cheque skips the active-count cap but still bumps per-period created
  counters (`ChequeBook.vy:544-549`). Determine whether this can grief period
  caps or desync counters.
- Replacement authorization uses creator identity. Check whether an expired,
  deactivated, or removed manager can still replace a cheque they created
  (`ChequeBook.vy:233`).
- Creation-time and pay-time USD values differ. A stale or manipulated
  creation-time value from `Appraiser.updatePriceAndGetUsdValue` can shorten an
  expensive cheque's unlock delay if expensive-cheque delay is computed from
  that value. Assess the practical risk.
- Audit `_isChequeSettingsWidening` and helpers. Confirm every field is covered,
  `0 = uncapped` is treated as widening, and cooldown direction is correct
  (`ChequeBook.vy:870-965`).
- `canBePulled` is enforced in Billing, not in Sentinel. Confirm a recipient
  cannot self-trigger `transferFunds(_isCheque=True)` for a non-pullable cheque
  without passing through Billing (`Billing.vy:102-151`,
  `Sentinel.vy:650-724`).
- Check pay-cooldown behavior across period boundaries, especially
  `payCooldownBlocks != 0 and lastChequePaidBlock != 0`
  (`Sentinel.vy:703-704`) and the fact that period reset zeroes paid counts but
  not `lastChequePaidBlock` (`ChequeBook.vy:559-575`).

### 9.3 Payees

- Instant add overwrites `startBlock` to the current block after validation
  (`Paymaster.vy:455-472`).
  Confirm a high-cap pullable payee cannot become live earlier than intended
  unless all instant gates are intentionally enabled.
- `updatePayee` has no timelock or widening guard in the current flow
  (`Paymaster.vy:501-561`). Determine whether instant cap raises or `canPull`
  flips are intended and bounded.
- Unit limits apply only to the primary asset (`Sentinel.vy:510-516`). A payee with
  `onlyPrimaryAsset=False` and unit-only limits may be able to pull a different
  asset capped only by tx count.
- `failOnZeroPrice` is required only when USD limits are set
  (`Paymaster.vy:985-1001`). Check whether unit-only payees can transact with a
  broken or zero oracle.
- Verify `didUpdate` persistence. If Sentinel returns payable with
  `didUpdate=False`, period/cooldown counters may not advance
  (`Sentinel.vy:449-520`, `UserWalletConfig.vy:475-516`).
- Registered user wallets appear to be valid payees but invalid managers in the
  mapped code because `Paymaster._isPrivilegedUndyAddr` appears not to call
  `isUserWallet` while HighCommand's privileged-address checks do. Confirm both
  call paths and verify this asymmetry cannot create wallet-to-wallet recursive
  drains.

### 9.4 Whitelist

- Whitelisting grants unlimited uncapped transfers in any asset. Treat any
  whitelist-timelock bypass or unintended whitelist grant as critical.
- `addWhitelistAddrViaMigrator` registers whitelist entries without a timelock,
  gated on the migrator (`UserWalletConfig.vy:606-611`). Verify hardening and
  confirm the migrator can only call it during a validated clone.
- A manager with `whitelistPerms.canConfirm` can finalize an owner-created
  pending whitelist entry, and whitelisted recipients bypass `allowedPayees`.
  Assess whether this trust boundary is intended and whether it allows
  self-expansion (`Kernel.vy:130-149`, `ActionDataProvider.vy:161-163`).
- Confirm `currentOwner` checks cannot be bypassed through owner-change
  interleavings (`Kernel.vy:139`, `UserWalletConfig.vy:593-599`).
- Confirm strict-confirm and silent-remove asymmetry cannot brick legitimate
  flows or create exploitability.
- Verify role-collision symmetry: an address cannot become whitelisted and later
  become a manager/payee/active-cheque recipient, or the reverse, unless that is
  explicitly intended.

### 9.5 Managers

- `allowedPayees` restrictions are bypassed for whitelisted recipients through
  the whitelist-to-empty-recipient rewrite (`ActionDataProvider.vy:161-163`);
  manager recipient validation only checks non-empty recipients
  (`Sentinel.vy:183-186`).
  Combined with manager-confirm-whitelist, can a restricted manager expand
  reachable recipients?
- `updateManager` skips the add-time exclusivity checks for payee, whitelist,
  and active-cheque collisions (`HighCommand.vy:273-329`; compare add-time
  checks at `HighCommand.vy:214-220`). On update, the validator path passes an
  empty "new manager" value, so the guard that prevents a manager from being its
  own `allowedPayee` can be skipped (`HighCommand.vy:645-675`,
  `HighCommand.vy:846-865`). Confirm whether a manager can add itself to its own
  `allowedPayees`.
- Instant manager add skips start delay when gates allow it. Check expiry math
  and non-expiring windows (`HighCommand.vy:221-237`).
- `neuterStarterAgent` may leave `canClaimLoot=True` with zero windows. Verify
  `startBlock == 0` and `expiryBlock == 0` are inert in every consumer,
  including cheque creation.
- Confirm `0 = unlimited` manager limits require explicit owner action and do
  not arise accidentally through defaults, migration, or update paths.

### 9.6 Agent And Signature Layer

- Independent nonce spaces exist in Generic, Special, and SpecialAdmin senders
  (`AgentSenderGeneric.vy:66`, `AgentSenderSpecial.vy:65`,
  `AgentSenderSpecialAdmin.vy:55`). Confirm the EIP-712 domain separator binds
  `verifyingContract = sender address` and prevents cross-sender replay
  (`AgentSenderGeneric.vy:832`, `AgentSenderSpecial.vy:569`,
  `AgentSenderSpecialAdmin.vy:347`).
- Hash builders and verifiers must encode payloads byte-identically, including
  action-code byte and `_agentWrapper`. Diff every action path.
- Signed `createCheque` payloads (action 5) can set flags such as
  `canManagerPay=True`, `unlock=0`, and `expiry=0`
  (`AgentSenderGeneric.vy:120-133`). Confirm downstream cheque settings and
  manager limits bound this.
- `harvestAndIssueCheque` (action 106) amount is not capped to proceeds in its
  own flow (`AgentSenderSpecialAdmin.vy:155-208`). Confirm an over-sized cheque
  cannot drain unintended assets given pay-time clamping.
- Batch actions use one nonce for up to 15 instructions. Verify
  `_assertChequeVersionMatches` cannot be bypassed with `amount2=0`, and that
  create-and-pay plus pay cannot double-spend a cheque in one batch/block
  (`AgentSenderGeneric.vy:139-158`, `AgentSenderGeneric.vy:611-612`).
- Signature `_verify` is duplicated across senders. Check low-s bound, `v`
  normalization, failed `ecrecover`, and drift between copies
  (`AgentSenderGeneric.vy:792`, `AgentSenderSpecial.vy:529`,
  `AgentSenderSpecialAdmin.vy:307`).
- `addSender` is the trust root. Check swap/remove bookkeeping, index 0
  reservation, ghost sender risk, and monitoring event gaps
  (`AgentWrapper.vy:609`).
- One wrapper can be a manager identity across wallets. Confirm per-wallet
  manager limits still bind and `removeSelfAsManager` (action 70) cannot be
  front-run into a payment bypass (`AgentSenderGeneric.vy:403-409`,
  `AgentWrapper.vy:428`).

### 9.7 Migration

- Special migration transfers skip recipient, limit, whitelist, and cheque
  checks. The destination must be a legitimate same-owner, same-`groupId`,
  ledger-registered sibling. Probe every assumption.
- `instantMigrationEnabled` removes the migration timelock. Assess whether
  switchboard or compromised governance can enable it too quickly
  (`Migrator.vy:149-168`, `Migrator.vy:530-532`).
- Switchboard-as-caller widens authority beyond owner execution. Combined with
  instant migration, can funds move between a victim's wallets without owner
  initiation (`Migrator.vy:484`).
- Migration clones `PayeeSettings` and `ManagerSettings` without re-running full
  per-entry setters. Confirm identity and collision checks are enough
  (`Migrator.vy:371-405`).
- `applyMigratedConfigSettings` bypasses per-setter timelocks. Confirm it is
  callable only on a legitimate fresh destination with trustworthy source
  settings (`UserWalletConfig.vy:369-389`).
- `_isValidMigratorConfigAddr` may treat manager, payee, and whitelist slots
  differently. Confirm a wallet or privileged address cannot be smuggled into a
  role (`Migrator.vy:690-710`).
- `cancelPendingMigration` lets any security-action holder cancel any wallet's
  pending migration. Assess DoS or griefing impact (`Migrator.vy:198-217`).

### 9.8 Creation And Data Layer

- New-wallet instant-action defaults are injected by Hatchery
  (`Hatchery.vy:253`, `UserWalletConfig.vy:210-216`). Test fixtures ship
  `(True, True, True, True)` (`tests/conf_core.py:320`). Confirm they match docs
  and production params, and assess residual risk.
- Starter agent is installed as `managers[1]` with transfer and cheque creation
  permissions (`UserWalletConfig.vy:216`,
  `HighCommand._createHappyManagerDefaults` at `HighCommand.vy:1003+`). Verify
  expiry and manager limits bind it.
- Hatchery validates defaults through one code path and constructs them through
  another. Confirm validated values equal written values.
- Defaults are snapshotted at creation, not live-referenced. Do not assume later
  global config tightening retroactively protects existing wallets.
- `isLockedSigner` is skipped for Billing and special transfer paths. Confirm a
  locked owner or manager cannot still move funds through those routes
  (`ActionDataProvider.vy:155-160`, `UserWallet.vy:203-205`).

### 9.9 Cross-Cutting And Vyper-Specific Checks

- Vyper `@nonreentrant` locks are contract-local. Confirm every state-mutating
  payment entry point holds a lock where needed, and reason about cross-contract
  reentrancy through recipient contracts, ERC777-like hooks, Billing, Kernel,
  ChequeBook, Appraiser, and lego calls.
- Check 1-based index bookkeeping and swap-and-pop removals for managers,
  payees, whitelisted addresses, and active cheques. Look for stale `indexOf`
  entries, slot reuse, underflow, or `numActiveCheques` desync.
- Confirm all ABI/struct cutover references are updated.
- Confirm view/pure convenience validators cannot be reached on fund-moving
  paths with attacker-supplied config.
- Audit integer and USD math: rounding, truncation, overflow, exact boundary
  behavior at `startBlock`, `expiryBlock`, `confirmBlock`, period rollover, and
  max-value sends.
- Review native ETH, zero balances, fee-on-transfer tokens, rebasing tokens,
  non-standard ERC20 returns, malicious registered ERC20s, and malicious yield
  lego/vault behavior at the payment edge.

---

## 10. Invariants To Verify

Turn these into code-path arguments and, where feasible, PoC tests:

1. No unauthorized egress. Money leaves a wallet only via `transferFunds`, and
   only when both signer authorization and recipient classification pass. The
   sole exception is the walletConfig-only special migration path.
2. Special transfer is walletConfig-only. No path reaches
   `transferFunds(_isSpecialTx=True)` except a properly authorized migration
   path. Billing must not use transfer-special mode.
3. Cheque single-use. A cheque pays at most once; payment deactivates it and
   decrements `numActiveCheques` before funds move.
4. Caps bind. Payee and manager limits cannot be exceeded across transfers,
   pulls, batches, period rollovers, replacements, and partial payments, except
   intentionally uncapped whitelist recipients.
5. Timelocks bind. Re-enabling disabled instant flags, lowering timelocks,
   widening cheque/payee/manager settings, adding whitelist entries, and
   migrating wait the required delay unless the documented instant path is fully
   enabled.
6. Role exclusivity. An address is not simultaneously manager, payee,
   whitelisted, active-cheque recipient, or privileged protocol/backpack address
   at set-time, confirm-time, update-time, and migration-time.
7. Whitelist gate. Only the owner can create a pending whitelist entry; confirm
   requires elapsed timelock and the same owner.
8. Signature soundness. A signed agent payload authorizes exactly one action, on
   one wallet, through one wrapper, once. No replay across senders, actions,
   wallets, or nonces; no malleability.
9. Migration safety. Migration moves funds only to a same-owner, same-`groupId`,
   ledger-registered sibling; it cannot inject malicious roles or carry over
   over-permissioned settings unexpectedly.
10. Docs match code. Every payment-security doc assertion holds in code.

---

## 11. Methodology

Use this order unless evidence tells you to deviate:

1. Read `docs/user-wallet-payment-security.md`, the instant-action docs, and the
   system model in this prompt.
2. Read `UserWallet.transferFunds` and `_validateCanTransfer` top to bottom.
3. Read the branch diff for high-churn contracts and deployment/config wiring.
4. Trace each money-exit path end to end, following every cross-contract call.
   Build a per-path call graph with authorization checks and state writes.
5. Work the component leads above. Confirm or refute each, then ask what else can
   break.
6. Write minimal PoC tests for credible issues. Prefer end-to-end tests through
   real public entry points over isolated internal-validator checks.
7. Self-review each finding adversarially. Can the attacker really reach the
   state? Is there an upstream check that prevents it? Downgrade or drop weak
   findings, but preserve genuinely uncertain high-impact issues as such.

Known coverage gaps worth probing:

- No adversarial-token tests for reentrant, fee-on-transfer, or non-standard
  ERC20 behavior at the `transferFunds` edge.
- No dedicated reentrancy harness around `transferFunds`.
- No fuzz/property coverage for cap, period, and USD arithmetic.
- Payee pull has end-to-end coverage in `tests/core/test_billing.py`; do not
  merely re-prove that happy path. Aim new tests at adversarial gaps.

---

## 12. Final Report Requirements

Lead with findings, not a broad summary.

For each finding include:

- Title.
- Severity: Critical / High / Medium / Low / Informational.
- Confidence: Confirmed via PoC / Likely / Speculative.
- Affected file and function, with call path.
- Preconditions.
- Exploit path.
- Impact, including which invariant breaks and whose funds or controls are at
  risk.
- Reproduction, failing test, or concrete step-by-step scenario.
- Recommended minimal fix.

Severity rubric:

- Critical: direct theft or loss of user funds, or unauthorized egress with no
  meaningful precondition.
- High: fund loss requiring a specific but reachable precondition; cap,
  timelock, whitelist, migration, or signature bypass.
- Medium: limited loss, griefing/DoS of user funds or controls, or a bypass
  requiring unusual config.
- Low: minor deviations, defense-in-depth gaps, unsafe defaults.
- Informational: code quality, doc/code divergence without direct security
  impact, test-coverage gaps.

After findings, include:

- Explicit deployment recommendation, exactly one of:
  - `Block deploy`
  - `Safe to deploy after fixes`
  - `Safe to deploy`
- For `Block deploy` or `Safe to deploy after fixes`, list the named blocking
  findings.
- For `Safe to deploy`, list residual risks and assumptions, including the
  accepted all-true instant-default posture if applicable. A `Safe to deploy`
  verdict must cite the code paths reviewed and the passing test evidence that
  supports it.
- Executive summary with overall posture and count by severity.
- Coverage matrix for whitelist, cheque, payee, manager, Billing pull,
  agent/signature callers, migration, instant settings, role collisions, and
  fee/loot adjacency. Use consistent cell labels: `existing-test`,
  `new-PoC`, `review-only`, `gap`, or `not-in-scope`, with a short note in each
  cell.
- Tests run with exact commands and results.
- Tests not run, and why.
- Test gaps and residual assumptions.
- Systemic risks, including trust in `ActionDataProvider`, `Migrator`, the agent
  server key, instant-action defaults, deploy scripts, and constructor wiring.

If no critical issues are found, still list unresolved assumptions and the
strongest remaining areas to probe. If a component appears sound after genuine
effort, say what you checked; negative results are valuable.
