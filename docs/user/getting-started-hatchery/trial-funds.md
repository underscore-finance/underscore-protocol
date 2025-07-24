## Trial Funds: A Risk-Free Start

To help you get acquainted with the powerful features of your new wallet, the Hatchery can provide you with **Trial Funds** upon creation.

**What You Get**: Typically 10 USDC of trial funds that allow you to explore the protocol without any personal financial risk.

**What You Can Do**: With trial funds, you can:
* Deposit into yield protocols like Aave, Morpho, or Euler
* Withdraw from yield positions
* Rebalance between different yield strategies
* Test security features and wallet controls

**Limitations**: To ensure trial funds are used for learning, certain advanced operations like token swaps and liquidity provision are restricted while you have trial funds in your wallet.

Once you have familiarized yourself with the system and are ready to deposit your own assets, the trial funds can be cleanly removed from your wallet via the `clawBackTrialFunds` function. This "clawback" process is smart; it can find the trial funds even if you've deposited them into a yield vault and will automatically withdraw them to clean up your wallet. Note that other protocol contracts may check your trial fund status and restrict certain advanced operations until the trial funds have been used or returned.