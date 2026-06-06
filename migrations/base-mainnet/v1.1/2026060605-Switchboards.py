from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # SwitchboardAlpha and SwitchboardBravo changed (instant-action governance
    # wrappers + Bravo instant-flag setters). SwitchboardCharlie is unchanged
    # bytecode (interface view->pure only) and is intentionally not redeployed.
    # Each new switchboard relinquishes deployer gov immediately, matching the
    # 2026050100-SwitchboardCharlie precedent; governance registers them into
    # the Switchboard registry and applies config separately.
    migration.log.h2("Switchboards")
    hq = migration.get_contract("UndyHq")

    switchboard_alpha = migration.deploy(
        "SwitchboardAlpha",
        hq,
        migration.account,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    migration.execute(switchboard_alpha.relinquishGov)

    switchboard_bravo = migration.deploy(
        "SwitchboardBravo",
        hq,
        migration.account,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    migration.execute(switchboard_bravo.relinquishGov)
