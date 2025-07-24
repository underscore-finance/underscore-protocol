## Permissions & Controls

This section details the full suite of permissions and controls you can configure for a Manager. It covers what actions they are allowed to perform and the security guardrails you can place around those actions.

#### The Dual-Permission System
For an action to be permitted, **both the global setting and the specific manager's setting must be enabled (`True`)**.

1.  **Global Manager Settings**: This is your master control panel where you define a default "template" of permissions and limits. If you turn a permission `off` at the global level, no manager will be able to perform that action. This also includes the `canOwnerManage` flag, which determines if you, the owner, are also subject to the global manager limits.
2.  **Specific Manager Settings**: This is the control panel for an individual Manager. A permission is only truly active if the same permission is *also* enabled in the Global Manager Settings.

---

### Manager Permissions (What They Can Do?)

These settings define the specific types of actions a Manager is authorized to perform.

#### Permission Matrix Overview

| Permission Category | Permission | What It Enables | Common Use Case |
|-------------------|------------|-----------------|-----------------|
| **DeFi Actions** | Manage Yield | Deposit/withdraw from yield protocols | Auto-compound farming rewards |
| | Buy & Sell | Swap tokens, mint/redeem assets | Portfolio rebalancing |
| | Manage Debt | Collateral, borrow, repay | Maintain healthy loan positions |
| | Manage Liquidity | Add/remove DEX liquidity | LP position management |
| | Claim Rewards | Harvest protocol rewards | Collect farming incentives |
| **Transfers** | General Transfers | Send assets to addresses | Pay team members |
| | Create Cheques | Schedule one-time payments | Delayed vendor payments |
| | Propose Payees | Add recurring payment recipients | New contractor setup |
| **Whitelist** | Propose Additions | Suggest new addresses | Add new protocols |
| | Confirm Additions | Activate pending addresses | Complete onboarding |
| | Cancel Pending | Stop proposed additions | Abort suspicious requests |
| | Remove Addresses | Delete from whitelist | Remove old vendors |
| **Rewards** | Claim Protocol | Harvest Underscore rewards | Collect platform incentives |
| | Claim Loot | Collect revenue share | Automated profit collection |

#### DeFi Permissions Explained

**Understanding "Legos"**: In Underscore, DeFi protocols are called "Legos" - modular building blocks that can be combined. Each Lego has a unique ID in the registry.

* **Manage Yield**: Deposit into and withdraw from yield-generating protocols
  * Example: Auto-compound Aave deposits every 24 hours
  * Example: Move funds between lending protocols for best rates

* **Buy & Sell**: Swap tokens and engage in minting or redeeming assets
  * Example: Rebalance portfolio to maintain 60/40 ETH/USDC ratio
  * Example: Convert rewards to stablecoins daily

* **Manage Debt**: Add/remove collateral, borrow assets, and repay debt
  * Example: Maintain 150% collateralization ratio automatically
  * Example: Borrow against assets for leveraged yield farming

* **Manage Liquidity**: Add or remove liquidity from decentralized exchanges
  * Example: Manage Uniswap V3 positions within price ranges
  * Example: Harvest LP fees and reinvest

* **Claim Rewards**: Claim accumulated rewards from DeFi activities
  * Example: Harvest and sell governance tokens every week

#### Transfer & Payment Permissions
These settings control how a Manager can move funds and manage payment-related primitives.
* **General Transfers**: A master switch that allows the Manager to transfer assets out of the wallet.
* **Create Cheques**: Allows the Manager to create schedulable, one-time payment Cheques.
* **Propose New Payees**: Permits the Manager to propose new, recurring Payees, which require your final confirmation.

#### Whitelist Permissions
These permissions control a Manager's ability to manage the wallet's address whitelist.
* **Propose Whitelist Additions**: Allows the Manager to propose a new address to be added to the whitelist.
* **Confirm Whitelist Additions**: Permits the Manager to confirm a pending address after the security time-lock has passed.
* **Cancel Pending Additions**: Allows the Manager to cancel a pending whitelist proposal before it is confirmed.
* **Remove Whitelisted Addresses**: Grants the Manager the ability to remove an already active address from the whitelist.

#### Reward Management Permissions
* **Claim Protocol Rewards**: Allows the Manager to claim Underscore protocol rewards that have been allocated to your wallet.
* **Claim Loot (Revenue Share)**: Permits the Manager to claim your share of protocol revenue (loot) on your behalf. This is particularly useful for AI agents that can monitor and claim rewards before they expire.

---

### Manager Controls (Security Guardrails)

These settings act as security guardrails, defining the boundaries within which a Manager must operate.

#### Two-Phase Security Model

Underscore implements a sophisticated two-phase validation system that provides comprehensive protection:

```
┌─────────────────────────┐     ┌──────────────────────────┐
│   Phase 1: Pre-Action   │     │   Phase 2: Post-Action   │
│      (Permission)       │     │      (USD Limits)        │
├─────────────────────────┤     ├──────────────────────────┤
│ ✓ Manager active?       │     │ ✓ Under per-tx limit?    │
│ ✓ Action permitted?     │ ──► │ ✓ Under period limit?    │
│ ✓ Asset allowed?        │     │ ✓ Under lifetime limit?  │
│ ✓ Lego allowed?         │     │ ✓ Update tracking data   │
│ ✓ Cooldown passed?      │     │                          │
└─────────────────────────┘     └──────────────────────────┘
         │                                    │
         └────────────────┬───────────────────┘
                          ▼
                   Action Executes
```

