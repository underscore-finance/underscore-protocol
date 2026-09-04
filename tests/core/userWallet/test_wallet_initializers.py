import warnings

import boa
import pytest
from eth_abi import encode
from eth_utils import keccak, to_checksum_address

from constants import ZERO_ADDRESS


WALLET_PATH = "contracts/core/userWallet/UserWallet.vy"
CONFIG_PATH = "contracts/core/userWallet/UserWalletConfig.vy"
ETH = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
EIP170_MAX_RUNTIME_SIZE = 24_576
VYPER_PROXY_INITCODE_PREFIX = bytes.fromhex(
    "602d3d8160093d39f3363d3d373d3d3d363d73"
)
VYPER_PROXY_INITCODE_SUFFIX = bytes.fromhex("5af43d82803e903d91602b57fd5bf3")
CANONICAL_CREATE2_SINGLETON = "0x4e59b44847b379578588920cA78FbF26c0B4956C"
CANONICAL_CREATE2_SINGLETON_RUNTIME = bytes.fromhex(
    "7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe0"
    "3601600081602082378035828234f58015156039578182fd5b8082525050506014"
    "600cf3"
)
USER_WALLET_IMPL_V1_SALT = keccak(b"UNDERSCORE_USER_WALLET_IMPL_V1")

# This helper deliberately exposes clone creation separately from initialization
# so these tests can inspect the implementation-level one-shot behavior. It is
# not the production deployment model: the real factory must create and
# initialize both proxies atomically, make no intervening external call, and
# expose no create-only path.
CLONE_FACTORY_SOURCE = """
# @version 0.4.3

USER_WALLET_CONFIG_IMPLEMENTATION: public(immutable(address))


@deploy
def __init__(_configImplementation: address):
    USER_WALLET_CONFIG_IMPLEMENTATION = _configImplementation


@external
def clone(_implementation: address, _salt: bytes32) -> address:
    return create_minimal_proxy_to(_implementation, salt=_salt)


@view
@external
def isUserWalletConfig(_config: address, _salt: bytes32) -> bool:
    initcode: Bytes[54] = concat(
        x"602d3d8160093d39f3363d3d373d3d3d363d73",
        convert(USER_WALLET_CONFIG_IMPLEMENTATION, bytes20),
        x"5af43d82803e903d91602b57fd5bf3",
    )
    create2Hash: uint256 = convert(
        keccak256(
            concat(
                x"ff",
                convert(self, bytes20),
                _salt,
                keccak256(initcode),
            )
        ),
        uint256,
    )
    expectedConfig: address = convert(
        create2Hash & convert(max_value(uint160), uint256),
        address,
    )
    return _config == expectedConfig


@external
def forward(_proxy: address, _calldata: Bytes[8192]):
    raw_call(_proxy, _calldata)
"""

CONFIG_POINTER_STUB_SOURCE = """
# @version 0.4.3

wallet: public(address)
walletSalt: public(bytes32)


@deploy
def __init__(_wallet: address, _walletSalt: bytes32):
    self.wallet = _wallet
    self.walletSalt = _walletSalt
"""


@pytest.fixture(scope="module")
def wallet_implementation(env):
    # Bootstrap only the canonical singleton runtime, then exercise the same
    # fixed-salt deployment path required on every production chain.
    singleton_code = boa.env.get_code(CANONICAL_CREATE2_SINGLETON)
    if singleton_code:
        assert singleton_code == CANONICAL_CREATE2_SINGLETON_RUNTIME
    else:
        boa.env.set_code(
            CANONICAL_CREATE2_SINGLETON,
            CANONICAL_CREATE2_SINGLETON_RUNTIME,
        )
    wallet_deployer = boa.load_partial(WALLET_PATH)
    creation_bytecode = wallet_deployer.compiler_data.bytecode
    predicted_address = _predict_create2(
        CANONICAL_CREATE2_SINGLETON,
        USER_WALLET_IMPL_V1_SALT,
        creation_bytecode,
    )
    config_deployer = boa.load_partial(CONFIG_PATH)
    assert (
        predicted_address
        == config_deployer._constants.USER_WALLET_IMPLEMENTATION
    )
    deployed_address = predicted_address
    if not boa.env.get_code(deployed_address):
        computation = boa.env.raw_call(
            CANONICAL_CREATE2_SINGLETON,
            data=USER_WALLET_IMPL_V1_SALT + creation_bytecode,
        )
        deployed_address = to_checksum_address(computation.output[-20:])
        assert deployed_address == predicted_address
    assert boa.env.get_code(deployed_address) == wallet_deployer.compiler_data.bytecode_runtime

    implementation = wallet_deployer.at(deployed_address)
    assert implementation.initialized() is True
    return implementation


