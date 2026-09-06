import boa
from boa.environment import Env
from eth_utils import keccak

from scripts.utils.migration import Migration
from scripts.utils.migration_helpers import get_vyper_abi
from scripts.utils.nonce_alignment import (
    align_account_nonce,
    assert_chain_id,
    get_account_nonces,
    guard_transaction_nonce,
    predict_create_address,
    require_account_nonce,
)


ROBINHOOD_CHAIN_ID = 4663
UNDY_HQ_DEPLOYER = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"
UNDY_HQ_DEPLOYER_NONCE = 5
COMPLETED_DEPLOYER_NONCE = 6
EXPECTED_UNDY_HQ = "0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9"

PRE_UNDY_HQ_ARTIFACTS = (
    (0, "UserWallet", True),
    (1, "UserWalletConfig", True),
    (2, "AgentWrapper", True),
    (3, "DefaultsRobinhood", False),
)


def _code_hash(code: bytes) -> str:
    return "0x" + keccak(code).hex()


def _precompile_expected_code(migration: Migration, deployer: str, addresses: dict):
    """Compile and constructor-check every artifact before nonce zero is spent."""
    source_names = [item[1] for item in PRE_UNDY_HQ_ARTIFACTS] + ["UndyHq"]
    for name in source_names:
        # Manifest generation invokes this same compiler surface after deploy.
        # Validate it now so a missing compiler cannot strand a partial sequence.
        get_vyper_abi(migration._files[name])

    expected_code = {}
    # Constructor execution is needed to materialize immutable data exactly.
    # Use an isolated Boa state and override addresses, so this validation cannot
    # consume or mutate the live Robinhood deployer's nonce.
    with boa.set_env(Env()) as compile_env:
        compile_env.eoa = deployer

        wallet = boa.load_partial(migration._files["UserWallet"]).deploy_as_blueprint(
            override_address=addresses["UserWallet"]
        )
        config = boa.load_partial(
            migration._files["UserWalletConfig"]
        ).deploy_as_blueprint(override_address=addresses["UserWalletConfig"])
        agent = boa.load_partial(
            migration._files["AgentWrapper"]
        ).deploy_as_blueprint(override_address=addresses["AgentWrapper"])
        defaults = boa.load_partial(migration._files["DefaultsRobinhood"]).deploy(
            wallet,
            config,
            override_address=addresses["DefaultsRobinhood"],
        )
        undy_hq = boa.load_partial(migration._files["UndyHq"]).deploy(
            deployer,
            migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
            override_address=EXPECTED_UNDY_HQ,
        )

        expected_code["UserWallet"] = compile_env.get_code(wallet.address)
        expected_code["UserWalletConfig"] = compile_env.get_code(config.address)
        expected_code["AgentWrapper"] = compile_env.get_code(agent.address)
        expected_code["DefaultsRobinhood"] = compile_env.get_code(defaults.address)
        expected_code["UndyHq"] = compile_env.get_code(undy_hq.address)

    return expected_code


def _assert_exact_code(name: str, address: str, expected_code: bytes):
    actual_code = boa.env.get_code(address)
    if actual_code != expected_code:
        raise RuntimeError(
            f"cannot authenticate {name} at {address}: expected codehash "
            f"{_code_hash(expected_code)}, got {_code_hash(actual_code)}"
        )


def _assert_empty_code(label: str, address: str):
    code = boa.env.get_code(address)
    if code:
        raise RuntimeError(
            f"{label} address {address} unexpectedly contains code with hash "
            f"{_code_hash(code)}"
        )


def _assert_pristine_create_target(label: str, address: str):
    _assert_empty_code(label, address)
    latest, pending = get_account_nonces(address)
    if latest != 0 or pending != 0:
        raise RuntimeError(
            f"{label} address {address} is not a pristine CREATE target: "
            f"latest nonce {latest}, pending nonce {pending}"
        )


