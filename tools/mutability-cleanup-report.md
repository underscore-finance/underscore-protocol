# Mutability Cleanup Report

## Branch And Scope

- Branch: `mutability-cleanup`
- Base: `master` at `7e73423a920a6b6f5c5cbfc7a33c7a147501cce4`
- Worktree: `/Users/wigglez/dev/underscore-protocol-mutability-cleanup`
- Original worktree was left untouched because `/Users/wigglez/dev/underscore-protocol` was on `cheque-enhance` with `?? find_view_asserts.py`.
- Compiler verified before implementation: local `vyper --version` was `0.4.3+commit.bff19ea2`; `requirements.txt` pins `vyper==0.4.3`; contracts use `# @version 0.4.3`.

## Scanner

Added `tools/mutability_scanner.py`, `tools/mutability-baseline.yml`, `tools/mutability-inventory-pre-cleanup.md`, and `tools/mutability-inventory-final.md`.

Pre-cleanup scanner snapshot:

| Metric | Count |
| --- | ---: |
| Vyper files | 95 |
| defs | 2490 |
| `@view` | 1239 |
| `@pure` | 19 |
| `@nonreentrant` | 33 |
| `view-revert` | 16 |
| `can-be-view` | 37 |
| `view-could-be-pure` | 123 |
| `interface-mismatch` | 0 |
| `interface-ambiguous` | 107 |

Final scanner result:

| Metric | Count |
| --- | ---: |
| Vyper files | 95 |
| defs | 2490 |
| `@view` | 1119 |
| `@pure` | 169 |
| `@nonreentrant` | 33 |
| `view-revert` | 0 |
| `can-be-view` | 8 |
| `view-could-be-pure` | 0 |
| `interface-mismatch` | 0 |
| `invalid-exemption` | 0 |
| `interface-ambiguous` | 107 |

Baseline file is intentionally empty apart from its header. The final 8 `can-be-view` items are inline-exempted with reasons, not baseline entries.

## Remaining Exemptions

| File | Symbol / reason |
| --- | --- |
| `contracts/vaults/modules/EarnVaultWallet.vy` | `_validateAndGetSwapInfo`: preserving exported vault runtime under EIP-170 |
| `contracts/vaults/modules/EarnVaultWallet.vy` | `_canManagerPerformAction`: preserving exported vault runtime under EIP-170 |
| `contracts/vaults/modules/LevgVaultWallet.vy` | `_canManagerPerformAction`: preserving exported vault runtime under EIP-170 |
| `contracts/vaults/modules/VaultErc20Token.vy` | `_validateNewApprovals`: preserving shared approval asserts keeps exported vault runtime under EIP-170 |
| `contracts/mock/MockRipe.vy` | `deleverageForWithdrawal`: mock matches mutating Ripe deleverage interface |
| `contracts/mock/MockYieldLego.vy` | `setMorphoRewardsAddr`: mock keeps mutating rewards setter interface |
| `contracts/mock/MockYieldLego.vy` | `setEulerRewardsAddr`: mock keeps mutating rewards setter interface |
| `contracts/mock/MockYieldLego.vy` | `setCompRewardsAddr`: mock keeps mutating rewards setter interface |

EIP-170 note: `EarnVault` deployment failed with Boa reporting code size `24678` bytes until the Earn-only swap-info helper was restored to assert-based non-view form with an inline exemption. Direct `EarnVault` deployment succeeds after that rollback.

## ABI StateMutability Changes

Compared `/tmp/underscore-mutability-abis-pre` to `/tmp/underscore-mutability-abis-final-check`.

