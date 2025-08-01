# Underscore Protocol Technical Documentation

> **Looking for user documentation?** Visit the [User Documentation](../) for guides on using Underscore Protocol.

## Overview

Underscore Protocol is a comprehensive wallet infrastructure system that provides **non-custodial smart contract wallets with integrated DeFi access, automated management capabilities, and sophisticated permission controls**. The protocol creates programmable wallet instances that can interact with external DeFi protocols through standardized interfaces while maintaining granular security controls and delegation mechanisms.

Each UserWallet functions as an autonomous financial account capable of yield farming, token swapping, liquidity provision, collateralized borrowing, and rewards claiming across integrated protocols. The system supports delegation through Agents (automated managers with signature-based authentication), Payees (authorized payment recipients with configurable limits), and Cheques (time-locked payment promises), enabling complex financial workflows while preserving user control and security.

### Key Features

| Feature                            | Why it matters                                                                                                                                                         |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Smart Contract Wallets**         | Non-custodial wallet contracts that track assets, calculate USD values, and manage yield profits with automatic price updates and comprehensive event logging.         |
| **Lego Partner Integrations**      | Standardized interfaces to external DeFi protocols enabling yield farming, swapping, lending, and liquidity operations through a unified routing system.               |
| **Delegation & Management System** | Agents can execute wallet operations via EIP-712 signatures, Payees can receive payments within configured limits, and Cheques enable time-locked payment commitments. |
| **Comprehensive Permission Model** | WalletConfig contracts control action permissions per signer, enforce spending limits, manage time-locks, and validate transaction recipients.                         |
| **Multi-Asset Yield Tracking**     | Automatic yield profit calculation for both rebasing and non-rebasing assets with price-per-share monitoring and fee distribution to protocol rewards.                 |
| **Modular Security Architecture**  | Time-locked configuration changes, emergency pause controls, ejection modes for asset recovery, and multi-tier governance with protocol-wide coordination.             |
| **Cross-Protocol Operations**      | Multi-hop token swaps, concentrated liquidity management, collateral deposits/withdrawals, debt borrowing/repayment, and reward claiming across integrated protocols.  |

### Protocol Components

The protocol consists of several interconnected systems:

- **Core Infrastructure**: User wallets, configuration management, data storage, and billing systems
- **Lego Partners**: Standardized integrations with external DeFi protocols for yield and trading
- **Registry System**: Coordinated management of protocol components, templates, and permissions
- **Configuration Layer**: Time-locked parameter management with governance oversight
- **Agent System**: Automated management services with configurable strategies and risk controls
- **Wallet Backpack**: Infrastructure services for transaction processing and system maintenance

## Core Infrastructure

Essential protocol functionality for user wallets and system operations.

| Contract                                              | Description                                                                                                                                                              |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [UserWallet.vy](userWallet/UserWallet.md)             | Intelligent wallet instance providing automated yield optimization and DeFi access with per-user configuration                                                           |
| [UserWalletConfig.vy](userWallet/UserWalletConfig.md) | Configuration management for individual wallets including risk parameters and strategy settings                                                                          |
| [Appraiser.vy](core/Appraiser.md)                     | Multi-oracle price aggregation system providing reliable asset valuations with staleness protection                                                                      |
| [Billing.vy](core/Billing.md)                         | Pull payment engine that enables authorized payees and cheque recipients to withdraw funds directly from a UserWallet, with logic to unwind yield positions if necessary |
| [Hatchery.vy](core/Hatchery.md)                       | User wallet factory with trial fund management and creation limit enforcement                                                                                            |
| [LootDistributor.vy](core/LootDistributor.md)         | Rewards distribution system managing loot claiming, deposit points, and user incentives                                                                                  |

## Data & Configuration

Protocol state management and configuration systems.

