from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import deploy_and_register
from scripts.utils.robinhood_runtime import (
    require_approved_robinhood_runtime,
    require_authenticated_robinhood_hq,
)

LEDGER_RUNTIME_CODEHASH = (
    "0xfa69a1f60d5dcf86d4780aa64ca6fe4232f1fa99604eb85393f9f2e183b99451"
)


def _validate_ledger(ledger, hq):
    if str(ledger.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError("Robinhood Ledger is bound to the wrong UndyHq")
    if ledger.numUserWallets() != 1:
        raise RuntimeError("Robinhood Ledger is not in its initial state")
    if ledger.isPaused() or ledger.canMintUndy():
        raise RuntimeError("Robinhood Ledger has unexpected department flags")


def migrate(migration: Migration):
    migration.log.h2("Ledger")
    hq = require_authenticated_robinhood_hq(migration)
    args = (hq,)
    migration.preflight_contract_manifest("Ledger", args)
    expected_runtime = require_approved_robinhood_runtime(
        migration,
        "Ledger",
        args,
        LEDGER_RUNTIME_CODEHASH,
    )
    deploy_and_register(
        migration,
        hq,
        name="Ledger",
        args=args,
        description="Ledger",
        expected_id=1,
        expected_prefix=(),
        context="before Robinhood Ledger deployment",
        validate=lambda ledger: _validate_ledger(ledger, hq),
        expected_runtime_codehash=LEDGER_RUNTIME_CODEHASH,
        expected_runtime=expected_runtime,
    )
