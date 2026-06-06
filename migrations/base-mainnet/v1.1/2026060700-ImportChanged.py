from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # OPTIONAL / FULL-RELEASE-SET ONLY.
    #
    # These contracts have no direct source diff in PR #67, but their runtime
    # bytecode changed via edits to imported modules (Ownership / Addys). They are
    # included so an "all changed bytecode" release does not silently omit them.
    #
    # Run paths (this file is intentionally numbered AFTER 2026060699-FinishSetup
    # so it can be cleanly skipped without skipping backpack wiring):
    #   - Full release set : `-t 2026060600 -e 2026060700` (bounding the end at
    #                        this timestamp avoids picking up any later-dated
    #                        scripts that land before execution).
    #   - Core-only        : stop after finish setup with `-e 2026060699`; the
    #                        new WalletBackpack is still fully wired and this file
    #                        is skipped.
    #
    # LootDistributor is also listed as a required registry dependency for the
    # instant-migration path (see docs/deploy-checklist.md Instant Migration
    # Runbook).
    #
    # SCOPE NOTE (EarnVaultAgent): this redeploys only the v1.1 manifest-tracked
    # EarnVaultAgent, which is the VAULT_AGENT_OWNER-owned manager
    # (0x8d6DD438B9748DCA269033A01B1581EE8ef21e3b). Base currently also runs a
    # second live EarnVaultAgent owned by UndyHq (0x6B014c7BE0fCA7801133Db96737378CCE85230a7),
    # which is NOT tracked in this manifest and is intentionally out of scope here.
    # If that manager must also reach the new module bytecode, deploy it
    # separately (constructor owner = UndyHq) under its own runbook.
    migration.log.h2("Import-Changed Contracts (full release set)")
    hq = migration.get_contract("UndyHq")

    migration.deploy(
        "LootDistributor",
        hq,
        migration.blueprint.TOKENS["RIPE"],
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )

    migration.deploy(
        "LevgVaultAgent",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["VAULT_AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
        migration.blueprint.TOKENS["GREEN"],
        migration.blueprint.TOKENS["SAVINGS_GREEN"],
    )

    migration.deploy(
        "EarnVaultAgent",
        hq,
        migration.blueprint.INTEGRATION_ADDYS["VAULT_AGENT_OWNER"],
        1,  # _groupId
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
