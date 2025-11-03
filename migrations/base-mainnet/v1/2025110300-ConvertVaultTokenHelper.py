from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.deploy(
        'ConvertVaultToken',
    )
