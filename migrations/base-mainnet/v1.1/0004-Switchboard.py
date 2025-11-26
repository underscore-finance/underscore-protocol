from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Switchboard")
    hq = migration.get_contract("UndyHq")

    switchboard = migration.deploy(
        'Switchboard',
        hq,
        migration.account,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )

    switchboard_alpha = migration.deploy(
        'SwitchboardAlpha',
        hq,
        migration.account,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    assert migration.execute(switchboard.startAddNewAddressToRegistry, switchboard_alpha, "SwitchboardAlpha")
    assert migration.execute(switchboard.confirmNewAddressToRegistry, switchboard_alpha) == 1

    switchboard_bravo = migration.deploy(
        'SwitchboardBravo',
        hq,
        migration.account,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    assert migration.execute(switchboard.startAddNewAddressToRegistry, switchboard_bravo, "SwitchboardBravo")
    assert migration.execute(switchboard.confirmNewAddressToRegistry, switchboard_bravo) == 2

    switchboard_charlie = migration.deploy(
        'SwitchboardCharlie',
        hq,
        migration.account,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    assert migration.execute(switchboard.startAddNewAddressToRegistry, switchboard_charlie, "SwitchboardCharlie")
    assert migration.execute(switchboard.confirmNewAddressToRegistry, switchboard_charlie) == 3
