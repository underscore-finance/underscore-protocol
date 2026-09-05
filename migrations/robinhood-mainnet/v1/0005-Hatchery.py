import boa
from eth_utils import keccak

from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import deploy_and_register
from scripts.utils.robinhood_runtime import (
    require_approved_robinhood_runtime,
    require_authenticated_robinhood_hq,
)


PRE_HATCHERY_REGISTRY = (
    (1, "Ledger"),
    (2, "MissionControl"),
    (3, "LegoBook"),
    (4, "Switchboard"),
)

HATCHERY_RUNTIME_CODEHASH = (
    "0x799f6480949a278ca20adf22f072cc8d5117d206a25e7690ca9bf30db4f13f4d"
)


def _require_weth(migration: Migration) -> str:
    weth = migration.blueprint.TOKENS["WETH"]
    approved_codehash = migration.blueprint.INTEGRATION_ADDYS.get("WETH_CODEHASH")
    if not approved_codehash:
        raise RuntimeError(
            "Robinhood WETH_CODEHASH is not approved; refusing to deploy Hatchery"
        )
    runtime = boa.env.get_code(weth)
    if not runtime:
        raise RuntimeError("Robinhood WETH has no code; refusing to deploy Hatchery")
    live_codehash = "0x" + keccak(runtime).hex()
    if live_codehash.lower() != approved_codehash.lower():
        raise RuntimeError("Robinhood WETH live codehash does not match its approval")
    return weth


def _validate_hatchery(hatchery, hq, weth, eth, zero_address):
    if str(hatchery.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError("Robinhood Hatchery is bound to the wrong UndyHq")
    expected_addresses = (
        ("WETH", hatchery.WETH(), weth),
        ("ETH", hatchery.ETH(), eth),
        ("non-prod creator", hatchery.nonProdCreator(), zero_address),
    )
    for label, actual, expected in expected_addresses:
        if str(actual).lower() != str(expected).lower():
            raise RuntimeError(
                f"Robinhood Hatchery {label} is {actual}, expected {expected}"
            )
    if tuple(hatchery.defaultInstantActionSettings()) != (True, True, True, True):
        raise RuntimeError("Robinhood Hatchery has unexpected instant settings")
    if tuple(hatchery.stagingStarterAgentConfig()) != (zero_address, 0):
        raise RuntimeError("Robinhood Hatchery has unexpected staging agent config")
    if tuple(hatchery.devStarterAgentConfig()) != (zero_address, 0):
        raise RuntimeError("Robinhood Hatchery has unexpected dev agent config")
    if hatchery.isPaused() is not False or hatchery.canMintUndy() is not False:
        raise RuntimeError("Robinhood Hatchery has unexpected department state")


def migrate(migration: Migration):
    migration.log.h2("Hatchery")
    hq = require_authenticated_robinhood_hq(migration)
    zero_address = migration.blueprint.CONSTANTS.ZERO_ADDRESS
    weth = _require_weth(migration)

    eth = migration.blueprint.TOKENS["ETH"]
    args = (
        hq,
        weth,
        eth,
        [True, True, True, True],
        [zero_address, 0],
        [zero_address, 0],
        zero_address,
    )
    migration.preflight_contract_manifest("Hatchery", args)
    expected_runtime = require_approved_robinhood_runtime(
        migration,
        "Hatchery",
        args,
        HATCHERY_RUNTIME_CODEHASH,
    )
    deploy_and_register(
        migration,
        hq,
        name="Hatchery",
        args=args,
        description="Hatchery",
        expected_id=5,
        expected_prefix=tuple(
            (name, migration.get_address(name))
            for _reg_id, name in PRE_HATCHERY_REGISTRY
        ),
        context="before Robinhood Hatchery deployment",
        validate=lambda hatchery: _validate_hatchery(
            hatchery,
            hq,
            weth,
            eth,
            zero_address,
        ),
        expected_runtime_codehash=HATCHERY_RUNTIME_CODEHASH,
        expected_runtime=expected_runtime,
    )
