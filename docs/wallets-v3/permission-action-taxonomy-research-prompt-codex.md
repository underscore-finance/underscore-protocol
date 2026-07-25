# Independent Research Prompt: Wallet Actions and Delegated Permissions

**Status:** Supporting research instrument for the owner-selected governing
wallet architecture. This prompt is not itself an architecture or
implementation authorization.

Copy everything below the divider into each research model.

For the most comparable first pass, run every model without web browsing. A
second browsing-enabled pass can then test the recommendations against current
standards and implementations.

---

You are conducting an independent architecture research project about delegated
permissions for a programmable smart-contract wallet.

You do not have access to our codebase. Work only from the facts and terminology
in this prompt, state any additional assumptions, and reason from first
principles. Do not ask follow-up questions.

Your job is not to ratify our current hypothesis or conceptual model. Your job
is to determine whether they are correct, identify where they fail, and
recommend the safest practical design.

## System facts

### Product and execution environment

- This is an externally used, EVM-compatible smart-contract wallet that holds
  user assets and interacts with external financial integrations.
- For this research run, assume the primary users are businesses: small
  companies and teams using the wallet for treasury management, operational
  payments, and payroll. The people configuring permissions are finance or
  engineering staff, not smart-contract security experts. Multiple people and
  many delegated agents operate a single wallet, so segregation of duties and
  dual control are practical options rather than exotic ones.
- Assume wallet value may range from thousands of dollars to
  multi-million-dollar treasuries. Do not make safety depend on a low balance; a
  full loss is material at every target scale.
- Assume individual transaction values span many orders of magnitude within the
  same wallet: sub-dollar machine payments at one end, and payroll runs, large
  treasury movements, and sizeable position changes at the other. A design that
  is safe for large transfers but uneconomical for micropayments, or economical
  for micropayments but unsafe at scale, has failed. Address this spread
  explicitly rather than optimizing for a single transaction size.
- Do not assume ERC-4337, ERC-7579, or another account-abstraction standard is
  already used. You may discuss a standard as precedent, but distinguish it from
  a recommendation for this system.
- The wallet may operate on more than one EVM chain, but this research does not
  need to design cross-chain infrastructure.
- Regulatory policy, sanctions screening, the Travel Rule, tax reporting, and
  jurisdiction-specific compliance are out of scope. Do not treat them as
  wallet-authority permissions.

### Actors

- The **owner** has full wallet authority and is typically a business multisig
  with an operational signing process. Owner action is therefore available but
  slow and deliberate: assume hours to days and a real coordination cost per
  approval, not seconds. An owner-only recommendation is affordable for rare,
  deliberate operations and unaffordable for anything on an operational hot
  path.
- **Product governance** means our product's administrative authority, such as
  a timelocked multisig, which may approve shared registries and
  implementations. It is not a wallet manager and cannot silently enlarge a
  manager's wallet grant.
- A **manager** is a delegated principal with limited authority. Assume the
  dominant case is an autonomous AI agent, with human delegates and scripted
  strategies as secondary cases. Expect many agents per wallet, each ideally
  narrow, operating continuously at machine speed and frequency with no human
  reviewing individual actions.
- Treat manager keys and automation as hot and compromise-prone. Separately,
  treat an AI agent as manipulable through its inputs: an agent may be induced
  by a malicious invoice, a poisoned price or data feed, a retrieved document,
  or a crafted instruction to take actions that are entirely within its granted
  permissions. Key compromise and input manipulation are distinct threats, and a
  design that contains one may not contain the other.
- Permissions, limits, expiration, and allowed action IDs are configured per
  manager.
- A manager cannot register code, change its own permissions, enlarge its own
  limits, or delegate authority to another identity unless the taxonomy
  explicitly and safely permits sub-delegation.

### Extensible actions

- We want to add actions without adding a new wallet entry point or recompiling
  the wallet for every action.
- Each registered action has a stable `actionId`.
- Our current design uses an explicit per-manager `actionId` allowlist, so
  registering a new action does not automatically expand an existing manager
  grant. This gate is itself under test: if you recommend removing or replacing
  it, say so explicitly and explain how new action registration remains
  fail-closed.
