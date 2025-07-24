from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Mission Control")
    hq = migration.get_contract("UndyHq")

    mission_control = migration.deploy(
        'MissionControl',
        hq,
        migration.get_address("DefaultsBase"),
    )

    assert migration.execute(hq.startAddNewAddressToRegistry, mission_control, "Mission Control")
    assert migration.execute(hq.confirmNewAddressToRegistry, mission_control) == 2
