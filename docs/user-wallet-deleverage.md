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

`_extraData` is signed and forwarded to Ripe preview and execution. For v1 it is
reserved unless Ripe explicitly implements behavior for it; preview and
execution must interpret it identically.
