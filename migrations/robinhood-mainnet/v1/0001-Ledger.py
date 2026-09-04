from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import (
    deploy_and_register,
    materialize_contract_runtime,
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
    hq = migration.get_contract("UndyHq")
    deploy_and_register(
        migration,
        hq,
        name="Ledger",
        args=(hq,),
        description="Ledger",
        expected_id=1,
        expected_prefix=(),
        context="before Robinhood Ledger deployment",
        validate=lambda ledger: _validate_ledger(ledger, hq),
        expected_runtime_codehash=LEDGER_RUNTIME_CODEHASH,
        runtime_builder=lambda: materialize_contract_runtime(
            migration,
            "Ledger",
            (hq,),
        ),
    )
