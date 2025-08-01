# Migrator Technical Documentation

[📄 View Source Code](../../../contracts/core/walletBackpack/Migrator.vy)

## Overview

Migrator is the wallet migration module for the Underscore Protocol, enabling secure transfer of funds and configuration between user wallets. As a critical wallet backpack item, it provides comprehensive migration capabilities while maintaining strict security controls to ensure only authorized migrations occur between wallets with matching ownership and group membership.

**Core Features**:
- **Complete Fund Migration**: Transfer all assets from one wallet to another
- **Configuration Cloning**: Copy managers, payees, and whitelist settings
- **Trial Fund Handling**: Automatic clawback of trial funds before migration
- **Validation Framework**: Extensive checks ensuring secure migrations
- **Atomic Operations**: All-or-nothing migration approach for safety

The contract implements sophisticated validation ensuring only same-owner wallets can migrate, group membership consistency, clean state requirements for destination wallets, and proper handling of special cases like trial funds and starting agents.

## System Architecture Diagram

```
+-------------------------------------------------------------------------+
|                               Migrator                                  |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                       Migration Flow                              | |
|  |                                                                   | |
|  |  1. Validation Phase:                                             | |
|  |     ├─> Verify both wallets are valid Underscore wallets         | |
|  |     ├─> Confirm same owner for both wallets                      | |
|  |     ├─> Check matching group IDs                                  | |
|  |     ├─> Ensure no pending ownership changes                      | |
|  |     ├─> Verify wallets not frozen                                | |
|  |     └─> Confirm destination wallet is clean                       | |
|  |                                                                   | |
|  |  2. Fund Migration:                                                | |
|  |     ├─> Handle trial funds (clawback if needed)                   | |
|  |     ├─> Transfer each asset with balance > 0                      | |
|  |     ├─> Track USD values for reporting                            | |
|  |     └─> Deregister assets from source wallet                      | |
|  |                                                                   | |
|  |  3. Configuration Clone:                                           | |
|  |     ├─> Copy global manager settings                              | |
|  |     ├─> Add all managers (except starting agent)                  | |
|  |     ├─> Copy global payee settings                                | |
|  |     ├─> Add all payees                                            | |
|  |     └─> Copy all whitelisted addresses                            | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                    Destination Wallet Requirements                 | |
|  |                                                                   | |
|  |  Clean State:                                                     | |
|  |    • No payees (numPayees ≤ 1)                                    | |
|  |    • No whitelist entries (numWhitelisted ≤ 1)                    | |
|  |    • No managers except starting agent                            | |
|  |                                                                   | |
|  |  Ownership:                                                       | |
|  |    • Same owner as source wallet                                  | |
|  |    • Same group ID                                                | |
|  |    • No pending ownership changes                                 | |
|  |                                                                   | |
|  |  Status:                                                          | |
|  |    • Not frozen                                                   | |
|  |    • Valid Underscore wallet                                      | |
|  +-------------------------------------------------------------------+ |
|                                                                         |
|  +-------------------------------------------------------------------+ |
|  |                      Trial Funds Handling                          | |
|  |                                                                   | |
|  |  Before Migration:                                                 | |
|  |    1. Check if wallet has trial funds                             | |
|  |    2. Calculate acceptable dust (1% of trial amount)              | |
|  |    3. Call Hatchery to clawback funds                             | |
|  |    4. Verify remaining amount ≤ dust threshold                    | |
|  |    5. Block migration if too much remains                         | |
|  +-------------------------------------------------------------------+ |
+-------------------------------------------------------------------------+
```

## Constants and Immutables

### Constants
- `LEDGER_ID: uint256 = 1` - Registry ID for Ledger contract
- `HATCHERY_ID: uint256 = 5` - Registry ID for Hatchery contract
- `MAX_DEREGISTER_ASSETS: uint256 = 25` - Maximum assets to deregister per migration
- `HUNDRED_PERCENT: uint256 = 100_00` - 100% in basis points

### Immutable Variables
- `UNDY_HQ: address` - UndyHq registry address

## Constructor

### `__init__`

Initializes Migrator with the protocol registry address.

```vyper
@deploy
def __init__(_undyHq: address):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_undyHq` | `address` | UndyHq registry contract address |

#### Access

Called only during deployment

