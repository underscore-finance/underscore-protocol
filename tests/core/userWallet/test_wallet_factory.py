import warnings

import boa
import pytest
from eth_abi import decode, encode
from eth_utils import keccak, to_checksum_address

from constants import ZERO_ADDRESS


pytestmark = pytest.mark.filterwarnings(
    "ignore:casted bytecode does not match compiled bytecode:UserWarning"
)


WALLET_PATH = "contracts/core/userWallet/UserWallet.vy"
CONFIG_PATH = "contracts/core/userWallet/UserWalletConfig.vy"
FACTORY_PATH = "contracts/core/userWallet/UserWalletFactory.vy"
ETH = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

CANONICAL_CREATE2_SINGLETON = "0x4e59b44847b379578588920cA78FbF26c0B4956C"
CANONICAL_CREATE2_SINGLETON_RUNTIME = bytes.fromhex(
    "7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe0"
    "3601600081602082378035828234f58015156039578182fd5b8082525050506014"
    "600cf3"
)
USER_WALLET_IMPL_V1_SALT = bytes.fromhex(
    "da9e0e08155d5e49d144d1878faacbcf25fec5790c5ca4cfea6c03788d80329d"
)
USER_WALLET_CONFIG_IMPL_V1_SALT = bytes.fromhex(
    "c54fd3bd79f3df3298ee349c311ac2d48d1dd8bdbc6e4c795ec0b851c7321227"
)
WALLET_FACTORY_V1_SALT = bytes.fromhex(
    "97049e1342f95e7c1a137d37a08a26977defb40ca4763dd6c6d05cef6bce600a"
)

VYPER_PROXY_INITCODE_PREFIX = bytes.fromhex(
    "602d3d8160093d39f3363d3d373d3d3d363d73"
)
VYPER_PROXY_RUNTIME_PREFIX = bytes.fromhex("363d3d373d3d3d363d73")
VYPER_PROXY_SUFFIX = bytes.fromhex("5af43d82803e903d91602b57fd5bf3")

HATCHERY_SOURCE = """
# @version 0.4.3


@external
def createUserWallet(_factory: address, _calldata: Bytes[8192]) -> Bytes[64]:
    return raw_call(_factory, _calldata, max_outsize=64)
"""


REGISTRY_SOURCE = """
# @version 0.4.3

hatchery: public(address)


@deploy
def __init__(_hatchery: address):
    self.hatchery = _hatchery


@external
def setHatchery(_hatchery: address):
    self.hatchery = _hatchery


@view
@external
def getAddr(_regId: uint256) -> address:
    if _regId == 5:
        return self.hatchery
    return empty(address)
"""


def _address_bytes(address):
    return bytes.fromhex(str(address)[2:])


def _predict_create2(deployer, salt, initcode):
    digest = keccak(b"\xff" + _address_bytes(deployer) + salt + keccak(initcode))
    return to_checksum_address(digest[-20:])


def _wallet_salt(owner, group_id, starter_agent_tier):
    return keccak(
        encode(
            ["address", "uint256", "uint256"],
            [str(owner), group_id, starter_agent_tier],
        )
    )


def _proxy_initcode(implementation):
    return (
        VYPER_PROXY_INITCODE_PREFIX
        + _address_bytes(implementation)
        + VYPER_PROXY_SUFFIX
    )


def _proxy_runtime(implementation):
    return (
        VYPER_PROXY_RUNTIME_PREFIX
        + _address_bytes(implementation)
        + VYPER_PROXY_SUFFIX
    )


def _predict_proxy(factory, implementation, salt):
    return _predict_create2(factory, salt, _proxy_initcode(implementation))


def _deploy_through_singleton(partial, salt):
    creation_bytecode = partial.compiler_data.bytecode
    expected = _predict_create2(
        CANONICAL_CREATE2_SINGLETON,
        salt,
        creation_bytecode,
    )
    runtime = partial.compiler_data.bytecode_runtime

    existing_code = boa.env.get_code(expected)
    if not existing_code:
        computation = boa.env.raw_call(
            CANONICAL_CREATE2_SINGLETON,
            data=salt + creation_bytecode,
        )
        deployed = to_checksum_address(computation.output[-20:])
        assert deployed == expected
    assert boa.env.get_code(expected) == runtime
    return partial.at(expected)