| Contract                                          | Description                                                                                          |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [Ledger.vy](data/Ledger.md)                       | Central data storage managing user positions, vault tokens, and protocol metrics with indexed access |
| [MissionControl.vy](data/MissionControl.md)       | Configuration hub storing operational parameters, security settings, and protocol defaults           |
| [SwitchboardAlpha.vy](config/SwitchboardAlpha.md) | Configuration management for user wallets, assets, agents, and security with time-locked changes     |
| [SwitchboardBravo.vy](config/SwitchboardBravo.md) | Operational management for fund recovery, loot adjustment, and maintenance functions                 |

## Lego Partners

Modular integrations with external DeFi protocols for yield generation and trading.

### Core Lego Infrastructure

| Contract                           | Description                                                                                        |
| ---------------------------------- | -------------------------------------------------------------------------------------------------- |
| [LegoTools.vy](legos/LegoTools.md) | Universal routing engine providing unified access to all Lego Partners with optimal path discovery |
| [RipeLego.vy](legos/RipeLego.md)   | Integration with Ripe Protocol for yield farming, collateralized borrowing, and RIPE token rewards |

### DEX Lego Partners

| Contract                                              | Description                                                                                             |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| [AeroClassic.vy](legos/dexes/AeroClassic.md)         | Integration with Aerodrome Classic AMM pools for token swapping and liquidity management               |
| [AeroSlipstream.vy](legos/dexes/AeroSlipstream.md)   | Integration with Aerodrome Slipstream (concentrated liquidity) for advanced trading and LP positioning |
| [Curve.vy](legos/dexes/Curve.md)                     | Integration with Curve Finance supporting multiple pool types and optimized stable swaps                |
| [UniswapV2.vy](legos/dexes/UniswapV2.md)             | Integration with Uniswap V2 AMM for token swapping and standard liquidity provision                    |
| [UniswapV3.vy](legos/dexes/UniswapV3.md)             | Integration with Uniswap V3 for concentrated liquidity and NFT-based position management               |

### Yield Lego Partners

| Contract                                            | Description                                                                                                    |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| [AaveV3.vy](legos/yields/AaveV3.md)                | Integration with Aave V3 for interest-bearing aTokens with automatic yield accrual                            |
| [CompoundV3.vy](legos/yields/CompoundV3.md)        | Integration with Compound V3 (Compound III) for single-asset borrowing markets and COMP rewards               |
| [Euler.vy](legos/yields/Euler.md)                  | Integration with Euler Protocol's ERC-4626 vaults for optimized lending with non-rebasing shares              |
| [Fluid.vy](legos/yields/Fluid.md)                  | Integration with Fluid Protocol's liquidity layer for dynamic yield optimization across markets               |
| [Moonwell.vy](legos/yields/Moonwell.md)            | Integration with Moonwell Protocol for cross-chain lending markets with multi-asset reward distribution       |
| [Morpho.vy](legos/yields/Morpho.md)                | Integration with Morpho Protocol's peer-to-peer layer for improved lending rates through MetaMorpho vaults    |

### Lego Data Management

| Contract                                     | Description                                                                                                              |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| [YieldLegoData.vy](modules/YieldLegoData.md) | Data management for yield protocol integrations with bidirectional vault token mappings                                  |
| [DexLegoData.vy](modules/DexLegoData.md)     | Minimal data module for DEX integrations that serves as a foundational module for DEX Legos that provide routing support |

## Registries

Central coordination points for protocol components and authoritative records.

| Contract                                          | Description                                                                            |
| ------------------------------------------------- | -------------------------------------------------------------------------------------- |
| [UndyHq.vy](registries/UndyHq.md)                 | Master protocol registry and governance hub coordinating all system components         |
| [LegoBook.vy](registries/LegoBook.md)             | Registry of approved Lego Partner contracts with validation and integration management |
| [Switchboard.vy](registries/Switchboard.md)       | Time-locked configuration registry managing protocol parameters and access control     |
| [WalletBackpack.vy](registries/WalletBackpack.md) | Infrastructure component registry for wallet support services and system utilities     |