@pytest.fixture(scope="module")
def config_implementation(env):
    return boa.load(CONFIG_PATH, name="user_wallet_config_implementation")


@pytest.fixture(scope="module")
def clone_factory(env, config_implementation):
    return boa.loads(
        CLONE_FACTORY_SOURCE,
        config_implementation.address,
        name="test_clone_factory",
    )


def _wallet_salt(owner, group_id, starter_agent_tier):
    return keccak(
        encode(
            ["address", "uint256", "uint256"],
            [str(owner), group_id, starter_agent_tier],
        )
    )


def _predict_create2(deployer, salt, initcode):
    digest = keccak(
        b"\xff"
        + bytes.fromhex(str(deployer)[2:])
        + salt
        + keccak(initcode)
    )
    return to_checksum_address(digest[-20:])


def _predict_proxy(factory, implementation, salt):
    initcode = (
        VYPER_PROXY_INITCODE_PREFIX
        + bytes.fromhex(str(implementation.address)[2:])
        + VYPER_PROXY_INITCODE_SUFFIX
    )
    return _predict_create2(factory.address, salt, initcode)


def _identity(label, group_id, starter_agent_tier=1):
    owner = boa.env.generate_address(f"{label}_owner")
    return {
        "owner": owner,
        "group_id": group_id,
        "starter_agent_tier": starter_agent_tier,
        "salt": _wallet_salt(owner, group_id, starter_agent_tier),
    }


def _clone(factory, implementation, path, salt):
    expected_address = _predict_proxy(factory, implementation, salt)
    # Boa warns because an EIP-1167 proxy's runtime is intentionally different
    # from the implementation ABI attached to it.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        proxy_address = factory.clone(implementation.address, salt)
        proxy = boa.load_partial(path).at(proxy_address)
    assert proxy.address == expected_address
    return proxy


def _forward(factory, proxy, function, *args):
    factory.forward(proxy.address, function.prepare_calldata(*args))


def _proxy_pair(factory, wallet_implementation, config_implementation, identity):
    wallet = _clone(
        factory,
        wallet_implementation,
        WALLET_PATH,
        identity["salt"],
    )
    config = _clone(
        factory,
        config_implementation,
        CONFIG_PATH,
        identity["salt"],
    )
    assert wallet.address != config.address
    return wallet, config


def _wallet_params(weth, config):
    return (weth, config)


def _config_params(
    wallet,
    identity,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
    label="initializer",
):
    addrs = {
        name: boa.env.generate_address(f"{label}_{name}")
        for name in (
            "undy_hq",
            "starting_agent",
            "kernel",
            "sentinel",
            "high_command",
            "paymaster",
            "cheque_book",
            "migrator",
            "action_data_provider",
            "weth",
        )
    }
    settings = {
        "global_manager": createGlobalManagerSettings(),
        "global_payee": createGlobalPayeeSettings(),
        "cheque": createChequeSettings(),
        "starting_agent": createManagerSettings(),
        "instant": (True, False, True, False),
    }
    values = {
        "min_timelock": 19,
        "max_timelock": 191,
    }
    params = (
        wallet,
        addrs["undy_hq"],
        identity["owner"],
        identity["group_id"],
        identity["starter_agent_tier"],
        settings["global_manager"],
        settings["global_payee"],
        settings["cheque"],
        addrs["starting_agent"],
        settings["starting_agent"],
        addrs["kernel"],
        addrs["sentinel"],
        addrs["high_command"],
        addrs["paymaster"],
        addrs["cheque_book"],
        addrs["migrator"],
        addrs["action_data_provider"],
        addrs["weth"],
        ETH,
        values["min_timelock"],
        values["max_timelock"],
        settings["instant"],
    )
    return params, addrs, settings, values


