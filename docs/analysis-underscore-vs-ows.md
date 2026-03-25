# Underscore Protocol vs Open Wallet Standard (OWS) - Full Analysis

## TL;DR

These are fundamentally different things solving different problems at different layers:

- **OWS** = Local key management software with pre-signing policy checks (off-chain)
- **Underscore** = On-chain programmable smart contract wallet with smart-contract-enforced policies

OWS manages private keys on your machine and checks policies in software before signing.
Underscore never touches wallet private keys inside the protocol itself. It is a smart contract wallet where policies are enforced by on-chain code, so a compromised manager machine is still bounded by contract-level limits.

They are complementary, not competitive.

---

## 1. Architecture

### OWS
```
Agent/CLI/SDK → Access Layer → Policy Engine → Signer → Wallet Vault (~/.ows/wallets/)
```
- **Rust core** with FFI bindings to Node.js and Python
- Runs entirely on the user's local machine
- Keys stored encrypted at rest in `~/.ows/wallets/` (AES-256-GCM, scrypt KDF)
- No smart contracts, no blockchain interaction (except broadcasting signed txs)
- Multi-chain: 9 chains (EVM, Solana, Bitcoin, Cosmos, Tron, TON, Sui, Filecoin, Spark)
- HD wallet derivation: single mnemonic generates addresses on all chains via CAIP standards

### Underscore
```
User EOA → AgentSenderGeneric (authorization sig verify) → AgentWrapper → UserWallet → Legos (DeFi protocols)
                                                          ↓
                                                   UserWalletConfig ↔ Sentinel (policy enforcement)
```
- **Vyper smart contracts** (v0.4.3) deployed on Base L2
- Smart contract system with a core wallet, policy enforcement layer, and many DeFi protocol adapters
- No local key storage — user keeps their own EOA wallet
- Single chain: Base (deep DeFi integration)
- Wallet IS a smart contract, not a local software process
- 6 specialized management contracts (WalletBackpack): Sentinel, HighCommand, Paymaster, Kernel, ChequeBook, Migrator

---

## 2. Signing: Where and How