- An action may be atomic and composite. For example, one action may exit a
  yield position, swap the proceeds, and deposit into another position.
- A reviewed action registry may bind an `actionId` to implementation and
  security metadata. The exact metadata and the way required authority is
  determined are research questions, not predetermined answers.

### Extender and execution-contract trust model

- An **extender** is registered action-specific logic that interprets typed
  action data and orchestrates one registered action. It does not own the
  wallet's assets or define the owner's permission grant. Whether it commits
  to, declares, or merely prepares an execution plan — or plays no part at all
  in determining required authority — is a research question, not a given; see
  the brownfield-integration section.
- An **execution contract** (also called an integration adapter) is registered
  integration-specific logic that consumes wallet-issued capability and performs
  the external protocol calls. An extender may invoke one or more execution
  contracts. If your recommendation combines these roles, say so in the
  brownfield-integration section and analyze the resulting trust boundary.
- Extenders and external-integration execution contracts are registered only by
  the owner or product governance through a delayed, reviewed process. Managers
  cannot supply arbitrary implementations.
- Our current preference is to codehash- or implementation-bind a registered
  version and to give materially different code a distinct version or action
  identity. Test that preference in the upgrade and revocation analysis.
- Reviewed code may still be buggy, compromised, or incorrectly configured.
  The design must not rely solely on an extender truthfully describing its own
  effects.
- We currently believe the wallet, rather than the extender, must be the final
  arbiter of what assets, amounts, spenders, recipients, and calls become
  executable. The brownfield-integration analysis must test whether that is
  necessary and achievable at acceptable cost.
- In the primary analysis, assume registered extenders are reviewed but
  potentially buggy. In the adversarial analysis, also test what happens if an
  approved implementation behaves maliciously.

### Existing brownfield policy system

This is a brownfield engine with a greenfield permission taxonomy. The limits
engine exists and should be reused where safe. There is no permission taxonomy
to migrate from; design that layer from first principles while identifying the
smallest safe changes to the existing engine.

The mature policy engine already provides both generic controls and some
action-specific controls.

Generic controls include:

- manager activation, expiration, suspension, and ejection;
- per-transaction, per-period, and lifetime value limits;
- transaction-count limits and cooldowns;
- allowed assets, external protocols/integrations, recipients, payees, and
  merchants;
- per-recipient and per-merchant limits;
- wallet freezing and recovery;
- price lookup, with explicit behavior needed for missing, stale, or zero
  prices.

Existing semantic controls include:

- swap-count limits and maximum slippage;
- approved yield opportunities;
- payment and cheque limits;
- owner-versus-manager distinctions.

The existing engine is therefore not fully action-agnostic. We prefer to reuse
it and make small, well-defined additions, but reuse is a constraint to
evaluate—not a reason to preserve an unsafe abstraction.

## Terminology and current working model

### Neutral payment and operational terminology

Use these terms consistently:

- **Direct payment:** the wallet initiates a transfer now to a recipient.
- **Approved-payee payment:** a direct payment to a recipient that the owner
  previously approved and configured.
- **Payee pull:** an approved payee initiates a later transfer from the wallet,
  subject to revocable payee, amount, frequency, and time bounds.
- **Cheque:** a deferred, recipient-specific claim for up to a fixed amount
  before expiry; it may be redeemed later and may be revocable before
  redemption according to its configured rules.
- **Reservation and capture:** value is reserved or encumbered now; an approved
  merchant may capture no more than the reserved amount before expiry, after
  which the remainder is released.
- **Recurring payment:** the wallet or approved automation initiates bounded
  payments on a schedule.
- **Stream:** a time-based payment obligation that accrues and can be claimed
  according to defined cancellation and settlement rules.
- **x402-style machine payment:** a machine makes a payment in response to an
  HTTP `402 Payment Required` challenge. Treat it as a one-time direct payment
  unless the transaction separately creates a pull right or recurring
  obligation. If unfamiliar with x402, use this definition rather than
  inventing additional semantics.
