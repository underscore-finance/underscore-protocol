from scripts.utils.migration import Migration


def migrate(migration: Migration):
    hq = migration.get_contract("UndyHq")
    migration.deploy(
        "AgentWrapper",
        hq,
        1,
        [
            migration.get_address("AgentSenderGeneric"),
            migration.get_address("AgentSenderSpecial"),
        ],
        label="AgentWrapper2",
    )