#### Example Usage
```python
migrator = Migrator.deploy(
    undy_hq.address
)
```

## Combined Migration Functions

### `migrateAll`

Migrates both funds and configuration in a single transaction.

```vyper
@external
def migrateAll(_fromWallet: address, _toWallet: address) -> (uint256, bool):
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_fromWallet` | `address` | Source wallet address |
| `_toWallet` | `address` | Destination wallet address |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Number of assets migrated |
| `bool` | Whether configuration was cloned |

#### Access

Must be called by the owner of both wallets

#### Events Emitted

- `FundsMigrated` - Contains fromWallet (indexed), toWallet (indexed), numAssetsMigrated, and totalUsdValue
- `ConfigCloned` - Contains fromWallet (indexed), toWallet (indexed), numManagersCopied, numPayeesCopied, and numWhitelistCopied

#### Example Usage
```python
# Migrate everything from old to new wallet
num_assets, config_cloned = migrator.migrateAll(
    old_wallet.address,
    new_wallet.address,
    sender=owner
)

print(f"Migrated {num_assets} assets")
print(f"Config cloned: {config_cloned}")
```

#### Notes

- At least one operation (funds or config) must succeed
- Funds migration handled first, then configuration
- Trial funds automatically handled if present

## Fund Migration Functions

### `migrateFunds`

Migrates all funds from one wallet to another.

```vyper
@external
def migrateFunds(_fromWallet: address, _toWallet: address) -> uint256:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_fromWallet` | `address` | Source wallet with funds |
| `_toWallet` | `address` | Destination wallet |

#### Returns

| Type | Description |
|------|-------------|
| `uint256` | Number of assets migrated |

#### Access

Must be called by the owner of both wallets

#### Events Emitted

- `FundsMigrated` - Contains fromWallet (indexed), toWallet (indexed), numAssetsMigrated, and totalUsdValue

#### Example Usage
```python
# Migrate only funds
num_migrated = migrator.migrateFunds(
    source_wallet.address,
    target_wallet.address,
    sender=owner
)

print(f"Successfully migrated {num_migrated} assets")
```

#### Notes

- Source wallet must have more than 1 asset registered
- Trial funds must be handled successfully
- Assets with zero balance are skipped
- Up to 25 assets deregistered from source per migration

### Trial Fund Handling

The migration process includes special handling for trial funds:

1. **Detection**: Checks if wallet has trial funds via `getTrialFundsInfo()`
2. **Threshold**: Calculates 1% of trial amount as acceptable dust
3. **Clawback**: Calls Hatchery to recover trial funds
4. **Verification**: Ensures remaining amount ≤ dust threshold
5. **Block/Allow**: Migration blocked if too much remains

## Configuration Clone Functions

### `cloneConfig`

Copies all configuration from one wallet to another.

```vyper
@external
def cloneConfig(_fromWallet: address, _toWallet: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_fromWallet` | `address` | Source wallet with configuration |
| `_toWallet` | `address` | Destination wallet (must be clean) |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | Success status |

#### Access

Must be called by the owner of the destination wallet

#### Events Emitted

- `ConfigCloned` - Contains fromWallet (indexed), toWallet (indexed), numManagersCopied, numPayeesCopied, and numWhitelistCopied

#### Example Usage
```python
# Clone configuration from template wallet
success = migrator.cloneConfig(
    template_wallet.address,
    new_wallet.address,
    sender=owner
)

if success:
    print("Configuration successfully cloned")
```

#### Configuration Items Cloned

1. **Global Manager Settings**: All default manager configurations
2. **Individual Managers**: Each manager with their specific settings (except starting agent)
3. **Global Payee Settings**: All default payee configurations
4. **Individual Payees**: Each payee with their specific settings
5. **Whitelist Addresses**: All whitelisted addresses (no time-lock on copy)

## Validation Functions

### `canMigrateFundsToNewWallet`

Checks if funds can be migrated between wallets.

```vyper
@view
@external
def canMigrateFundsToNewWallet(_fromWallet: address, _toWallet: address, _caller: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_fromWallet` | `address` | Source wallet address |
| `_toWallet` | `address` | Destination wallet address |
| `_caller` | `address` | Address attempting migration |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if migration is allowed |

#### Access

Public view function

#### Validation Criteria

**Source Wallet**:
- Must be valid Underscore wallet
- Caller must be owner
- Not frozen
- No pending ownership change