- **Ejection:** forced deactivation of a manager or integration and revocation
  of its future delegated execution authority. Existing positions,
  reservations, streams, pulls, bridge messages, debt, or signatures may still
  require explicit unwind or cancellation handling.

### Provisional conceptual decomposition

The following reflects how we currently think about the system. These are design
choices under review, not facts or mandatory constraints. If this decomposition
is wrong, say so in deliverable section 15 and proceed using a better one.

1. **Action identity:** currently, the particular operation requested,
   represented by an `actionId`.
2. **Permission:** currently, a durable category of authority that an owner may
   independently grant to or withhold from a manager.
3. **Policy or limit:** currently, a quantitative or contextual constraint on
   authority, such as value, frequency, asset, integration, recipient,
   duration, or slippage.
4. **Execution mode:** currently, a bounded variation in how an authorized
   action is carried out. Our intent is that a mode not silently create a new
   category of authority; test whether that boundary is workable.
5. **Settlement/accounting mode:** our current model uses a wallet-owned set of
   post-execution accounting and validation routines—for example, asset-only,
   debt, or persistent-position accounting. Whether this should be a fixed enum,
   derived per invocation, permission-relevant, or extensible is under review.
6. **Temporary capability:** currently, transaction-scoped authority activated
   for one approved execution, such as a token amount for an approved spender.
   Our preference is exact authority that expires or is cleared atomically; test
   whether that is necessary and sufficient.
7. **Persistent authority:** currently, authority that survives the transaction,
   such as an allowance, pull right, stream, order, delegation, or future
   obligation.
8. **Administrative authority:** currently, power to alter permissions, limits,
   registrations, security state, ownership, guardians, or recovery.

## Research question and hypotheses to test

Design a permission model that allows open-ended action identities while
keeping delegated wallet authority understandable, auditable, economical, and
fail-closed.

Test—not merely accept—the following hypothesis:

> Action identities and implementations may be open-ended, while permission
> semantics, limit semantics, temporary-authority primitives, and wallet
> security invariants remain a small, fixed, compile-time-reviewed set.

Under this hypothesis:

- a new action may use one or more existing permissions;
- registration cannot invent arbitrary authority or policy logic;
- unknown action identities, permission requirements, settlement modes, and
  authority semantics fail closed;
- genuinely new authority or settlement semantics require an explicit core
  review and upgrade.

Also test the two-gate model directly:

> Managers are allowlisted per `actionId` and also hold categorical
> permissions. Justify why both layers are necessary, or recommend collapsing
> them.

If the permission layer's primary value is owner comprehension, grant
management, or reporting rather than independent enforcement, say so
explicitly. That changes what the taxonomy should optimize for.

We have no prior commitment to either a very small taxonomy or a very granular
one. We also have no prior commitment for or against a policy-expression layer.
Assess each option symmetrically:

- If a fixed taxonomy is sufficient, explain why it remains sufficient under
  the adversarial cases.
- If a bounded expression layer is warranted, define its grammar and abuse
  cases.
- If a more expressive layer is necessary, explain why a bounded grammar and
  ordinary permissions plus limits are inadequate, and account for the larger
  audit and governance surface.

Do not optimize for the smallest or largest permission count. State a ranked
split-versus-merge decision rule and apply it consistently.

## Required deliverable

Produce a 9,000–13,000 word report using the following exact numbered sections.
You may add appendices after section 17.

Treat sections 6, 7, 8, 11, 12, 13, 14, and 15 as the analytical core; together
they should account for at least half of the report's words, excluding
appendices and the machine-readable block. Sections 3, 4, 9, and 10 are
principally descriptive. This is allocation guidance, not a machine-verifiable
compliance condition.

If space is constrained, shorten sections 3, 4, 9, and 10 first. Do not shorten
sections 8, 11, 12, 13, or 15. Disclose every shortened or omitted deliverable
section by its unambiguous number.