@pytest.fixture(scope="module")
def wallet_factory_artifacts(env):
    boa.env.set_code(
        CANONICAL_CREATE2_SINGLETON,
        CANONICAL_CREATE2_SINGLETON_RUNTIME,
    )

    wallet_partial = boa.load_partial(WALLET_PATH)
    wallet = _deploy_through_singleton(wallet_partial, USER_WALLET_IMPL_V1_SALT)
    config_partial = boa.load_partial(CONFIG_PATH)
    config = _deploy_through_singleton(
        config_partial,
        USER_WALLET_CONFIG_IMPL_V1_SALT,
    )

    # Boa can model the zero sender even though no live transaction can
    # originate there. This exercises the exact checked-in placeholder
    # bytecode; the release gate separately forbids blessing that placeholder.
    test_admin = ZERO_ADDRESS
    factory_partial = boa.load_partial(FACTORY_PATH)
    factory = _deploy_through_singleton(factory_partial, WALLET_FACTORY_V1_SALT)

    assert factory.WALLET_FACTORY_ADMIN() == test_admin
    assert factory.USER_WALLET_IMPLEMENTATION() == wallet.address
    assert factory.USER_WALLET_IMPLEMENTATION_CODEHASH() == keccak(
        wallet_partial.compiler_data.bytecode_runtime
    )
    assert factory.USER_WALLET_CONFIG_IMPLEMENTATION() == config.address
    assert factory.USER_WALLET_CONFIG_IMPLEMENTATION_CODEHASH() == keccak(
        config_partial.compiler_data.bytecode_runtime
    )

    return {
        "admin": test_admin,
        "wallet": wallet,
        "wallet_partial": wallet_partial,
        "config": config,
        "config_partial": config_partial,
        "factory": factory,
        "factory_partial": factory_partial,
    }


def _new_registry(label):
    hatchery = boa.loads(HATCHERY_SOURCE, name=f"{label}_hatchery")
    registry = boa.loads(
        REGISTRY_SOURCE,
        hatchery.address,
        name=f"{label}_registry",
    )
    return registry, hatchery


def _configure_factory(artifacts, label):
    registry, hatchery = _new_registry(label)
    artifacts["factory"].setUndyHq(
        registry.address,
        sender=artifacts["admin"],
    )
    return registry, hatchery


def _create_wallet_pair(factory, hatchery, params):
    result = hatchery.createUserWallet(
        factory.address,
        factory.createUserWallet.prepare_calldata(params),
    )
    wallet, config = decode(["address", "address"], result)
    return to_checksum_address(wallet), to_checksum_address(config)


