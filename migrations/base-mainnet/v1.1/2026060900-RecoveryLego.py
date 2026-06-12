from scripts.utils.migration import Migration


def migrate(migration: Migration):

    hq = migration.get_address("UndyHq")
    recovery_lego = migration.deploy("RecoveryLego", hq)

    print(f"Deployed RecoveryLego at {recovery_lego.address}")
