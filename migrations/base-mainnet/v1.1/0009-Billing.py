from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Billing")
    hq = migration.get_contract("UndyHq")

    migration.deploy(
        'Billing',
        hq,
    )
