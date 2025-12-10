================================================================================
# Underscore Vault Parameters

**Generated:** 2025-12-04 20:00:07 UTC
**Block:** 39044466
**Network:** Base Mainnet

## Table of Contents

1. [All Vaults Summary](#all-vaults-summary)
2. [VaultRegistry Configuration](#vault-registry-config)
   - [Registry Settings (AddressRegistry)](#registry-settings)
   - [Governance Settings (LocalGov)](#governance-settings)
3. [Earn Vaults](#earn-vaults)
4. [Leverage Vaults](#leverage-vaults)


================================================================================

<a id="all-vaults-summary"></a>
## All Vaults Summary

| ID | Name | Type | Total Assets (Max) | Total Assets (Low) | HQ |
| --- | --- | --- | --- | --- | --- |
| 1 | Underscore Blue Chip USD | Earn | 312.32K  | 312.28K  | Y |
| 2 | Underscore Blue Chip ETH | Earn | 3.17  | 3.17  | Y |
| 3 | Underscore Blue Chip BTC | Earn | 0.03  | 0.03  | Y |
| 4 | Underscore Blue Chip AERO | Earn | 5.19K  | 5.19K  | Y |
| 5 | Underscore Blue Chip EURC | Earn | 178.13  | 178.08  | Y |
| 6 | Underscore Blue Chip USDS | Earn | 99.12  | 99.12  | Y |
| 7 | Underscore Blue Chip CBETH | Earn | 0.02  | 0.02  | Y |
| 8 | Underscore Blue Chip GHO | Earn | 99.13  | 99.13  | Y |
| 9 | Underscore Leveraged USD | Leverage | 3.00  | 3.00  | Y |
| 10 | Underscore Leveraged cbBTC | Leverage | 0.00  | 0.00  | Y |

================================================================================

<a id="vault-registry-config"></a>
## VaultRegistry Configuration
Address: `0x1C17ef5Ef2AefcEE958E7e3dC345e96aBfF4e3Cf`

<a id="registry-settings"></a>

### Registry Settings (AddressRegistry Module)
| Parameter | Value |
| --- | --- |
| numAddrs (vaults) | 10 |
| registryChangeTimeLock | 0 blocks (~0s) |

<a id="governance-settings"></a>

### Governance Settings (LocalGov Module)
| Parameter | Value |
| --- | --- |
| governance | None |
| govChangeTimeLock | 43200 blocks (~1.0d) |
| pendingGov | None |

================================================================================

<a id="earn-vaults"></a>
## Earn Vaults

### Underscore Blue Chip USD
Address: `0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf`
Symbol: `undyUSD` | Decimals: 6
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01 |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (21):**
| Index | Token |
| --- | --- |
| 1 | MORPHO_SPARK_USDC (0x7BfA7C4f149E7415b73bdeDfe609237e29CBF34A) |
| 2 | MORPHO_STEAKHOUSE_USDC (0xbeeF010f9cb27031ad51e3333f9aF9C6B1228183) |
| 3 | MORPHO_MOONWELL_USDC (0xc1256Ae5FF1cf2719D4937adb3bbCCab2E00A2Ca) |
| 4 | MORPHO_SEAMLESS_USDC (0x616a4E1db48e22028f6bbf20444Cd3b8e3273738) |
| 5 | MORPHO_GAUNTLET_USDC_PRIME (0xeE8F4eC5672F09119b96Ab6fB59C27E1b7e44b61) |
| 6 | `0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2` |
| 7 | MORPHO_IONIC_USDC (0x23479229e52Ab6aaD312D0B03DF9F33B46753B5e) |
| 8 | `0xBEEFA7B88064FeEF0cEe02AAeBBd95D30df3878F` |
| 9 | MORPHO_GAUNTLET_USDC_CORE (0xc0c5689e6f4D256E861F65465b691aeEcC0dEb12) |
| 10 | `0xB7890CEE6CF4792cdCC13489D36D9d42726ab863` |
| 11 | MORPHO_RE7_USDC (0x12AFDeFb2237a5963e7BAb3e2D46ad0eee70406e) |
| 12 | `0x236919F11ff9eA9550A4287696C2FC9e18E6e890` |
| 13 | EULER_USDC (0x0A1a3b5f2041F33522C4efc754a7D096f880eE16) |
| 14 | AAVEV3_USDC (0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB) |
| 15 | COMPOUNDV3_USDC (0xb125E6687d4313864e53df431d5425969c15Eb2F) |
| 16 | FLUID_USDC (0xf42f5795D9ac7e9D757dB633D693cD548Cfd9169) |
| 17 | MOONWELL_USDC (0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22) |
| 18 | FORTY_ACRES_USDC (0xB99B6dF96d4d5448cC0a5B3e0ef7896df9507Cf5) |
| 19 | WASABI_USDC (0x1C4a802FD6B591BB71dAA01D8335e43719048B24) |
| 20 | AVANTIS_USDC (0x944766f715b51967E56aFdE5f0Aa76cEaCc9E7f9) |

### EarnVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 311,028.741798 |
| totalAssets (max) | 312,323.263936 |
| totalAssets (low) | 312,275.723288 |
| sharePrice (1 share =) | 1.004162 |
| numAssets (yield positions) | 6 |
| lastUnderlyingBal | 312,639.12037 |
| pendingYieldRealized | 1,579.423013 |
| claimablePerformanceFees | 315.891644 |
| numManagers | 2 |

**Yield Position Assets (6):**
| Index | Vault Token | Lego ID |
| --- | --- | --- |
| 1 | WASABI_USDC (0x1C4a802FD6B591BB71dAA01D8335e43719048B24) | 15 |
| 2 | FORTY_ACRES_USDC (0xB99B6dF96d4d5448cC0a5B3e0ef7896df9507Cf5) | 14 |
| 3 | `0xBEEFA7B88064FeEF0cEe02AAeBBd95D30df3878F` | 7 |
| 4 | MORPHO_IONIC_USDC (0x23479229e52Ab6aaD312D0B03DF9F33B46753B5e) | 7 |
| 5 | `0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2` | 7 |
| 6 | MOONWELL_USDC (0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22) | 6 |

**Managers (2):**

**Manager 1:** `0x6B014c7BE0fCA7801133Db96737378CCE85230a7`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: UndyHq (0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9)
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

**Manager 2:** `0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: `0xe8c5B195E7634952b375ff633FA98Ca0FaDaC4e5`
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

### Underscore Blue Chip ETH
Address: `0x02981DB1a99A14912b204437e7a2E02679B57668`
Symbol: `undyETH` | Decimals: 18
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.0000025 |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (12):**
| Index | Token |
| --- | --- |
| 1 | MORPHO_MOONWELL_WETH (0xa0E430870c4604CcfC7B38Ca7845B1FF653D0ff1) |
| 2 | MORPHO_SEAMLESS_WETH (0x27D8c7273fd3fcC6956a0B370cE5Fd4A7fc65c18) |
| 3 | MORPHO_IONIC_WETH (0x5A32099837D89E3a794a44fb131CBbAD41f87a8C) |
| 4 | `0x09832347586E238841F49149C84d121Bc2191C53` |
| 5 | MORPHO_GAUNTLET_WETH_CORE (0x6b13c060F13Af1fdB319F52315BbbF3fb1D88844) |
| 6 | MORPHO_RE7_WETH (0xA2Cac0023a4797b4729Db94783405189a4203AFc) |
| 7 | EULER_WETH (0x859160DB5841E5cfB8D3f144C6b3381A85A4b410) |
| 8 | AAVEV3_WETH (0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7) |
| 9 | COMPOUNDV3_WETH (0x46e6b214b524310239732D51387075E0e70970bf) |
| 10 | FLUID_WETH (0x9272D6153133175175Bc276512B2336BE3931CE9) |
| 11 | MOONWELL_WETH (0x628ff693426583D9a7FB391E54366292F509D457) |

### EarnVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 3.164134977557775841 |
| totalAssets (max) | 3.16655340165328969 |
| totalAssets (low) | 3.166527611038985945 |
| sharePrice (1 share =) | 1.000764323934556055 |
| numAssets (yield positions) | 6 |
| lastUnderlyingBal | 3.167128881959222486 |
| pendingYieldRealized | 0.002943758790409847 |
| claimablePerformanceFees | 0.000592069621119203 |
| numManagers | 2 |

**Yield Position Assets (6):**
| Index | Vault Token | Lego ID |
| --- | --- | --- |
| 1 | MORPHO_SEAMLESS_WETH (0x27D8c7273fd3fcC6956a0B370cE5Fd4A7fc65c18) | 7 |
| 2 | MORPHO_IONIC_WETH (0x5A32099837D89E3a794a44fb131CBbAD41f87a8C) | 7 |
| 3 | MORPHO_MOONWELL_WETH (0xa0E430870c4604CcfC7B38Ca7845B1FF653D0ff1) | 7 |
| 4 | COMPOUNDV3_WETH (0x46e6b214b524310239732D51387075E0e70970bf) | 3 |
| 5 | MORPHO_GAUNTLET_WETH_CORE (0x6b13c060F13Af1fdB319F52315BbbF3fb1D88844) | 7 |
| 6 | AAVEV3_WETH (0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7) | 2 |

**Managers (2):**

**Manager 1:** `0x6B014c7BE0fCA7801133Db96737378CCE85230a7`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: UndyHq (0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9)
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

**Manager 2:** `0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: `0xe8c5B195E7634952b375ff633FA98Ca0FaDaC4e5`
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

### Underscore Blue Chip BTC
Address: `0x3fb0fC9D3Ddd543AD1b748Ed2286a022f4638493`
Symbol: `undyBTC` | Decimals: 8
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.0000001 |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (7):**
| Index | Token |
| --- | --- |
| 1 | MORPHO_MOONWELL_CBBTC (0x543257eF2161176D7C8cD90BA65C2d4CaEF5a796) |
| 2 | MORPHO_GAUNTLET_CBBTC_CORE (0x6770216aC60F634483Ec073cBABC4011c94307Cb) |
| 3 | MORPHO_SEAMLESS_CBBTC (0x5a47C803488FE2BB0A0EAaf346b420e4dF22F3C7) |
| 4 | EULER_CBBTC (0x882018411Bc4A020A879CEE183441fC9fa5D7f8B) |
| 5 | AAVEV3_CBBTC (0xBdb9300b7CDE636d9cD4AFF00f6F009fFBBc8EE6) |
| 6 | MOONWELL_CBBTC (0xF877ACaFA28c19b96727966690b2f44d35aD5976) |

### EarnVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 0.02565143 |
| totalAssets (max) | 0.02565275 |
| totalAssets (low) | 0.0256526 |
| sharePrice (1 share =) | 1.00005145 |
| numAssets (yield positions) | 4 |
| lastUnderlyingBal | 0.02565357 |
| pendingYieldRealized | 0.00000418 |
| claimablePerformanceFees | 0.00000083 |
| numManagers | 2 |

**Yield Position Assets (4):**
| Index | Vault Token | Lego ID |
| --- | --- | --- |
| 1 | MORPHO_GAUNTLET_CBBTC_CORE (0x6770216aC60F634483Ec073cBABC4011c94307Cb) | 7 |
| 2 | MORPHO_MOONWELL_CBBTC (0x543257eF2161176D7C8cD90BA65C2d4CaEF5a796) | 7 |
| 3 | MORPHO_SEAMLESS_CBBTC (0x5a47C803488FE2BB0A0EAaf346b420e4dF22F3C7) | 7 |
| 4 | MOONWELL_CBBTC (0xF877ACaFA28c19b96727966690b2f44d35aD5976) | 6 |

**Managers (2):**

**Manager 1:** `0x6B014c7BE0fCA7801133Db96737378CCE85230a7`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: UndyHq (0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9)
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

**Manager 2:** `0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: `0xe8c5B195E7634952b375ff633FA98Ca0FaDaC4e5`
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

### Underscore Blue Chip AERO
Address: `0x96F1a7ce331F40afe866F3b707c223e377661087`
Symbol: `undyAERO` | Decimals: 18
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01 |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (3):**
| Index | Token |
| --- | --- |
| 1 | COMPOUNDV3_AERO (0x784efeB622244d2348d4F2522f8860B96fbEcE89) |
| 2 | MOONWELL_AERO (0x73902f619CEB9B31FD8EFecf435CbDf89E369Ba6) |

### EarnVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 5,181.2564458691767868 |
| totalAssets (max) | 5,186.891046564884163672 |
| totalAssets (low) | 5,186.719511213886107726 |
| sharePrice (1 share =) | 1.00108749697193633 |
| numAssets (yield positions) | 2 |
| lastUnderlyingBal | 5,188.021384151168604149 |
| pendingYieldRealized | 6.760117209789870962 |
| claimablePerformanceFees | 1.407444905876493513 |
| numManagers | 2 |

**Yield Position Assets (2):**
| Index | Vault Token | Lego ID |
| --- | --- | --- |
| 1 | COMPOUNDV3_AERO (0x784efeB622244d2348d4F2522f8860B96fbEcE89) | 3 |
| 2 | MOONWELL_AERO (0x73902f619CEB9B31FD8EFecf435CbDf89E369Ba6) | 6 |

**Managers (2):**

**Manager 1:** `0x6B014c7BE0fCA7801133Db96737378CCE85230a7`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: UndyHq (0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9)
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

**Manager 2:** `0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: `0xe8c5B195E7634952b375ff633FA98Ca0FaDaC4e5`
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

### Underscore Blue Chip EURC
Address: `0x1cb8DAB80f19fC5Aca06C2552AECd79015008eA8`
Symbol: `undyEURC` | Decimals: 6
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01 |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (8):**
| Index | Token |
| --- | --- |
| 1 | MORPHO_MOONWELL_EURC (0xf24608E0CCb972b0b0f4A6446a0BBf58c701a026) |
| 2 | MORPHO_STEAKHOUSE_EURC (0xBeEF086b8807Dc5E5A1740C5E3a7C4c366eA6ab5) |
| 3 | MORPHO_GAUNTLET_EURC_CORE (0x1c155be6bC51F2c37d472d4C2Eba7a637806e122) |
| 4 | EULER_EURC (0x9ECD9fbbdA32b81dee51AdAed28c5C5039c87117) |
| 5 | `0x90DA57E0A6C0d166Bf15764E03b83745Dc90025B` |
| 6 | FLUID_EURC (0x1943FA26360f038230442525Cf1B9125b5DCB401) |
| 7 | MOONWELL_EURC (0xb682c840B5F4FC58B20769E691A6fa1305A501a2) |

### EarnVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 177.854931 |
| totalAssets (max) | 178.134545 |
| totalAssets (low) | 178.082421 |
| sharePrice (1 share =) | 1.001572 |
| numAssets (yield positions) | 5 |
| lastUnderlyingBal | 178.170271 |
| pendingYieldRealized | 0.314429 |
| claimablePerformanceFees | 0.069675 |
| numManagers | 2 |

**Yield Position Assets (5):**
| Index | Vault Token | Lego ID |
| --- | --- | --- |
| 1 | MORPHO_STEAKHOUSE_EURC (0xBeEF086b8807Dc5E5A1740C5E3a7C4c366eA6ab5) | 7 |
| 2 | FLUID_EURC (0x1943FA26360f038230442525Cf1B9125b5DCB401) | 5 |
| 3 | MOONWELL_EURC (0xb682c840B5F4FC58B20769E691A6fa1305A501a2) | 6 |
| 4 | MORPHO_GAUNTLET_EURC_CORE (0x1c155be6bC51F2c37d472d4C2Eba7a637806e122) | 7 |
| 5 | EULER_EURC (0x9ECD9fbbdA32b81dee51AdAed28c5C5039c87117) | 4 |

**Managers (2):**

**Manager 1:** `0x6B014c7BE0fCA7801133Db96737378CCE85230a7`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: UndyHq (0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9)
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

**Manager 2:** `0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: `0xe8c5B195E7634952b375ff633FA98Ca0FaDaC4e5`
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

### Underscore Blue Chip USDS
Address: `0xaA0C35937a193ca81A64b3cFd5892dac384d22bB`
Symbol: `undyUSDS` | Decimals: 18
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01 |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (5):**
| Index | Token |
| --- | --- |
| 1 | `0x2c776041CCFe903071AF44aa147368a9c8EEA518` |
| 2 | MOONWELL_USDS (0xb6419c6C2e60c4025D6D06eE4F913ce89425a357) |
| 3 | EULER_USDS (0x556d518FDFDCC4027A3A1388699c5E11AC201D8b) |
| 4 | SUSDS (0x5875eEE11Cf8398102FdAd704C9E96607675467a) |

### EarnVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 99.125 |
| totalAssets (max) | 99.125 |
| totalAssets (low) | 99.125 |
| sharePrice (1 share =) | 1 |
| numAssets (yield positions) | 0 |
| lastUnderlyingBal | 0 |
| pendingYieldRealized | 0 |
| claimablePerformanceFees | 0 |
| numManagers | 2 |

**Managers (2):**

**Manager 1:** `0x6B014c7BE0fCA7801133Db96737378CCE85230a7`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: UndyHq (0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9)
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

**Manager 2:** `0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: `0xe8c5B195E7634952b375ff633FA98Ca0FaDaC4e5`
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

### Underscore Blue Chip CBETH
Address: `0xFe75aD75AD59a5c80de5AE0726Feee89567F080d`
Symbol: `undyCBETH` | Decimals: 18
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.0000025 |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (4):**
| Index | Token |
| --- | --- |
| 1 | AAVEV3_CBETH (0xcf3D55c10DB69f28fD1A75Bd73f3D8A2d9c595ad) |
| 2 | MOONWELL_CBETH (0x3bf93770f2d4a794c3d9EBEfBAeBAE2a8f09A5E5) |
| 3 | `0x358f25F82644eaBb441d0df4AF8746614fb9ea49` |

### EarnVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 0.021864298733844493 |
| totalAssets (max) | 0.021864298733844493 |
| totalAssets (low) | 0.021864298733844493 |
| sharePrice (1 share =) | 1 |
| numAssets (yield positions) | 0 |
| lastUnderlyingBal | 0 |
| pendingYieldRealized | 0 |
| claimablePerformanceFees | 0 |
| numManagers | 2 |

**Managers (2):**

**Manager 1:** `0x6B014c7BE0fCA7801133Db96737378CCE85230a7`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: UndyHq (0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9)
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

**Manager 2:** `0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: `0xe8c5B195E7634952b375ff633FA98Ca0FaDaC4e5`
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

### Underscore Blue Chip GHO
Address: `0x220b8B08c8CfD6975ed203AA26887c0AA5a8cf44`
Symbol: `undyGHO` | Decimals: 18
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 0.01 |
| performanceFee | 20.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | False |
| shouldEnforceAllowlist | False |

**Approved Vault Tokens (3):**
| Index | Token |
| --- | --- |
| 1 | AAVEV3_GHO (0x067ae75628177FD257c2B1e500993e1a0baBcBd1) |
| 2 | `0x8DdbfFA3CFda2355a23d6B11105AC624BDbE3631` |

### EarnVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 99.1284528365220865 |
| totalAssets (max) | 99.1284528365220865 |
| totalAssets (low) | 99.1284528365220865 |
| sharePrice (1 share =) | 1 |
| numAssets (yield positions) | 0 |
| lastUnderlyingBal | 0 |
| pendingYieldRealized | 0 |
| claimablePerformanceFees | 0 |
| numManagers | 2 |

**Managers (2):**

**Manager 1:** `0x6B014c7BE0fCA7801133Db96737378CCE85230a7`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: UndyHq (0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9)
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

**Manager 2:** `0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b`
  - Type: EarnVaultAgent
  - groupId: 1
  - owner: `0xe8c5B195E7634952b375ff633FA98Ca0FaDaC4e5`
  - ownershipTimeLock: 3600 blocks (~2.0h)
  - MIN/MAX_OWNERSHIP_TIMELOCK: 3600 blocks (~2.0h) / 1296000 blocks (~30.0d)
  - pendingOwner: None

================================================================================

<a id="leverage-vaults"></a>
## Leverage Vaults

### Underscore Leveraged USD
Address: `0x4B018fE4ad63d3fDf81DbCc77168c64676F244cE`
Symbol: `undyLevgUSD` | Decimals: 6
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 100,000 |
| performanceFee | 0.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | True |
| shouldEnforceAllowlist | True |

### LevgVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 3 |
| totalAssets (max) | 3.004461 |
| totalAssets (low) | 3.004297 |
| sharePrice (1 share =) | 1.001487 |
| collateralAsset.vaultToken | Underscore Blue Chip USD (0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf) |
| collateralAsset.ripeVaultId | 5 |
| leverageAsset.vaultToken | Underscore Blue Chip USD (0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf) |
| leverageAsset.ripeVaultId | 5 |
| maxDebtRatio | 0.00% |
| netUserCapital | 3 |
| usdcSlippageAllowed | 1.00% |
| greenSlippageAllowed | 1.00% |
| levgVaultHelper | `0xCCE531215D9841E3D69b1Db4e31e1005331DAe4c` |
| numManagers | 2 |

### LevgVaultHelper Configuration
| Parameter | Value |
| --- | --- |
| RIPE_REGISTRY | `0x6162df1b329E157479F8f1407E888260E0EC3d2b` |
| GREEN_TOKEN | GREEN (0xd1Eac76497D06Cf15475A5e3984D5bC03de7C707) |
| SAVINGS_GREEN | SAVINGS_GREEN (0xaa0f13488CE069A7B5a099457c753A7CFBE04d36) |
| USDC | USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) |

**Managers (2):**

**Manager 1:** `0xaDd738FD4e8b43c7923E170d1789f5E2140Cba9F`
  - Type: Unknown (not EarnVaultAgent)

**Manager 2:** `0x699308fEb03b9AF84C52F2d67cAcE4ea847aB73E`
  - Type: Unknown (not EarnVaultAgent)

### Underscore Leveraged cbBTC
Address: `0x936c3C493Dc45D0f4D2FA36C7640f3BCABd64B4B`
Symbol: `undyLevgCBBTC` | Decimals: 8
UNDY_HQ: Verified

### VaultConfig (from VaultRegistry)
| Parameter | Value |
| --- | --- |
| canDeposit | True |
| canWithdraw | True |
| maxDepositAmount | Unlimited |
| isVaultOpsFrozen | False |
| redemptionBuffer | 2.00% |
| minYieldWithdrawAmount | 1,000 |
| performanceFee | 0.00% |
| shouldAutoDeposit | True |
| defaultTargetVaultToken | None |
| isLeveragedVault | True |
| shouldEnforceAllowlist | True |

### LevgVaultWallet Storage
| Parameter | Value |
| --- | --- |
| totalSupply (shares) | 0 |
| totalAssets (max) | 0 |
| totalAssets (low) | 0 |
| sharePrice (1 share =) | 1 |
| collateralAsset.vaultToken | Underscore Blue Chip BTC (0x3fb0fC9D3Ddd543AD1b748Ed2286a022f4638493) |
| collateralAsset.ripeVaultId | 5 |
| leverageAsset.vaultToken | Underscore Blue Chip USD (0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf) |
| leverageAsset.ripeVaultId | 5 |
| maxDebtRatio | 0.00% |
| netUserCapital | 0 |
| usdcSlippageAllowed | 1.00% |
| greenSlippageAllowed | 1.00% |
| levgVaultHelper | `0xCCE531215D9841E3D69b1Db4e31e1005331DAe4c` |
| numManagers | 1 |

### LevgVaultHelper Configuration
| Parameter | Value |
| --- | --- |
| RIPE_REGISTRY | `0x6162df1b329E157479F8f1407E888260E0EC3d2b` |
| GREEN_TOKEN | GREEN (0xd1Eac76497D06Cf15475A5e3984D5bC03de7C707) |
| SAVINGS_GREEN | SAVINGS_GREEN (0xaa0f13488CE069A7B5a099457c753A7CFBE04d36) |
| USDC | USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) |

**Managers (1):**

**Manager 1:** `0xaDd738FD4e8b43c7923E170d1789f5E2140Cba9F`
  - Type: Unknown (not EarnVaultAgent)

================================================================================

---
*Report generated at block 39044466 on 2025-12-04 20:02:08 UTC*
