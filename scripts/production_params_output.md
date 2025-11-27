Connecting to Base mainnet via Alchemy...
Connected. Block: 38697479

Loading contracts from Etherscan...
Fetching configuration data...

================================================================================
# Underscore Protocol Production Parameters

**Generated:** 2025-11-26 19:12:21 UTC
**Block:** 38697479
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
| 2 | Mission Control | MissionControl (0x910F...2006) | No | No |
| 3 | Lego Book | LegoBook (0x9788...d8e3) | No | No |
| 4 | Switchboard | 0xe52A...fC7e | No | Yes |
| 5 | Hatchery | 0xCCE4...D4d2 | No | No |
| 6 | Loot Distributor | 0x2D77...910C | No | No |
| 7 | Appraiser | 0x2126...39E5 | No | No |
| 8 | Wallet Backpack | WalletBackpack (0x0E8D...5CcD) | No | No |
| 9 | Billing | 0x4139...C73E | No | No |
| 10 | Vault Registry | VaultRegistry (0xC64A...5b64) | No | No |

================================================================================

<a id="mission-control"></a>
# MissionControl - Core Protocol Configuration
Address: 0x910FE9484540fa21B092eE04a478A30A6B342006

<a id="user-wallet-config"></a>

## User Wallet Config
| Parameter | Value |
| --- | --- |
| walletTemplate | 0x4C4D...3a40 |
| configTemplate | 0x0E70...24F1 |
| numUserWalletsAllowed | 10000 |
| enforceCreatorWhitelist | True |
| minKeyActionTimeLock | 21600 blocks (~12.0h) |
| maxKeyActionTimeLock | 302400 blocks (~7.0d) |
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

<a id="agent-config"></a>

## Agent Config
| Parameter | Value |
| --- | --- |
| startingAgent | 0x9d3F...a2F9 |
| startingAgentActivationLength | 31536000 blocks (~730.0d) |

<a id="manager-config"></a>

## Manager Config
| Parameter | Value |
| --- | --- |
| managerPeriod | 43200 blocks (~1.0d) |
| managerActivationLength | 1296000 blocks (~30.0d) |
| mustHaveUsdValueOnSwaps | N/A |
| maxNumSwapsPerPeriod | N/A |
| maxSlippageOnSwaps | N/A |
| onlyApprovedYieldOpps | N/A |

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
Address: 0xb7622CB741C2B26E59e262604d941C50D309C358

## Timelock Config
| Parameter | Value |
| --- | --- |
| minConfigTimeLock | N/A |
| maxConfigTimeLock | N/A |
| configTimeLock | N/A |
| numActions | N/A |

================================================================================

<a id="vault-registry"></a>
# VaultRegistry - Vault Configuration
Address: 0xC64A779FE55673F93F647F1E2A30B3C3a9A25b64

## Registry Config
| Parameter | Value |
| --- | --- |
| numAddrs (vaults) | 16 |
| registryChangeTimeLock | 3600 blocks (~2.0h) |

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
| isLeveragedVault | N/A |
| shouldEnforceAllowlist | N/A |

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
| isLeveragedVault | N/A |
| shouldEnforceAllowlist | N/A |

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
| isLeveragedVault | N/A |
| shouldEnforceAllowlist | N/A |

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
| isLeveragedVault | N/A |
| shouldEnforceAllowlist | N/A |

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
| isLeveragedVault | N/A |
| shouldEnforceAllowlist | N/A |

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
| isLeveragedVault | N/A |
| shouldEnforceAllowlist | N/A |

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
| isLeveragedVault | N/A |
| shouldEnforceAllowlist | N/A |

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
| isLeveragedVault | N/A |
| shouldEnforceAllowlist | N/A |

================================================================================

<a id="earn-vault-details"></a>
# Earn Vault Details - Managers & Assets

### UndyUsd Details
Address: 0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf

## UndyUsd Stats
| Parameter | Value |
| --- | --- |
| asset | USDC (0x8335...2913) |
| totalAssets | 301.85K  |
| totalSupply (shares) | 0.00  |
| numManagers | 2 |
| numAssets (yield positions) | 5 |
| lastUnderlyingBal | 302.03K  |
| pendingYieldRealized | 986.62  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | 0x6B01...30a7 |
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
| 1 | 0x6B01...30a7 |
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
| 1 | 0x6B01...30a7 |
| 2 | 0x8d6D...1e3b |

### UndyAero Details
Address: 0x96F1a7ce331F40afe866F3b707c223e377661087

