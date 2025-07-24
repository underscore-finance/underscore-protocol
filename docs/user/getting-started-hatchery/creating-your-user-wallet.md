## Creating Your User Wallet

Creating an Underscore User Wallet is a simple, single transaction that sets up your entire secure ecosystem. When you call `createUserWallet`, the Hatchery does several things for you automatically:

* **Deploys Your Wallet**: It deploys your main `UserWallet` contract, which is where your assets will be held.
* **Deploys Your Config**: It deploys a separate `UserWalletConfig` contract. This is your personal "control panel" where all the security rules and settings for Managers, Payees, and Cheques are stored.
* **Establishes Default Settings**: It automatically configures your wallet with a complete set of sensible and secure default settings for all the management primitives, so you are protected from day one.
* **Assigns a Starter Agent** (if configured): Your new wallet may come with a pre-approved "Starter Agent" (a type of Manager) to help you explore the wallet's capabilities immediately.
* **Distributes Trial Funds**: You have the option to receive "Trial Funds" to begin interacting with the protocol without needing to deposit your own capital first.
* **Sets Up Ambassador Relationship** (if provided): If you were referred by an existing user, their wallet can be set as your ambassador, allowing them to earn rewards from your activity.