## Agent System

Automated management services with configurable strategies.

| Contract                                 | Description                                                                                            |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| [AgentWrapper.vy](agent/AgentWrapper.md) | Automated portfolio management agent providing strategy execution and risk management for user wallets |

## Wallet Backpack Infrastructure

Modular components that provide specialized functionality for UserWallet operations.

| Contract                                        | Description                                                                                                                                                             |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Kernel.vy](walletBackpack/Kernel.md)           | Whitelist management module that handles the time-locked addition, confirmation, and removal of whitelisted addresses for a UserWallet                                  |
| [HighCommand.vy](walletBackpack/HighCommand.md) | Manager administration module that allows the wallet owner to add, update, and remove managers and configure their specific permissions and spending limits             |
| [ChequeBook.vy](walletBackpack/ChequeBook.md)   | Cheque creation and management module that allows the wallet owner or authorized managers to create, cancel, and configure time-locked payment promises (cheques)       |
| [Paymaster.vy](walletBackpack/Paymaster.md)     | Payee administration module that allows the wallet owner to add, update, and remove authorized payment recipients (payees) and configure their specific spending limits |
| [Sentinel.vy](walletBackpack/Sentinel.md)       | Stateless validation engine that enforces all permission and limit rules for managers, payees, and cheques with no stored state                                         |
| [Migrator.vy](walletBackpack/Migrator.md)       | User wallet migration module that facilitates the secure transfer of all funds and configurations from one UserWallet to another                                        |

## Common Modules

Shared functionality used across multiple contracts.

| Module                                           | Description                                                                                 |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| [Addys.vy](modules/Addys.md)                     | Centralized address resolution providing validated protocol component addresses             |
| [AddressRegistry.vy](modules/AddressRegistry.md) | Flexible registry for managing dynamic address mappings with time-lock controls             |
| [DeptBasics.vy](modules/DeptBasics.md)           | Base functionality for protocol departments including pause controls and access management  |
| [Erc20Token.vy](modules/Erc20Token.md)           | Enhanced ERC20 implementation with advanced features and protocol integration               |
| [LocalGov.vy](modules/LocalGov.md)               | Two-tier governance system enabling both protocol-wide and contract-specific administration |
| [Ownership.vy](modules/Ownership.md)             | Ownership management module with transfer controls and access validation                    |
| [Timelock.vy](modules/Timelock.md)               | Time-delay mechanism for critical configuration changes with expiration windows             |

---

## Getting Started

1. **New Users**: Start with [UserWallet.vy](userWallet/UserWallet.md) to understand wallet functionality
2. **Developers**: Review [UndyHq.vy](registries/UndyHq.md) for protocol architecture overview
3. **Integrators**: Explore [LegoTools.vy](legos/LegoTools.md) for protocol integration patterns
4. **Operators**: Check [SwitchboardAlpha.vy](config/SwitchboardAlpha.md) for configuration management

## Architecture Principles

- **Modular Design**: Reusable modules reduce complexity and enable rapid feature development
- **Department Pattern**: Logical separation of concerns with specialized contract roles
- **Registry Coordination**: Central registries maintain authoritative records and component relationships
- **Time-Locked Governance**: Critical changes require delays and multi-signature approval
- **Multi-Oracle Resilience**: Diverse price sources prevent single points of failure
- **User-Centric Security**: Non-custodial design with user-controlled risk parameters and emergency controls

## Protocol Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   User Wallet   │◄──►│   Lego Partners  │◄──►│  External Protocols │
│                 │    │                  │    │                     │
│ • Yield Optimization │    │ • Standardized   │    │ • Ripe Protocol     │
│ • Asset Management  │    │   Interfaces     │    │ • AMMs & DEXs      │
│ • Risk Controls     │    │ • Route Discovery│    │ • Lending Markets   │
└─────────┬───────┘    └─────────┬────────┘    └─────────────────────┘
          │                      │
          ▼                      ▼