Do not write Solidity or other implementation code. Tables, state diagrams,
structural sketches, registry-record examples, and bitmask layouts are welcome.
Use `SCREAMING_SNAKE_CASE` for every proposed permission identifier and
`actionId`.

### 1. Executive recommendation

Write this section last even though it appears first.

State:

- the recommended model and permission count;
- whether the open-actions/closed-authority hypothesis survives;
- whether both per-action and categorical permission gates are necessary;
- the most important tradeoff;
- the largest unresolved risk;
- the smallest policy-engine change required;
- your confidence level.

### 2. Assumptions and ranked decision procedure

List every material assumption beyond the supplied facts.

Then give a ranked decision procedure for deciding whether two authorities:

- share a permission;
- require separate permissions;
- require multiple permissions together;
- differ only through limits, configuration, or execution mode;
- remain owner-only.

State which criterion wins when criteria conflict. Consider at least:

- whether an owner would delegate the authorities independently;
- compromise blast radius;
- different custody, recipient, counterparty, liability, or persistence risks;
- different limit and revocation requirements;
- whether one action can be safely described on the same consent screen as the
  other;
- whether an authority is intrinsically defensive because it can only repay,
  add collateral, close a position, or otherwise reduce exposure without
  extracting value;
- whether the difference is authority or merely execution mechanics.

### 3. Competing taxonomy sketches

Provide three compact alternatives of your own choosing. Do not mechanically
label them minimal, balanced, and comprehensive unless those are genuinely the
most useful alternatives.

For each, provide:

- approximate permission count;
- organizing principle;
- strongest advantage;
- most dangerous weakness;
- the failure mode that would make you abandon it.

Keep all three sketches together to approximately 600 words. Detail only the
recommended taxonomy in later sections.

### 4. Final recommended permission taxonomy and grant model

Use the following block once per recommended permission. Do not use a wide
Markdown table.

```text
PERMISSION: <SCREAMING_SNAKE_CASE identifier>
OWNER CONSENT: <one plain-language sentence>
PRECISE AUTHORITY: <the exact authority granted>
EXAMPLE ACTIONS: <representative actions that may consume this permission>
EXPLICIT EXCLUSIONS: <what it does not authorize>
COMMON COMBINATIONS: <other permissions commonly required>
LIMITS AND CONFIGURATION: <required constraints>
ROLLOUT STATE: INITIAL | LATER | RESERVED
WHY SEPARATE: <security and delegation reason>
```

Each permission must have exactly one rollout state:

- `INITIAL`: required for the initial system;
- `LATER`: likely useful but not initially required;
- `RESERVED`: named now only to preserve a reviewed conceptual boundary.

The owner-consent sentence must be something a finance or operations person at
a small company could understand and approve without smart-contract expertise.
Difficulty explaining a permission plainly is evidence that its boundary may be
wrong, but a business audience can absorb more granularity than a retail one:
do not merge two genuinely distinct authorities merely to shorten the list.

Do not create a catch-all that authorizes arbitrary calldata or unconstrained
external-protocol interaction. If you conclude a broad integration-scoped
permission is necessary, define its exact boundaries and argue for it
explicitly rather than banning or accepting it by name.

Because one wallet may delegate to many narrow agents with different jobs, the
grant model matters as much as the taxonomy. State whether owners grant
permissions individually or through owner-facing roles, presets, or bundles,
and how that model scales to dozens of agents without pushing operators toward
granting everything. If bundles are recommended:

- are they wallet-enforced or presentation-only;
- who defines and versions them;
- can the owner inspect and customize their expanded permissions;
- what prevents a convenience bundle from becoming a hidden catch-all;
- what happens when a bundle definition changes after an owner used it.

### 5. Concept-separation audit

Use at least 500 words. Give at least five concrete examples, each
distinguishing two or more of the following eight concepts in this order:

1. action identity;
2. delegated permission;
3. policy or limit;
4. execution mode;
5. settlement/accounting mode;
6. temporary capability;
7. persistent authority;
8. administrative authority.