def _assert_initial_undy_hq_state(migration: Migration):
    undy_hq = boa.load_partial(migration._files["UndyHq"]).at(EXPECTED_UNDY_HQ)
    deployer = str(migration.account.address)
    expected = migration.blueprint.PARAMS

    latest, pending = get_account_nonces(EXPECTED_UNDY_HQ)
    if latest != 1 or pending != 1:
        raise RuntimeError(
            "cannot authenticate completed UndyHq: contract account nonce is "
            f"latest {latest}, pending {pending}; expected 1"
        )

    checks = (
        (str(undy_hq.governance()).lower(), deployer.lower(), "governance"),
        (undy_hq.numGovChanges(), 0, "numGovChanges"),
        (undy_hq.govChangeTimeLock(), 0, "govChangeTimeLock"),
        (undy_hq.numAddrs(), 1, "numAddrs"),
        (undy_hq.registryChangeTimeLock(), 0, "registryChangeTimeLock"),
        (str(undy_hq.undyToken()).lower(), "0x" + "00" * 20, "undyToken"),
        (undy_hq.mintEnabled(), False, "mintEnabled"),
        (
            undy_hq.minGovChangeTimeLock(),
            expected["UNDY_HQ_MIN_GOV_TIMELOCK"],
            "minGovChangeTimeLock",
        ),
        (
            undy_hq.maxGovChangeTimeLock(),
            expected["UNDY_HQ_MAX_GOV_TIMELOCK"],
            "maxGovChangeTimeLock",
        ),
        (
            undy_hq.minRegistryTimeLock(),
            expected["UNDY_HQ_MIN_REG_TIMELOCK"],
            "minRegistryTimeLock",
        ),
        (
            undy_hq.maxRegistryTimeLock(),
            expected["UNDY_HQ_MAX_REG_TIMELOCK"],
            "maxRegistryTimeLock",
        ),
        (undy_hq.getRegistryDescription(), "UndyHq.vy", "registry description"),
    )
    for actual, expected_value, label in checks:
        if actual != expected_value:
            raise RuntimeError(
                f"cannot authenticate completed UndyHq: {label} is {actual!r}, "
                f"expected {expected_value!r}"
            )


def _verify_onchain_prefix(
    migration: Migration,
    current_nonce: int,
    addresses: dict,
    expected_code: dict,
):
    if current_nonce == COMPLETED_DEPLOYER_NONCE:
        _assert_exact_code("UndyHq", EXPECTED_UNDY_HQ, expected_code["UndyHq"])
        _assert_initial_undy_hq_state(migration)
    else:
        _assert_pristine_create_target("UndyHq", EXPECTED_UNDY_HQ)

    for nonce, name, _ in PRE_UNDY_HQ_ARTIFACTS:
        if nonce < current_nonce:
            _assert_exact_code(name, addresses[name], expected_code[name])
        else:
            _assert_pristine_create_target(name, addresses[name])

    # Nonce four is deliberately a zero-value self-send, not a CREATE.
    _assert_empty_code("nonce-4 CREATE", addresses["Nonce4Create"])


def _register_or_deploy_pre_hq_artifacts(
    migration: Migration,
    starting_nonce: int,
    addresses: dict,
    expected_code: dict,
):
    contracts = {}
    deployer = str(migration.account.address)

    for nonce, name, is_blueprint in PRE_UNDY_HQ_ARTIFACTS:
        args = ()
        if name == "DefaultsRobinhood":
            args = (contracts["UserWallet"], contracts["UserWalletConfig"])

        if nonce < starting_nonce:
            contracts[name] = migration.register_existing(
                name,
                addresses[name],
                *args,
            )
            continue

        require_account_nonce(deployer, nonce)
        with guard_transaction_nonce(deployer, nonce):
            if is_blueprint:
                contract = migration.deploy_bp(name, no_retry=True)
            else:
                contract = migration.deploy(name, *args, no_retry=True)

        if str(contract.address).lower() != addresses[name].lower():
            raise RuntimeError(
                f"{name} deployed at {contract.address}; expected {addresses[name]}"
            )
        _assert_exact_code(name, addresses[name], expected_code[name])
        contracts[name] = contract

    return contracts


