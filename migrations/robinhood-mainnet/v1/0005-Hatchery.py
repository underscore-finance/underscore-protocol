import boa
from eth_utils import keccak

from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import deploy_and_register
from scripts.utils.robinhood_runtime import require_approved_robinhood_runtime


PRE_HATCHERY_REGISTRY = (
    (1, "Ledger"),
    (2, "MissionControl"),
    (3, "LegoBook"),
    (4, "Switchboard"),
)

HATCHERY_RUNTIME_CODEHASH = (
    "0x7f8baab1a9c140c28c4159ab33d3a6a98adcc1b0b7c1adf19a22d62716a2cbec"
)


def _require_wallet_factory(migration: Migration, hq) -> str:
    factory_address = migration.blueprint.INTEGRATION_ADDYS.get("WALLET_FACTORY")
    approved_codehash = migration.blueprint.INTEGRATION_ADDYS.get(
        "WALLET_FACTORY_CODEHASH"
    )
    zero_address = migration.blueprint.CONSTANTS.ZERO_ADDRESS
    zero_hash = "0x" + "00" * 32

    if not factory_address or factory_address.lower() == zero_address.lower():
        raise RuntimeError(
            "Robinhood WALLET_FACTORY is not approved; refusing to deploy Hatchery"
        )
    if not approved_codehash or approved_codehash.lower() == zero_hash:
        raise RuntimeError(
            "Robinhood WALLET_FACTORY_CODEHASH is not approved; "
            "refusing to deploy Hatchery"
        )

    factory_code = boa.env.get_code(factory_address)
    if not factory_code:
        raise RuntimeError(
            "Robinhood WALLET_FACTORY has no code; refusing to deploy Hatchery"
        )
    live_factory_codehash = "0x" + keccak(factory_code).hex()
    if live_factory_codehash.lower() != approved_codehash.lower():
        raise RuntimeError(
            "Robinhood WALLET_FACTORY live codehash does not match its approval"
        )

    try:
        factory = boa.load_abi(
            "scripts/abis/UserWalletFactory.json",
            name="UserWalletFactoryPreflight",
        ).at(factory_address)
        factory_hq = factory.undyHq()
        factory_admin = factory.WALLET_FACTORY_ADMIN()
        implementations = (
            (
                "UserWallet",
                factory.USER_WALLET_IMPLEMENTATION(),
                factory.USER_WALLET_IMPLEMENTATION_CODEHASH(),
            ),
            (
                "UserWalletConfig",
                factory.USER_WALLET_CONFIG_IMPLEMENTATION(),
                factory.USER_WALLET_CONFIG_IMPLEMENTATION_CODEHASH(),
            ),
        )
    except Exception as exc:
        raise RuntimeError(
            "Robinhood WALLET_FACTORY does not expose the required trust-root getters"
        ) from exc

    if str(factory_hq).lower() != str(hq.address).lower():
        raise RuntimeError(
            "Robinhood WALLET_FACTORY is initialized for a different UndyHq"
        )
    if str(factory_admin).lower() == zero_address.lower():
        raise RuntimeError(
            "Robinhood WALLET_FACTORY still has the zero-address admin placeholder"
        )

    for label, implementation, expected_codehash in implementations:
        implementation_address = str(implementation)
        if implementation_address.lower() == zero_address.lower():
            raise RuntimeError(f"{label} implementation address is zero")
        implementation_code = boa.env.get_code(implementation_address)
        if not implementation_code:
            raise RuntimeError(f"{label} implementation has no code")

        live_codehash = "0x" + keccak(implementation_code).hex()
        if isinstance(expected_codehash, bytes):
            expected_codehash_hex = "0x" + expected_codehash.hex()
        else:
            expected_codehash_hex = str(expected_codehash)
        if live_codehash.lower() != expected_codehash_hex.lower():
            raise RuntimeError(
                f"{label} implementation codehash does not match the factory trust root"
            )
    return factory_address


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


def _validate_hatchery(hatchery, hq, weth, eth, wallet_factory, zero_address):
    if str(hatchery.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError("Robinhood Hatchery is bound to the wrong UndyHq")
    expected_addresses = (
        ("WETH", hatchery.WETH(), weth),
        ("ETH", hatchery.ETH(), eth),
        ("wallet factory", hatchery.WALLET_FACTORY(), wallet_factory),
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
    hq = migration.get_contract("UndyHq")

    # This profile entry intentionally remains absent until the deterministic
    # factory sources, admin and release artifacts are frozen. Keep every check
    # above the first transaction so an incomplete profile cannot consume HQ ID 5.
    wallet_factory = _require_wallet_factory(migration, hq)
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
        wallet_factory,
    )
    require_approved_robinhood_runtime(
        migration,
        "Hatchery",
        args,
        HATCHERY_RUNTIME_CODEHASH,
        wallet_factory_address=wallet_factory,
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
            wallet_factory,
            zero_address,
        ),
        expected_runtime_codehash=HATCHERY_RUNTIME_CODEHASH,
    )