Identify design mistakes caused by conflating them. Explicitly analyze whether
action-specific controls already present in the policy engine—such as slippage,
yield-opportunity approval, and cheque limits—belong where they are.

### 6. Payment authority analysis

Use at least 800 words.

Analyze direct payments, approved-payee payments, merchant payments, payee
pulls, cheques, invoice payments, reservation/capture, recurring payments,
subscriptions, streams, x402-style machine payments, batch and payroll
disbursements, refunds, cancellation, and revocation.

Argue the strongest version of both designs before choosing:

- **Mechanism-specific permissions:** materially different payment mechanisms
  receive independently delegable permissions.
- **Shared payment permissions:** a smaller number of payment authorities use
  modes, recipient configuration, persistence flags, and distinct limits.

Explain exactly where "pay now" ends and "create future payment authority"
begins. Cover revocation, partial capture, expiry, recipient changes, refunds,
and obligations that survive manager ejection.

### 7. Persistent authority, signatures, and administration

Use at least 700 words.

Separately analyze:

- exact and unlimited token allowances;
- EIP-1271 and other off-chain signatures;
- Permit2-style authorization;
- gasless orders and marketplace listings;
- delegation of governance or financial control;
- sub-delegation to another manager or session key;
- owner, guardian, recovery, freeze, and ejection authority;
- registration and codehash rebinding;
- global limit or policy changes.

Identify which are ordinary permissions, special owner-approved commitments,
dual-control actions, or categorically non-routable administration.

Also answer:

- Given that the owner is typically a business multisig, which administrative
  actions still warrant an additional delay, timelock, or guardian confirmation
  beyond multisig approval, and which are made unnecessary by it?
- Can a narrowly defined defensive permission safely authorize repaying debt,
  adding collateral, closing a position, or reducing exposure without also
  enabling value extraction or a new persistent obligation?

### 8. Fixed adversarial narratives

For each scenario, write at least 150 words and use:

`attacker capability → exact permitted sequence → violated invariant or maximum loss → prevention/detection/recovery`

Each scenario must name specific example assets, give a concrete sequence of
steps, and quantify the loss or clearly bound it when exact quantification is
impossible.

Analyze these exact scenarios:

1. A compromised manager uses only explicitly allowed action IDs, external
   integrations, assets, recipients, permissions, and limits. Find the cheapest
   or most damaging attack that remains fully compliant for days or weeks.
2. An AI-agent manager is not compromised but is manipulated through its inputs
   — a malicious invoice, a poisoned data or price feed, a retrieved document,
   a crafted instruction — into a sequence of actions that are individually
   permitted, individually plausible, and within every limit. No key is stolen
   and no limit is exceeded. State which parts of your taxonomy still constrain
   the outcome and which offer no protection at all.
3. An approved extender or integration adapter is buggy or malicious and
   attempts arbitrary calldata, recipient substitution, a larger token
   allowance, or a persistent approval.
4. A permitted action executes while an asset price is stale, manipulated,
   missing, or zero, thereby weakening value-denominated limits.
5. A manager is revoked or ejected while streams, pull rights, reservations,
   open debt, bridge messages, and signed off-chain orders remain outstanding.
6. A composite action fails after some internal work, while allowances,
   counters, cooldowns, reservations, or external-protocol state may already
   have changed.

Then, in at least 200 further words, identify:

- the broadest permission in your taxonomy;
- the most dangerous two-permission combination;
- the most dangerous action that appears operationally harmless;
- the fail-closed behavior for unknown values and unsupported combinations.

### 9. Independent stress-test inventory

Before using the coverage checklist in Appendix A, derive 20–25 actions that
stress the taxonomy. Use only:

| Action identity | Underlying authority | Permission(s) | Persistent effect? |
|---|---|---|---|

The persistent-effect column must identify any surviving position, signature,
allowance, liability, or future obligation, or say `NONE`.

Five of the 20–25 actions must be plausible actions that do not fit the
recommended taxonomy cleanly. After the table, briefly explain whether each
awkward action exposes a taxonomy defect, is appropriately owner-only, or could
be extender-routable only after adding a new bounded authority primitive.