**Destination Wallet**:
- Must be valid Underscore wallet
- Same owner as source
- Same group ID as source
- Not frozen
- No pending ownership change
- No payees (except index 0)
- No whitelist entries (except index 0)
- No managers (except starting agent)

### `canCopyWalletConfig`

Checks if configuration can be copied between wallets.

```vyper
@view
@external
def canCopyWalletConfig(_fromWallet: address, _toWallet: address, _caller: address) -> bool:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_fromWallet` | `address` | Source wallet address |
| `_toWallet` | `address` | Destination wallet address |
| `_caller` | `address` | Address attempting copy |

#### Returns

| Type | Description |
|------|-------------|
| `bool` | True if configuration copy is allowed |

#### Access

Public view function

#### Validation Criteria

Similar to fund migration with key difference:
- Caller must be owner of **destination** wallet (not source)
- Allows copying from any wallet you can read

## Utility Functions

### `getMigrationConfigBundle`

Retrieves migration-relevant configuration data.

```vyper
@view
@external
def getMigrationConfigBundle(_userWallet: address) -> wcs.MigrationConfigBundle:
```

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `_userWallet` | `address` | Wallet to query |

#### Returns

| Type | Description |
|------|-------------|
| `MigrationConfigBundle` | Bundle containing migration-relevant data |

#### Access

Public view function

#### Bundle Contents
- `owner` - Wallet owner address
- `isFrozen` - Whether wallet is frozen
- `numPayees` - Number of registered payees
- `numWhitelisted` - Number of whitelisted addresses
- `numManagers` - Number of managers
- `startingAgent` - Starting agent address if set
- `startingAgentIndex` - Index of starting agent
- `hasPendingOwnerChange` - Pending ownership status
- `groupId` - Wallet group identifier

## Security Considerations

### Ownership Verification
- Both wallets must have same owner
- Caller must be the owner
- No pending ownership changes allowed

### State Requirements
- Destination wallet must be clean
- No existing configurations that could conflict
- Starting agent handled specially

### Group Consistency
- Both wallets must belong to same group
- Ensures organizational boundaries maintained

### Frozen Wallet Protection
- Cannot migrate to/from frozen wallets
- Prevents unauthorized movement during lock

### Trial Fund Security
- Automatic clawback before migration
- Dust threshold prevents gaming
- Migration blocked if clawback fails

## Common Integration Patterns

### Complete Wallet Migration
```python
# 1. Create new wallet
new_wallet = create_user_wallet(owner)

# 2. Migrate everything
num_assets, config_cloned = migrator.migrateAll(
    old_wallet.address,
    new_wallet.address,
    sender=owner
)

# 3. Verify migration
assert num_assets > 0 or config_cloned
print(f"Migration complete: {num_assets} assets, config: {config_cloned}")
```

### Selective Migration
```python
# Just migrate funds
if migrator.canMigrateFundsToNewWallet(source, target, owner):
    num = migrator.migrateFunds(source, target, sender=owner)

# Just copy configuration
if migrator.canCopyWalletConfig(template, new_wallet, owner):
    success = migrator.cloneConfig(template, new_wallet, sender=owner)
```

### Pre-Migration Validation
```python
# Check migration eligibility
source_bundle = migrator.getMigrationConfigBundle(source)
target_bundle = migrator.getMigrationConfigBundle(target)

# Verify requirements
assert source_bundle.owner == target_bundle.owner
assert source_bundle.groupId == target_bundle.groupId
assert not source_bundle.isFrozen
assert not target_bundle.isFrozen
assert target_bundle.numPayees <= 1
assert target_bundle.numWhitelisted <= 1

# Proceed with migration
migrator.migrateAll(source, target, sender=owner)
```

### Handling Migration Failures
```python
try:
    # Attempt migration
    num, cloned = migrator.migrateAll(old, new, sender=owner)
except Exception as e:
    if "trial funds" in str(e):
        print("Trial funds need manual handling")
    elif "no assets" in str(e):
        print("Source wallet has no assets to migrate")
    elif "invalid migration" in str(e):
        print("Wallets don't meet migration requirements")
```

## Testing

For comprehensive test examples, see: [`tests/core/walletBackpack/migrator/`](../../../tests/core/walletBackpack/migrator/)