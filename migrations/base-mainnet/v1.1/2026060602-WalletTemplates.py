from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # UserWallet and UserWalletConfig both changed (UserWalletConfig now captures
    # the ActionDataProvider as an immutable + carries instant-action settings).
    # Deployed as blueprints; the constructor does not run here. Governance cuts
    # them over via SwitchboardAlpha.setUserWalletTemplates.
    migration.log.h2("Wallet Templates")
    migration.deploy_bp("UserWallet")
    migration.deploy_bp("UserWalletConfig")
