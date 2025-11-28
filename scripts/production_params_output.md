Connecting to Base mainnet via Alchemy...
Connected. Block: 38739832

Loading contracts from Etherscan...
Fetching configuration data...

================================================================================
# Underscore Protocol Production Parameters

**Generated:** 2025-11-27 18:44:01 UTC
**Block:** 38739832
**Network:** Base Mainnet

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [UndyHq Configuration](#undy-hq)
3. [MissionControl Configuration](#mission-control)
   - [User Wallet Config](#user-wallet-config)
   - [Agent Config](#agent-config)
   - [Manager Config](#manager-config)
   - [Payee Config](#payee-config)
   - [Cheque Config](#cheque-config)
4. [SwitchboardAlpha Timelock](#switchboard-alpha)
5. [VaultRegistry Configuration](#vault-registry)
6. [Earn Vaults](#earn-vaults)
7. [Earn Vault Details](#earn-vault-details)
8. [WalletBackpack Components](#wallet-backpack)
9. [LegoBook Registry](#lego-book)
10. [Switchboard Registry](#switchboard-registry)
11. [LootDistributor Config](#loot-distributor)
12. [Ledger Statistics](#ledger)


<a id="executive-summary"></a>
## Executive Summary

| Metric | Value |
| --- | --- |
| **Total User Wallets** | 251 |
| **Registered Legos** | 17 |
| **Earn Vaults** | 8 |

================================================================================

<a id="undy-hq"></a>
# UndyHq - Main Registry & Governance
Address: 0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9

## Registry Config
| Parameter | Value |
| --- | --- |
| undyToken | None |
| mintEnabled | False |
| numAddrs (departments) | 10 |
| registryChangeTimeLock | 21600 blocks (~12.0h) |

### Registered Departments
| ID | Description | Address | Can Mint UNDY | Can Set Blacklist |
| --- | --- | --- | --- | --- |
| 1 | Ledger | Ledger (0x9e97...c5D0) | No | No |
| 2 | Mission Control | MissionControl (0x89c8...2cBE) | No | No |
| 3 | Lego Book | LegoBook (0x2fD6...50EB) | No | No |
| 4 | Switchboard | Switchboard (0xd6B8...4e11) | No | Yes |
| 5 | Hatchery | 0x3ea1...c193 | No | No |
| 6 | Loot Distributor | LootDistributor (0x23d6...9dE8) | No | No |
| 7 | Appraiser | Appraiser (0x8C65...45e2) | No | No |
| 8 | Wallet Backpack | WalletBackpack (0x1009...6250) | No | No |
| 9 | Billing | Billing (0xB61d...6E4e) | No | No |
| 10 | Vault Registry | VaultRegistry (0x1C17...e3Cf) | No | No |

================================================================================

<a id="mission-control"></a>
# MissionControl - Core Protocol Configuration
Address: 0x89c8A842CD9428024294cB6a52c28D5EB23e2cBE

<a id="user-wallet-config"></a>

## User Wallet Config
| Parameter | Value |
| --- | --- |
| walletTemplate | 0x880E...7C12 |
| configTemplate | 0xbF7b...10Fb |
| numUserWalletsAllowed | 100000 |
| enforceCreatorWhitelist | True |
| minKeyActionTimeLock | 21600 blocks (~12.0h) |
| maxKeyActionTimeLock | 604800 blocks (~14.0d) |
| depositRewardsAsset | 0x2A0a...dDC0 |
| lootClaimCoolOffPeriod | 0 blocks (~0s) |

## Default Transaction Fees
| Parameter | Value |
| --- | --- |
| swapFee | 0.25% |
| stableSwapFee | 0.25% |
| rewardsFee | 20.00% |

## Default Ambassador Revenue Share
| Parameter | Value |
| --- | --- |
| swapRatio | 0.00% |
| rewardsRatio | 0.00% |
| yieldRatio | 0.00% |

## Default Yield Config
| Parameter | Value |
| --- | --- |
| maxYieldIncrease | 5.00% |
| performanceFee | 20.00% |
| ambassadorBonusRatio | 100.00% |
| bonusRatio | 100.00% |
| bonusAsset | 0x2A0a...dDC0 |

<a id="agent-config"></a>

## Agent Config
| Parameter | Value |
| --- | --- |
| startingAgent | 0x761f...203B |
| startingAgentActivationLength | 31536000 blocks (~730.0d) |

<a id="manager-config"></a>

## Manager Config
| Parameter | Value |
| --- | --- |
| managerPeriod | 43200 blocks (~1.0d) |
| managerActivationLength | 1296000 blocks (~30.0d) |
| mustHaveUsdValueOnSwaps | True |
| maxNumSwapsPerPeriod | 2 |
| maxSlippageOnSwaps | 5.00% |
| onlyApprovedYieldOpps | True |

<a id="payee-config"></a>

## Payee Config
| Parameter | Value |
| --- | --- |
| payeePeriod | 1296000 blocks (~30.0d) |
| payeeActivationLength | 15768000 blocks (~365.0d) |

<a id="cheque-config"></a>

## Cheque Config
| Parameter | Value |
| --- | --- |
| maxNumActiveCheques | 3 |
| instantUsdThreshold | Very High (1.00e+14 USD) |
| periodLength | 43200 blocks (~1.0d) |
| expensiveDelayBlocks | 43200 blocks (~1.0d) |
| defaultExpiryBlocks | 86400 blocks (~2.0d) |

================================================================================

<a id="switchboard-alpha"></a>
# SwitchboardAlpha - Timelock Settings
Address: 0xB7d32916c8E7F74f70aF7ECFcb35B04358E50bAc

## Timelock Config
| Parameter | Value |
| --- | --- |
| minActionTimeLock | 3600 blocks (~2.0h) |
| maxActionTimeLock | 1296000 blocks (~30.0d) |
| actionTimeLock | 0 blocks (~0s) |

================================================================================

<a id="vault-registry"></a>
# VaultRegistry - Vault Configuration
Address: 0x1C17ef5Ef2AefcEE958E7e3dC345e96aBfF4e3Cf

## Registry Config
| Parameter | Value |
| --- | --- |
| numAddrs (vaults) | 10 |
| registryChangeTimeLock | 0 blocks (~0s) |

================================================================================

<a id="earn-vaults"></a>
# Earn Vaults - Per-Vault Configuration

### UndyUsd
Address: 0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf

## UndyUsd Config
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01  |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (21):**
| Index | Token |
| --- | --- |
| 1 | 0x7BfA...F34A |
| 2 | 0xbeeF...8183 |
| 3 | 0xc125...A2Ca |
| 4 | 0x616a...3738 |
| 5 | 0xeE8F...4b61 |
| 6 | 0xBEEF...83b2 |
| 7 | 0x2347...3B5e |
| 8 | 0xBEEF...878F |
| 9 | 0xc0c5...Eb12 |
| 10 | 0xB789...b863 |
| 11 | 0x12AF...406e |
| 12 | 0x2369...e890 |
| 13 | 0x0A1a...eE16 |
| 14 | 0x4e65...c0AB |
| 15 | 0xb125...Eb2F |
| 16 | 0xf42f...9169 |
| 17 | 0xEdc8...6c22 |
| 18 | 0xB99B...7Cf5 |
| 19 | 0x1C4a...8B24 |
| 20 | 0x9447...E7f9 |

### UndyEth
Address: 0x02981DB1a99A14912b204437e7a2E02679B57668

## UndyEth Config
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.00  |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (12):**
| Index | Token |
| --- | --- |
| 1 | 0xa0E4...0ff1 |
| 2 | 0x27D8...5c18 |
| 3 | 0x5A32...7a8C |
| 4 | 0x0983...1C53 |
| 5 | 0x6b13...8844 |
| 6 | 0xA2Ca...3AFc |
| 7 | 0x8591...b410 |
| 8 | 0xD4a0...8bb7 |
| 9 | 0x46e6...70bf |
| 10 | 0x9272...1CE9 |
| 11 | 0x628f...D457 |

### UndyBtc
Address: 0x3fb0fC9D3Ddd543AD1b748Ed2286a022f4638493

## UndyBtc Config
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.00  |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (7):**
| Index | Token |
| --- | --- |
| 1 | 0x5432...a796 |
| 2 | 0x6770...07Cb |
| 3 | 0x5a47...F3C7 |
| 4 | 0x8820...7f8B |
| 5 | 0xBdb9...8EE6 |
| 6 | 0xF877...5976 |

### UndyAero
Address: 0x96F1a7ce331F40afe866F3b707c223e377661087

## UndyAero Config
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01  |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (3):**
| Index | Token |
| --- | --- |
| 1 | 0x784e...cE89 |
| 2 | 0x7390...9Ba6 |

### UndyEurc
Address: 0x1cb8DAB80f19fC5Aca06C2552AECd79015008eA8

## UndyEurc Config
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01  |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (8):**
| Index | Token |
| --- | --- |
| 1 | 0xf246...a026 |
| 2 | 0xBeEF...6ab5 |
| 3 | 0x1c15...e122 |
| 4 | 0x9ECD...7117 |
| 5 | 0x90DA...025B |
| 6 | 0x1943...B401 |
| 7 | 0xb682...01a2 |

### UndyUsds
Address: 0xaA0C35937a193ca81A64b3cFd5892dac384d22bB

## UndyUsds Config
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01  |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (5):**
| Index | Token |
| --- | --- |
| 1 | 0x2c77...A518 |
| 2 | 0xb641...a357 |
| 3 | 0x556d...1D8b |
| 4 | 0x5875...467a |

### UndyCbeth
Address: 0xFe75aD75AD59a5c80de5AE0726Feee89567F080d

## UndyCbeth Config
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.00  |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (4):**
| Index | Token |
| --- | --- |
| 1 | 0xcf3D...95ad |
| 2 | 0x3bf9...A5E5 |
| 3 | 0x358f...ea49 |

### UndyGho
Address: 0x220b8B08c8CfD6975ed203AA26887c0AA5a8cf44

## UndyGho Config
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01  |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (3):**
| Index | Token |
| --- | --- |
| 1 | 0x067a...cBd1 |
| 2 | 0x8Ddb...3631 |

================================================================================

<a id="earn-vault-details"></a>
# Earn Vault Details - Managers & Assets

### UndyUsd Details
Address: 0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf

## UndyUsd Stats
| Parameter | Value |
| --- | --- |
| asset | USDC (0x8335...2913) |
| totalAssets | 301.91K  |
| totalSupply (shares) | 0.00  |
| numManagers | 2 |
| numAssets (yield positions) | 6 |
| lastUnderlyingBal | 302.12K  |
| pendingYieldRealized | 1.05K  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | EarnVaultAgent (0x6B01...30a7) |
| 2 | 0x8d6D...1e3b |

### UndyEth Details
Address: 0x02981DB1a99A14912b204437e7a2E02679B57668

## UndyEth Stats
| Parameter | Value |
| --- | --- |
| asset | WETH (0x4200...0006) |
| totalAssets | 3.17  |
| totalSupply (shares) | 3.16  |
| numManagers | 2 |
| numAssets (yield positions) | 5 |
| lastUnderlyingBal | 3.17  |
| pendingYieldRealized | 0.00  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | EarnVaultAgent (0x6B01...30a7) |
| 2 | 0x8d6D...1e3b |

### UndyBtc Details
Address: 0x3fb0fC9D3Ddd543AD1b748Ed2286a022f4638493

## UndyBtc Stats
| Parameter | Value |
| --- | --- |
| asset | cbBTC (0xcbB7...33Bf) |
| totalAssets | 0.02  |
| totalSupply (shares) | 0.00  |
| numManagers | 2 |
| numAssets (yield positions) | 4 |
| lastUnderlyingBal | 0.02  |
| pendingYieldRealized | 0.00  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | EarnVaultAgent (0x6B01...30a7) |
| 2 | 0x8d6D...1e3b |

### UndyAero Details
Address: 0x96F1a7ce331F40afe866F3b707c223e377661087

## UndyAero Stats
| Parameter | Value |
| --- | --- |
| asset | AERO (0x9401...8631) |
| totalAssets | 5.20K  |
| totalSupply (shares) | 5.19K  |
| numManagers | 2 |
| numAssets (yield positions) | 2 |
| lastUnderlyingBal | 5.20K  |
| pendingYieldRealized | 4.66  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | EarnVaultAgent (0x6B01...30a7) |
| 2 | 0x8d6D...1e3b |

### UndyEurc Details
Address: 0x1cb8DAB80f19fC5Aca06C2552AECd79015008eA8

## UndyEurc Stats
| Parameter | Value |
| --- | --- |
| asset | EURC (0x60a3...db42) |
| totalAssets | 177.15  |
| totalSupply (shares) | 0.00  |
| numManagers | 2 |
| numAssets (yield positions) | 5 |
| lastUnderlyingBal | 177.19  |
| pendingYieldRealized | 0.19  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | EarnVaultAgent (0x6B01...30a7) |
| 2 | 0x8d6D...1e3b |

### UndyUsds Details
Address: 0xaA0C35937a193ca81A64b3cFd5892dac384d22bB

## UndyUsds Stats
| Parameter | Value |
| --- | --- |
| asset | USDS (0x820C...21Dc) |
| totalAssets | 99.12  |
| totalSupply (shares) | 99.12  |
| numManagers | 2 |
| numAssets (yield positions) | 0 |
| lastUnderlyingBal | 0.00  |
| pendingYieldRealized | 0.00  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | EarnVaultAgent (0x6B01...30a7) |
| 2 | 0x8d6D...1e3b |

### UndyCbeth Details
Address: 0xFe75aD75AD59a5c80de5AE0726Feee89567F080d

## UndyCbeth Stats
| Parameter | Value |
| --- | --- |
| asset | cbETH (0x2Ae3...Ec22) |
| totalAssets | 0.02  |
| totalSupply (shares) | 0.02  |
| numManagers | 2 |
| numAssets (yield positions) | 0 |
| lastUnderlyingBal | 0.00  |
| pendingYieldRealized | 0.00  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | EarnVaultAgent (0x6B01...30a7) |
| 2 | 0x8d6D...1e3b |

### UndyGho Details
Address: 0x220b8B08c8CfD6975ed203AA26887c0AA5a8cf44

## UndyGho Stats
| Parameter | Value |
| --- | --- |
| asset | GHO (0x6Bb7...10Ee) |
| totalAssets | 99.13  |
| totalSupply (shares) | 99.13  |
| numManagers | 2 |
| numAssets (yield positions) | 0 |
| lastUnderlyingBal | 0.00  |
| pendingYieldRealized | 0.00  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | EarnVaultAgent (0x6B01...30a7) |
| 2 | 0x8d6D...1e3b |

================================================================================

<a id="wallet-backpack"></a>
# WalletBackpack - Wallet Components
Address: 0x10099b1386b434Ea4da1967d952931b645Df6250

## Wallet Components
| Component | Address |
| --- | --- |
| kernel | Kernel (0xAdED...B389) |
| sentinel | Sentinel (0xCCe9...667b) |
| highCommand | HighCommand (0x0649...78EC) |
| paymaster | Paymaster (0x80bf...AFCb) |
| chequeBook | ChequeBook (0xcC93...0Dc9) |
| migrator | Migrator (0xe008...169a) |

================================================================================

<a id="lego-book"></a>
# LegoBook - Lego Registry
Address: 0x2fD67d572806Fc43B55aFE2ad032702d826450EB

## Registry Config
| Parameter | Value |
| --- | --- |
| legoTools | None |
| numAddrs (legos) | 17 |
| registryChangeTimeLock | 0 blocks (~0s) |

### Registered Legos
| ID | Description | Address |
| --- | --- | --- |
| 1 | Ripe Protocol | 0x2728...9A54 |
| 2 | Aave v3 | 0xac80...1478 |
| 3 | Compound v3 | 0x590F...fbA7 |
| 4 | Euler | 0x7f52...4fd6 |
| 5 | Fluid | 0x67E7...4f93 |
| 6 | Moonwell | 0x0657...d804 |
| 7 | Morpho | 0x1485...8868 |
| 8 | Aero Classic | 0x43B2...84D1 |
| 9 | Aero Slipstream | 0x2DD2...70bd |
| 10 | Curve | 0x7192...dF65 |
| 11 | Uniswap V2 | 0x9597...6fd7 |
| 12 | Uniswap V3 | 0xEa1f...e7A5 |
| 13 | Underscore Lego | 0x0f79...f9E9 |
| 14 | 40 Acres | 0x39F5...6514 |
| 15 | Wasabi | 0xe67E...3BEd |
| 16 | Avantis | 0xc88C...F1f0 |
| 17 | Sky Psm | 0xEe7B...92CF |

================================================================================

<a id="switchboard-registry"></a>
# Switchboard - Config Contracts Registry
Address: 0xd6B83538214B7e7d57Cd9faCd260E284a5fe4e11

## Registry Config
| Parameter | Value |
| --- | --- |
| numAddrs (config contracts) | 3 |
| registryChangeTimeLock | 0 blocks (~0s) |

### Registered Config Contracts
| ID | Description | Address |
| --- | --- | --- |
| 1 | SwitchboardAlpha | SwitchboardAlpha (0xB7d3...0bAc) |
| 2 | SwitchboardBravo | SwitchboardBravo (0x5ed8...9B84) |
| 3 | SwitchboardCharlie | SwitchboardCharlie (0xDd75...0117) |

================================================================================

<a id="loot-distributor"></a>
# LootDistributor - Rewards Configuration
Address: 0x23d69D99061acf04c6e86f58692F533E4f039dE8

## Loot Config
| Parameter | Value |
| --- | --- |
| depositRewards.asset | None |
| depositRewards.amount | 0.00  |
| ripeStakeRatio | 80.00% |
| ripeLockDuration | 7776000 blocks (~180.0d) |
| RIPE_TOKEN | 0x2A0a...dDC0 |
| RIPE_REGISTRY | 0x6162...3d2b |

================================================================================

<a id="ledger"></a>
# Ledger - Protocol Data
Address: 0x9e97A2e527890E690c7FA978696A88EFA868c5D0

## Protocol Statistics
| Parameter | Value |
| --- | --- |
| numUserWallets | 251 |

## Global Points
| Parameter | Value |
| --- | --- |
| usdValue | 213.17K USD |
| depositPoints | 93,179,168,091 |
| lastUpdate (block) | 38,727,772 |

================================================================================

---
*Report generated at block 38739832 on 2025-11-27 18:45:38 UTC*