### OWS Signing Flow
1. Agent calls `sign()` with wallet ID, chain ID, and serialized transaction hex
2. OWS resolves credentials (passphrase for owner, API token for agent)
3. **For agents**: Policy engine evaluates all attached policies
4. Key is **decrypted from disk into memory** (mlock'd, hardened buffer)
5. Chain-specific signer signs the transaction
6. Key is **zeroized** (wiped from memory)
7. Signature returned to caller

**Key fact**: OWS holds the actual private key. It decrypts it, uses it, wipes it. The key material exists briefly in the OWS process memory. The agent never sees it, but the OWS process does.

**Supported signing operations**:
- `sign()` — raw transaction signing
- `signAndSend()` — sign + broadcast
- `signMessage()` — arbitrary message signing (EIP-191, Ed25519, etc.)
- `signTypedData()` — EIP-712 structured data

**No on-chain nonce management** — callers must coordinate nonces themselves.

### Underscore Signing Flow
1. Manager/agent signs an authorization payload with **their own private key** (off-chain)
2. Signed message includes: action parameters + nonce + expiration timestamp
3. Transaction is submitted to `AgentSenderGeneric` contract on-chain
4. Contract performs **ECDSA recovery** (ecrecover precompile) to verify signer
5. Contract checks signer is an approved manager for this wallet
6. **Sentinel contract** runs full policy validation (permissions, limits, cooldowns, etc.)
7. If all checks pass, `UserWallet` executes the action through the appropriate Lego
8. **Post-execution validation**: USD value limits, period limits, slippage verified
9. Nonce incremented on-chain (replay protection)

**Key fact**: Underscore never holds or decrypts anyone's private key. The manager signs with their own key. The smart contract verifies the signature and enforces all policies. The wallet's "key" is the owner's EOA — it's never stored or managed by the protocol.

**Signature structure**:
```vyper
struct Signature:
    signature: Bytes[65]    # r, s, v
    nonce: uint256          # per-wallet, on-chain replay protection
    expiration: uint256     # timestamp-based expiry
```

**Domain separator used by the relay path**:
```vyper
domain_separator = keccak256(
    'EIP712Domain(string name,uint256 chainId,address verifyingContract)',
    'UnderscoreAgent', chain.id, agentSenderAddress
)
```

Note: this relay path is EIP-712-like in structure, but it is not currently exposed as a standard typed-data schema in the way OWS `signTypedData()` expects. That means OWS would not be a strict drop-in signer for `AgentSenderGeneric` today without an adapter or a small standardization pass.

**Security details**:
- Signature malleability prevention (s-value must be in lower half of curve order)
- Per-wallet nonce tracking (incremented after each use)
- Timestamp-based signature expiration
- Chain-specific domain separator prevents cross-chain replay

---

## 3. Policies: The Critical Difference

### OWS Policies — OFF-CHAIN, SOFTWARE-ENFORCED

**Where they live**: JSON files in `~/.ows/policies/`

**Schema**:
```json
{
  "id": "policy-id",
  "name": "Human-readable name",
  "version": 1,
  "rules": [...],
  "executable": "/path/to/custom-validator",
  "action": "deny"
}
```

**Built-in declarative rule types (only 2)**:
1. `allowed_chains` — restrict to specific CAIP-2 chain IDs
2. `expires_at` — time-bound access with ISO-8601 timestamp

**Custom executable policies**:
- Arbitrary executables that receive `PolicyContext` as JSON on stdin
- Return `{ "allow": true }` or `{ "allow": false, "reason": "..." }`
- 5-second timeout, fail-closed (deny on error/timeout)
- Can implement anything: spending limits, simulation, allowlists
- BUT: these are custom code the user must write/provide

**PolicyContext available to executables**:
```json
{
  "chain_id": "eip155:8453",
  "wallet_id": "uuid",
  "api_key_id": "uuid",
  "transaction": { "to": "0x...", "value": "...", "data": "0x..." },
  "spending": { "daily_total": "wei-amount", "date": "YYYY-MM-DD" },
  "timestamp": "ISO-8601"
}
```

**Enforcement model**:
- Owner (passphrase): **bypasses all policies entirely**
- Agent (API token): all attached policies evaluated, AND semantics
- Policies attach to API keys at creation time
- Evaluated in-process before key decryption
- No post-execution validation

**Not built-in declaratively** (would require custom executables): spending limits, USD value tracking, per-period caps, asset whitelists, protocol restrictions, slippage controls, payee systems, time-locks, cooldowns.

### Underscore Policies — ON-CHAIN, SMART-CONTRACT-ENFORCED

**Where they live**: Immutable Vyper smart contracts on Base L2

**Built-in policy types (comprehensive)**:

#### Manager Limits (HighCommand + Sentinel contracts)
```vyper
struct ManagerLimits:
    maxUsdValuePerTx: uint256        # e.g. $5,000 per transaction
    maxUsdValuePerPeriod: uint256    # e.g. $50,000 per day
    maxUsdValueLifetime: uint256     # e.g. $500,000 total
    maxNumTxsPerPeriod: uint256      # e.g. 100 txs per period
    txCooldownBlocks: uint256        # e.g. 1800 blocks (1 hour)
    failOnZeroPrice: bool            # block if oracle price unavailable
```

#### Action Permissions (per manager)
```vyper
struct LegoPerms:
    canManageYield: bool
    canBuyAndSell: bool
    canManageDebt: bool
    canManageLiq: bool
    canClaimRewards: bool
    onlyApprovedYieldOpps: bool
    allowedLegos: DynArray[uint256, 25]   # specific protocol IDs
```

#### Swap Controls
```vyper
struct SwapPerms:
    mustHaveUsdValue: bool
    maxNumSwapsPerPeriod: uint256
    maxSlippage: uint256              # basis points
```

#### Transfer Controls
```vyper
struct TransferPerms:
    canTransfer: bool
    canCreateCheque: bool
    canAddPendingPayee: bool
    allowedPayees: DynArray[address, 40]  # specific recipient addresses
```

#### Asset Restrictions
- Up to 40 allowed assets per manager
- Global + manager-specific settings (most restrictive always wins)

#### Time-Based Security
- Manager activation delays (can't act immediately after being added)
- Auto-expiry (30/90/365 days or custom)
- Whitelist time-locks (configurable delay to add a new address)
- Cheque unlock delays for large amounts

#### Payment Rails (3-tier recipient system)
1. **Whitelist**: instant, unlimited, highest trust (time-locked to add)
2. **Payees**: recurring, limited, with per-tx/period/lifetime caps + cooldowns + asset restrictions
3. **Cheques**: one-time, delayed for large amounts, cancellable before cashing

**Enforcement model**:
- Owner: can bypass IF `canOwnerManage` is enabled (configurable per wallet)
- Manager: ALL policies enforced atomically on-chain
- Pre-execution: permission checks, asset checks, protocol checks, cooldown checks
- Post-execution: USD value limit checks, slippage checks, period tracking
- If ANY check fails at ANY stage, entire transaction reverts (atomic)
- Manager CANNOT modify their own permissions or escalate privileges
- Dual-layer limits: both manager-specific AND global limits apply (most restrictive wins)

---

## 4. Trust Model Comparison

| Dimension | OWS | Underscore |
|-----------|-----|------------|
| **What you trust** | Local software process + OS security | Blockchain consensus + smart contract code |
| **Key exposure** | Key briefly exists in process memory | Key never leaves the signer's control |
| **If machine is compromised** | Attacker can extract keys despite encryption (memory dump, swap file) | Attacker gets manager key, but smart contract still enforces all limits |
| **Policy bypass** | Possible if OWS process is modified/replaced | Impossible — policies are immutable on-chain code |
| **Policy bypass by owner** | Owner passphrase bypasses all policies | Owner can bypass only if `canOwnerManage` is enabled |
| **Auditability** | Local logs only | Fully on-chain, publicly verifiable |
| **Upgrade risk** | Software updates could change behavior | Wallet contracts are immutable (no proxy upgrades) |
| **Spending counters** | Local state (tamperable, resettable) | On-chain storage (immutable, network-verified) |
| **Post-execution checks** | None | Atomic revert if limits exceeded |

### The Fundamental Security Difference

**OWS**: If an attacker compromises the machine running OWS, they can:
- Extract the encrypted wallet file
- Attempt to brute-force the passphrase (scrypt, but still possible)
- Hook the OWS process to intercept decrypted keys
- Modify the policy engine to skip checks
- Replace the OWS binary entirely
- Modify the policy executable to always return `{"allow": true}`

**Underscore**: If an attacker compromises a manager's machine, they can:
- Use the manager's key to submit transactions
- BUT the smart contract still enforces all limits (per-tx cap, daily cap, lifetime cap, asset restrictions, protocol restrictions, cooldowns)
- They CANNOT exceed the manager's configured permissions
- They CANNOT modify permissions (only the owner can)
- They CANNOT bypass time-locks or whitelist requirements
- Maximum damage is mathematically bounded by the manager's configured limits
- Owner can revoke the manager instantly

Important nuance: if the owner's EOA or hardware wallet is compromised, Underscore does not magically eliminate that risk. What it does do is put real friction around critical drain paths such as whitelist additions via timelocks, and it can restrict owner behavior when `canOwnerManage` is disabled. The strongest "bounded damage" claim applies to compromised managers and delegated agents, not compromised owners.

---

## 5. Deep Dive: Why Off-Chain Policies Can Never Match On-Chain Enforcement

### 5.1 The Pre-Sign-Only Problem

OWS policies evaluate **before** signing. There is **zero post-execution validation**. The policy makes a decision based on a `PolicyContext` prediction of what the transaction will do, but once the signature is issued, there's no mechanism to verify reality matched the prediction.

Underscore enforces in **two phases atomically**:
1. **Pre-execution** (Sentinel): permission checks, asset/protocol restrictions, cooldowns
2. **Post-execution** (UserWalletConfig -> Sentinel): USD value limits, slippage checks, period tracking

Both phases use Vyper `assert` statements. If ANY check fails at ANY stage, the entire transaction reverts. No partial execution is possible.

### 5.2 The Owner Bypass Problem

OWS explicitly states: owner passphrase access **bypasses all policies**. There is no way to attach policies to owner-level access. Anyone with the passphrase has unrestricted signing capability.

Underscore: Even the owner can be restricted. The `canOwnerManage` flag is configurable — the owner can choose to require manager-level policy checks even for their own actions. And critically, the 3-tier payment system (Whitelist/Payees/Cheques) applies to ALL transfers regardless of who initiates them.

### 5.3 The Binary Compromise Problem

OWS's own docs acknowledge: *"In-process models cannot fully mitigate compromised process memory."*

If an attacker:
- **Replaces the OWS binary** -> All policies gone. Full key access.
- **Modifies the policy executable** -> Returns `{"allow": true}` for everything.
- **Hooks the process memory** -> Intercepts decrypted keys during signing.
- **Reads swap files** -> Keys may have been paged to disk despite mlock.

OWS proposes a future "subprocess enclave model" to address this, but current implementations lack it.

In Underscore, none of these attacks matter:
- The manager's machine is irrelevant to policy enforcement
- Policies live in immutable smart contract code verified by blockchain consensus
- Even a fully compromised manager machine can only submit transactions that pass on-chain validation
- The attack surface is bounded by the manager's configured limits

### 5.4 The Spending Limit Gap

OWS provides `PolicyContext.spending.daily_total` — but this is tracked **locally** by the OWS process itself. If the process is restarted, the counter may reset. If the local database is modified, limits can be circumvented. There's no external source of truth.

Underscore tracks all spending counters **on-chain**:
- `totalUsdValueInPeriod` — resets only when the period actually elapses (block-based)
- `totalUsdValue` — lifetime cumulative, never resets
- `numTxsInPeriod`, `numSwapsInPeriod` — period-based counters
- `lastTxBlock` — cooldown enforcement

These values are stored in contract storage, verified by the network, and cannot be tampered with.

### 5.5 The Atomicity Gap

OWS: Policy check -> Sign -> Broadcast -> Hope for the best. If a transaction's actual execution differs from what the policy evaluated (e.g., MEV sandwich, state change between evaluation and mining), OWS has no recourse.

Underscore: Policy check -> Execute -> Post-check -> Commit **OR** Revert. The post-execution check sees the *actual results* (actual USD values, actual slippage, actual assets received) and can revert if they violate limits. This is a fundamentally stronger guarantee.

### Summary Table: Architectural Limitations of Off-Chain Policies

| Property | OWS (Off-Chain) | Underscore (On-Chain) |
|----------|-----------------|----------------------|
| When policies run | Pre-sign only | Pre-execution + post-execution |
| What policies see | Predicted tx data | Actual execution results |
| Enforcement mechanism | Software process | Blockchain consensus |
| Can be bypassed by | Binary replacement, memory access, owner passphrase | Nothing short of a 51% attack |
| Spending counters | Local state (tamperable, resettable) | On-chain storage (immutable, verifiable) |
| Failed check result | Signature not issued (but no revert) | Entire transaction reverts atomically |
| Audit trail | Local logs (deletable) | On-chain events (permanent, public) |

---

## 6. Multi-Chain vs Single-Chain Deep

| Feature | OWS | Underscore |
|---------|-----|------------|
| **Chains** | 9 (EVM, Solana, Bitcoin, Cosmos, Tron, TON, Sui, Filecoin, Spark) | 1 (Base L2) |
| **DeFi integration** | None — just signs transactions | 37 protocol adapters (Aave, Morpho, Compound, Euler, Uniswap, Aerodrome, Curve, etc.) |
| **Yield management** | N/A | AI-managed vaults, rebalancing, leverage |
| **Payment systems** | N/A | Whitelist + Payees + Cheques with full policy rails |
| **Protocol operations** | Raw tx signing only | Atomic multi-protocol operations (swap+deposit+rebalance in one tx) |

---

## 7. Agent Access Model

### OWS
- Create API token: `ows key create --name "agent" --wallet <id> --policy <policy-id>`
- Token scoped to specific wallet(s)
- Policies attached at token creation time
- Agent calls `sign()` with the token
- OWS validates token -> evaluates policies -> signs if allowed
- Agent NEVER sees private key material
- Four access methods: in-process binding, local subprocess, local service (loopback), CLI

### Underscore
- Owner registers manager address on-chain via `HighCommand` contract
- Owner configures granular permissions (what actions, what assets, what limits, what protocols)
- Manager can either call the wallet directly from their EOA or use the agent relay path with signed authorizations
- Submits to `AgentSenderGeneric` contract
- Contract verifies signature -> `Sentinel` enforces policies -> executes if allowed
- Manager NEVER has access to wallet funds beyond their configured limits
- Owner can revoke manager instantly
- Signer can be frozen via `MissionControl` for emergency lockout

---

## 8. What Each Has That the Other Doesn't

### What OWS Has (That Underscore Doesn't)
1. **Multi-chain support** — 9 chains vs 1
2. **Local-first / no blockchain dependency** — works offline for signing
3. **HD wallet derivation** — single mnemonic, all chains
4. **Message signing** — EIP-191, Ed25519, ADR-036, etc.
5. **Custom executable policies** — arbitrary validation logic (simulation, ML, etc.)
6. **Lighter weight** — no gas costs, no contract deployment
7. **Privacy** — no on-chain footprint for policy configuration
8. **Bitcoin/non-smart-contract chain support** — works on chains without smart contracts

### What Underscore Has (That OWS Doesn't)
1. **On-chain policy enforcement** — immutable, consensus-verified, unbypassable
2. **Built-in spending limits** — per-tx, per-period, lifetime, all USD-aware via oracles
3. **Post-execution validation** — checks actual results, reverts atomically if violated
4. **Asset whitelisting** — restrict which tokens a manager can touch (up to 40)
5. **Protocol restrictions** — control which DeFi protocols a manager can use (up to 25 Legos)
6. **Swap controls** — max slippage, max swaps per period, USD value requirements
7. **Payment rails** — 3-tier system (Whitelist/Payees/Cheques) with full guardrails
8. **Time-locks** — delayed confirmations for whitelist additions, cheque payments, manager activation
9. **DeFi integration** — broad protocol-adapter support for yield, swaps, debt, and liquidity
10. **Atomic multi-step operations** — complex strategies in one transaction
11. **Immutable enforcement** — contract code cannot be modified
12. **Public audit trail** — all policy checks verifiable on-chain

---

## 9. Competitive Positioning: Underscore vs Off-Chain Policy Solutions

### The Core Argument

> "Enforced by code, not policy."

This is the single most powerful differentiator. Off-chain solutions enforce policies in software — which means they're only as strong as the software's integrity. Underscore enforces policies in immutable smart contracts — which means they're as strong as the blockchain itself.

### Five Key Arguments

#### 1. Immutable Guarantees vs. Mutable Software

Off-chain policies are JSON files and executables on a filesystem. They can be edited, replaced, or deleted. The wallet binary itself can be modified. Software updates can silently change enforcement behavior.

Underscore's wallet contracts are immutable — deployed once, never upgradeable. The policy logic in Sentinel, UserWalletConfig, HighCommand, and Paymaster is permanent. An audited contract behaves identically on day 1 and day 1,000.

> *"Your guardrails shouldn't depend on software that can be updated, patched, or replaced. Underscore's policies are immutable code verified by every node on the network."*

#### 2. Post-Execution Validation vs. Pre-Sign Prediction

Off-chain solutions can only evaluate what a transaction *claims* it will do. They see raw transaction bytes and make a best-effort judgment. They cannot know the actual outcome (slippage, MEV, state changes between evaluation and execution).

Underscore validates *after* execution but *before* state commitment. The Sentinel contract checks actual USD values, actual slippage, actual assets received. If reality doesn't match the rules, the transaction reverts.

> *"Off-chain policies guess what will happen. On-chain policies verify what actually happened — and revert if it breaks the rules."*

#### 3. Machine Compromise = Bounded Damage vs. Total Loss

If the machine running an off-chain wallet is compromised, the attacker gets everything: keys, unlimited signing, policy bypass.

If a machine running an Underscore manager is compromised, the attacker can only operate within the manager's on-chain limits. Maximum damage is mathematically bounded: `maxUsdValuePerTx`, `maxUsdValuePerPeriod`, `maxUsdValueLifetime`. The owner can revoke the manager instantly.

> *"When a key is compromised, the question isn't if damage occurs — it's how much. Off-chain wallets lose everything. Underscore managers lose at most what you configured them to spend."*

#### 4. Public Auditability vs. Trust-Me Logs

Off-chain enforcement is invisible. There's no public record that policies were evaluated, what they checked, or whether they were bypassed. Audit logs are local files that can be deleted or modified.

Every Underscore policy check happens on-chain. Anyone can verify that a manager stayed within limits, that a payee payment respected its caps, that a cheque waited its unlock period. The audit trail is permanent and public.

> *"Don't trust — verify. Every Underscore policy check is an on-chain transaction anyone can audit. No local logs to delete. No claims to take on faith."*

#### 5. Comprehensive Built-In vs. Build-It-Yourself

Off-chain solutions ship with minimal built-in policy types and require writing custom validators from scratch. There's no standard, no interoperability, and no guarantees about the quality of custom implementations.

Underscore ships with a complete policy system: USD-aware spending limits (per-tx, per-period, lifetime), asset whitelists (40 per manager), protocol restrictions (25 per manager), swap controls (slippage, count limits), transfer controls (payee lists), time-locks, cooldowns, activation delays, auto-expiry, 3-tier payment rails, cheque delays, and signer freezing — all built-in, all battle-tested, all on-chain.

> *"Other solutions give you a policy 'framework' and wish you luck. Underscore gives you production-grade financial guardrails — spending limits, asset restrictions, payment rails, time-locks — all enforced on-chain, out of the box."*

### The Killer Analogy

> OWS is a lock on your front door. It works if the door is intact, the lock isn't picked, and nobody climbs through the window. It's local security.
>
> Underscore is a bank vault with time-locks, dual-key requirements, and surveillance cameras monitored by 1,000 independent witnesses. Even if someone gets a key, they can only open the boxes they're authorized for, up to their configured limit, during business hours. It's systemic security.

### When to Acknowledge OWS's Strengths

Be honest about what off-chain solutions do well:
- **Multi-chain support** is genuinely useful for agents operating across ecosystems
- **Lightweight/local** means no gas costs and instant operation
- **Custom executable policies** are infinitely flexible (even if unverifiable)
- **Privacy** — policy configs aren't public

These are real trade-offs, not weaknesses. Underscore chose depth over breadth, guarantees over flexibility, and verifiability over privacy — because when real money is at stake, the strongest enforcement wins.

---

## 10. How We Could Work Together

OWS and Underscore are complementary, not competitive. They operate at different layers of the stack and solve different problems. Here are concrete ways they could integrate:

### 10.1 OWS as the Key Layer, Underscore as the Policy Layer

**The natural split**: OWS manages keys and signs transactions across chains. Underscore enforces what those transactions can do on-chain.

An agent using both would:
1. Use OWS to manage its signing key (HD derivation, encrypted storage, memory protection)
2. Register that key as a Manager on an Underscore Programmable Wallet
3. When executing DeFi operations on Base, sign EIP-712 messages via OWS
4. Submit to Underscore's `AgentSenderGeneric` for on-chain policy enforcement
5. For non-Base operations (Solana, Bitcoin, etc.), use OWS policies as the primary guardrail

**Benefit**: Best of both worlds — OWS's multi-chain key management + Underscore's on-chain enforcement for high-value DeFi operations.

### 10.2 OWS Executable Policy That Calls Underscore

OWS's custom executable policy system could be used to add an Underscore-aware pre-check:

```bash
# OWS executable policy that simulates against Underscore contracts
# Before OWS signs, check if the transaction would pass Underscore's on-chain validation
```

The executable could:
- Decode the transaction calldata
- Simulate it against Underscore's Sentinel contract via `eth_call`
- Reject transactions that would revert on-chain (saving gas)
- Add an off-chain pre-filter to complement on-chain enforcement

### 10.3 Underscore as an OWS "Chain Plugin" for DeFi

OWS could offer Underscore as a specialized execution layer for Base DeFi:
- Instead of raw `sign()` for Base transactions, route through Underscore's higher-level operations
- `earnDeposit()`, `swapTokens()`, `transferFunds()` as first-class operations
- Inherit all of Underscore's on-chain guardrails automatically
- Abstract away the complexity of interacting with 37 DeFi protocols

### 10.4 Shared Agent Ecosystem

**Agent developers** could use OWS for:
- Key management across all chains
- Non-DeFi signing (message signing, attestations, identity)
- Chains without smart contract wallets (Bitcoin, Cosmos)

**The same agents** would use Underscore for:
- DeFi operations on Base with full guardrails
- Yield management, swaps, debt operations
- Payment automation (payees, cheques)
- Any operation where on-chain enforcement matters

### 10.5 OWS MCP Server + Underscore MCP Server

Both could expose MCP (Model Context Protocol) interfaces:
- **OWS MCP**: Key creation, message signing, multi-chain operations
- **Underscore MCP**: DeFi operations, policy management, payment rails

AI agents using MCP would naturally discover and use both — OWS for signing, Underscore for policy-enforced DeFi execution.

### 10.6 Underscore Earn Vaults via OWS

OWS users could access Underscore Earn Vaults:
- Use OWS to sign deposit/withdrawal transactions
- Get AI-managed yield strategies (ERC-4626)
- Receive composable vault tokens (standard ERC-20)
- No need for a Programmable Wallet — just standard DeFi interaction

This is the lightest integration path: OWS handles keys, Underscore handles yield.

### 10.7 Joint Security Model: Defense in Depth

The strongest configuration uses both layers:

```
Layer 1 (OWS - Local): Pre-sign policy check, key encryption, memory protection
Layer 2 (Underscore - On-chain): Post-execution validation, spending limits, asset restrictions
```

Even if Layer 1 is fully compromised (binary replaced, keys extracted), Layer 2 still holds for delegated Underscore manager paths. The attacker has the signing key but is still bounded by on-chain limits. This is true defense in depth for manager and agent access: each layer helps independently, and together they provide materially stronger guarantees.

### 10.8 OWS as The Owner EOA Custody Layer

This is the cleanest practical integration in the current architecture.

- Store the Base owner EOA inside OWS
- Use OWS to sign normal Base transactions that call Underscore contracts
- Let Underscore enforce all wallet rules once those transactions hit chain

This requires no change to Underscore's core wallet model. OWS is simply the local key vault for the owner.

### 10.9 OWS as The Signing Backend For `AgentSenderGeneric`

This is possible, but not yet turnkey.

Current blocker:
- `AgentSenderGeneric` verifies a custom authorization digest built inside the contract
- OWS `signTypedData()` expects a standard typed-data payload

So there are two ways to make this work well:

1. Add an adapter outside OWS that constructs the exact digest `AgentSenderGeneric` expects, then asks OWS to sign the raw message bytes.
2. Standardize the relay authorization into a canonical EIP-712 typed-data schema so OWS can sign it directly via `signTypedData()`.

Option 2 is much cleaner if you want first-class interoperability.

### 10.10 OWS Executable Policies That Understand Underscore

OWS executable policies can become Underscore-aware even without protocol changes.

Examples:
- decode calldata for `transferFunds`, `swapTokens`, `depositForYield`, `borrow`, `repayDebt`
- deny local requests that target forbidden selectors or recipients
- simulate the call against Base using `eth_call`
- reject obviously reverting or suspicious actions before paying gas

This would not replace Underscore's on-chain enforcement. It would be a local pre-filter on top of it.

### 10.11 OWS as Multichain Perimeter, Underscore as Base Execution Core

This is the strongest product fit.

- OWS handles multichain identity, custody, and lightweight signing across EVM, Solana, Bitcoin, Cosmos, and others
- Underscore handles high-value programmable execution on Base

That turns the comparison from "which wallet wins?" into "which layer owns which responsibility?"

OWS owns:
- local key custody
- multichain account derivation
- generic signing interfaces
- local agent tokenization

Underscore owns:
- programmable execution
- DeFi-specific permissions
- payment rails
- on-chain enforceable spend controls
- atomic post-execution safety checks

---

## 11. Summary

| Dimension | OWS | Underscore |
|-----------|-----|------------|
| **Type** | Local key management library | On-chain programmable wallet |
| **Chains** | 9 | 1 (Base) |
| **Policy enforcement** | Off-chain, software-based | On-chain, smart-contract-based |
| **Built-in policies** | 2 (chain allowlist, expiry) | 20+ (spending limits, asset restrictions, protocol limits, payment rails, time-locks, etc.) |
| **Post-execution checks** | None | Atomic revert on violation |
| **DeFi integration** | None | Broad protocol-adapter integration on Base |
| **Key management** | Manages actual private keys | Never touches keys |
| **Compromise impact** | Total loss possible | Bounded by on-chain limits |
| **Best for** | Multi-chain agents, lightweight signing | DeFi operations with real money at stake |
| **Together** | Defense in depth: OWS for keys + Underscore for enforcement |

---

## 12. Direct Answers To The Original Questions

### Does OWS have blockchain-based policies enforced by smart contract?

No, not in the standard as currently specified.

OWS policies are:
- local JSON policy files
- attached to API keys
- evaluated in software before decryption/signing
- enforced by the OWS code path, not by a smart contract onchain

The strongest evidence is:
- wallet and key material live in `~/.ows/...`
- policies live in `~/.ows/policies/...`
- executable policies are local programs
- key isolation docs describe in-process policy evaluation before decryption

### How are OWS policies implemented?

Two ways:

1. Declarative rules
- `allowed_chains`
- `expires_at`

2. Custom executable policies
- local executable gets `PolicyContext` JSON
- returns allow/deny JSON
- fail-closed on timeout, invalid output, or non-zero exit

This means OWS's advanced policy story is effectively "bring your own local validator."

### Where do OWS guardrails come into play?

They come into play only before signing:

1. authenticate credential
2. if API token, load attached policies
3. evaluate policies
4. if allowed, decrypt mnemonic/private key
5. sign
6. wipe memory

Once the signature exists, OWS is done. The chain does not know those policies existed.

### Where do Underscore guardrails come into play?

They come into play during execution itself:

1. wallet checks signer permissions
2. wallet checks asset/protocol/recipient constraints
3. wallet executes the action
4. wallet checks post-action USD/slippage/period limits
5. transaction commits or reverts atomically

That is a much stronger guarantee because the chain is enforcing the rule set.

### What is the cleanest one-line difference?

OWS controls access to keys.
Underscore controls access to funds.

---

## 13. Source Map

### OWS

- `openwallet.sh` homepage:
  https://openwallet.sh/
- OWS overview:
  https://docs.openwallet.sh/
- OWS storage format:
  https://raw.githubusercontent.com/open-wallet-standard/core/main/docs/01-storage-format.md
- OWS signing interface:
  https://raw.githubusercontent.com/open-wallet-standard/core/main/docs/02-signing-interface.md
- OWS policy engine:
  https://raw.githubusercontent.com/open-wallet-standard/core/main/docs/03-policy-engine.md
- OWS agent access layer:
  https://raw.githubusercontent.com/open-wallet-standard/core/main/docs/04-agent-access-layer.md
- OWS key isolation:
  https://raw.githubusercontent.com/open-wallet-standard/core/main/docs/05-key-isolation.md
- OWS conformance/security:
  https://raw.githubusercontent.com/open-wallet-standard/core/main/docs/08-conformance-and-security.md

### Underscore Docs / Website

- `../underscore-docs/user-wallet.md`
- `../underscore-docs/managers.md`
- `../underscore-docs/payees.md`
- `../underscore-docs/cheques.md`
- `../underscore-docs/whitelist.md`
- `../underscore-website/src/components/home/MoneyForAgents.tsx`

### Underscore Contracts

- `contracts/core/userWallet/UserWallet.vy`
- `contracts/core/userWallet/UserWalletConfig.vy`
- `contracts/core/walletBackpack/Sentinel.vy`
- `contracts/core/walletBackpack/Kernel.vy`
- `contracts/core/walletBackpack/Paymaster.vy`
- `contracts/core/walletBackpack/ChequeBook.vy`
- `contracts/core/walletBackpack/HighCommand.vy`
- `contracts/core/agent/AgentWrapper.vy`
- `contracts/core/agent/AgentSenderGeneric.vy`
- `contracts/core/agent/UserWalletSignatureHelper.vy`
- `contracts/core/Hatchery.vy`
- `contracts/data/MissionControl.vy`

### Relevant Tests Read During Analysis

- `tests/core/agent/test_agent_signatures.py`
- `tests/core/userWallet/test_user_wallet_owner_bypass.py`
- `tests/core/walletBackpack/sentinel/test_manager_validation.py`
- `tests/core/walletBackpack/kernel/test_whitelist.py`
