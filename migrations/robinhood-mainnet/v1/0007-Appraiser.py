from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import deploy_and_register
from scripts.utils.ripe_preconditions import require_robinhood_ripe_dependencies
from scripts.utils.robinhood_runtime import (
    require_approved_robinhood_runtime,
    require_authenticated_robinhood_hq,
)


APPRAISER_RUNTIME_CODEHASH = (
    "0x3c445ff13419f479897ac584b1c48e89c67650304b4cfae9c6c2b10d718399cf"
)


def _validate_appraiser(appraiser, hq):
    if str(appraiser.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError("Robinhood Appraiser is bound to the wrong UndyHq")
    if appraiser.isPaused() is not False or appraiser.canMintUndy() is not False:
        raise RuntimeError("Robinhood Appraiser has unexpected department state")


def migrate(migration: Migration):
    migration.log.h2("Appraiser")
    hq = require_authenticated_robinhood_hq(migration)
    ripe_registry, _ripe_token, _price_desk, _teller = (
        require_robinhood_ripe_dependencies(migration)
    )
    args = (hq, ripe_registry)
    migration.preflight_contract_manifest("Appraiser", args)
    expected_runtime = require_approved_robinhood_runtime(
        migration,
        "Appraiser",
        args,
        APPRAISER_RUNTIME_CODEHASH,
    )
    names = (
        "Ledger",
        "MissionControl",
        "LegoBook",
        "Switchboard",
        "Hatchery",
        "LootDistributor",
    )
    deploy_and_register(
        migration,
        hq,
        name="Appraiser",
        args=args,
        description="Appraiser",
        expected_id=7,
        expected_prefix=tuple(
            (name, migration.get_address(name)) for name in names
        ),
        context="before Robinhood Appraiser deployment",
        validate=lambda appraiser: _validate_appraiser(appraiser, hq),
        expected_runtime_codehash=APPRAISER_RUNTIME_CODEHASH,
        expected_runtime=expected_runtime,
    )
