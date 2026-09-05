from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import deploy_and_register
from scripts.utils.robinhood_runtime import (
    require_approved_robinhood_runtime,
    require_authenticated_robinhood_hq,
)


BILLING_RUNTIME_CODEHASH = (
    "0x6d7538e85fec61d0febc772951150cd33ea2d7e33a354833245dc88d61a3b01a"
)


def _validate_billing(billing, hq):
    if str(billing.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError("Robinhood Billing is bound to the wrong UndyHq")
    if billing.isPaused() is not False or billing.canMintUndy() is not False:
        raise RuntimeError("Robinhood Billing has unexpected department state")


def migrate(migration: Migration):
    migration.log.h2("Billing")
    hq = require_authenticated_robinhood_hq(migration)
    args = (hq,)
    migration.preflight_contract_manifest("Billing", args)
    expected_runtime = require_approved_robinhood_runtime(
        migration,
        "Billing",
        args,
        BILLING_RUNTIME_CODEHASH,
    )
    names = (
        "Ledger",
        "MissionControl",
        "LegoBook",
        "Switchboard",
        "Hatchery",
        "LootDistributor",
        "Appraiser",
        "WalletBackpack",
    )
    deploy_and_register(
        migration,
        hq,
        name="Billing",
        args=args,
        description="Billing",
        expected_id=9,
        expected_prefix=tuple(
            (name, migration.get_address(name)) for name in names
        ),
        context="before Robinhood Billing deployment",
        validate=lambda billing: _validate_billing(billing, hq),
        expected_runtime_codehash=BILLING_RUNTIME_CODEHASH,
        expected_runtime=expected_runtime,
    )
