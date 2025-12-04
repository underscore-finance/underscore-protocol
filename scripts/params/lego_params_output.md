================================================================================
# Underscore Protocol Lego Parameters

**Generated:** 2025-12-04 20:01:30 UTC
**Block:** 39044543
**Network:** Base Mainnet

## Table of Contents

1. [LegoBook Registry](#lego-book)
   - [Registry Config](#registry-config)
   - [Governance Settings](#governance-settings)
   - [Registered Legos](#registered-legos)
2. **Yield Legos**
   - [Ripe Protocol](#ripe-protocol)
   - [Aave v3](#aave-v3)
   - [Compound v3](#compound-v3)
   - [Euler](#euler)
   - [Fluid](#fluid)
   - [Moonwell](#moonwell)
   - [Morpho](#morpho)
   - [Underscore Lego](#underscore-lego)
   - [40 Acres](#40-acres)
   - [Wasabi](#wasabi)
   - [Avantis](#avantis)
   - [Sky Psm](#sky-psm)
3. **DEX Legos**
   - [Aero Classic](#aero-classic)
   - [Aero Slipstream](#aero-slipstream)
   - [Curve](#curve)
   - [Uniswap V2](#uniswap-v2)
   - [Uniswap V3](#uniswap-v3)


================================================================================

<a id="lego-book"></a>
# LegoBook - Lego Registry
Address: 0x2fD67d572806Fc43B55aFE2ad032702d826450EB

### Registry Config (AddressRegistry Module)
| Parameter | Value |
| --- | --- |
| legoTools | None |
| numAddrs (legos) | 17 |
| registryChangeTimeLock | 0 blocks (~0s) |

### Governance Settings (LocalGov Module)
| Parameter | Value |
| --- | --- |
| governance | None |
| govChangeTimeLock | 43200 blocks (~1.0d) |
| pendingGov | None |

### Registered Legos
| ID | Description | Address |
| --- | --- | --- |
| 1 | Ripe Protocol | `0x272812fC816a6a8C1A2988b24D06878493459A54` |
| 2 | Aave v3 | `0xac80b9465d70AAFBe492A08baeA5c6e9d77b1478` |
| 3 | Compound v3 | `0x590FB39919c5F0323a93B54f2634d010b6ECfbA7` |
| 4 | Euler | `0x7f52A8bCF7589e157961dbc072e1C5E45A3F4fd6` |
| 5 | Fluid | `0x67E7bcC1deBd060251a9ECeA37002a3986E74f93` |
| 6 | Moonwell | `0x0657CF4683870b8420bB8Da57db83e5F9A1ad804` |
| 7 | Morpho | `0x14852dcEEA98d5E781335bA8ea8d4B3a14508868` |
| 8 | Aero Classic | `0x43B2a72595016D765E2A66e4c2Cf3026619784D1` |
| 9 | Aero Slipstream | `0x2DD267Ab1BA631E93e7c6a9EA6fbcc48882770bd` |
| 10 | Curve | `0x7192867D67329800345750f5A281Ce1352C3dF65` |
| 11 | Uniswap V2 | `0x95979aEF0F70887f31701944b658948890F56fd7` |
| 12 | Uniswap V3 | `0xEa1f7604E751b54AF321636DBc2dc75C0045e7A5` |
| 13 | Underscore Lego | `0x0f79a5A21dC0829ce3B4C72d75a94f67927Af9E9` |
| 14 | 40 Acres | `0x39F5EDd73ce1682Da63C92C34fBbBEdB07156514` |
| 15 | Wasabi | `0xe67Ef17B6c82a555CB040173273FB271fcc43BEd` |
| 16 | Avantis | `0xc88CD884bdFa8F2D93e32a13EE16543b8a2CF1f0` |
| 17 | Sky Psm | `0xEe7B4F2338389A6453E85a65976F3241986492CF` |

================================================================================

# Yield Legos

Legos that generate yield through lending protocols and yield vaults.

================================================================================

<a id="ripe-protocol"></a>
# Ripe Protocol
Address: `0x272812fC816a6a8C1A2988b24D06878493459A54`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| GREEN (0xd1Eac76497D06Cf15475A5e3984D5bC03de7C707) | SAVINGS_GREEN (0xaa0f13488CE069A7B5a099457c753A7CFBE04d36) | 18 |

================================================================================

<a id="aave-v3"></a>
# Aave v3
Address: `0xac80b9465d70AAFBe492A08baeA5c6e9d77b1478`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| WETH (0x4200000000000000000000000000000000000006) | AAVEV3_WETH (0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7) | 18 |
| EURC (0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42) | aBasEURC (0x90DA57E0A6C0d166Bf15764E03b83745Dc90025B) | 6 |

================================================================================

<a id="compound-v3"></a>
# Compound v3
Address: `0x590FB39919c5F0323a93B54f2634d010b6ECfbA7`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631) | COMPOUNDV3_AERO (0x784efeB622244d2348d4F2522f8860B96fbEcE89) | 18 |
| WETH (0x4200000000000000000000000000000000000006) | COMPOUNDV3_WETH (0x46e6b214b524310239732D51387075E0e70970bf) | 18 |

================================================================================

<a id="euler"></a>
# Euler
Address: `0x7f52A8bCF7589e157961dbc072e1C5E45A3F4fd6`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| EURC (0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42) | EULER_EURC (0x9ECD9fbbdA32b81dee51AdAed28c5C5039c87117) | 6 |

================================================================================

<a id="fluid"></a>
# Fluid
Address: `0x67E7bcC1deBd060251a9ECeA37002a3986E74f93`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| EURC (0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42) | FLUID_EURC (0x1943FA26360f038230442525Cf1B9125b5DCB401) | 6 |
| WETH (0x4200000000000000000000000000000000000006) | FLUID_WETH (0x9272D6153133175175Bc276512B2336BE3931CE9) | 18 |

================================================================================

<a id="moonwell"></a>
# Moonwell
Address: `0x0657CF4683870b8420bB8Da57db83e5F9A1ad804`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| EURC (0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42) | MOONWELL_EURC (0xb682c840B5F4FC58B20769E691A6fa1305A501a2) | 8 |
| USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | MOONWELL_USDC (0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22) | 8 |
| AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631) | MOONWELL_AERO (0x73902f619CEB9B31FD8EFecf435CbDf89E369Ba6) | 8 |
| CBBTC (0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf) | MOONWELL_CBBTC (0xF877ACaFA28c19b96727966690b2f44d35aD5976) | 8 |

================================================================================

<a id="morpho"></a>
# Morpho
Address: `0x14852dcEEA98d5E781335bA8ea8d4B3a14508868`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | MORPHO_IONIC_USDC (0x23479229e52Ab6aaD312D0B03DF9F33B46753B5e) | 18 |
| USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | MORPHO_RE7_USDC (0x12AFDeFb2237a5963e7BAb3e2D46ad0eee70406e) | 18 |
| USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | bbqUSDC (0xBEEFA7B88064FeEF0cEe02AAeBBd95D30df3878F) | 18 |
| USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | steakUSDC (0xBEEFE94c8aD530842bfE7d8B397938fFc1cb83b2) | 18 |
| USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | gtUSDCf (0x236919F11ff9eA9550A4287696C2FC9e18E6e890) | 18 |
| CBBTC (0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf) | MORPHO_MOONWELL_CBBTC (0x543257eF2161176D7C8cD90BA65C2d4CaEF5a796) | 18 |
| CBBTC (0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf) | MORPHO_GAUNTLET_CBBTC_CORE (0x6770216aC60F634483Ec073cBABC4011c94307Cb) | 18 |
| CBBTC (0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf) | MORPHO_SEAMLESS_CBBTC (0x5a47C803488FE2BB0A0EAaf346b420e4dF22F3C7) | 18 |
| EURC (0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42) | MORPHO_GAUNTLET_EURC_CORE (0x1c155be6bC51F2c37d472d4C2Eba7a637806e122) | 18 |
| EURC (0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42) | MORPHO_STEAKHOUSE_EURC (0xBeEF086b8807Dc5E5A1740C5E3a7C4c366eA6ab5) | 18 |
| WETH (0x4200000000000000000000000000000000000006) | MORPHO_SEAMLESS_WETH (0x27D8c7273fd3fcC6956a0B370cE5Fd4A7fc65c18) | 18 |
| WETH (0x4200000000000000000000000000000000000006) | MORPHO_IONIC_WETH (0x5A32099837D89E3a794a44fb131CBbAD41f87a8C) | 18 |
| WETH (0x4200000000000000000000000000000000000006) | MORPHO_MOONWELL_WETH (0xa0E430870c4604CcfC7B38Ca7845B1FF653D0ff1) | 18 |
| WETH (0x4200000000000000000000000000000000000006) | MORPHO_GAUNTLET_WETH_CORE (0x6b13c060F13Af1fdB319F52315BbbF3fb1D88844) | 18 |

================================================================================

<a id="underscore-lego"></a>
# Underscore Lego
Address: `0x0f79a5A21dC0829ce3B4C72d75a94f67927Af9E9`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | undyUSD (0xb33852cfd0c22647AAC501a6Af59Bc4210a686Bf) | 6 |
| AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631) | undyAERO (0x96F1a7ce331F40afe866F3b707c223e377661087) | 18 |
| WETH (0x4200000000000000000000000000000000000006) | undyETH (0x02981DB1a99A14912b204437e7a2E02679B57668) | 18 |
| EURC (0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42) | undyEURC (0x1cb8DAB80f19fC5Aca06C2552AECd79015008eA8) | 6 |
| CBBTC (0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf) | undyBTC (0x3fb0fC9D3Ddd543AD1b748Ed2286a022f4638493) | 8 |

================================================================================

<a id="40-acres"></a>
# 40 Acres
Address: `0x39F5EDd73ce1682Da63C92C34fBbBEdB07156514`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | FORTY_ACRES_USDC (0xB99B6dF96d4d5448cC0a5B3e0ef7896df9507Cf5) | 6 |

================================================================================

<a id="wasabi"></a>
# Wasabi
Address: `0xe67Ef17B6c82a555CB040173273FB271fcc43BEd`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

### Registered Assets & Vault Tokens
| Underlying Asset | Vault Token | Decimals |
| --- | --- | --- |
| USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) | WASABI_USDC (0x1C4a802FD6B591BB71dAA01D8335e43719048B24) | 6 |

================================================================================

<a id="avantis"></a>
# Avantis
Address: `0xc88CD884bdFa8F2D93e32a13EE16543b8a2CF1f0`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

*No registered assets*

================================================================================

<a id="sky-psm"></a>
# Sky Psm
Address: `0xEe7B4F2338389A6453E85a65976F3241986492CF`

### Snapshot Price Config (YieldLegoData Module)
| Parameter | Value |
| --- | --- |
| minSnapshotDelay | 600 seconds (10 min) |
| maxNumSnapshots | 20 |
| maxUpsideDeviation | 10.00% |
| staleTime | 86,400 seconds (24 hours) |

*No registered assets*

================================================================================

# DEX Legos

Legos for decentralized exchange swaps. These do not have yield data.

================================================================================

<a id="aero-classic"></a>
# Aero Classic
Address: `0x43B2a72595016D765E2A66e4c2Cf3026619784D1`

*DEX Lego - used for swaps, not yield generation*

================================================================================

<a id="aero-slipstream"></a>
# Aero Slipstream
Address: `0x2DD267Ab1BA631E93e7c6a9EA6fbcc48882770bd`

*DEX Lego - used for swaps, not yield generation*

================================================================================

<a id="curve"></a>
# Curve
Address: `0x7192867D67329800345750f5A281Ce1352C3dF65`

*DEX Lego - used for swaps, not yield generation*

================================================================================

<a id="uniswap-v2"></a>
# Uniswap V2
Address: `0x95979aEF0F70887f31701944b658948890F56fd7`

*DEX Lego - used for swaps, not yield generation*

================================================================================

<a id="uniswap-v3"></a>
# Uniswap V3
Address: `0xEa1f7604E751b54AF321636DBc2dc75C0045e7A5`

*DEX Lego - used for swaps, not yield generation*

================================================================================

---
*Report generated at block 39044543 on 2025-12-04 20:02:15 UTC*
