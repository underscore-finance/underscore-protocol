from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Ledger")
    hq = migration.get_contract("UndyHq")

    ledger = migration.deploy(
        'Ledger',
        hq,
    )

    assert migration.execute(hq.startAddNewAddressToRegistry, ledger, "Ledger")
    assert migration.execute(hq.confirmNewAddressToRegistry, ledger) == 1
