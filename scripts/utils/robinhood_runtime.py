import boa
from boa.environment import Env
from eth_utils import keccak

from scripts.utils.nonce_alignment import get_account_nonces


ROBINHOOD_UNDY_HQ = "0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9"
ROBINHOOD_UNDY_HQ_DEPLOYER = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"
ROBINHOOD_USER_WALLET_BLUEPRINT = (
    "0xAfF6aE05285c543B1Bbb6298d023c613B07817CB"
)
ROBINHOOD_USER_WALLET_CONFIG_BLUEPRINT = (
    "0x5aB75ef37A30736f38F637a9129348AD327EfD08"
)
ROBINHOOD_DEFAULTS = "0x55eeA103abA26FA85fb1359E2D2e1961d1B46218"

# Release trust roots for the nonce-critical V1 bootstrap. These are checked
# against runtime independently materialized from the current source before a
# post-HQ migration is allowed to mutate the chain.
ROBINHOOD_UNDY_HQ_RUNTIME_CODEHASH = (
    "0x5a5acd3311a6ea69a0c6df4cd54c95918729f3a61cba01cc1b5cf48a584da88b"
)
ROBINHOOD_DEFAULTS_RUNTIME_CODEHASH = (
    "0xf0ce6b570eed1a0f2f429a54737a8a796d7299b286bfaa540b19c2dd70e78f24"
)

_RUNTIME_PROBE_ADDRESS = "0x000000000000000000000000000000000000dEaD"


def _address(value):
    return str(value.address if hasattr(value, "address") else value)


