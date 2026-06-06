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

    dev_wrapper = migration.get_address('AgentWrapperDev')
    print(f"dev wrapper: {dev_wrapper}")
    migration.deploy(
        "Hatchery",
        hq,
        migration.blueprint.TOKENS["WETH"],
        migration.blueprint.TOKENS["ETH"],
        [True, True, True, True],  # _defaultInstantActionSettings
        [dev_wrapper, 1_138_320_000],  # _stagingStarterAgentConfig
        [dev_wrapper, 1_138_320_000],  # _devStarterAgentConfig
        '0xb9530631Ab15449aCBf3F7056bf1EBc2cF867452',   # _nonProdCreator
    )
