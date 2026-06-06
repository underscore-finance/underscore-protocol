from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # Agent stack redeploy. AgentSenderSpecialAdmin is new (privileged sender:
    # see the Agent Sender Production Gate in docs/deploy-checklist.md). Senders
    # and the wrapper are registered into production via SwitchboardAlpha.
    migration.log.h2("Agent Contracts")
    hq = migration.get_contract("UndyHq")

    migration.deploy("AgentWrapper", hq, 1)

    migration.deploy(
        "AgentSenderGeneric",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
    )

    migration.deploy(
        "AgentSenderSpecial",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
        migration.blueprint.TOKENS["GREEN"],
        migration.blueprint.TOKENS["SAVINGS_GREEN"],
    )

    migration.deploy(
        "AgentSenderSpecialAdmin",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
    )

    migration.deploy("AgentSenderSpecialSigHelper")
    migration.deploy("UserWalletSignatureHelper")
