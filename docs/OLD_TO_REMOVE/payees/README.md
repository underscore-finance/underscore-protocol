## Overview

Running a business or managing regular payments in crypto can be stressful. You worry about missing payroll while traveling, manually processing each payment, or accidentally sending too much. **Payees** solve these problems by creating automated, controlled payment relationships directly from your wallet.

### What Are Payees?

A Payee is a pre-approved address (person, service, or smart contract) that can receive funds from your wallet according to rules you define. It's like setting up automatic bill pay at your bank, but with far more control and transparency.

**Concrete Example**: Add your employee as a Payee with a $5,000 monthly limit, $5,000 per-transaction cap, and 25-day cooldown. They can receive their salary payment but cannot drain your wallet or get paid twice by accident.

### Why Payees Matter

**Traditional Crypto Payments**: Manual, error-prone, and time-consuming. One wrong digit in an amount or address can be costly.

**Traditional Banking**: Automatic payments exist but you're limited by banking hours, wire fees, and opaque systems.

**Underscore Payees**: Programmable payment relationships with crystal-clear rules, no intermediaries, and 24/7 operation.

### Real-World Benefits

* **Run Payroll from Anywhere**: Set up 10 employees as Payees, each with a $10,000 monthly limit. Your $100,000 payroll fund earns ~$400/month in yield (at 5% APY) until payment day.

* **Never Miss a Payment**: Your $50,000 in operating funds sits in Aave earning 4.5% APY. When your $2,000 monthly rent is due, the system automatically withdraws just what's needed.

* **Prevent Costly Mistakes**: Set a vendor's limit to $5,000 per payment. Even if you accidentally type $50,000, the transaction will fail, protecting you from a $45,000 error.

* **Streamline Operations**: Replace $50 wire fees and 3-day delays with instant, on-chain payments costing under $5 in gas.

### How It Works

1. **Add a Payee**: Specify their address (e.g., `0x123...`) with a 3-day security delay
2. **Define Limits**: 
   - Per transaction: $1,000 maximum
   - Per month: $5,000 total
   - Lifetime: $50,000 cap
   - Allowed tokens: USDC only
3. **Set and Forget**: After the 3-day delay, payments work within your rules
4. **Stay in Control**: Remove instantly or update limits anytime

**Example Timeline**:
- Day 1: Add contractor as Payee
- Day 4: Payee becomes active (after 3-day security delay)
- Day 5: Send first $1,000 payment
- Day 30: Monthly limit resets automatically

### Payment Validation Hierarchy

When you send funds, the system checks recipients in this order:

1. **Whitelisted Addresses** → No limits apply, instant payment
2. **Owner Address** → Can receive without limits (if enabled)  
3. **Registered Payees** → All configured limits and rules apply
4. **Others** → Payment rejected

This hierarchy ensures maximum flexibility while maintaining security.

### Security Features

* **Time-Delayed Activation**: New Payees wait 3 days (configurable) before becoming active, giving you time to catch mistakes
* **Automatic Period Reset**: Monthly limits refresh automatically - no manual intervention needed
* **Zero-Price Protection**: Optional setting to block payments if price oracles fail
* **Dual Limit System**: Control both token amounts (1,000 USDC) and USD values ($1,000)
* **Emergency Removal**: Remove any Payee instantly if something seems wrong

The best part? Your funds keep earning yield until the moment they're needed for a payment. A $100,000 treasury earning 5% APY generates ~$400/month that would be lost sitting in a checking account.