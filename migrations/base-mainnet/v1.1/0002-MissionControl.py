from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Mission Control")
    hq = migration.get_contract("UndyHq")

    migration.deploy(
        'MissionControl',
        hq,
        migration.get_address("DefaultsBase"),
    )
