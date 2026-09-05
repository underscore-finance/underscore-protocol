from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import deploy_and_register
from scripts.utils.robinhood_empty_registry import (
    empty_registry_constructor_args,
    validate_empty_robinhood_registry,
)
from scripts.utils.robinhood_runtime import (
    require_approved_robinhood_runtime,
    require_authenticated_robinhood_hq,
)


VAULT_REGISTRY_RUNTIME_CODEHASH = (
    "0x2fb78e063e05e53ac6472539c6b5a7df532eab4e57308cdb8bdb4abf16598408"
)


def _validate_vault_registry(vault_registry, hq, migration):
    validate_empty_robinhood_registry(
        vault_registry,
        hq,
        migration,
        name="VaultRegistry",
        registry_description="VaultRegistry.vy",
    )
    if vault_registry.isBasicEarnVault(migration.account.address) is not False:
        raise RuntimeError(
            "Robinhood empty VaultRegistry classifies the probe as an earn vault"
        )


def migrate(migration: Migration):
    migration.log.h2("Vault Registry")
    hq = require_authenticated_robinhood_hq(migration)
    args = empty_registry_constructor_args(migration, hq)
    migration.preflight_contract_manifest("VaultRegistry", args)
    expected_runtime = require_approved_robinhood_runtime(
        migration,
        "VaultRegistry",
        args,
        VAULT_REGISTRY_RUNTIME_CODEHASH,
    )
    names = (
        "Ledger",
        "MissionControl",
        "LegoBook",
        "Switchboard",
        "Hatchery",
        "LootDistributor",
        "Appraiser",
        "WalletBackpack",
        "Billing",
    )
    deploy_and_register(
        migration,
        hq,
        name="VaultRegistry",
        args=args,
        description="Vault Registry",
        expected_id=10,
        expected_prefix=tuple(
            (name, migration.get_address(name)) for name in names
        ),
        context="before Robinhood VaultRegistry deployment",
        validate=lambda registry: _validate_vault_registry(
            registry, hq, migration
        ),
        expected_runtime_codehash=VAULT_REGISTRY_RUNTIME_CODEHASH,
        expected_runtime=expected_runtime,
    )