def migrate(migration: Migration):
    migration.log.h2("Core")

    deployer = str(migration.account.address)
    if deployer.lower() != UNDY_HQ_DEPLOYER.lower():
        raise RuntimeError(
            f"Robinhood core must use deployer {UNDY_HQ_DEPLOYER}; got {deployer}"
        )

    # A mislabeled --rpc must never spend this address-critical EOA nonce on a
    # different chain. This check precedes every nonce or code decision.
    assert_chain_id(ROBINHOOD_CHAIN_ID)

    if boa.env.get_code(deployer):
        raise RuntimeError(
            f"Robinhood core deployer {deployer} must be a code-empty EOA"
        )

    predicted_undy_hq = predict_create_address(deployer, UNDY_HQ_DEPLOYER_NONCE)
    if predicted_undy_hq.lower() != EXPECTED_UNDY_HQ.lower():
        raise RuntimeError(
            "configured Robinhood UndyHq CREATE prediction is invalid: "
            f"expected {EXPECTED_UNDY_HQ}, got {predicted_undy_hq}"
        )

    addresses = {
        name: predict_create_address(deployer, nonce)
        for nonce, name, _ in PRE_UNDY_HQ_ARTIFACTS
    }
    addresses["Nonce4Create"] = predict_create_address(deployer, 4)

    # Compile source, ABI extraction, constructors, and immutable materialization
    # before inspecting the live prefix or spending the first nonce.
    expected_code = _precompile_expected_code(migration, deployer, addresses)

    current_nonce = require_account_nonce(deployer)
    if current_nonce > COMPLETED_DEPLOYER_NONCE:
        if not boa.env.get_code(EXPECTED_UNDY_HQ):
            raise RuntimeError(
                f"deployer nonce {current_nonce} has passed nonce 5 and UndyHq "
                f"is absent at {EXPECTED_UNDY_HQ}; the target is unreachable"
            )
        raise RuntimeError(
            f"deployer nonce {current_nonce} is beyond the only automatically "
            "reconcilable completed nonce 6; refusing to trust migration history"
        )
    if current_nonce == COMPLETED_DEPLOYER_NONCE and not boa.env.get_code(
        EXPECTED_UNDY_HQ
    ):
        raise RuntimeError(
            f"deployer nonce 6 has consumed the nonce-5 CREATE but UndyHq is "
            f"absent at {EXPECTED_UNDY_HQ}; the target is unreachable"
        )

    # Positional log replay cannot safely represent an interrupted conditional
    # padding step. All progress below is derived from nonce plus exact live code.
    migration.discard_transaction_replay()

    try:
        _verify_onchain_prefix(
            migration,
            current_nonce,
            addresses,
            expected_code,
        )
    except RuntimeError as exc:
        if current_nonce <= UNDY_HQ_DEPLOYER_NONCE:
            raise RuntimeError(
                f"Robinhood core prefix at nonce {current_nonce} cannot be "
                "authenticated; no transaction was sent and the nonce-5 UndyHq "
                "address may still be reachable only after manual reconciliation"
            ) from exc
        raise

    contracts = _register_or_deploy_pre_hq_artifacts(
        migration,
        current_nonce,
        addresses,
        expected_code,
    )

    live_nonce = require_account_nonce(deployer)
    if live_nonce == 4:
        migration.log.h3(
            "Exclusive deployer use is required until UndyHq confirms at nonce 5"
        )
        align_account_nonce(migration, UNDY_HQ_DEPLOYER_NONCE)
        live_nonce = UNDY_HQ_DEPLOYER_NONCE
    elif live_nonce < UNDY_HQ_DEPLOYER_NONCE:
        raise RuntimeError(
            f"pre-UndyHq deployment stopped at nonce {live_nonce}; expected nonce 4"
        )

    if live_nonce == UNDY_HQ_DEPLOYER_NONCE:
        hq_args = (
            migration.account,
            migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        )
        _assert_pristine_create_target("UndyHq", EXPECTED_UNDY_HQ)
        with guard_transaction_nonce(deployer, UNDY_HQ_DEPLOYER_NONCE):
            undy_hq = migration.deploy("UndyHq", *hq_args, no_retry=True)
        if str(undy_hq.address).lower() != EXPECTED_UNDY_HQ.lower():
            raise RuntimeError(
                "UndyHq deployed at the wrong address: "
                f"expected {EXPECTED_UNDY_HQ}, got {undy_hq.address}"
            )
        _assert_exact_code("UndyHq", EXPECTED_UNDY_HQ, expected_code["UndyHq"])
        _assert_initial_undy_hq_state(migration)
    elif live_nonce == COMPLETED_DEPLOYER_NONCE:
        hq_args = (
            migration.account,
            migration.blueprint.PARAMS["UNDY_HQ_MIN_GOV_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MAX_GOV_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
            migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
        )
        migration.register_existing(
            "UndyHq",
            EXPECTED_UNDY_HQ,
            *hq_args,
        )
    else:
        raise RuntimeError(
            f"unexpected deployer nonce {live_nonce} before UndyHq reconciliation"
        )

    require_account_nonce(deployer, COMPLETED_DEPLOYER_NONCE)
