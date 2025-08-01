## Overview

Imagine having a financial assistant who works 24/7, optimizing your portfolio while you sleep, but can never exceed the strict limits you set. That's the power of **Managers** in your Underscore User Wallet.

Unlike traditional finance where you hand over complete control to an advisor, or other DeFi protocols where delegation means trusting someone with your private keys, Underscore's Manager system provides a fundamentally different approach: you maintain ultimate control while enabling sophisticated automation through smart contract-enforced permissions.

### What Makes This Special

**Traditional Finance**: Give your advisor full control and hope they act in your best interest.
**Other Crypto Wallets**: Share private keys or seed phrases, risking everything.
**Underscore Managers**: Grant specific, limited, revocable permissions enforced by unbreakable smart contract rules.

### Real-World Impact

With Managers, you can:
* **Take a vacation** while your AI agent rebalances your portfolio to capture the best yields
* **Run a business** with team members who can pay expenses without accessing your treasury
* **Sleep soundly** knowing your trading bot can't lose more than your set limits
* **Support family** by giving them emergency access without compromising your life savings

### The Technology Behind the Magic

Managers can be:
* **Trusted People**: Family members, business partners, or team members
* **Professional Services**: Registered financial services with proven track records
* **AI Agents**: Sophisticated algorithms that optimize your portfolio 24/7

### Why AI Agents Are Finally Safe
Traditional AI wallets are risky—if the AI or its server is compromised, you lose everything. Underscore's approach is different:
* **Hard Limits**: Set a maximum of $10,000 per month, and the AI cannot spend $10,001. Configure per-transaction limits (e.g., $1,000 max) and lifetime caps (e.g., $100,000 total)
* **Transparent Rules**: Every permission is visible on-chain—no hidden capabilities
* **Instant Revocation**: Remove a manager with one transaction if anything seems wrong
* **Time-Locked Activation**: New managers wait 7 days (configurable) before activation, giving you time to verify legitimate additions

### Concrete Examples
* **Monthly DCA Bot**: $5,000/month limit, can only buy ETH and BTC, 24-hour cooldown between purchases
* **Yield Optimizer**: Access to USDC/USDT only, can interact with Aave and Compound, $50,000 lifetime limit
* **Team Treasury Manager**: Can pay 5 pre-approved vendors, $2,000 per transaction, requires 12-hour gaps between payments

### Two-Phase Security Model
Underscore employs a unique two-phase validation system for every Manager action:

1. **Pre-Action Validation**: Before any action executes, the system checks:
   - Is this Manager active and within their valid time period?
   - Does this Manager have permission for this type of action?
   - Is this asset/protocol on their allowed list?
   - Has enough time passed since their last transaction?

2. **Post-Action Validation**: After execution, the system enforces:
   - Did this stay within per-transaction USD limits?
   - Are we still under period and lifetime USD caps?
   - Update tracking data for future limit enforcement

This dual-layer approach ensures comprehensive protection that's enforced atomically by smart contracts.

### Core Benefits at a Glance
* **Secure Delegation**: Like giving someone a credit card with a strict limit instead of your bank account
* **Advanced Automation**: Professional-grade portfolio management that never sleeps
* **Gasless Experience**: Many AI services pay the gas fees for you
* **Emergency Safety**: You can revoke access instantly, and the protocol security team provides an additional safety net