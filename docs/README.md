# Underscore Protocol Technical Documentation

## Overview  

Underscore Protocol is a comprehensive wallet infrastructure system that provides **non-custodial smart contract wallets with integrated DeFi access, automated management capabilities, and sophisticated permission controls**. The protocol creates programmable wallet instances that can interact with external DeFi protocols through standardized interfaces while maintaining granular security controls and delegation mechanisms.

Each UserWallet functions as an autonomous financial account capable of yield farming, token swapping, liquidity provision, collateralized borrowing, and rewards claiming across integrated protocols. The system supports delegation through Agents (automated managers with signature-based authentication), Payees (authorized payment recipients with configurable limits), and Cheques (time-locked payment promises), enabling complex financial workflows while preserving user control and security.

### Key Features  

| Feature | Why it matters |
|---------|----------------|
| **Smart Contract Wallets** | Non-custodial wallet contracts that track assets, calculate USD values, and manage yield profits with automatic price updates and comprehensive event logging. |
| **Lego Partner Integrations** | Standardized interfaces to external DeFi protocols enabling yield farming, swapping, lending, and liquidity operations through a unified routing system. |
| **Delegation & Management System** | Agents can execute wallet operations via EIP-712 signatures, Payees can receive payments within configured limits, and Cheques enable time-locked payment commitments. |
| **Comprehensive Permission Model** | WalletConfig contracts control action permissions per signer, enforce spending limits, manage time-locks, and validate transaction recipients. |
| **Multi-Asset Yield Tracking** | Automatic yield profit calculation for both rebasing and non-rebasing assets with price-per-share monitoring and fee distribution to protocol rewards. |
| **Modular Security Architecture** | Time-locked configuration changes, emergency pause controls, ejection modes for asset recovery, and multi-tier governance with protocol-wide coordination. |
| **Cross-Protocol Operations** | Multi-hop token swaps, concentrated liquidity management, collateral deposits/withdrawals, debt borrowing/repayment, and reward claiming across integrated protocols. |

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

| Contract | Description |
|----------|-------------|
| [UserWallet.vy](userWallet/UserWallet.md) | Intelligent wallet instance providing automated yield optimization and DeFi access with per-user configuration |
| [UserWalletConfig.vy](userWallet/UserWalletConfig.md) | Configuration management for individual wallets including risk parameters and strategy settings |
| [Appraiser.vy](core/Appraiser.md) | Multi-oracle price aggregation system providing reliable asset valuations with staleness protection |
| [Billing.vy](core/Billing.md) | Pull payment engine that enables authorized payees and cheque recipients to withdraw funds directly from a UserWallet, with logic to unwind yield positions if necessary |
| [Hatchery.vy](core/Hatchery.md) | User wallet factory with trial fund management and creation limit enforcement |
| [LootDistributor.vy](core/LootDistributor.md) | Rewards distribution system managing loot claiming, deposit points, and user incentives |

## Data & Configuration

Protocol state management and configuration systems.

| Contract | Description |
|----------|-------------|
| [Ledger.vy](data/Ledger.md) | Central data storage managing user positions, vault tokens, and protocol metrics with indexed access |
| [MissionControl.vy](data/MissionControl.md) | Configuration hub storing operational parameters, security settings, and protocol defaults |
| [SwitchboardAlpha.vy](config/SwitchboardAlpha.md) | Configuration management for user wallets, assets, agents, and security with time-locked changes |
| [SwitchboardBravo.vy](config/SwitchboardBravo.md) | Operational management for fund recovery, loot adjustment, and maintenance functions |

## Lego Partners

Modular integrations with external DeFi protocols for yield generation and trading.

| Contract | Description |
|----------|-------------|
| [LegoTools.vy](legos/LegoTools.md) | Universal routing engine providing unified access to all Lego Partners with optimal path discovery |
| [RipeLego.vy](legos/RipeLego.md) | Integration with Ripe Protocol for yield farming, collateralized borrowing, and RIPE token rewards |

### Lego Data Management

| Contract | Description |
|----------|-------------|
| [YieldLegoData.vy](modules/YieldLegoData.md) | Data management for yield protocol integrations with bidirectional vault token mappings |
| [DexLegoData.vy](modules/DexLegoData.md) | Minimal data module for DEX integrations that serves as a foundational module for DEX Legos that provide routing support |

## Registries

Central coordination points for protocol components and authoritative records.

| Contract | Description |
|----------|-------------|
| [UndyHq.vy](registries/UndyHq.md) | Master protocol registry and governance hub coordinating all system components |
| [LegoBook.vy](registries/LegoBook.md) | Registry of approved Lego Partner contracts with validation and integration management |
| [Switchboard.vy](registries/Switchboard.md) | Time-locked configuration registry managing protocol parameters and access control |
| [WalletBackpack.vy](registries/WalletBackpack.md) | Infrastructure component registry for wallet support services and system utilities |

## Agent System

Automated management services with configurable strategies.

| Contract | Description |
|----------|-------------|
| [AgentWrapper.vy](agent/AgentWrapper.md) | Automated portfolio management agent providing strategy execution and risk management for user wallets |

## Wallet Backpack Infrastructure

Modular components that provide specialized functionality for UserWallet operations.

| Contract | Description |
|----------|-------------|
| [Kernel.vy](walletBackpack/Kernel.md) | Whitelist management module that handles the time-locked addition, confirmation, and removal of whitelisted addresses for a UserWallet |
| [HighCommand.vy](walletBackpack/HighCommand.md) | Manager administration module that allows the wallet owner to add, update, and remove managers and configure their specific permissions and spending limits |
| [ChequeBook.vy](walletBackpack/ChequeBook.md) | Cheque creation and management module that allows the wallet owner or authorized managers to create, cancel, and configure time-locked payment promises (cheques) |
| [Paymaster.vy](walletBackpack/Paymaster.md) | Payee administration module that allows the wallet owner to add, update, and remove authorized payment recipients (payees) and configure their specific spending limits |
| [Sentinel.vy](walletBackpack/Sentinel.md) | Stateless validation engine that enforces all permission and limit rules for managers, payees, and cheques with no stored state |
| [Migrator.vy](walletBackpack/Migrator.md) | User wallet migration module that facilitates the secure transfer of all funds and configurations from one UserWallet to another |

## Common Modules

Shared functionality used across multiple contracts.

| Module | Description |
|--------|-------------|
| [Addys.vy](modules/Addys.md) | Centralized address resolution providing validated protocol component addresses |
| [AddressRegistry.vy](modules/AddressRegistry.md) | Flexible registry for managing dynamic address mappings with time-lock controls |
| [DeptBasics.vy](modules/DeptBasics.md) | Base functionality for protocol departments including pause controls and access management |
| [Erc20Token.vy](modules/Erc20Token.md) | Enhanced ERC20 implementation with advanced features and protocol integration |
| [LocalGov.vy](modules/LocalGov.md) | Two-tier governance system enabling both protocol-wide and contract-specific administration |
| [Ownership.vy](modules/Ownership.md) | Ownership management module with transfer controls and access validation |
| [Timelock.vy](modules/Timelock.md) | Time-delay mechanism for critical configuration changes with expiration windows |

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