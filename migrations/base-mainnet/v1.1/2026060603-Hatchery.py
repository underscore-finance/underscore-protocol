from scripts.utils.migration import Migration
from tests.constants import ZERO_ADDRESS


def migrate(migration: Migration):
    # New Hatchery constructor adds default instant-action settings, staging/dev
    # starter-agent configs, and a non-prod creator. Production cutover values:
    #   - defaultInstantActionSettings = all true (instant V1 cutover)
    #   - staging/dev starter-agent configs = empty (no non-prod starter agent)
    #   - nonProdCreator = empty (no non-prod creation lane)
    # If nonProdCreator is ever set nonzero, it must NOT also be in
    # MissionControl.creatorWhitelist (see docs/deploy-checklist.md).
    migration.log.h2("Hatchery")
    hq = migration.get_contract("UndyHq")

    migration.deploy(
        "Hatchery",
        hq,
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.TOKENS["ETH"],
        (True, True, True, True),  # _defaultInstantActionSettings
        (ZERO_ADDRESS, 0),         # _stagingStarterAgentConfig
        (ZERO_ADDRESS, 0),         # _devStarterAgentConfig
        ZERO_ADDRESS,              # _nonProdCreator
    )
