# Payment Audit Handoff Plan

This document is a handoff prompt for a fresh agent auditing the Underscore
Protocol payment surface. It is intentionally scoped to the `cheque-enhance`
branch and should be executed from `/Users/wigglez/dev/underscore-protocol`.

## Mission

You are auditing every path where value can leave a user wallet through the
payment model. The core transfer function is `UserWallet.transferFunds`; the
three primary payment categories are:

- Whitelist / trusted transfers.
- Cheques / one-off payments.
- Payees / recurring payments.

The audit goal is to find bugs, permission bypasses, faulty logic, exploitable
edge cases, unsafe defaults, missing tests, and weak assumptions before this
branch is deployed. Treat this as a security review, not a remediation task:
write focused proof tests for suspected issues, but do not modify protocol
contracts unless explicitly asked.

## First Commands

Run these before making conclusions:

```bash
cd /Users/wigglez/dev/underscore-protocol
git status --short --branch
git fetch origin
git checkout cheque-enhance
git status --short --branch
git diff --stat origin/master...HEAD
```

Expected branch: `cheque-enhance`. If the branch is different, stop and report
that the audit is not running on the intended code.

This repo uses `pytest` with the fixture harness in `tests/conftest.py` and
`tests/conf_*.py`. There is no `pytest.ini`, `pyproject.toml`, or Makefile test
entry point. If collection fails because environment keys are missing, use dummy
values for local mock-EVM tests:

```bash
export ETHERSCAN_API_KEY=dummy
export WEB3_ALCHEMY_API_KEY=dummy
```

## Primary Review Surface

Review these files first:

- `contracts/core/userWallet/UserWallet.vy`
  - `transferFunds`
  - `_validateCanTransfer`
  - `_performPreActionTasks`
  - `_performPostActionTasks`
- `contracts/core/userWallet/UserWalletConfig.vy`
  - `checkRecipientLimitsAndUpdateData`
  - `validateCheque`
  - whitelist, payee, cheque, manager storage mutations
  - `preparePayment`
  - `deregisterAsset`
- `contracts/core/userWallet/ActionDataProvider.vy`
  - billing signer bypass
  - whitelist recipient rewrite
  - manager permission bundle
- `contracts/core/Billing.vy`
  - `pullPaymentAsCheque`
  - `pullPaymentAsPayee`
  - `_pullPayment`
  - yield withdrawal during pull payment
- `contracts/core/walletBackpack/Kernel.vy`
  - whitelist add, confirm, cancel, remove
  - manager whitelist permissions
  - role collision checks
- `contracts/core/walletBackpack/Paymaster.vy`
  - payee add, update, remove
  - global payee settings
  - `canPull`
  - instant and timelock paths
- `contracts/core/walletBackpack/ChequeBook.vy`
  - cheque create, replace, cancel
  - cheque settings
  - unlock and expiry rules
  - manager-created and manager-paid cheque flags
- `contracts/core/walletBackpack/Sentinel.vy`
  - manager validation
  - payee validation
  - cheque validation
- `contracts/core/walletBackpack/HighCommand.vy`
  - manager settings
  - transfer permissions
  - `allowedPayees`
  - manager/payee/whitelist role separation

## Agent And Signature Surface

Managers can trigger payments through the agent/signature layer. Treat this as
first-class audit scope:

- `contracts/core/agent/AgentWrapper.vy`
- `contracts/core/agent/AgentSenderGeneric.vy`
- `contracts/core/agent/AgentSenderSpecial.vy`
- `contracts/core/agent/AgentSenderSpecialAdmin.vy`
- `contracts/core/agent/AgentSenderSpecialSigHelper.vy`
- `contracts/core/agent/UserWalletSignatureHelper.vy`

Confirm that a partially permissioned manager, an approved sender, a replayed
signature, a stale nonce, a forged call, or a batch action cannot create a
cheque, pay a cheque, transfer to a payee, or bypass recipient restrictions
outside its intended permissions.

## Secondary And Configuration Surface

Inspect these after the primary flow is mapped:

- `contracts/core/walletBackpack/Migrator.vy`
- `contracts/core/Hatchery.vy`
- `contracts/data/MissionControl.vy`
- `contracts/config/SwitchboardAlpha.vy`
- `contracts/config/SwitchboardBravo.vy`
- `contracts/config/SwitchboardCharlie.vy`
- `contracts/config/DefaultsBase.vy`
- `contracts/config/DefaultsLocal.vy`
- `contracts/core/LootDistributor.vy`

`SwitchboardCharlie.vy` is not a primary payment authorizer, but include a scan
for payment-relevant configuration, deployment wiring, and manager/instant flag
side effects so its exclusion or inclusion is explicit in the final report.

`LootDistributor.vy` and fee helpers are adjacent value-exit paths. Do not state
that `transferFunds` directly calls `_payTransactionFee`; in this branch,
transaction fees are charged on swap/rewards paths, while yield-fee behavior can
be reached through asset/yield accounting. Review fee/loot behavior as an
adjacent "value leaves the wallet" surface and report whether it is in or out of
scope for the payment deployment decision.

## Deployment And Defaults Context

Read these docs before finalizing conclusions:

- `docs/user-wallet-payment-security.md`
- `docs/instant-action-model.md`
- `docs/deploy-checklist.md`

Inspect relevant migration scripts and deployment wiring:

- `migrations/base-mainnet/v1.1/2026032400-Payments.py`
- `migrations/base-mainnet/v1.1/2026032500-Chequebook.py`
- `migrations/base-mainnet/v1.1/0002-MissionControl.py`
- `migrations/base-mainnet/v1.1/0004-Switchboard.py`
- `migrations/base-mainnet/v1.1/2026050100-SwitchboardCharlie.py`
- `migrations/base-mainnet/v1.1/2025121100-SwitchboardCharlie.py`
- `migrations/base-mainnet/v1.1/2025120900-MissionControl.py`

Check that deployed defaults, constructor args, protocol flags, wallet instant
settings, and switchboard/migration actions cannot accidentally widen payment
permissions without the intended timelock and actor gates.

## Threat Model

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
- Switchboard/governance.
- Malicious ERC20.
- Malicious yield lego or vault token.
- Stale pending-action beneficiary.
- Ordinary EOA or contract with no role.

Assume attackers chain weak primitives, timing edges, stale pending state,
rounding, zero/stale prices, role collisions, and signature/batch call confusion.

## Required Audit Questions

Answer these from code and tests:

- Can money leave the wallet through any path other than the intended
  `transferFunds` or explicitly privileged special/migration paths?
- Does `_isSpecialTx=True` remain callable only by the wallet config, and are all
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
- Do instant-action paths require all gates: protocol flag, user wallet flag,
  and per-call instant bool?
- Do migration/config clone paths preserve or reset manager, payee, whitelist,
  cheque, and counter state safely?
- Can malicious ERC20 behavior, fee-on-transfer behavior, rebasing, native ETH,
  max-value sends, zero balances, or non-standard return values break safety?
- Is reentrancy prevented or harmless around token transfers, yield withdrawals,
  appraiser/lego calls, Billing pulls, and post-transfer accounting?
- Are fee/loot value-exit paths correctly separated from payment recipient
  authorization, and do they introduce any unexpected way to drain funds?

## Starter Test Command

Run or extend this focused suite:

```bash
pytest \
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

When you suspect an issue, write the smallest failing test or reproducible script
before proposing a fix. Prefer tests that prove the exploit path end-to-end
through the real public entry point instead of only calling internal validators
through views.

## Final Report Format

Lead with findings, not a broad summary.

For each finding include:

- Severity.
- Affected file/function.
- Preconditions.
- Exploit path.
- Impact.
- Reproduction or failing test.
- Recommended fix.

Then include:

- Explicit go/no-go recommendation for deploying this branch.
- Coverage matrix for whitelist, cheque, payee, manager, Billing pull,
  agent/signature callers, migration, instant settings, role collisions, and
  fee/loot adjacency.
- Tests run with exact commands and results.
- Test gaps and residual assumptions.

Do not say the payment system is safe unless that claim is defended by both code
path analysis and test evidence. If the result is "no critical issues found,"
still list unresolved assumptions and the strongest remaining areas to probe.