| ABI | Function | Before | After |
| --- | --- | --- | --- |
| `40Acres.json` | `isValidPriceConfig(tuple)` | view | pure |
| `40Acres.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `40Acres.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `40Acres.json` | `hasClaimableRewards(address)` | view | pure |
| `AaveV3.json` | `isValidPriceConfig(tuple)` | view | pure |
| `AaveV3.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `AaveV3.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `AaveV3.json` | `hasClaimableRewards(address)` | view | pure |
| `AeroClassic.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `AeroClassic.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `AeroSlipstream.json` | `onERC721Received(address,address,uint256,bytes)` | view | pure |
| `AeroSlipstream.json` | `getLpToken(address)` | view | pure |
| `AeroSlipstream.json` | `getPoolForLpToken(address)` | view | pure |
| `AeroSlipstream.json` | `getPrice(address,uint256)` | view | pure |
| `AeroSlipstream.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `AeroSlipstream.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `Appraiser.json` | `calculateYieldProfits(address,uint256,uint256,uint256,address,address)` | nonpayable | view |
| `Avantis.json` | `isValidPriceConfig(tuple)` | view | pure |
| `Avantis.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `Avantis.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `Avantis.json` | `hasClaimableRewards(address)` | view | pure |
| `ChequeBook.json` | `createDefaultChequeSettings(uint256,uint256,uint256,uint256,uint256)` | view | pure |
| `CompoundV3.json` | `isValidPriceConfig(tuple)` | view | pure |
| `Curve.json` | `isYieldLego()` | view | pure |
| `Curve.json` | `isDexLego()` | view | pure |
| `Curve.json` | `getAccessForLego(address,uint256)` | view | pure |
| `Euler.json` | `isValidPriceConfig(tuple)` | view | pure |
| `Euler.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `Euler.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `Euler.json` | `hasClaimableRewards(address)` | view | pure |
| `ExtraFi.json` | `isValidPriceConfig(tuple)` | view | pure |
| `ExtraFi.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `ExtraFi.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `ExtraFi.json` | `hasClaimableRewards(address)` | view | pure |
| `Fluid.json` | `isValidPriceConfig(tuple)` | view | pure |
| `Fluid.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `Fluid.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `Fluid.json` | `hasClaimableRewards(address)` | view | pure |
| `Hatchery.json` | `doesWalletStillHaveTrialFundsWithAddys(address,address,address,address,address,address)` | view | pure |
| `HighCommand.json` | `createDefaultGlobalManagerSettings(uint256,uint256,uint256,bool,uint256,uint256,bool)` | view | pure |
| `LegoTools.json` | `prepareSwapInstructionsAmountOut(uint256,tuple[])` | nonpayable | pure |
| `LevgVault.json` | `isLeveragedVault()` | view | pure |
| `Moonwell.json` | `isValidPriceConfig(tuple)` | view | pure |
| `Morpho.json` | `isValidPriceConfig(tuple)` | view | pure |
| `Morpho.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `Morpho.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `Morpho.json` | `hasClaimableRewards(address)` | view | pure |
| `Paymaster.json` | `createDefaultGlobalPayeeSettings(uint256,uint256,uint256)` | view | pure |
| `RipeLego.json` | `isValidPriceConfig(tuple)` | view | pure |
| `RipeLego.json` | `hasClaimableRewards(address)` | view | pure |
| `SkyPsm.json` | `isValidPriceConfig(tuple)` | view | pure |
| `SkyPsm.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `SkyPsm.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `SkyPsm.json` | `hasClaimableRewards(address)` | view | pure |
| `UnderscoreLego.json` | `isValidPriceConfig(tuple)` | view | pure |
| `UniswapV2.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `UniswapV2.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `UniswapV3.json` | `onERC721Received(address,address,uint256,bytes)` | view | pure |
| `UniswapV3.json` | `getLpToken(address)` | view | pure |
| `UniswapV3.json` | `getPoolForLpToken(address)` | view | pure |
| `UniswapV3.json` | `getPrice(address,uint256)` | view | pure |
| `UniswapV3.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `UniswapV3.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `VaultRegistry.json` | `isValidPerformanceFee(uint256)` | view | pure |
| `VaultRegistry.json` | `isValidRedemptionBuffer(uint256)` | view | pure |
| `Wasabi.json` | `isValidPriceConfig(tuple)` | view | pure |
| `Wasabi.json` | `claimRewards(address,address,uint256,bytes32)` | nonpayable | pure |
| `Wasabi.json` | `claimRewards(address,address,uint256,bytes32,tuple)` | nonpayable | pure |
| `Wasabi.json` | `hasClaimableRewards(address)` | view | pure |

