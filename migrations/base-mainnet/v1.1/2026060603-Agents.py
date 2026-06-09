from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # Agent stack redeploy. AgentSenderSpecialAdmin is new (privileged sender:
    # see the Agent Sender Production Gate in docs/deploy-checklist.md). Senders
    # and the wrapper are registered into production via SwitchboardAlpha.
    migration.log.h2("Agent Contracts")
    hq = migration.get_contract("UndyHq")

    # DEV AGENT WRAPPER
    as_generic_dev = migration.deploy(
        "AgentSenderGeneric",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER_DEV"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
        label="AgentSenderGenericDev"
    )

    as_special_dev = migration.deploy(
        "AgentSenderSpecial",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER_DEV"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
        migration.blueprint.TOKENS["GREEN"],
        migration.blueprint.TOKENS["SAVINGS_GREEN"],
        label="AgentSenderSpecialDev"
    )

    as_admin_dev = migration.deploy(
        "AgentSenderSpecialAdmin",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER_DEV"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
        label="AgentSenderSpecialAdminDev"
    )

    migration.deploy(
        "AgentWrapper", hq, 1, [as_generic_dev.address, as_special_dev.address, as_admin_dev.address], label="AgentWrapperDev")

    # PROD AGENT WRAPPER
    as_generic = migration.deploy(
        "AgentSenderGeneric",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
    )

    as_special = migration.deploy(
        "AgentSenderSpecial",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
        migration.blueprint.TOKENS["GREEN"],
        migration.blueprint.TOKENS["SAVINGS_GREEN"],
    )

    as_admin = migration.deploy(
        "AgentSenderSpecialAdmin",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
    )

    migration.deploy(
        "AgentWrapper", hq, 1, [as_generic.address, as_special.address, as_admin.address])

    migration.deploy("AgentSenderSpecialSigHelper")
    migration.deploy("UserWalletSignatureHelper")
