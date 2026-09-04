import boa

from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import deploy_and_register
from scripts.utils.ripe_preconditions import require_robinhood_ripe_dependencies
from scripts.utils.robinhood_runtime import require_approved_robinhood_runtime


LOOT_DISTRIBUTOR_RUNTIME_CODEHASH = (
    "0x8a240d7c2037eda1b695a327c1a73c529ad415aa0721b32b4e576999a9db1d10"
)


def _validate_loot_distributor(loot_distributor, hq, ripe_token, ripe_registry):
    if str(loot_distributor.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError("Robinhood LootDistributor is bound to the wrong UndyHq")
    if str(loot_distributor.RIPE_TOKEN()).lower() != ripe_token.lower():
        raise RuntimeError("Robinhood LootDistributor has the wrong RIPE token")
    if str(loot_distributor.RIPE_REGISTRY()).lower() != ripe_registry.lower():
        raise RuntimeError("Robinhood LootDistributor has the wrong RIPE registry")
    if loot_distributor.isPaused() is not False:
        raise RuntimeError("Robinhood LootDistributor is unexpectedly paused")


def migrate(migration: Migration):
    migration.log.h2("Loot Distributor")
    hq = migration.get_contract("UndyHq")
    ripe_registry, ripe_token, _price_desk, _teller = (
        require_robinhood_ripe_dependencies(migration)
    )
    args = (
        hq,
        ripe_token,
        ripe_registry,
    )
    require_approved_robinhood_runtime(
        migration,
        "LootDistributor",
        args,
        LOOT_DISTRIBUTOR_RUNTIME_CODEHASH,
    )
    names = ("Ledger", "MissionControl", "LegoBook", "Switchboard", "Hatchery")
    deploy_and_register(
        migration,
        hq,
        name="LootDistributor",
        args=args,
        description="Loot Distributor",
        expected_id=6,
        expected_prefix=tuple(
            (name, migration.get_address(name)) for name in names
        ),
        context="before Robinhood LootDistributor deployment",
        validate=lambda loot_distributor: _validate_loot_distributor(
            loot_distributor,
            hq,
            ripe_token,
            ripe_registry,
        ),
        expected_runtime_codehash=LOOT_DISTRIBUTOR_RUNTIME_CODEHASH,
    )