## Interface Declaration Changes

Local interface declarations were updated to match promoted implementations. The changed signatures are:

- `VaultRegistry.isValidPerformanceFee` and `VaultRegistry.isValidRedemptionBuffer`: `view` to `pure`
- yield-lego `isValidPriceConfig` declarations: `view` to `pure`
- wallet-backpack default settings helpers: `view` to `pure`
- `Appraiser.calculateYieldProfits`: `nonpayable` to `view`
- local helper/lego declarations such as `getFirstVaultIdForAsset`, `doesUndyLegoHaveAccess`, `getTotalDebt`, `factory`, `isValidDeployment`, `isProxy`, `isMetaMorpho`, `susds`, `usds`, `isLeveragedVault`, and `isSupportedAssetInVault`: `view` to `pure`

## Gas

Reports:

- Pre-cleanup: `tools/gas-baseline-pre-cleanup.json`
- Final: `tools/gas-baseline-final.json`

| Metric | Pre | Final | Delta |
| --- | ---: | ---: | ---: |
| Representative tests captured | 367 | 367 | 0 |
| Total gas | 288784817 | 288825114 | +40297 |

This is not a net improvement. The largest single-test increase is `+1155` gas. The representative suite had 256 tests with a positive delta, 111 unchanged, and none lower.

Critical-path regression justification:

- Signature and agent paths now return status codes from `_verify` helpers and assert exact dev strings in mutating callers. This removes `@view` reverts while preserving user-facing failure specificity, at the cost of small extra branching/tuple handling.
- Appraiser permission checks now use a view-safe sentinel and assert in mutating wallet callers. This keeps ABI-compatible return shape and avoids view reverts.
- Curve pool-data and vault swap helpers use sentinel/status handling where needed so view callers can propagate failure without reverting.
- EIP-170-sensitive exported vault helpers are intentionally exempted rather than expanded into larger sentinel refactors.
- The measured regressions are small relative to the transaction flows and are the direct cost of making revert behavior compatible with `@view` / `@pure` rules.

## Validation

Commands run:

```bash
python scripts/export_abis.py --output-dir /tmp/underscore-mutability-abis-final-check
python tools/mutability_scanner.py --baseline tools/mutability-baseline.yml --inventory tools/mutability-inventory-final.md --jobs 8
python -m pytest tests/config/test_switchboard_charlie.py tests/vaults/earn/test_earn_vault_actions.py::test_vault_mini_wallet_deposit_for_yield_basic tests/vaults/leverage/test_levg_vault_wallet_actions.py::test_deposit_to_collateral_vault_usdc tests/core/test_appraiser.py tests/core/agent/test_agent_signatures.py tests/core/walletBackpack/chequeBook/test_cheque_mgmt.py -q
python -m pytest
python scripts/utils/capture_gas.py --output tools/gas-baseline-final.json
```

Results:

- ABI export: passed, exported 67 ABIs; skipped 23 excluded mocks and 5 embedded modules.
- Scanner: passed with zero unexempted violations and zero interface mismatches.
- Targeted high-risk tests: `179 passed in 30.98s`.
- Full suite: `2630 passed, 317 skipped, 248 deselected in 257.65s`.
- Final gas capture: `367 passed`, total gas `288825114`.

## High-Risk Notes

- `ActionDataProvider` / wallet config: `checkSignerPermissionsAndGetBundle` remains ABI-compatible and uses `ad.walletOwner == empty(address)` as the failure sentinel. Mutating callers assert immediately before using the returned bundle.
- `_verify` helpers: refactored to return `(address, status)` and keep exact dev-string asserts in callers.
- `Curve._getPoolData`: refactored to return status with zero/default pool data for view-safe failure paths.
- ERC-721 callbacks: `AeroSlipstream` and `UniswapV3` callbacks are `@pure` and return `empty(bytes4)` for invalid callback data. Grep found no docs/runbook hits for `did not receive from within Underscore wallet`.
- Mocks: mock-specific mutability changes are kept in mocks, with interface-preserving exemptions where mocks intentionally model mutating external surfaces.

