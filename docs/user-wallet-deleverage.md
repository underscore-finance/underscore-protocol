# User-Wallet Ripe Deleverage

Normal `UserWallet` Ripe deleverage is exposed through `UserWallet.deleverage`,
`AgentWrapper.deleverage`, and `AgentSenderGeneric.deleverage`.

Action codes:

| Code | Mode | Meaning |
| --- | --- | --- |
| 44 | Specific assets | Repay via requested `DeleverageAsset[]` entries. |
| 45 | Auto | Repay up to `_autoDeleverageAmount` using Ripe's previewed asset set. |

Specific mode signs and executes with `_deleverageAssets` non-empty and
`_autoDeleverageAmount == 0`. Auto mode signs and executes with
`_deleverageAssets == []` and `_autoDeleverageAmount != 0`. The signed payload
includes both fields to prevent mode confusion.

User-wallet deleverage accepts up to 10 assets. Vault-specific deleverage flows
keep their existing vault-agent caps.

The deleverage ABI requires all mode fields to be passed explicitly. Specific
mode should pass `_autoDeleverageAmount = 0`; auto mode should pass
`_deleverageAssets = []`.

`_extraData` is signed and forwarded to Ripe preview and execution. The current
Ripe implementation ignores it, so v1 callers should treat it as reserved unless
Ripe explicitly implements behavior for it. Preview and execution must interpret
it identically.

Phase 1 deploys `RipeLego` in compatibility mode. The new wallet-authenticated
path works because the wallet calls Ripe as `_caller == _user`; the old direct
user-wallet selectors remain callable by registered agent senders during the
migration window. The phase-5 tightening removes that agent-sender compatibility
branch and leaves only `_caller == _user` for user wallets. Earn-vault manager
paths are unchanged in both phases.

The Ripe wallet function returns touched wallet ERC20 assets for wallet
post-action accounting. Specific mode returns the requested asset list. Auto mode
currently previews and returns GREEN plus sGREEN so wallet accounting reconciles
either balance if Ripe's route changes it. If Ripe execution ever mutates other
wallet ERC20 balances, the Ripe implementation must include those assets in
`previewAutoDeleverageAssets` and `touchedAssets` before routing traffic to the
new selector.

ABI/SDK notes:

- `repayAndWithdraw` deleverage entries are capped at 10 for user-wallet flows.
- `UserWallet` liquidity functions now require explicit amount/minimum/extraData
  parameters; default-argument selector variants were removed as an approved size
  tradeoff. Regenerate ABIs/SDKs and survey production callers before phase 2.