### 10. Fixed benchmark action mapping

Map the following exact actions in this exact order so results from multiple
researchers can be compared:

1. transfer to an owner-approved recipient;
2. transfer to a first-time recipient;
3. one-time payment to an approved merchant;
4. create a revocable payee-pull authorization;
5. create a bounded recurring payment;
6. cancel an outstanding recurring payment or stream created earlier;
7. reserve value for later merchant capture;
8. grant an exact token allowance to an approved spender for one action;
9. grant an unlimited token allowance that survives the transaction;
10. revoke or reduce an existing token allowance;
11. produce an EIP-1271, Permit2, gasless-order, or marketplace signature that
    can move value later;
12. pay gas, relayer fees, or paymaster charges from wallet funds;
13. deposit into an approved yield opportunity;
14. withdraw from an existing yield position back to the wallet;
15. execute a spot swap within an approved integration and slippage bound;
16. add approved collateral and borrow against it;
17. repay existing debt with wallet funds, without another action;
18. cast a governance vote using a position held by the wallet;
19. wrap or unwrap the chain's native asset without changing the beneficial
    owner;
20. issue a recipient-specific cheque for up to a fixed amount before expiry;
21. make a one-time x402-style machine payment in response to an HTTP 402
    challenge;
22. execute a batch disbursement to many approved recipients in one action,
    such as a payroll run;
23. bridge assets to an approved recipient on an approved destination chain,
    without a destination action.

Use this block once per benchmark action. Do not use a wide Markdown table.

```text
BENCHMARK: <number>
PROPOSED ACTION_ID: <SCREAMING_SNAKE_CASE identifier>
PERMISSIONS: <permission IDs or OWNER_ONLY>
LIMITS AND CONFIGURATION: <required constraints>
EXECUTION AND SETTLEMENT: <relevant bounded mechanics>
PERSISTENT EFFECT OR AUTHORITY: <specific effect or NONE>
ROUTABILITY AND OWNER CONTROL: <extender-routable, owner, or dual control>
RATIONALE: <short reason for the mapping>
```

### 11. Composite actions and partial failure

Use at least 600 words.

Map at least:

- yield rebalance without a swap;
- yield rebalance with a swap;
- deleverage using collateral conversion;
- claim and restake;
- bridge and deposit;
- withdraw and pay;
- refinance debt across external integrations;
- unwind liquidity and repay debt.

For each, state:

- permission composition;
- whether one `actionId` may represent the entire atomic operation;
- the authority consumed at each stage;
- what happens if step 2 of 3 or step 3 of 4 fails;
- when counters, cooldowns, allowances, and limits advance;
- whether partial completion can strand funds or authority;
- whether the composition creates privilege greater than the union of its
  permissions.

### 12. Minimal brownfield integration and feasibility

Use at least 800 words.

The goal is for the wallet to determine the required authority for an unknown
but registered action without embedding action-specific code in the wallet.

Compare plausible mechanisms rather than assuming one:

- registry-bound fixed permission requirements;
- bounded declarations committed by an extender and independently constrained
  by the wallet;
- wallet-derived requirements from a typed action plan;
- post-state evidence;
- another mechanism you believe is safer.

For each, explain what is trusted, what is wallet-enforced, and how a malicious
or buggy extender could lie. Test our belief that the wallet must be the final
arbiter rather than treating it as a conclusion.

Then recommend:

- the smallest safe registry record;
- the smallest policy-engine changes;
- whether permission requirements and settlement behavior should be fixed per
  `actionId`, derived per invocation, or use a bounded combination;
- whether both per-manager action-ID approval and categorical permissions are
  necessary, and the distinct security or UX job performed by each;
- how unknown or malformed values fail closed;
- whether a fixed bitmask is sufficient and, if so, a sensible capacity;
- the approximate on-chain validation cost, including the important storage
  reads, writes, calldata, and repeated checks on each action;
