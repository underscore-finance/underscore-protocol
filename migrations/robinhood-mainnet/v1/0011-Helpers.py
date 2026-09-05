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


HELPERS_RUNTIME_CODEHASH = (
    "0xa3b2eab0b95464e263a78b8977a8bbbf97342136406d9c87e454673c84db46ca"
)


def _validate_helpers(helpers, hq, migration):
    validate_empty_robinhood_registry(
        helpers,
        hq,
        migration,
        name="Helpers",
        registry_description="Helpers.vy",
    )
    if helpers.isHelpersAddr(migration.account.address) is not False:
        raise RuntimeError(
            "Robinhood empty Helpers registry classifies the probe as registered"
        )


def migrate(migration: Migration):
    migration.log.h2("Helpers")
    hq = require_authenticated_robinhood_hq(migration)
    args = empty_registry_constructor_args(migration, hq)
    migration.preflight_contract_manifest("Helpers", args)
    expected_runtime = require_approved_robinhood_runtime(
        migration,
        "Helpers",
        args,
        HELPERS_RUNTIME_CODEHASH,
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
        "VaultRegistry",
    )
    deploy_and_register(
        migration,
        hq,
        name="Helpers",
        args=args,
        description="Helpers",
        expected_id=11,
        expected_prefix=tuple(
            (name, migration.get_address(name)) for name in names
        ),
        context="before Robinhood Helpers deployment",
        validate=lambda registry: _validate_helpers(registry, hq, migration),
        expected_runtime_codehash=HELPERS_RUNTIME_CODEHASH,
        expected_runtime=expected_runtime,
    )
