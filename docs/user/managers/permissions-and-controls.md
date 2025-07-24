## Permissions & Controls

This section details the full suite of permissions and controls you can configure for a Manager. It covers what actions they are allowed to perform and the security guardrails you can place around those actions.

#### The Dual-Permission System
For an action to be permitted, **both the global setting and the specific manager's setting must be enabled (`True`)**.

1.  **Global Manager Settings**: This is your master control panel where you define a default "template" of permissions and limits. If you turn a permission `off` at the global level, no manager will be able to perform that action. This also includes the `canOwnerManage` flag, which determines if you, the owner, are also subject to the global manager limits.
2.  **Specific Manager Settings**: This is the control panel for an individual Manager. A permission is only truly active if the same permission is *also* enabled in the Global Manager Settings.

---

### Manager Permissions (What They Can Do?)

These settings define the specific types of actions a Manager is authorized to perform.

#### DeFi Permissions
These permissions grant the ability to interact with various DeFi protocols ("Legos").
* **Manage Yield**: Allows the Manager to deposit into and withdraw from yield-generating protocols.
* **Buy & Sell**: Permits the Manager to swap tokens and engage in minting or redeeming assets.
* **Manage Debt**: Authorizes the Manager to add/remove collateral, borrow assets, and repay debt.
* **Manage Liquidity**: Enables the Manager to add or remove liquidity from decentralized exchanges.
* **Claim Rewards**: Grants the Manager permission to claim accumulated rewards from DeFi activities.

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

#### Understanding Period-Based Limits
Many Manager controls operate on a **period system**. A period is a configurable time window (measured in blocks) that automatically resets, giving your Manager fresh limits. For example:
* Set a period of 50,400 blocks (roughly 7 days on Ethereum)
* Give your Manager a $10,000 limit per period
* Every week, they get a fresh $10,000 to work with
* Any unused amount doesn't roll over—it's use it or lose it

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