def _creation_params(
    label,
    owner,
    group_id,
    starter_agent_tier,
    weth,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    addrs = {
        name: boa.env.generate_address(f"{label}_{name}")
        for name in (
            "starting_agent",
            "kernel",
            "sentinel",
            "high_command",
            "paymaster",
            "cheque_book",
            "migrator",
            "action_data_provider",
        )
    }
    return (
        owner,
        group_id,
        starter_agent_tier,
        createGlobalManagerSettings(),
        createGlobalPayeeSettings(),
        createChequeSettings(),
        addrs["starting_agent"],
        createManagerSettings(),
        addrs["kernel"],
        addrs["sentinel"],
        addrs["high_command"],
        addrs["paymaster"],
        addrs["cheque_book"],
        addrs["migrator"],
        addrs["action_data_provider"],
        weth,
        ETH,
        19,
        191,
        (True, False, True, False),
    )


def _attach_proxy(path, address):
    # Boa warns because a proxy runtime intentionally differs from the ABI's
    # implementation runtime.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return boa.load_partial(path).at(address)


def _assert_proxy_pair(artifacts, result, owner, group_id, tier, weth):
    factory = artifacts["factory"]
    wallet_impl = artifacts["wallet"].address
    config_impl = artifacts["config"].address
    salt = _wallet_salt(owner, group_id, tier)
    expected_wallet = _predict_proxy(factory.address, wallet_impl, salt)
    expected_config = _predict_proxy(factory.address, config_impl, salt)

    assert tuple(result) == (expected_wallet, expected_config)
    assert boa.env.get_code(expected_wallet) == _proxy_runtime(wallet_impl)
    assert boa.env.get_code(expected_config) == _proxy_runtime(config_impl)
    assert factory.isUserWalletConfig(expected_config, salt) is True
    assert factory.isUserWalletConfig(expected_wallet, salt) is False

    wallet = _attach_proxy(WALLET_PATH, expected_wallet)
    config = _attach_proxy(CONFIG_PATH, expected_config)
    assert wallet.initialized() is True
    assert wallet.walletConfig() == expected_config
    assert wallet.WETH() == weth
    assert config.initialized() is True
    assert config.wallet() == expected_wallet
    assert config.walletSalt() == salt
    assert config.owner() == owner
    assert config.groupId() == group_id
    assert config.eval("self.UNDY_HQ") == factory.undyHq()
    return expected_wallet, expected_config


def test_real_factory_deploys_independently_predicted_pair_with_chain_parity(
    wallet_factory_artifacts,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    artifacts = wallet_factory_artifacts
    owner = boa.env.generate_address("factory_parity_owner")
    group_id = 420
    tier = 1
    observed = []

    # Each anchor represents a chain-local factory setup. The factory and
    # implementation bytecode are identical, while WETH and HQ differ.
    for chain in ("chain_a", "chain_b"):
        with boa.env.anchor():
            _, hatchery = _configure_factory(artifacts, chain)
            weth = boa.env.generate_address(f"{chain}_weth")
            params = _creation_params(
                chain,
                owner,
                group_id,
                tier,
                weth,
                createGlobalManagerSettings,
                createGlobalPayeeSettings,
                createChequeSettings,
                createManagerSettings,
            )
            result = _create_wallet_pair(artifacts["factory"], hatchery, params)
            observed.append(
                _assert_proxy_pair(
                    artifacts,
                    result,
                    owner,
                    group_id,
                    tier,
                    weth,
                )
            )

    assert observed[0] == observed[1]


def test_factory_hq_is_admin_gated_and_permanently_one_shot(
    wallet_factory_artifacts,
):
    artifacts = wallet_factory_artifacts
    factory = artifacts["factory"]
    registry, _ = _new_registry("one_shot")
    other_registry, _ = _new_registry("one_shot_replacement")
    stranger = boa.env.generate_address("one_shot_stranger")

    assert factory.undyHq() == ZERO_ADDRESS
    with boa.reverts("no perms"):
        factory.setUndyHq(registry.address, sender=stranger)
    with boa.reverts("invalid undy hq"):
        factory.setUndyHq(ZERO_ADDRESS, sender=artifacts["admin"])
    with boa.reverts("invalid undy hq"):
        factory.setUndyHq(stranger, sender=artifacts["admin"])

    factory.setUndyHq(registry.address, sender=artifacts["admin"])
    assert factory.undyHq() == registry.address

    with boa.reverts("already initialized"):
        factory.setUndyHq(other_registry.address, sender=artifacts["admin"])
    assert factory.undyHq() == registry.address


def test_factory_rejects_unregistered_caller_without_occupying_addresses(
    wallet_factory_artifacts,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    artifacts = wallet_factory_artifacts
    _, hatchery = _configure_factory(artifacts, "wrong_caller")
    stranger = boa.env.generate_address("wrong_factory_caller")
    owner = boa.env.generate_address("wrong_caller_owner")
    params = _creation_params(
        "wrong_caller",
        owner,
        421,
        1,
        boa.env.generate_address("wrong_caller_weth"),
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
    )
    salt = _wallet_salt(owner, 421, 1)
    wallet = _predict_proxy(
        artifacts["factory"].address,
        artifacts["wallet"].address,
        salt,
    )
    config = _predict_proxy(
        artifacts["factory"].address,
        artifacts["config"].address,
        salt,
    )

    assert stranger != hatchery.address
    with boa.reverts("no perms"):
        artifacts["factory"].createUserWallet(params, sender=stranger)
    assert boa.env.get_code(wallet) == b""
    assert boa.env.get_code(config) == b""


def test_factory_follows_registered_hatchery_rotation_and_rejects_invalid_tier(
    wallet_factory_artifacts,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    artifacts = wallet_factory_artifacts
    registry, old_hatchery = _configure_factory(artifacts, "rotation")
    new_hatchery = boa.loads(HATCHERY_SOURCE, name="rotation_new_hatchery")
    owner = boa.env.generate_address("rotation_owner")
    params = _creation_params(
        "rotation",
        owner,
        422,
        1,
        boa.env.generate_address("rotation_weth"),
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
    )

    registry.setHatchery(new_hatchery.address)
    with boa.reverts("no perms"):
        _create_wallet_pair(artifacts["factory"], old_hatchery, params)

    invalid_tier_params = list(params)
    invalid_tier_params[2] = 3
    with boa.reverts("invalid starter agent tier"):
        _create_wallet_pair(
            artifacts["factory"],
            new_hatchery,
            tuple(invalid_tier_params),
        )

    result = _create_wallet_pair(artifacts["factory"], new_hatchery, params)
    _assert_proxy_pair(artifacts, result, owner, 422, 1, params[15])


def test_factory_exposes_no_create_only_or_forwarding_surface(
    wallet_factory_artifacts,
):
    function_names = set(
        wallet_factory_artifacts["factory_partial"]
        .compiler_data.function_signatures
    )
    assert function_names == {
        "setUndyHq",
        "isUserWalletConfig",
        "createUserWallet",
    }


def test_factory_rejects_absent_or_wrong_implementation_code_before_create(
    wallet_factory_artifacts,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    artifacts = wallet_factory_artifacts

    cases = (
        ("wallet_absent", artifacts["wallet"].address, b"", "invalid wallet implementation"),
        ("wallet_wrong", artifacts["wallet"].address, b"\x00", "invalid wallet implementation"),
        ("config_absent", artifacts["config"].address, b"", "invalid config implementation"),
        ("config_wrong", artifacts["config"].address, b"\x00", "invalid config implementation"),
    )
    for index, (label, implementation, replacement, reason) in enumerate(cases):
        with boa.env.anchor():
            _, hatchery = _configure_factory(artifacts, label)
            boa.env.set_code(implementation, replacement)
            owner = boa.env.generate_address(f"{label}_owner")
            group_id = 430 + index
            params = _creation_params(
                label,
                owner,
                group_id,
                1,
                boa.env.generate_address(f"{label}_weth"),
                createGlobalManagerSettings,
                createGlobalPayeeSettings,
                createChequeSettings,
                createManagerSettings,
            )
            salt = _wallet_salt(owner, group_id, 1)
            wallet = _predict_proxy(
                artifacts["factory"].address,
                artifacts["wallet"].address,
                salt,
            )
            config = _predict_proxy(
                artifacts["factory"].address,
                artifacts["config"].address,
                salt,
            )

            with boa.reverts(reason):
                _create_wallet_pair(artifacts["factory"], hatchery, params)
            assert boa.env.get_code(wallet) == b""
            assert boa.env.get_code(config) == b""


def test_duplicate_identity_reverts_without_mutating_existing_pair(
    wallet_factory_artifacts,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    artifacts = wallet_factory_artifacts
    _, hatchery = _configure_factory(artifacts, "duplicate")
    owner = boa.env.generate_address("duplicate_owner")
    params = _creation_params(
        "duplicate",
        owner,
        440,
        2,
        boa.env.generate_address("duplicate_weth"),
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
    )
    result = _create_wallet_pair(artifacts["factory"], hatchery, params)
    wallet_address, config_address = _assert_proxy_pair(
        artifacts,
        result,
        owner,
        440,
        2,
        params[15],
    )
    wallet_code = boa.env.get_code(wallet_address)
    config_code = boa.env.get_code(config_address)

    replacement = list(params)
    replacement[15] = boa.env.generate_address("duplicate_replacement_weth")
    with boa.reverts("wallet already exists"):
        _create_wallet_pair(artifacts["factory"], hatchery, tuple(replacement))

    wallet = _attach_proxy(WALLET_PATH, wallet_address)
    config = _attach_proxy(CONFIG_PATH, config_address)
    assert boa.env.get_code(wallet_address) == wallet_code
    assert boa.env.get_code(config_address) == config_code
    assert wallet.WETH() == params[15]
    assert config.owner() == owner


def test_prefunded_counterfactual_wallet_deploys_without_touching_balances(
    wallet_factory_artifacts,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    artifacts = wallet_factory_artifacts
    _, hatchery = _configure_factory(artifacts, "prefunded")
    owner = boa.env.generate_address("prefunded_owner")
    group_id = 441
    tier = 1
    params = _creation_params(
        "prefunded",
        owner,
        group_id,
        tier,
        boa.env.generate_address("prefunded_weth"),
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
    )
    salt = _wallet_salt(owner, group_id, tier)
    expected_wallet = _predict_proxy(
        artifacts["factory"].address,
        artifacts["wallet"].address,
        salt,
    )
    expected_config = _predict_proxy(
        artifacts["factory"].address,
        artifacts["config"].address,
        salt,
    )
    prefunded_balance = 7 * 10**18
    native_holder = boa.env.generate_address("prefunded_native_holder")
    token_holder = boa.env.generate_address("prefunded_token_holder")
    token = boa.load(
        "contracts/mock/MockErc20.vy",
        token_holder,
        "Prefunded Token",
        "PREFUND",
        18,
        10,
        name="prefunded_token",
    )
    prefunded_token_balance = 3 * 10**18

    assert boa.env.get_code(expected_wallet) == b""
    assert boa.env.get_code(expected_config) == b""
    boa.env.set_balance(native_holder, prefunded_balance)
    boa.env.raw_call(
        expected_wallet,
        sender=native_holder,
        value=prefunded_balance,
    )
    assert token.transfer(
        expected_wallet,
        prefunded_token_balance,
        sender=token_holder,
    )
    assert token.balanceOf(expected_wallet) == prefunded_token_balance

    result = _create_wallet_pair(artifacts["factory"], hatchery, params)

    assert tuple(result) == (expected_wallet, expected_config)
    assert boa.env.get_balance(expected_wallet) == prefunded_balance
    assert token.balanceOf(expected_wallet) == prefunded_token_balance
    _assert_proxy_pair(
        artifacts,
        result,
        owner,
        group_id,
        tier,
        params[15],
    )


def test_wallet_init_failure_rolls_back_both_creates_and_salt_is_reusable(
    wallet_factory_artifacts,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    artifacts = wallet_factory_artifacts
    _, hatchery = _configure_factory(artifacts, "atomic_rollback")
    owner = boa.env.generate_address("atomic_rollback_owner")
    group_id = 450
    tier = 4
    bad_params = _creation_params(
        "atomic_rollback",
        owner,
        group_id,
        tier,
        ZERO_ADDRESS,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
    )
    salt = _wallet_salt(owner, group_id, tier)
    wallet_address = _predict_proxy(
        artifacts["factory"].address,
        artifacts["wallet"].address,
        salt,
    )
    config_address = _predict_proxy(
        artifacts["factory"].address,
        artifacts["config"].address,
        salt,
    )

    # Config initialization accepts/stores WETH before the wallet initializer
    # rejects zero, so this failure occurs only after both CREATE2 operations
    # and the first initializer have run.
    with boa.reverts("inv addr"):
        _create_wallet_pair(artifacts["factory"], hatchery, bad_params)
    assert boa.env.get_code(wallet_address) == b""
    assert boa.env.get_code(config_address) == b""

    good_params = list(bad_params)
    good_params[15] = boa.env.generate_address("atomic_rollback_valid_weth")
    result = _create_wallet_pair(
        artifacts["factory"],
        hatchery,
        tuple(good_params),
    )
    assert _assert_proxy_pair(
        artifacts,
        result,
        owner,
        group_id,
        tier,
        good_params[15],
    ) == (wallet_address, config_address)