def _normalize_arg(value):
    if hasattr(value, "address"):
        return str(value.address)
    if isinstance(value, list):
        return [_normalize_arg(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_arg(item) for item in value)
    return value


def _runtime_codehash(runtime: bytes) -> str:
    return "0x" + keccak(runtime).hex()


def _undy_hq_args(migration):
    params = migration.blueprint.PARAMS
    return (
        ROBINHOOD_UNDY_HQ_DEPLOYER,
        params["UNDY_HQ_MIN_GOV_TIMELOCK"],
        params["UNDY_HQ_MAX_GOV_TIMELOCK"],
        params["UNDY_HQ_MIN_REG_TIMELOCK"],
        params["UNDY_HQ_MAX_REG_TIMELOCK"],
    )


def _install_defaults_dependency(files):
    # The constructor checks both immutable template addresses for code. Only
    # their code-existence is consulted; the fixed addresses and resulting
    # Defaults runtime are authenticated separately against the live bootstrap.
    boa.env.set_code(ROBINHOOD_USER_WALLET_BLUEPRINT, b"\x00")
    boa.env.set_code(ROBINHOOD_USER_WALLET_CONFIG_BLUEPRINT, b"\x00")
    boa.load_partial(files["DefaultsRobinhood"]).deploy(
        ROBINHOOD_USER_WALLET_BLUEPRINT,
        ROBINHOOD_USER_WALLET_CONFIG_BLUEPRINT,
        override_address=ROBINHOOD_DEFAULTS,
    )


def materialize_robinhood_runtime(
    migration,
    name: str,
    args,
    *,
    defaults_dependency=False,
):
    """Materialize constructor-specific runtime without touching live state.

    Every live address and constructor argument is normalized before entering
    the isolated environment. Boa contract objects read through the active
    environment, so consulting one after ``set_env`` would query the empty
    materialization state rather than Robinhood.
    """
    try:
        deployer = _address(migration.account)
        dependency_names = {"UndyHq", name}
        if defaults_dependency:
            dependency_names.add("DefaultsRobinhood")
        files = {
            contract_name: migration.get_contract_file(contract_name)
            for contract_name in dependency_names
        }
        hq_args = tuple(_normalize_arg(arg) for arg in _undy_hq_args(migration))
    except (AttributeError, KeyError, TypeError) as exc:
        raise RuntimeError(
            f"cannot materialize expected Robinhood {name} runtime"
        ) from exc

    normalized_args = tuple(_normalize_arg(arg) for arg in args)
    with boa.set_env(Env()) as compile_env:
        compile_env.eoa = deployer

        if name != "UndyHq":
            boa.load_partial(files["UndyHq"]).deploy(
                *hq_args,
                override_address=ROBINHOOD_UNDY_HQ,
            )

        if defaults_dependency:
            _install_defaults_dependency(files)

        target_address = (
            ROBINHOOD_UNDY_HQ if name == "UndyHq" else _RUNTIME_PROBE_ADDRESS
        )
        contract = boa.load_partial(files[name]).deploy(
            *normalized_args,
            override_address=target_address,
        )
        runtime = compile_env.get_code(contract.address)

    if not runtime:
        raise RuntimeError(f"materialized Robinhood {name} runtime is empty")
    return runtime


def require_approved_robinhood_runtime(
    migration,
    name: str,
    args,
    approved_codehash: str,
    *,
    defaults_dependency=False,
):
    """Return exact current-source runtime or fail before any broadcast."""
    runtime = materialize_robinhood_runtime(
        migration,
        name,
        args,
        defaults_dependency=defaults_dependency,
    )
    actual_hash = _runtime_codehash(runtime)
    if actual_hash.lower() != approved_codehash.lower():
        raise RuntimeError(
            f"Robinhood {name} source runtime codehash is {actual_hash}, "
            f"expected approved hash {approved_codehash}"
        )
    return runtime


def _require_bootstrap_manifest_entry(
    migration,
    name: str,
    expected_address: str,
    expected_codehash: str,
):
    entry = migration.get_manifest_entry(name)
    if entry is None:
        raise RuntimeError(f"Robinhood bootstrap manifest is missing {name}")
    if str(entry.get("address", "")).lower() != expected_address.lower():
        raise RuntimeError(
            f"Robinhood bootstrap manifest points {name} at "
            f"{entry.get('address')}, expected {expected_address}"
        )
    if str(entry.get("runtime_codehash", "")).lower() != expected_codehash.lower():
        raise RuntimeError(
            f"Robinhood bootstrap manifest has an unapproved {name} runtime hash"
        )


def _require_exact_live_runtime(
    name: str,
    address: str,
    expected_runtime: bytes,
    expected_codehash: str,
):
    live_runtime = boa.env.get_code(address)
    if live_runtime != expected_runtime:
        raise RuntimeError(
            f"Robinhood {name} runtime at {address} does not match the "
            "approved current-source artifact"
        )
    live_hash = _runtime_codehash(live_runtime)
    if live_hash.lower() != expected_codehash.lower():
        raise RuntimeError(
            f"Robinhood {name} live runtime codehash is {live_hash}, expected "
            f"{expected_codehash}"
        )


def require_authenticated_robinhood_hq(migration):
    """Load the fixed RH UndyHq trust root after code and state authentication."""
    if _address(migration.account).lower() != ROBINHOOD_UNDY_HQ_DEPLOYER.lower():
        raise RuntimeError(
            "Robinhood post-HQ migrations require the original UndyHq governor "
            f"{ROBINHOOD_UNDY_HQ_DEPLOYER}"
        )

    args = _undy_hq_args(migration)
    expected_runtime = require_approved_robinhood_runtime(
        migration,
        "UndyHq",
        args,
        ROBINHOOD_UNDY_HQ_RUNTIME_CODEHASH,
    )
    _require_bootstrap_manifest_entry(
        migration,
        "UndyHq",
        ROBINHOOD_UNDY_HQ,
        ROBINHOOD_UNDY_HQ_RUNTIME_CODEHASH,
    )
    _require_exact_live_runtime(
        "UndyHq",
        ROBINHOOD_UNDY_HQ,
        expected_runtime,
        ROBINHOOD_UNDY_HQ_RUNTIME_CODEHASH,
    )

    latest_nonce, pending_nonce = get_account_nonces(ROBINHOOD_UNDY_HQ)
    if latest_nonce != 1 or pending_nonce != 1:
        raise RuntimeError(
            "Robinhood UndyHq contract nonce is not the authenticated initial "
            f"value: latest {latest_nonce}, pending {pending_nonce}"
        )

    hq = boa.load_partial(migration.get_contract_file("UndyHq")).at(
        ROBINHOOD_UNDY_HQ
    )
    params = migration.blueprint.PARAMS
    checks = (
        (
            _address(hq.governance()).lower(),
            ROBINHOOD_UNDY_HQ_DEPLOYER.lower(),
            "governance",
        ),
        (hq.numGovChanges(), 0, "numGovChanges"),
        (hq.govChangeTimeLock(), 0, "govChangeTimeLock"),
        (hq.hasPendingGovChange(), False, "pending governance"),
        (hq.registryChangeTimeLock(), 0, "registryChangeTimeLock"),
        (
            hq.minGovChangeTimeLock(),
            params["UNDY_HQ_MIN_GOV_TIMELOCK"],
            "minimum governance timelock",
        ),
        (
            hq.maxGovChangeTimeLock(),
            params["UNDY_HQ_MAX_GOV_TIMELOCK"],
            "maximum governance timelock",
        ),
        (
            hq.minRegistryTimeLock(),
            params["UNDY_HQ_MIN_REG_TIMELOCK"],
            "minimum registry timelock",
        ),
        (
            hq.maxRegistryTimeLock(),
            params["UNDY_HQ_MAX_REG_TIMELOCK"],
            "maximum registry timelock",
        ),
        (_address(hq.undyToken()).lower(), "0x" + "00" * 20, "UNDY token"),
        (hq.mintEnabled(), False, "mint flag"),
        (hq.getRegistryDescription(), "UndyHq.vy", "registry description"),
    )
    for actual, expected, label in checks:
        if actual != expected:
            raise RuntimeError(
                f"Robinhood UndyHq has unexpected {label}: {actual!r}, "
                f"expected {expected!r}"
            )
    return hq


def require_authenticated_robinhood_defaults(migration):
    """Load the fixed DefaultsRobinhood bootstrap after exact authentication."""
    args = (
        ROBINHOOD_USER_WALLET_BLUEPRINT,
        ROBINHOOD_USER_WALLET_CONFIG_BLUEPRINT,
    )
    expected_runtime = require_approved_robinhood_runtime(
        migration,
        "DefaultsRobinhood",
        args,
        ROBINHOOD_DEFAULTS_RUNTIME_CODEHASH,
        defaults_dependency=True,
    )
    _require_bootstrap_manifest_entry(
        migration,
        "DefaultsRobinhood",
        ROBINHOOD_DEFAULTS,
        ROBINHOOD_DEFAULTS_RUNTIME_CODEHASH,
    )
    _require_exact_live_runtime(
        "DefaultsRobinhood",
        ROBINHOOD_DEFAULTS,
        expected_runtime,
        ROBINHOOD_DEFAULTS_RUNTIME_CODEHASH,
    )
    defaults = boa.load_partial(
        migration.get_contract_file("DefaultsRobinhood")
    ).at(ROBINHOOD_DEFAULTS)
    wallet_config = defaults.userWalletConfig()
    if (
        _address(wallet_config.walletTemplate).lower()
        != ROBINHOOD_USER_WALLET_BLUEPRINT.lower()
        or _address(wallet_config.configTemplate).lower()
        != ROBINHOOD_USER_WALLET_CONFIG_BLUEPRINT.lower()
    ):
        raise RuntimeError(
            "Robinhood DefaultsRobinhood contains unexpected wallet templates"
        )
    return defaults
