from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Switchboard")
    hq = migration.get_contract("UndyHq")

    switchboard = migration.deploy(
        'Switchboard',
        hq,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )

    assert migration.execute(hq.startAddNewAddressToRegistry, switchboard, "Switchboard")
    assert migration.execute(hq.confirmNewAddressToRegistry, switchboard) == 4

    switchboard_alpha = migration.deploy(
        'SwitchboardAlpha',
        hq,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    assert migration.execute(switchboard.startAddNewAddressToRegistry, switchboard_alpha, "SwitchboardAlpha")
    assert migration.execute(switchboard.confirmNewAddressToRegistry, switchboard_alpha) == 1

    switchboard_bravo = migration.deploy(
        'SwitchboardBravo',
        hq,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    assert migration.execute(switchboard.startAddNewAddressToRegistry, switchboard_bravo, "SwitchboardBravo")
    assert migration.execute(switchboard.confirmNewAddressToRegistry, switchboard_bravo) == 2