This dual validation ensures that:
1. Managers can only attempt authorized actions
2. Even authorized actions must stay within financial limits
3. All checks happen atomically within the transaction

#### Understanding Period-Based Limits
Many Manager controls operate on a **period system**. A period is a configurable time window (measured in blocks) that automatically resets, giving your Manager fresh limits.

**How Periods Work:**
```
Period 1                Period 2                Period 3
[----$10k limit----] → [----$10k limit----] → [----$10k limit----]
Used: $7k              Used: $10k              Used: $3k
Remaining: $3k         Remaining: $0           Remaining: $7k
     ↓                      ↓                      ↓
  (doesn't roll)        (fresh start)         (fresh start)
```

**Common Period Configurations:**

| Use Case | Period Length | Blocks | Reset Frequency |
|----------|--------------|--------|-----------------|
| Daily Operations | 1 day | ~7,200 | Every 24 hours |
| Weekly Budget | 7 days | ~50,400 | Every week |
| Monthly Allowance | 30 days | ~216,000 | Every month |
| Quarterly Review | 90 days | ~648,000 | Every quarter |

This system ensures consistent, predictable spending patterns while preventing runaway spending.

#### Financial & Transaction Limits
These settings control the "how much" and "how often" of a Manager's financial activities.

* **Max Value Per Transaction**: Sets the maximum USD value for any single transaction.
  * *Example*: Set to $5,000 to prevent large one-time losses from bad trades

* **Max Value Per Period**: Sets the total USD value a Manager can transact within a recurring time window.
  * *Example*: $10,000 per week for an AI trading agent
  * *Example*: $50,000 per month for a business operations manager

* **Lifetime Value Limit**: Sets the cumulative USD value a Manager can transact over their entire tenure.
  * *Example*: $500,000 lifetime limit for a year-long AI agent subscription

* **Max Transactions Per Period**: Sets the maximum number of transactions a Manager can execute in a period.
  * *Example*: 100 transactions per day to prevent spam or runaway bots

* **Transaction Cooldown**: Enforces a mandatory waiting period (in blocks) between a Manager's transactions.
  * *Example*: 50 blocks (~10 minutes) to slow down potential attacks
  * *Example*: 300 blocks (~1 hour) for high-value manager accounts

* **Fail on Zero Price**: A security feature that blocks a transaction if an asset's price is reported as zero.
  * *Why it matters*: Prevents managers from trading during oracle failures when assets might appear worthless

#### Asset & Application Restrictions
For ultimate security, you can restrict a Manager to a very specific, pre-approved "sandbox".

* **Restrict to Specific Assets**: Provide a specific list of tokens (e.g., USDC, WETH) that the Manager is allowed to interact with.
  * *Example*: Only allow stablecoins (USDC, USDT, DAI) for a conservative yield strategy
  * *Example*: Restrict to ETH and WETH for an Ethereum-focused trading bot

* **Restrict to Specific dApps**: Provide a specific list of DeFi applications ("Legos") that the Manager is permitted to use.
  * *Example*: Only allow Aave and Compound for a yield-focused manager
  * *Example*: Restrict to Uniswap and Curve for a trading-only agent
  * *Note*: You specify Lego IDs, giving you protocol-level control

* **Restrict to Specific Payees**: Provide a specific list of pre-approved addresses that the Manager is allowed to send funds to.
  * *Example*: Only allow payments to your verified business vendors
  * *Example*: Restrict family member manager to emergency addresses only

---

### Permission Hierarchy: How Settings Combine

Understanding how global and manager-specific settings interact is crucial for proper configuration:

```
Global Settings           Manager Settings         Applied Result
─────────────────────────────────────────────────────────────────
canBuyAndSell: true   +  canBuyAndSell: true   =  ✓ Can trade
canBuyAndSell: false  +  canBuyAndSell: true   =  ✗ Cannot trade
canBuyAndSell: true   +  canBuyAndSell: false  =  ✗ Cannot trade

maxPerTx: $10,000     +  maxPerTx: $5,000      =  $5,000 limit
maxPerTx: $5,000      +  maxPerTx: $10,000     =  $5,000 limit
(Most restrictive limit always applies)
```

**Key Rules:**
1. **Permissions**: Both global AND manager-specific must be `true`
2. **Limits**: The more restrictive value always wins
3. **Asset Lists**: Manager list must be subset of global list
4. **Time Delays**: Maximum of global and manager settings

**Example Configuration:**
```
Global Settings:
- Can trade: Yes
- Max per period: $100,000
- Allowed assets: [USDC, USDT, DAI, ETH, WBTC]

Manager A (Conservative):
- Can trade: Yes
- Max per period: $10,000
- Allowed assets: [USDC, USDT, DAI]
Result: Can only trade stablecoins up to $10k/period

Manager B (Aggressive):
- Can trade: Yes
- Max per period: $200,000
- Allowed assets: [All from global]
Result: Limited to $100k/period (global cap)
```