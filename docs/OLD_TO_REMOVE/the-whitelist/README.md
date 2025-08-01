## Overview

Sometimes you need to move large amounts quickly between your own wallets, or ensure a trusted family member can always receive emergency funds. The **Whitelist** serves as your wallet's highest trust tier—addresses that can receive unlimited transfers without any restrictions.

### What is the Whitelist?

The Whitelist is a carefully managed list of addresses that bypass all payment limits and restrictions. Think of it as designating beneficiaries on a bank account or authorized users on a credit card, but with more control and transparency.

**Example**: If your daily limit is $10,000 but you need to move $250,000 to your hardware wallet, a whitelisted address allows this transfer immediately.

### Why the Whitelist Matters

In DeFi, we often need to balance security with flexibility:

**The Challenge**: You want strong limits on most transactions to prevent losses, but these same limits can block legitimate large transfers when you need them most.

**The Solution**: The Whitelist creates a clear distinction between general recipients (subject to limits) and fully trusted addresses (unrestricted access).

### Key Benefits

* **Instant Large Transfers**: Move any amount to your hardware wallet, multi-sig, or other personal wallets without hitting limits.

* **Emergency Access**: Ensure family members or business partners can receive funds immediately in critical situations.

* **Operational Efficiency**: Business treasuries can sweep funds from operational wallets without friction.

* **Multi-Wallet Strategies**: Manage complex wallet setups where funds need to flow freely between your own addresses.

### Security Model

```
Highest Authority:     Owner (You)
                         ↓
Delegated Control:     Managers (with specific whitelist permissions)
                         ↓
Emergency Override:    MissionControl (can only remove/cancel)
```

### How It Works

1. **Propose an Address**: Submit an address for whitelisting
2. **Security Delay**: Wait for the time-lock period (typically 3-7 days)
3. **Confirm Addition**: Complete the whitelisting after the delay
4. **Unrestricted Transfers**: Send any amount, anytime

The time-lock ensures that even if your wallet is compromised, an attacker cannot immediately add their own address and drain your funds. It's security that doesn't get in your way during normal operations.

**Time-lock Examples**:
- 3 days = 25,920 blocks (Ethereum mainnet)
- 7 days = 60,480 blocks (Ethereum mainnet)
- Your specific delay is configured when setting up your wallet

### Important Considerations

* **Highest Trust Level**: Only whitelist addresses you completely control or absolutely trust
* **No Cheques**: You cannot create Cheques for whitelisted addresses (they already have unlimited access)
* **Permanent Until Removed**: Whitelisted addresses remain trusted until explicitly removed
* **Owner Change Protection**: If the wallet owner changes during the pending period, the whitelist proposal is automatically cancelled
* **System Protection**: Cannot whitelist the wallet itself, owner address, or configuration contracts

### Integration with Other Features

- **vs Managers**: Managers have limits; whitelisted addresses don't
- **vs Payees**: Payees can pull payments within limits; whitelisted addresses receive unlimited push payments
- **vs Cheques**: Cheques are for controlled, scheduled payments; whitelist is for unrestricted transfers

The Whitelist is a powerful tool that ensures your security measures enhance rather than hinder your financial operations.