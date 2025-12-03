================================================================================
# Underscore Protocol Production Parameters

**Generated:** 2025-12-02 23:44:58 UTC
**Block:** 38964843
**Network:** Base Mainnet

## Table of Contents

1. [Executive Summary](#executive-summary)
2. **Registries**
   - [UndyHq Configuration](#undy-hq)
   - [Switchboard Registry](#switchboard-registry) (includes all config contracts)
3. **Core Protocol**
   - [WalletBackpack Components](#wallet-backpack)
   - [MissionControl Configuration](#mission-control)
     - [User Wallet Config](#user-wallet-config)
     - [Agent Config](#agent-config)
     - [Manager Config](#manager-config)
     - [Payee Config](#payee-config)
     - [Cheque Config](#cheque-config)
     - [Security Signers](#security-signers)
     - [Creator Whitelist](#creator-whitelist)
   - [LootDistributor Config](#loot-distributor)
   - [Ledger Statistics](#ledger)

> **Note:** Contract addresses: `deployments_output.md`
> **Note:** Vault configuration: `vaults_params_output.md`
> **Note:** Lego configuration: `lego_params_output.md`


<a id="executive-summary"></a>
## Executive Summary

| Metric | Value |
| --- | --- |
| **Total User Wallets** | 254 |
| **Registered Legos** | 17 |
| **Earn Vaults** | 10 |

================================================================================

<a id="undy-hq"></a>
# UndyHq - Main Registry & Governance
Address: 0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9

### Registry Config (AddressRegistry Module)
| Parameter | Value |
| --- | --- |
| undyToken | None |
| mintEnabled | False |
| numAddrs (departments) | 10 |
| registryChangeTimeLock | 21600 blocks (~12.0h) |

### Governance Settings (LocalGov Module)
| Parameter | Value |
| --- | --- |
| governance | `0xaDd738FD4e8b43c7923E170d1789f5E2140Cba9F` |
| govChangeTimeLock | 43200 blocks (~1.0d) |
| pendingGov | None |

### Registered Departments
| ID | Description | Address | Can Mint UNDY | Can Set Blacklist |
| --- | --- | --- | --- | --- |
| 1 | Ledger | Ledger (0x9e97A2e527890E690c7FA978696A88EFA868c5D0) | No | No |
| 2 | Mission Control | MissionControl (0x89c8A842CD9428024294cB6a52c28D5EB23e2cBE) | No | No |
| 3 | Lego Book | LegoBook (0x2fD67d572806Fc43B55aFE2ad032702d826450EB) | No | No |
| 4 | Switchboard | Switchboard (0xd6B83538214B7e7d57Cd9faCd260E284a5fe4e11) | No | Yes |
| 5 | Hatchery | Hatchery (0x3ea153bf93367e5933818BB0E7ebE3A9AC0ac193) | No | No |
| 6 | Loot Distributor | LootDistributor (0x23d69D99061acf04c6e86f58692F533E4f039dE8) | No | No |
| 7 | Appraiser | Appraiser (0x8C6521e6f2676a7AdC8484444f161c3538e545e2) | No | No |
| 8 | Wallet Backpack | WalletBackpack (0x10099b1386b434Ea4da1967d952931b645Df6250) | No | No |
| 9 | Billing | Billing (0xB61dDF5a56b4a008f072087BBe411A9B6F576E4e) | No | No |
| 10 | Vault Registry | VaultRegistry (0x1C17ef5Ef2AefcEE958E7e3dC345e96aBfF4e3Cf) | No | No |

================================================================================

<a id="switchboard-registry"></a>
# Switchboard - Config Contracts Registry
Address: 0xd6B83538214B7e7d57Cd9faCd260E284a5fe4e11

### Registry Config (AddressRegistry Module)
| Parameter | Value |
| --- | --- |
| numAddrs (config contracts) | 3 |
| registryChangeTimeLock | 0 blocks (~0s) |

### Governance Settings (LocalGov Module)
| Parameter | Value |
| --- | --- |
| governance | None |
| govChangeTimeLock | 43200 blocks (~1.0d) |
| pendingGov | None |

### Registered Config Contracts
| ID | Description | Address |
| --- | --- | --- |
| 1 | SwitchboardAlpha | SwitchboardAlpha (0xB7d32916c8E7F74f70aF7ECFcb35B04358E50bAc) |
| 2 | SwitchboardBravo | SwitchboardBravo (0x5ed80D2F832da36CCCCd26F856C72b1AdD359B84) |
| 3 | SwitchboardCharlie | SwitchboardCharlie (0xDd7507f7FC1845Ba0f07C3f0164D7b114C150117) |

### SwitchboardAlpha
Address: `0xB7d32916c8E7F74f70aF7ECFcb35B04358E50bAc`

### Governance Settings (LocalGov Module)
| Parameter | Value |
| --- | --- |
| governance | None |
| govChangeTimeLock | 43200 blocks (~1.0d) |
| pendingGov | None |

### Timelock Settings (TimeLock Module)
| Parameter | Value |
| --- | --- |
| minActionTimeLock | 3600 blocks (~2.0h) |
| maxActionTimeLock | 1296000 blocks (~30.0d) |
| actionTimeLock | 0 blocks (~0s) |
| expiration | 1296000 blocks (~30.0d) |

### SwitchboardBravo
Address: `0x5ed80D2F832da36CCCCd26F856C72b1AdD359B84`

### Governance Settings (LocalGov Module)
| Parameter | Value |
| --- | --- |
| governance | None |
| govChangeTimeLock | 43200 blocks (~1.0d) |
| pendingGov | None |

### Timelock Settings (TimeLock Module)
| Parameter | Value |
| --- | --- |
| minActionTimeLock | 3600 blocks (~2.0h) |
| maxActionTimeLock | 1296000 blocks (~30.0d) |
| actionTimeLock | 0 blocks (~0s) |
| expiration | 1296000 blocks (~30.0d) |

### SwitchboardCharlie
Address: `0xDd7507f7FC1845Ba0f07C3f0164D7b114C150117`

### Governance Settings (LocalGov Module)
| Parameter | Value |
| --- | --- |
| governance | None |
| govChangeTimeLock | 43200 blocks (~1.0d) |
| pendingGov | None |

### Timelock Settings (TimeLock Module)
| Parameter | Value |
| --- | --- |
| minActionTimeLock | 3600 blocks (~2.0h) |
| maxActionTimeLock | 1296000 blocks (~30.0d) |
| actionTimeLock | 0 blocks (~0s) |
| expiration | 1296000 blocks (~30.0d) |

================================================================================

<a id="wallet-backpack"></a>
# WalletBackpack - Wallet Components
Address: 0x10099b1386b434Ea4da1967d952931b645Df6250

### Wallet Components
| Component | Address |
| --- | --- |
| kernel | Kernel (0xAdED981a6Dfc6C3e3E4DbBa54362375FDcF7B389) |
| sentinel | Sentinel (0xCCe9B58b7d377631e58d3Bd95f12a35cF49F667b) |
| highCommand | HighCommand (0x06492EA8F83B3a61d71B61FEEF7F167aDD9A78EC) |
| paymaster | Paymaster (0x80bf71E098Dc328D87456c34675C2B4C10a1AFCb) |
| chequeBook | ChequeBook (0xcC939d6b16C6a5f07cde6Bc2bD23cb9B8b7a0Dc9) |
| migrator | Migrator (0xe008114992187138a7C341Db0CD900F88BC0169a) |

### Governance Settings (LocalGov Module)
| Parameter | Value |
| --- | --- |
| governance | None |
| govChangeTimeLock | 43200 blocks (~1.0d) |
| pendingGov | None |

### Timelock Settings (TimeLock Module)
| Parameter | Value |
| --- | --- |
| minActionTimeLock | 3600 blocks (~2.0h) |
| maxActionTimeLock | 1296000 blocks (~30.0d) |
| actionTimeLock | 0 blocks (~0s) |
| expiration | 1296000 blocks (~30.0d) |

================================================================================

<a id="mission-control"></a>
# MissionControl - Core Protocol Configuration
Address: 0x89c8A842CD9428024294cB6a52c28D5EB23e2cBE

<a id="user-wallet-config"></a>

### User Wallet Config
| Parameter | Value |
| --- | --- |
| walletTemplate | UserWalletTemplate (0x880E453Ec494FB17bffba537BeaB4Cc6CD1B7C12) |
| configTemplate | UserWalletConfigTemplate (0xbF7bAdf4c71102cA49b3f82D50348256cE6C10Fb) |
| numUserWalletsAllowed | 100000 |
| enforceCreatorWhitelist | True |
| minKeyActionTimeLock | 21600 blocks (~12.0h) |
| maxKeyActionTimeLock | 604800 blocks (~14.0d) |
| depositRewardsAsset | RIPE (0x2A0a59d6B975828e781EcaC125dBA40d7ee5dDC0) |
| lootClaimCoolOffPeriod | 0 blocks (~0s) |

### Default Transaction Fees
| Parameter | Value |
| --- | --- |
| swapFee | 0.25% |
| stableSwapFee | 0.25% |
| rewardsFee | 20.00% |

### Default Ambassador Revenue Share
| Parameter | Value |
| --- | --- |
| swapRatio | 0.00% |
| rewardsRatio | 0.00% |
| yieldRatio | 0.00% |

### Default Yield Config
| Parameter | Value |
| --- | --- |
| maxYieldIncrease | 5.00% |
| performanceFee | 20.00% |
| ambassadorBonusRatio | 100.00% |
| bonusRatio | 100.00% |
| bonusAsset | RIPE (0x2A0a59d6B975828e781EcaC125dBA40d7ee5dDC0) |

<a id="agent-config"></a>

### Agent Config
| Parameter | Value |
| --- | --- |
| startingAgent | AgentWrapper (0x761fCDFfF8B187901eA11415237632A3F7E0203B) |
| startingAgentActivationLength | 31536000 blocks (~730.0d) |

**Registered Senders (2):**
| Index | Address | Type |
| --- | --- | --- |
| 1 | `0x459f7612F3DFe7b1d7f10c2D01e68dd9AfeA66E9` | AgentSenderGeneric |
| 2 | `0xF02Bc5c9a1A57015C09c4e1B89A273a2849874D3` | AgentSenderSpecial |

<a id="manager-config"></a>

### Manager Config
| Parameter | Value |
| --- | --- |
| managerPeriod | 43200 blocks (~1.0d) |
| managerActivationLength | 1296000 blocks (~30.0d) |
| mustHaveUsdValueOnSwaps | True |
| maxNumSwapsPerPeriod | 2 |
| maxSlippageOnSwaps | 5.00% |
| onlyApprovedYieldOpps | True |

<a id="payee-config"></a>

### Payee Config
| Parameter | Value |
| --- | --- |
| payeePeriod | 1296000 blocks (~30.0d) |
| payeeActivationLength | 15768000 blocks (~365.0d) |

<a id="cheque-config"></a>

### Cheque Config
| Parameter | Value |
| --- | --- |
| maxNumActiveCheques | 3 |
| instantUsdThreshold | Very High (1.00e+14 USD) |
| periodLength | 43200 blocks (~1.0d) |
| expensiveDelayBlocks | 43200 blocks (~1.0d) |
| defaultExpiryBlocks | 86400 blocks (~2.0d) |

<a id="security-signers"></a>

*Could not fetch security signers (not available in this contract version).*

<a id="creator-whitelist"></a>

*Could not fetch creator whitelist (not available in this contract version).*

================================================================================

<a id="loot-distributor"></a>
# LootDistributor - Rewards Configuration
Address: 0x23d69D99061acf04c6e86f58692F533E4f039dE8

### Loot Config
| Parameter | Value |
| --- | --- |
| depositRewards.asset | None |
| depositRewards.amount | 0.00  |
| ripeStakeRatio | 80.00% |
| ripeLockDuration | 7776000 blocks (~180.0d) |
| RIPE_TOKEN | RIPE (0x2A0a59d6B975828e781EcaC125dBA40d7ee5dDC0) |
| RIPE_REGISTRY | `0x6162df1b329E157479F8f1407E888260E0EC3d2b` |

================================================================================

<a id="ledger"></a>
# Ledger - Protocol Data
Address: 0x9e97A2e527890E690c7FA978696A88EFA868c5D0

### Protocol Statistics
| Parameter | Value |
| --- | --- |
| numUserWallets | 254 |

### Global Points
| Parameter | Value |
| --- | --- |
| usdValue | 221.10K USD |
| depositPoints | 143,213,807,037 |
| lastUpdate (block) | 38,963,156 |

================================================================================

---
*Report generated at block 38964843 on 2025-12-02 23:45:24 UTC*