## Files Changed

Contract/test files:

- `contracts/config/SwitchboardAlpha.vy`
- `contracts/config/SwitchboardCharlie.vy`
- `contracts/core/Appraiser.vy`
- `contracts/core/Hatchery.vy`
- `contracts/core/agent/AgentSenderGeneric.vy`
- `contracts/core/agent/AgentSenderSpecial.vy`
- `contracts/core/agent/EarnVaultAgent.vy`
- `contracts/core/agent/LevgVaultAgent.vy`
- `contracts/core/userWallet/UserWallet.vy`
- `contracts/core/userWallet/UserWalletConfig.vy`
- `contracts/core/walletBackpack/ChequeBook.vy`
- `contracts/core/walletBackpack/HighCommand.vy`
- `contracts/core/walletBackpack/Paymaster.vy`
- `contracts/core/walletBackpack/Sentinel.vy`
- `contracts/helpers/LevgVaultTools.vy`
- `contracts/legos/LegoTools.vy`
- `contracts/legos/RipeLego.vy`
- `contracts/legos/UnderscoreLego.vy`
- `contracts/legos/dexes/AeroClassic.vy`
- `contracts/legos/dexes/AeroSlipstream.vy`
- `contracts/legos/dexes/Curve.vy`
- `contracts/legos/dexes/UniswapV2.vy`
- `contracts/legos/dexes/UniswapV3.vy`
- `contracts/legos/yield/40Acres.vy`
- `contracts/legos/yield/AaveV3.vy`
- `contracts/legos/yield/Avantis.vy`
- `contracts/legos/yield/CompoundV3.vy`
- `contracts/legos/yield/Euler.vy`
- `contracts/legos/yield/ExtraFi.vy`
- `contracts/legos/yield/Fluid.vy`
- `contracts/legos/yield/Moonwell.vy`
- `contracts/legos/yield/Morpho.vy`
- `contracts/legos/yield/SkyPsm.vy`
- `contracts/legos/yield/Wasabi.vy`
- `contracts/mock/Mock40AcresVault.vy`
- `contracts/mock/MockAaveV3Pool.vy`
- `contracts/mock/MockBadERC1271.vy`
- `contracts/mock/MockDexLego.vy`
- `contracts/mock/MockERC1271.vy`
- `contracts/mock/MockErc4626Vault.vy`
- `contracts/mock/MockLegoRegistry.vy`
- `contracts/mock/MockRipe.vy`
- `contracts/mock/MockSwapLego.vy`
- `contracts/mock/MockVaultRegistry.vy`
- `contracts/mock/MockYieldLego.vy`
- `contracts/modules/Addys.vy`
- `contracts/modules/Erc20Token.vy`
- `contracts/modules/YieldLegoData.vy`
- `contracts/registries/VaultRegistry.vy`
- `contracts/vaults/EarnVault.vy`
- `contracts/vaults/LevgVault.vy`
- `contracts/vaults/LevgVaultHelper.vy`
- `contracts/vaults/modules/EarnVaultWallet.vy`
- `contracts/vaults/modules/LevgVaultWallet.vy`
- `contracts/vaults/modules/VaultErc20Token.vy`
- `tests/core/test_appraiser.py`

New tooling/docs:

- `docs/mutability-policy.md`
- `scripts/utils/capture_gas.py`
- `tools/gas-baseline-final.json`
- `tools/gas-baseline-pre-cleanup.json`
- `tools/mutability-baseline.yml`
- `tools/mutability-cleanup-report.md`
- `tools/mutability-inventory-final.md`
- `tools/mutability-inventory-pre-cleanup.md`
- `tools/mutability_scanner.py`
