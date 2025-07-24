## Creating an AI Agent (AgentWrapper)

This is an advanced feature primarily for **developers, service providers, and teams** who want to build automated services that can interact with User Wallets.

The Hatchery provides a `createAgent` function that deploys a new `AgentWrapper` contract. This new contract is a secure, signature-based tool that a service can use to manage wallet interactions programmatically.

The process is simple:

1.  A developer calls `createAgent` from the Hatchery to deploy their own `AgentWrapper` contract. The developer is the owner of this new agent contract.
2.  The address of this newly created agent contract is what a user would then add as a **Manager** to their User Wallet.

This allows for a powerful and secure relationship where users can safely grant permissions to sophisticated, automated AI Agents and professional services.