- whether that cost is viable at both ends of the transaction-value spread,
  given that one wallet must support sub-dollar machine payments and large
  treasury movements. If a single validation path cannot serve both, state what
  differentiates the cheap path from the expensive one and what new risk that
  differentiation introduces.

A taxonomy that is conceptually elegant but requires economically unreasonable
validation on every action is not viable. Use rough orders of magnitude or
comparisons when exact gas estimates are not supportable; do not invent false
precision.

Do not preserve the existing engine merely because it exists. Identify any
specific existing semantic control that should be redesigned.

### 13. Revocation, taxonomy versioning, upgrade, and exit semantics

Use at least 900 words.

#### 13a. Revocation, exit, and outstanding authority

Explain:

- immediate versus delayed revocation;
- effects on in-flight and persistent obligations;
- cancellation authority and its griefing risks;
- emergency disablement;
- surviving exit or debt-repayment paths when entry actions are disabled;
- attribution of each action, commitment, and persistent authority to the
  manager that created it, in a form usable for business audit and accounting
  when dozens of agents share one wallet;
- whether an owner can enumerate every outstanding allowance, signature or
  order, stream, pull right, cheque, reservation, bridge message, and other
  surviving authority or obligation;
- how an owner revokes authority that cannot be enumerated on-chain.

#### 13b. Taxonomy versioning and implementation upgrade

Explain:

- safe codehash or implementation rebinding;
- whether a new implementation must receive a new `actionId`;
- how the permission taxonomy itself is versioned and extended;
- whether bit positions are permanent;
- how adding, deprecating, or reordering permissions avoids silently enlarging
  stored manager grants.

### 14. Future-compatibility test

Name three realistic action types that may become important within three years
and that the recommended taxonomy handles poorly.

For each, state whether support would require:

- only a new `actionId`;
- new configuration or limit semantics;
- a new permission;
- a new temporary-authority primitive;
- a new settlement behavior;
- a core-contract upgrade.

Explain what would falsify your claim that the taxonomy is sufficiently
future-compatible.

### 15. Mandatory disagreement and rejected alternative

This section must be non-empty and 350–500 words.

State:

- where the supplied hypothesis or provisional decomposition is wrong,
  incomplete, or too convenient;
- which supplied system constraint most harms the ideal design;
- which apparent requirement should be removed if you controlled the product;
- the strongest alternative architecture you rejected;
- why a reasonable expert could prefer that alternative;
- what evidence would make you switch to it.

Do not use this section merely to restate ordinary tradeoffs. If a supplied
definition or constraint prevents your preferred recommendation, reject it here
and proceed with the safer design rather than complying silently.

### 16. External precedents and analogy limits

Select two authorization or capability precedents from outside blockchain,
without being given candidate names. For each, explain:

- what design lesson it contributes;
- where the analogy to a financial wallet breaks.

If browsing is enabled, also assess at least two current smart-wallet,
session-key, delegation, or capability standards using primary standards,
official documentation, research papers, or source repositories. Clearly
separate observed precedent from your recommendation.

If browsing is disabled, state that and skip the current-blockchain-precedent
subsection. Do not fabricate citations or current adoption claims.

### 17. Machine-comparable summary

Do not repeat the permission blocks from section 4.

Provide exactly one fenced block:

```text
WEB_RESEARCH_USED: YES | NO
KNOWLEDGE_CUTOFF_IF_KNOWN: <date or UNKNOWN>
PERMISSION_IDS: <comma-separated identifiers>
PERMISSION_STATES: <ID_A=INITIAL, ID_B=LATER, ID_C=RESERVED, ...>
RECOMMENDED_PERMISSION_COUNT: <number>
INITIAL_PERMISSION_COUNT: <number>
LATER_PERMISSION_COUNT: <number>
RESERVED_PERMISSION_COUNT: <number>
COUNT_CHECK: <recommended number> = <initial number> + <later number> + <reserved number>
COUNT_CHECK_PASSES: YES | NO
TWO_GATE_MODEL: KEEP_BOTH | ACTION_ID_ONLY | PERMISSION_ONLY | OTHER
FIXED_TAXONOMY_SUFFICIENT: YES | NO | CONDITIONAL
POLICY_EXPRESSION_LAYER: NONE | BOUNDED | EXPRESSIVE | CONDITIONAL
PRIMARY_DISAGREEMENT_WITH_PROMPT: <one sentence>
STRONGEST_REJECTED_ALTERNATIVE: <one sentence>
CONFIDENCE: LOW | MEDIUM | HIGH
SECTIONS_SHORTENED_OR_OMITTED: NONE | <comma-separated deliverable section numbers>
```

