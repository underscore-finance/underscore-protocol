from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import (
    deploy_and_register,
    install_hq_materialization_dependency,
    materialize_contract_runtime,
)

LEGO_BOOK_RUNTIME_CODEHASH = (
    "0xf96e13b169b48b095f4993b37207e4d6f8d4a59d861655cd8e6ca865bd18a3b4"
)


def _validate_lego_book(lego_book, hq, migration):
    if str(lego_book.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError("Robinhood LegoBook is bound to the wrong UndyHq")
    if str(lego_book.governance()) != migration.blueprint.CONSTANTS.ZERO_ADDRESS:
        raise RuntimeError("Robinhood LegoBook has unexpected local governance")
    if lego_book.getRegistryDescription() != "LegoBook.vy":
        raise RuntimeError("Robinhood LegoBook has an unexpected registry identity")
    if lego_book.numAddrs() != 1:
        raise RuntimeError("Robinhood LegoBook is not empty")
    if lego_book.registryChangeTimeLock() != 0:
        raise RuntimeError("Robinhood LegoBook registry timelock is already active")
    if (
        lego_book.govChangeTimeLock() != hq.minGovChangeTimeLock()
        or lego_book.numGovChanges() != 0
        or lego_book.hasPendingGovChange()
    ):
        raise RuntimeError("Robinhood LegoBook has unexpected governance state")
    if lego_book.isPaused() or lego_book.canMintUndy():
        raise RuntimeError("Robinhood LegoBook has unexpected department flags")
    if (
        lego_book.minRegistryTimeLock()
        != migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"]
        or lego_book.maxRegistryTimeLock()
        != migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"]
    ):
        raise RuntimeError("Robinhood LegoBook has unexpected registry timelocks")


def migrate(migration: Migration):
    migration.log.h2("Lego Book")
    hq = migration.get_contract("UndyHq")
    args = (
        hq,
        # HQ governance can govern LocalGov children directly. A matching
        # local governor is forbidden by LocalGov.__init__.
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )
    deploy_and_register(
        migration,
        hq,
        name="LegoBook",
        args=args,
        description="Lego Book",
        expected_id=3,
        expected_prefix=(
            ("Ledger", migration.get_address("Ledger")),
            ("MissionControl", migration.get_address("MissionControl")),
        ),
        context="before Robinhood LegoBook deployment",
        validate=lambda lego_book: _validate_lego_book(
            lego_book,
            hq,
            migration,
        ),
        expected_runtime_codehash=LEGO_BOOK_RUNTIME_CODEHASH,
        runtime_builder=lambda: materialize_contract_runtime(
            migration,
            "LegoBook",
            args,
            prepare=lambda: install_hq_materialization_dependency(
                hq,
                migration,
            ),
        ),
    )

    # Robinhood launches without protocol integrations. The registry is a core
    # dependency, but Lego implementations and LegoTools are deliberately not
    # deployed until their chain-specific addresses have been approved.
