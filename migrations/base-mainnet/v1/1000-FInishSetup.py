from scripts.utils.migration import Migration


def migrate(migration: Migration):
    migration.log.h2("Billing")
    hq = migration.get_contract("UndyHq")

    # Deploy an agent contract
    hatchery = migration.get_contract("Hatchery")
    agent = migration.execute(hatchery.createAgent, migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"], 1)

    switchboard_alpha = migration.get_contract("SwitchboardAlpha")

    actionId = migration.execute(switchboard_alpha.setStarterAgentParams, agent, migration.blueprint.BLOCKS.YEAR * 2)
    migration.execute(switchboard_alpha.executePendingAction, actionId)

    actionId = migration.execute(switchboard_alpha.setAgentCreationLimits, 25, True)
    migration.execute(switchboard_alpha.executePendingAction, actionId)

    migration.execute(switchboard_alpha.setActionTimeLockAfterSetup)

    switchboard_bravo = migration.get_contract("SwitchboardBravo")
    migration.execute(switchboard_bravo.setActionTimeLockAfterSetup)

    wallet_backpack = migration.get_contract("WalletBackpack")
    migration.execute(wallet_backpack.setActionTimeLockAfterSetup)

    switchboard = migration.get_contract("Switchboard")
    migration.execute(switchboard.setRegistryTimeLockAfterSetup)

    lego_book = migration.get_contract("LegoBook")
    migration.execute(lego_book.setRegistryTimeLockAfterSetup)

    # switchboard can set token blacklists
    migration.execute(hq.initiateHqConfigChange, 4, False, True)
    migration.execute(hq.confirmHqConfigChange, 4)

    # finish undy hq setup
    migration.execute(hq.setRegistryTimeLockAfterSetup)
    migration.execute(hq.finishUndyHqSetup, migration.blueprint.INTEGRATION_ADDYS["GOVERNANCE"])
