from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # Agent stack redeploy. AgentSenderSpecialAdmin is new (privileged sender:
    # see the Agent Sender Production Gate in docs/deploy-checklist.md). Senders
    # and the wrapper are registered into production via SwitchboardAlpha.
    migration.log.h2("Agent Contracts")
    hq = migration.get_contract("UndyHq")

    # PROD AGENT WRAPPER
    as_generic = migration.get_contract("AgentSenderGeneric")
    as_special = migration.get_contract("AgentSenderSpecial")
    as_admin = migration.get_address("AgentSenderSpecialAdmin")

    migration.deploy("AgentWrapper", hq, 1, [as_generic, as_special, as_admin], label="AgentWrapper1")
    migration.deploy("AgentWrapper", hq, 1, [as_generic, as_special, as_admin], label="AgentWrapper2")
    migration.deploy("AgentWrapper", hq, 1, [as_generic, as_special, as_admin], label="AgentWrapper3")
