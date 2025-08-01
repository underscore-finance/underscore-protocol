## Introduction

Welcome to your Underscore User Wallet—a comprehensive DeFi management system that combines institutional-grade security with seamless protocol integration.

The User Wallet is built on two foundational principles: **layered security controls** and **modular protocol integration**.

* **Security Through Layers**: Your wallet implements a clear permission hierarchy with built-in management tools. **Managers**, **Payees**, **Cheques**, and the **Whitelist** work together to give you precise control over every transaction, from daily operations to emergency scenarios.

* **Modular Architecture**: Your wallet connects to DeFi protocols through vetted integrations called **"Legos"**. As new protocols are added, your wallet automatically gains access without requiring fund migration or new interfaces.

### Security Hierarchy at a Glance

```
Owner (You)
    ├─ Full control over all wallet functions
    ├─ Can freeze wallet or enable emergency mode
    └─ Manages all permissions
    
Whitelist
    ├─ Trusted addresses (your other wallets)
    └─ Bypass all transfer restrictions
    
Managers
    ├─ Delegated permissions with limits
    ├─ Daily/monthly USD caps
    └─ Action-specific permissions
    
Payees
    ├─ Pre-approved recipients only
    └─ Fixed limits per address
    
Everyone Else
    └─ No access
```

## Real-World Scenarios

Here's what becomes possible with your User Wallet:

**Automated Yield Optimization**: Configure an AI agent as a Manager with a $10,000 daily limit to monitor yield rates. When Morpho offers 8% APY vs Aave's 6%, the agent can rebalance your position in a single transaction, saving ~$20-40 in gas compared to manual operations.

**Business Payment Rails**: Set up monthly payroll for a 5-person team:
- Each employee configured as a Payee with specific limits
- Total monthly limit: $25,000
- Individual payment caps: $3,000-$7,000
- Automatic execution on set dates
- Gas cost: ~$5 per payment vs $25-50 for wire transfers

**Family Emergency Access**: Add a trusted family member as a Manager:
- Daily limit: $1,000 for routine expenses
- Monthly cap: $5,000
- Restricted to stablecoin transfers only
- 24-hour time delay for amounts over $500
- Instant revocation if needed

**Efficient DeFi Operations**: Execute complex strategies in single transactions:
- Withdraw from Aave → Swap on Uniswap → Deposit to Compound
- Gas saved: ~40% compared to separate transactions
- Automatic yield tracking shows exact profits
- Maximum 5 swap steps per transaction

### Technical Capabilities

Your wallet operates within these parameters:
- **Asset Tracking**: Up to 10 different tokens per transaction
- **Swap Routing**: Maximum 5-step paths for optimal rates
- **Yield Tracking**: Automatic profit calculation for all yield-bearing assets
- **Fee Structure**: 0-5% cap on specific operations (configurable)
- **Gas Efficiency**: Batch operations reduce costs by 40-60%