def test_wallet_implementation_runtimes_fit_eip170(
    wallet_implementation,
    config_implementation,
):
    for name, implementation in (
        ("UserWallet", wallet_implementation),
        ("UserWalletConfig", config_implementation),
    ):
        runtime_size = len(implementation.compiler_data.bytecode_runtime)
        headroom = EIP170_MAX_RUNTIME_SIZE - runtime_size
        assert runtime_size <= EIP170_MAX_RUNTIME_SIZE, (
            f"{name} runtime is {runtime_size} bytes; "
            f"EIP-170 limit is {EIP170_MAX_RUNTIME_SIZE} bytes; "
            f"headroom is {headroom} bytes"
        )


def test_implementation_instances_are_locked(
    wallet_implementation,
    config_implementation,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    identity = _identity("implementation", 71)
    config_params, _, _, _ = _config_params(
        wallet_implementation.address,
        identity,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
        "implementation",
    )

    assert wallet_implementation.initialized() is True
    assert config_implementation.initialized() is True
    assert config_implementation.eval("ownership.ownershipInitialized") is True

    with boa.reverts("already initialized"):
        wallet_implementation.initialize(
            *_wallet_params(
                boa.env.generate_address("implementation_weth"),
                config_implementation.address,
            )
        )

    with boa.reverts("already initialized"):
        config_implementation.initialize(*config_params)


def test_user_wallet_proxy_initializes_once(
    clone_factory,
    wallet_implementation,
    config_implementation,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    identity = _identity("wallet_proxy", 72)
    wallet, config = _proxy_pair(
        clone_factory,
        wallet_implementation,
        config_implementation,
        identity,
    )
    config_params, addrs, _, _ = _config_params(
        wallet.address,
        identity,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
        "wallet_proxy",
    )
    wallet_params = _wallet_params(addrs["weth"], config.address)

    assert wallet.initialized() is False
    assert wallet.WETH() == ZERO_ADDRESS
    assert wallet.walletConfig() == ZERO_ADDRESS

    # The config must be bound first so the wallet can verify the reciprocal
    # pointer while it initializes.
    _forward(clone_factory, config, config.initialize, *config_params)
    _forward(clone_factory, wallet, wallet.initialize, *wallet_params)

    assert wallet.initialized() is True
    assert wallet.WETH() == addrs["weth"]
    assert wallet.ETH() == ETH
    assert wallet.walletConfig() == config.address
    assert wallet.numAssets() == 1
    assert config.wallet() == wallet.address

    with boa.reverts("already initialized"):
        _forward(clone_factory, wallet, wallet.initialize, *wallet_params)

    assert wallet.WETH() == addrs["weth"]
    assert wallet.walletConfig() == config.address


def test_user_wallet_config_proxy_initializes_once(
    clone_factory,
    config_implementation,
    wallet_implementation,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    identity = _identity("config_proxy", 73)
    wallet, config = _proxy_pair(
        clone_factory,
        wallet_implementation,
        config_implementation,
        identity,
    )
    params, addrs, settings, values = _config_params(
        wallet.address,
        identity,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
        "config_proxy",
    )

    assert config.initialized() is False
    assert config.owner() == ZERO_ADDRESS
    assert config.wallet() == ZERO_ADDRESS

    _forward(clone_factory, config, config.initialize, *params)
    _forward(
        clone_factory,
        wallet,
        wallet.initialize,
        *_wallet_params(addrs["weth"], config.address),
    )

    assert config.initialized() is True
    assert config.eval("ownership.ownershipInitialized") is True
    assert config.wallet() == wallet.address
    assert config.walletSalt() == identity["salt"]
    assert config.owner() == identity["owner"]
    assert config.groupId() == identity["group_id"]
    assert config.startingAgent() == addrs["starting_agent"]
    assert config.numManagers() == 2
    assert config.managers(1) == addrs["starting_agent"]
    assert config.indexOfManager(addrs["starting_agent"]) == 1

    assert config.kernel() == addrs["kernel"]
    assert config.sentinel() == addrs["sentinel"]
    assert config.highCommand() == addrs["high_command"]
    assert config.paymaster() == addrs["paymaster"]
    assert config.chequeBook() == addrs["cheque_book"]
    assert config.migrator() == addrs["migrator"]

    assert config.timeLock() == values["min_timelock"]
    assert config.MIN_TIMELOCK() == values["min_timelock"]
    assert config.MAX_TIMELOCK() == values["max_timelock"]
    assert config.ownershipTimeLock() == values["min_timelock"]
    assert config.MIN_OWNERSHIP_TIMELOCK() == values["min_timelock"]
    assert config.MAX_OWNERSHIP_TIMELOCK() == values["max_timelock"]

    assert config.globalManagerSettings() == settings["global_manager"]
    assert config.globalPayeeSettings() == settings["global_payee"]
    assert config.chequeSettings() == settings["cheque"]
    assert tuple(config.instantActionSettings()) == settings["instant"]
    assert config.managerSettings(addrs["starting_agent"]) == settings["starting_agent"]

    # These values intentionally have no external getters. Boa's read-only eval
    # confirms that the former immutables now live in proxy storage.
    assert config.eval("self.UNDY_HQ") == addrs["undy_hq"]
    assert config.eval("self.WETH") == addrs["weth"]
    assert config.eval("self.ETH") == ETH
    assert config.eval("self.ACTION_DATA_PROVIDER") == addrs["action_data_provider"]
    assert config.eval("ownership.UNDY_HQ_FOR_OWNERSHIP") == addrs["undy_hq"]

    replacement = list(params)
    replacement[1] = boa.env.generate_address("replacement_undy_hq")
    replacement[2] = boa.env.generate_address("replacement_owner")
    replacement[17] = boa.env.generate_address("replacement_config_weth")

    with boa.reverts("already initialized"):
        _forward(clone_factory, config, config.initialize, *replacement)

    assert config.owner() == identity["owner"]
    assert config.groupId() == identity["group_id"]
    assert config.eval("self.UNDY_HQ") == addrs["undy_hq"]
    assert config.eval("self.WETH") == addrs["weth"]


def test_user_wallet_config_rejects_eoa_wallet(
    clone_factory,
    config_implementation,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    identity = _identity("eoa_wallet", 74)
    config = _clone(
        clone_factory,
        config_implementation,
        CONFIG_PATH,
        identity["salt"],
    )
    params, _, _, _ = _config_params(
        boa.env.generate_address("eoa_wallet_target"),
        identity,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
        "eoa_wallet",
    )

    with boa.reverts("invalid wallet"):
        _forward(clone_factory, config, config.initialize, *params)

    assert config.initialized() is False
    assert config.wallet() == ZERO_ADDRESS
    assert config.owner() == ZERO_ADDRESS


def test_user_wallet_rejects_eoa_wallet_config(
    clone_factory,
    wallet_implementation,
):
    identity = _identity("eoa_config", 75)
    wallet = _clone(
        clone_factory,
        wallet_implementation,
        WALLET_PATH,
        identity["salt"],
    )

    with boa.reverts("invalid wallet config"):
        _forward(
            clone_factory,
            wallet,
            wallet.initialize,
            *_wallet_params(
                boa.env.generate_address("eoa_config_weth"),
                boa.env.generate_address("eoa_config_target"),
            ),
        )

    assert wallet.initialized() is False
    assert wallet.walletConfig() == ZERO_ADDRESS


def test_user_wallet_rejects_unrelated_contract_as_wallet_config(
    clone_factory,
    wallet_implementation,
    governance,
):
    identity = _identity("unrelated_config", 76)
    wallet = _clone(
        clone_factory,
        wallet_implementation,
        WALLET_PATH,
        identity["salt"],
    )
    assert len(boa.env.get_code(governance.address)) != 0

    with boa.reverts():
        _forward(
            clone_factory,
            wallet,
            wallet.initialize,
            *_wallet_params(
                boa.env.generate_address("unrelated_config_weth"),
                governance.address,
            ),
        )

    assert wallet.initialized() is False
    assert wallet.walletConfig() == ZERO_ADDRESS


def test_user_wallet_config_rejects_wallet_from_another_group(
    clone_factory,
    wallet_implementation,
    config_implementation,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    identity = _identity("mismatched_pair", 77)
    wallet, config = _proxy_pair(
        clone_factory,
        wallet_implementation,
        config_implementation,
        identity,
    )
    other_identity = dict(identity)
    other_identity["group_id"] += 1
    other_identity["salt"] = _wallet_salt(
        other_identity["owner"],
        other_identity["group_id"],
        other_identity["starter_agent_tier"],
    )
    other_wallet = _clone(
        clone_factory,
        wallet_implementation,
        WALLET_PATH,
        other_identity["salt"],
    )
    params, _, _, _ = _config_params(
        other_wallet.address,
        identity,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
        "mismatched_pair",
    )
    with boa.reverts("invalid proxy pair"):
        _forward(clone_factory, config, config.initialize, *params)

    assert config.initialized() is False
    assert config.wallet() == ZERO_ADDRESS
    assert config.walletSalt() == bytes(32)
    assert config.owner() == ZERO_ADDRESS
    assert wallet.initialized() is False
    assert wallet.walletConfig() == ZERO_ADDRESS


def test_user_wallet_config_rejects_wallet_from_another_owner(
    clone_factory,
    wallet_implementation,
    config_implementation,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    config_identity = _identity("cross_identity_config", 82)
    wallet_identity = _identity("cross_identity_wallet", 83)
    assert config_identity["owner"] != wallet_identity["owner"]
    assert config_identity["salt"] != wallet_identity["salt"]

    config = _clone(
        clone_factory,
        config_implementation,
        CONFIG_PATH,
        config_identity["salt"],
    )
    wallet = _clone(
        clone_factory,
        wallet_implementation,
        WALLET_PATH,
        wallet_identity["salt"],
    )
    config_params, _, _, _ = _config_params(
        wallet.address,
        config_identity,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
        "cross_identity",
    )
    with boa.reverts("invalid proxy pair"):
        _forward(clone_factory, config, config.initialize, *config_params)

    assert config.initialized() is False
    assert config.wallet() == ZERO_ADDRESS
    assert config.walletSalt() == bytes(32)
    assert config.owner() == ZERO_ADDRESS
    assert wallet.initialized() is False
    assert wallet.walletConfig() == ZERO_ADDRESS


def test_user_wallet_rejects_reciprocal_config_with_wrong_wallet_pointer(
    clone_factory,
    wallet_implementation,
):
    identity = _identity("wrong_wallet_pointer", 84)
    wallet = _clone(
        clone_factory,
        wallet_implementation,
        WALLET_PATH,
        identity["salt"],
    )
    config = boa.loads(
        CONFIG_POINTER_STUB_SOURCE,
        boa.env.generate_address("wrong_wallet_pointer_target"),
        identity["salt"],
        name="wrong_wallet_pointer_config",
    )

    # The stub reports the wallet's correct salt, so removing the reciprocal
    # pointer check would let the wallet's individual CREATE2 proof succeed.
    with boa.reverts("invalid wallet config"):
        _forward(
            clone_factory,
            wallet,
            wallet.initialize,
            *_wallet_params(
                boa.env.generate_address("wrong_wallet_pointer_weth"),
                config.address,
            ),
        )

    assert wallet.initialized() is False
    assert wallet.walletConfig() == ZERO_ADDRESS


def test_user_wallet_rejects_reciprocal_config_with_wrong_salt(
    clone_factory,
    wallet_implementation,
):
    identity = _identity("wallet_salt", 85)
    other_identity = _identity("wrong_wallet_salt", 86)
    wallet = _clone(
        clone_factory,
        wallet_implementation,
        WALLET_PATH,
        identity["salt"],
    )
    config = boa.loads(
        CONFIG_POINTER_STUB_SOURCE,
        wallet.address,
        other_identity["salt"],
        name="wrong_wallet_salt_config",
    )

    # The reciprocal pointer is valid. The wallet must read the config's salt
    # and authenticate itself against that committed identity; without that
    # read/self-authentication, this mismatched config would be accepted.
    with boa.reverts("invalid proxy deployer"):
        _forward(
            clone_factory,
            wallet,
            wallet.initialize,
            *_wallet_params(
                boa.env.generate_address("wrong_wallet_salt_weth"),
                config.address,
            ),
        )

    assert wallet.initialized() is False
    assert wallet.walletConfig() == ZERO_ADDRESS


def test_user_wallet_rejects_noncanonical_config_with_correct_pointer_and_salt(
    clone_factory,
    wallet_implementation,
):
    identity = _identity("noncanonical_config", 87)
    wallet = _clone(
        clone_factory,
        wallet_implementation,
        WALLET_PATH,
        identity["salt"],
    )
    config = boa.loads(
        CONFIG_POINTER_STUB_SOURCE,
        wallet.address,
        identity["salt"],
        name="noncanonical_config",
    )

    # A lying contract can report both reciprocal values correctly. It still
    # is not the config implementation clone created by this factory and salt.
    with boa.reverts("invalid proxy pair"):
        _forward(
            clone_factory,
            wallet,
            wallet.initialize,
            *_wallet_params(
                boa.env.generate_address("noncanonical_config_weth"),
                config.address,
            ),
        )

    assert wallet.initialized() is False
    assert wallet.walletConfig() == ZERO_ADDRESS


def test_user_wallet_rejects_direct_eoa_initializer(
    clone_factory,
    wallet_implementation,
    config_implementation,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    identity = _identity("direct_initializer", 79)
    wallet, config = _proxy_pair(
        clone_factory,
        wallet_implementation,
        config_implementation,
        identity,
    )
    config_params, addrs, _, _ = _config_params(
        wallet.address,
        identity,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
        "direct_initializer",
    )
    _forward(clone_factory, config, config.initialize, *config_params)
    wallet_params = _wallet_params(addrs["weth"], config.address)

    # The reciprocal pair and identity are valid; only the caller is wrong.
    # Self-authentication runs before any callback into the proven factory.
    with boa.reverts("invalid proxy deployer"):
        wallet.initialize(*wallet_params)

    assert wallet.initialized() is False
    assert wallet.walletConfig() == ZERO_ADDRESS


def test_user_wallet_rejects_initializer_from_another_factory(
    clone_factory,
    wallet_implementation,
    config_implementation,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    identity = _identity("wrong_factory", 80)
    wallet, config = _proxy_pair(
        clone_factory,
        wallet_implementation,
        config_implementation,
        identity,
    )
    config_params, addrs, _, _ = _config_params(
        wallet.address,
        identity,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
        "wrong_factory",
    )
    _forward(clone_factory, config, config.initialize, *config_params)
    wallet_params = _wallet_params(addrs["weth"], config.address)
    other_factory = boa.loads(
        CLONE_FACTORY_SOURCE,
        config_implementation.address,
        name="other_test_clone_factory",
    )

    with boa.reverts("invalid proxy deployer"):
        _forward(other_factory, wallet, wallet.initialize, *wallet_params)

    assert wallet.initialized() is False
    assert wallet.walletConfig() == ZERO_ADDRESS


@pytest.mark.parametrize(
    "mismatched_field",
    ("owner", "group_id", "starter_agent_tier"),
)
def test_user_wallet_config_rejects_identity_that_does_not_match_proxy(
    mismatched_field,
    clone_factory,
    wallet_implementation,
    config_implementation,
    createGlobalManagerSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
    createManagerSettings,
):
    identity = _identity(f"wrong_{mismatched_field}", 81)
    wallet, config = _proxy_pair(
        clone_factory,
        wallet_implementation,
        config_implementation,
        identity,
    )
    mismatched_identity = dict(identity)
    if mismatched_field == "owner":
        mismatched_identity["owner"] = boa.env.generate_address(
            "mismatched_identity_owner"
        )
    elif mismatched_field == "group_id":
        mismatched_identity["group_id"] += 1
    else:
        mismatched_identity["starter_agent_tier"] = 2

    # The proxy used the original identity salt. Changing any initializer word
    # changes the internally derived salt, so the proxy provenance proof fails.
    params, _, _, _ = _config_params(
        wallet.address,
        mismatched_identity,
        createGlobalManagerSettings,
        createGlobalPayeeSettings,
        createChequeSettings,
        createManagerSettings,
        f"wrong_{mismatched_field}",
    )
    with boa.reverts("invalid proxy deployer"):
        _forward(clone_factory, config, config.initialize, *params)

    assert config.initialized() is False
    assert config.wallet() == ZERO_ADDRESS
    assert config.owner() == ZERO_ADDRESS