## UndyAero Stats
| Parameter | Value |
| --- | --- |
| asset | AERO (0x9401...8631) |
| totalAssets | 5.20K  |
| totalSupply (shares) | 5.20K  |
| numManagers | 2 |
| numAssets (yield positions) | 2 |
| lastUnderlyingBal | 5.20K  |
| pendingYieldRealized | 2.86  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | 0x6B01...30a7 |
| 2 | 0x8d6D...1e3b |

### UndyEurc Details
Address: 0x1cb8DAB80f19fC5Aca06C2552AECd79015008eA8

## UndyEurc Stats
| Parameter | Value |
| --- | --- |
| asset | EURC (0x60a3...db42) |
| totalAssets | 177.14  |
| totalSupply (shares) | 0.00  |
| numManagers | 2 |
| numAssets (yield positions) | 5 |
| lastUnderlyingBal | 177.16  |
| pendingYieldRealized | 0.16  |

**Managers (2):**
| Index | Manager |
| --- | --- |
| 1 | 0x6B01...30a7 |
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
| 1 | 0x6B01...30a7 |
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
| 1 | 0x6B01...30a7 |
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
| 1 | 0x6B01...30a7 |
| 2 | 0x8d6D...1e3b |

================================================================================

<a id="wallet-backpack"></a>
# WalletBackpack - Wallet Components
Address: 0x0E8D974Cdea08BcAa43421A15B7947Ec901f5CcD

## Wallet Components
| Component | Address |
| --- | --- |
| kernel | 0xcb91...D217 |
| sentinel | 0xA9A7...Bf30 |
| highCommand | 0x84c5...4372 |
| paymaster | 0x5aDc...4946 |
| chequeBook | 0xF800...0318 |
| migrator | 0x99bf...b22C |

================================================================================

<a id="lego-book"></a>
# LegoBook - Lego Registry
Address: 0x9788f0D9D1A6577F685972B066b4Db2D73fEd8e3

## Registry Config
| Parameter | Value |
| --- | --- |
| legoTools | None |
| numAddrs (legos) | 17 |
| registryChangeTimeLock | 3600 blocks (~2.0h) |

### Registered Legos
| ID | Description | Address |
| --- | --- | --- |
| 1 | Ripe Protocol | 0xf819...cb56 |
| 2 | Aave v3 | 0x256f...d1D3 |
| 3 | Compound v3 | 0xAB75...1f58 |
| 4 | Euler | 0x6669...E069 |
| 5 | Fluid | 0x7C61...DF45 |
| 6 | Moonwell | 0x3F42...fEc1 |
| 7 | Morpho | 0x77ED...2e1E |
| 8 | Aero Classic | 0x5Dec...0245 |
| 9 | Aero Slipstream | 0xC626...2248 |
| 10 | Curve | 0x4e0C...0743 |
| 11 | Uniswap v2 | 0x33F7...4ce6 |
| 12 | Uniswap v3 | 0xda8C...91cB |
| 13 | Underscore Lego | 0xB3a0...220a |
| 14 | 40 Acres | 0xea19...FA91 |
| 15 | Wasabi | 0x2b99...a6D4 |
| 16 | Avantis | 0x0b6D...3D35 |
| 17 | Sky Psm | 0x8cC1...57EB |

================================================================================

<a id="switchboard-registry"></a>
# Switchboard - Config Contracts Registry
Address: 0xe52A6790fC8210DE16847f1FaF55A6146c0BfC7e

## Registry Config
| Parameter | Value |
| --- | --- |
| numAddrs (config contracts) | 3 |
| registryChangeTimeLock | 21600 blocks (~12.0h) |

### Registered Config Contracts
| ID | Description | Address |
| --- | --- | --- |
| 1 | SwitchboardAlpha | 0xb762...C358 |
| 2 | SwitchboardBravo | 0xf1F5...368c |
| 3 | Switchboard Charlie | 0xAb0e...8987 |

================================================================================

<a id="loot-distributor"></a>
# LootDistributor - Rewards Configuration
Address: 0x2D775AfA205729b8e74F9215611Ed700f564910C

## Loot Config
| Parameter | Value |
| --- | --- |
| depositRewards.asset | 0x2A0a...dDC0 |
| depositRewards.amount | 152.31  |
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
| usdValue | 213.13K USD |
| depositPoints | 86,093,441,298 |
| lastUpdate (block) | 38,694,540 |

================================================================================

---
*Report generated at block 38697479 on 2025-11-26 19:14:34 UTC*