The numerical equality in `COUNT_CHECK` must hold. Verify and correct every
count before returning the report; `COUNT_CHECK_PASSES` must be `YES` in a
completed report.

## Research quality rules

- Do not ask follow-up questions.
- Do not mirror the appendix categories as the permission taxonomy.
- Do not equate action IDs with permissions.
- Do not assume every action needs a unique permission.
- Do not assume different execution mechanics are different authority.
- Do not assume a smaller taxonomy is safer.
- Do not assume a larger taxonomy is more future-compatible.
- Do not assume owner-only is costless.
- Do not trust an extender merely because it was reviewed.
- Do not hide persistent authority inside a supposedly one-transaction action.
- Off-chain automation may trigger or schedule an action, but do not rely on
  off-chain monitoring, a trusted relayer, or operator intervention to enforce
  safety or contain delegated authority.
- If a supplied definition or constraint prevents the recommendation you
  believe is correct, say so in section 15 rather than complying silently.
- Apply the ranked split-versus-merge rule consistently.
- Prefer concrete attack sequences over generic risk lists.
- Clearly label facts, assumptions, inferences, and recommendations.

## Appendix A: coverage checklist

Use this only after drafting the independent stress-test inventory in section 9.
Reconcile omissions, but do not reorganize the taxonomy around this list.

- direct transfers and approved-recipient payments;
- merchant, invoice, cheque, pull, reservation/capture, recurring, subscription,
  stream, x402-style, refund, and cancellation flows;
- exact, standing, and unlimited token approvals;
- off-chain signatures, permits, orders, and listings;
- gas, relayer, and paymaster fees;
- spot swaps, minting, redemption, wrapping, and unwrapping;
- yield deposits, withdrawals, migrations, and rebalances;
- collateral, borrowing, repayment, leverage, deleverage, and refinancing;
- liquidity provision and concentrated-liquidity management;
- rewards, staking, locking, restaking, and slashing exposure;
- bridges, cross-chain messages, delayed finality, and destination execution;
- derivatives, perpetuals, options, liquidation, and contingent liabilities;
- governance voting, delegation, proposal creation, and execution;
- escrow, vesting, claims, tokenized real-world assets, NFTs, and tokenized
  positions;
- manager administration, sub-delegation, freeze, recovery, ejection, registry
  changes, and codehash rebinding;
- atomic composites, partial failure, persistent obligations, and future actions
  that do not fit cleanly.

## Final compliance check before answering

Confirm all of the following before returning the report:

- all 17 deliverable sections are present and numbered unambiguously;
- the report is between 9,000 and 13,000 words;
- section 5 is at least 500 words, section 6 is at least 800 words, section 7 is
  at least 700 words, every section-8 narrative is at least 150 words followed
  by at least 200 words of summary identifications, section 11 is at least 600
  words,
  section 12 is at least 800 words, section 13 is at least 900 words, and
  section 15 is 350–500 words;
- every permission uses the exact labeled block, including an owner-consent
  sentence and exactly one rollout state;
- all 23 benchmark blocks appear in the required order and use the exact
  labeled block;
- all six adversarial scenarios are present, each at least 150 words and
  concrete;
- section 9 contains 20–25 actions, five of which are explicitly identified as
  awkward; section 3 contains three sketches; section 14 names three future
  action types;
- section 15 contains a real disagreement;
- permission counts balance and `COUNT_CHECK_PASSES` is `YES`;
- exactly one section-17 machine-readable summary block is emitted.
