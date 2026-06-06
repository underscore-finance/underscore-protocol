from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # New read-only helper for wallet action data. Must be deployed before the
    # WalletBackpack/UserWalletConfig cutover: the new UserWalletConfig template
    # captures the provider as an immutable, and the new WalletBackpack stores it
    # as the canonical provider address.
    migration.log.h2("Action Data Provider")
    migration.deploy("ActionDataProvider")
