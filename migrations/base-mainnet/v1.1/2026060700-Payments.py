from scripts.utils.migration import Migration


def migrate(migration: Migration):
    # x402 + MPP payments stack. Governance registers VendorRegistry/PayProcessor
    # into UndyHq ids 12/13 and SwitchboardDelta into the Switchboard registry
    # separately; this migration only deploys and bootstraps immutable genesis args.
    migration.log.h2("Payments - x402 + MPP")
    hq = migration.get_contract("UndyHq")

    usdc = migration.blueprint.TOKENS["USDC"]
    initial_bridge = migration.blueprint.INTEGRATION_ADDYS.get(
        "PAYMENTS_BRIDGE",
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
    )

    vendor_template = migration.deploy_bp("VendorProxy")
    migration.deploy("VendorRegistry", hq, vendor_template)

    agent_sender_pay = migration.deploy(
        "AgentSenderPay",
        hq,
        usdc,
        migration.blueprint.INTEGRATION_ADDYS["AGENT_OWNER"],
        migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
    )

    migration.deploy(
        "PayProcessor",
        hq,
        usdc,
        initial_bridge,
        agent_sender_pay,
    )

    switchboard_delta = migration.deploy(
        "SwitchboardDelta",
        hq,
        migration.account,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    migration.execute(switchboard_delta.relinquishGov)