┌─────────────────┐    ┌──────────────────┐
│  Configuration  │    │    Registries    │
│                 │    │                  │
│ • Switchboards  │    │ • UndyHq         │
│ • MissionControl│    │ • LegoBook       │
│ • Time Locks    │    │ • WalletBackpack │
└─────────────────┘    └──────────────────┘
```

The protocol creates a unified interface for DeFi interactions while maintaining the flexibility and composability that makes decentralized finance powerful. Users benefit from automated optimization without sacrificing control, while developers can easily integrate new protocols and strategies through the standardized Lego Partner interface.

## Deployed Contracts

### Base Mainnet

| Contract                 | Address                                                                                                               |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| UndyHq                   | [0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9](https://basescan.org/address/0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9) |
| UserWalletTemplate       | [0x5aB75ef37A30736f38F637a9129348AD327EfD08](https://basescan.org/address/0x5aB75ef37A30736f38F637a9129348AD327EfD08) |
| UserWalletConfigTemplate | [0x0E7064202c4F906Adc4D9F6D3C92470b62F624F1](https://basescan.org/address/0x0E7064202c4F906Adc4D9F6D3C92470b62F624F1) |
| AgentWrapperTemplate     | [0x55eeA103abA26FA85fb1359E2D2e1961d1B46218](https://basescan.org/address/0x55eeA103abA26FA85fb1359E2D2e1961d1B46218) |
| Ledger                   | [0x9e97A2e527890E690c7FA978696A88EFA868c5D0](https://basescan.org/address/0x9e97A2e527890E690c7FA978696A88EFA868c5D0) |
| MissionControl           | [0x910FE9484540fa21B092eE04a478A30A6B342006](https://basescan.org/address/0x910FE9484540fa21B092eE04a478A30A6B342006) |
| LegoBook                 | [0xEaf30ef8a98055981a67222E9088b4dE90B0924A](https://basescan.org/address/0xEaf30ef8a98055981a67222E9088b4dE90B0924A) |
| RipeLego                 | [0xF3F436491e9a0d50F67eBED70D2cE5586F098fB4](https://basescan.org/address/0xF3F436491e9a0d50F67eBED70D2cE5586F098fB4) |
| AaveV3Lego               | [0xb7401d91f1586474164B6c6Df328E3C3A5f24649](https://basescan.org/address/0xb7401d91f1586474164B6c6Df328E3C3A5f24649) |
| CompoundV3Lego           | [0x5Dec90961280605Dd9f3BA19dB0ad57459a86A61](https://basescan.org/address/0x5Dec90961280605Dd9f3BA19dB0ad57459a86A61) |
| EulerLego                | [0x22D16D820c20492597caDb6e36db976Ca16c4156](https://basescan.org/address/0x22D16D820c20492597caDb6e36db976Ca16c4156) |
| FluidLego                | [0x4719731fC7c8A3e17CB3e1EadD4412692432B404](https://basescan.org/address/0x4719731fC7c8A3e17CB3e1EadD4412692432B404) |
| MoonwellLego             | [0x9CdE6b17b88432734f64E760B5Dfbba372b4975F](https://basescan.org/address/0x9CdE6b17b88432734f64E760B5Dfbba372b4975F) |
| MorphoLego               | [0xd7a412C42c7430802e2A60F8145c36A4c6d0bA84](https://basescan.org/address/0xd7a412C42c7430802e2A60F8145c36A4c6d0bA84) |
| AeroClassicLego          | [0x15099c548DDE962ca9Bf520A771fB523818261C3](https://basescan.org/address/0x15099c548DDE962ca9Bf520A771fB523818261C3) |
| AeroSlipstreamLego       | [0x680D5701F6f328C01eF0dad2B1E6eAD224a51D36](https://basescan.org/address/0x680D5701F6f328C01eF0dad2B1E6eAD224a51D36) |
| CurveLego                | [0x01A8Fa2Dbd240f197C820DE22e279150edE5BCF4](https://basescan.org/address/0x01A8Fa2Dbd240f197C820DE22e279150edE5BCF4) |
| UniswapV2Lego            | [0xadB9aa252dD6163f4958443b414177248435c0EC](https://basescan.org/address/0xadB9aa252dD6163f4958443b414177248435c0EC) |
| UniswapV3Lego            | [0x804EC0b82525DE4EA25Bc777a652e8A5c0A97249](https://basescan.org/address/0x804EC0b82525DE4EA25Bc777a652e8A5c0A97249) |
| LegoTools                | [0x2edb54bE8c4F6Cde402CAAe86A809D434b3AFC66](https://basescan.org/address/0x2edb54bE8c4F6Cde402CAAe86A809D434b3AFC66) |
| Switchboard              | [0xe52A6790fC8210DE16847f1FaF55A6146c0BfC7e](https://basescan.org/address/0xe52A6790fC8210DE16847f1FaF55A6146c0BfC7e) |
| SwitchboardAlpha         | [0x2256122FCb6F9789aa356F387435F545c3C52ba5](https://basescan.org/address/0x2256122FCb6F9789aa356F387435F545c3C52ba5) |
| SwitchboardBravo         | [0xf1F5938559884D3c54400b417292B93cd81C368c](https://basescan.org/address/0xf1F5938559884D3c54400b417292B93cd81C368c) |
| Hatchery                 | [0xFd89e4A3D9B97f4dD117c29Fa71c25aD904c590a](https://basescan.org/address/0xFd89e4A3D9B97f4dD117c29Fa71c25aD904c590a) |
| LootDistributor          | [0x3e1B07E220B861e82c15f2E0844e9B0560Ed3067](https://basescan.org/address/0x3e1B07E220B861e82c15f2E0844e9B0560Ed3067) |
| Appraiser                | [0x50B32Df18452986f35Cb5B3d59B2Ea6C101ab2ad](https://basescan.org/address/0x50B32Df18452986f35Cb5B3d59B2Ea6C101ab2ad) |
| WalletBackpack           | [0x0E8D974Cdea08BcAa43421A15B7947Ec901f5CcD](https://basescan.org/address/0x0E8D974Cdea08BcAa43421A15B7947Ec901f5CcD) |
| Kernel                   | [0xf5097601AeeE421F0B1b33deBE788ab2159f6704](https://basescan.org/address/0xf5097601AeeE421F0B1b33deBE788ab2159f6704) |
| HighCommand              | [0xD13E72Dea7a32f487be9a3c6d0B640472Eccb4C8](https://basescan.org/address/0xD13E72Dea7a32f487be9a3c6d0B640472Eccb4C8) |
| Paymaster                | [0x5aDc5a2b5018426243C98Aa52E4696F614274946](https://basescan.org/address/0x5aDc5a2b5018426243C98Aa52E4696F614274946) |
| ChequeBook               | [0x27F769D5eFaddB6f3beb5b51A7F083144a55aE5D](https://basescan.org/address/0x27F769D5eFaddB6f3beb5b51A7F083144a55aE5D) |
| Migrator                 | [0xD30961C917709FE4bC2690A2B69E185acef392bD](https://basescan.org/address/0xD30961C917709FE4bC2690A2B69E185acef392bD) |
| Sentinel                 | [0xA9A71c4eA67f8ff41A4639f71CFc5E79611BBf30](https://basescan.org/address/0xA9A71c4eA67f8ff41A4639f71CFc5E79611BBf30) |
| Billing                  | [0xA44685E909e61072271937871Ca93B43fA7fa654](https://basescan.org/address/0xA44685E909e61072271937871Ca93B43fA7fa654) |
