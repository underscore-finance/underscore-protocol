# User-Wallet Ripe Deleverage

Normal `UserWallet` Ripe deleverage is exposed through `UserWallet.deleverage`,
`AgentWrapper.deleverage`, and `AgentSenderGeneric.deleverage`.

Action codes:

| Code | Mode | Meaning |
| --- | --- | --- |
| 44 | Specific assets | Repay via requested `DeleverageAsset[]` entries. |
| 45 | Auto | Repay up to `_autoDeleverageAmount` through Ripe auto deleverage. |

Specific mode signs and executes with `_deleverageAssets` non-empty and
`_autoDeleverageAmount == 0`. Auto mode signs and executes with
`_deleverageAssets == []` and `_autoDeleverageAmount != 0`. The signed payload
includes both fields to prevent mode confusion.

User-wallet deleverage accepts up to 10 assets. Vault-specific deleverage flows
keep their existing vault-agent caps.

The deleverage ABI requires all mode fields to be passed explicitly. Specific
mode should pass `_autoDeleverageAmount = 0`; auto mode should pass
`_deleverageAssets = []`.

`_extraData` is signed and forwarded to Ripe execution. The current Ripe
implementation ignores it, so v1 callers should treat it as reserved unless Ripe
explicitly implements behavior for it.

Phase 1 deploys `RipeLego` in compatibility mode. The new wallet-authenticated
path works because the wallet calls Ripe as `_caller == _user`; the old direct
user-wallet selectors remain callable by registered agent senders during the
migration window. The phase-5 tightening removes that agent-sender compatibility
branch and leaves only `_caller == _user` for user wallets. Earn-vault manager
paths are unchanged in both phases.

The Ripe wallet function returns touched wallet ERC20 assets for wallet
post-action accounting when it can identify them. Specific mode pre-checks the
requested assets and requires returned touched assets to be a subset of that
request. Auto mode intentionally does not pre-check or subset-check assets,
because the signed request does not name assets and Ripe may choose from a broad
collateral set at execution time. Manager debt permissions, allowed legos,
transaction count/cooldown, and post-transaction USD limits still apply to auto
mode; manager asset allowlists do not. Do not add auto-mode asset allowlist
enforcement until the Ripe deleverage interface can return the actual assets
used for repayment.

ABI/SDK notes:

- `repayAndWithdraw` deleverage entries are capped at 10 for user-wallet flows.
- `UserWallet` liquidity functions now require explicit amount/minimum/extraData
  parameters; default-argument selector variants were removed as an approved size
  tradeoff. Regenerate ABIs/SDKs and survey production callers before phase 2.
