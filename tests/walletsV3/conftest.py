from pathlib import Path

import boa
import pytest
from vyper.compiler.settings import OptimizationLevel


REPO_ROOT = Path(__file__).resolve().parents[2]
V3_COMPILER_ARGS = {
    "optimize": OptimizationLevel.GAS,
    "evm_version": "cancun",
}
V3_COMPILER_REPORT = {
    "vyper": "0.4.3",
    "optimizer": "gas",
    "evmVersion": "cancun",
}


def deploy_v3(relative_path, *args, name=None):
    """The only deployment path for wallet-v3 source artifacts."""
    path = REPO_ROOT / relative_path
    deployer = boa.load_partial(str(path), compiler_args=V3_COMPILER_ARGS)
    settings = deployer.compiler_data.settings
    assert settings.optimize == OptimizationLevel.GAS
    assert settings.evm_version == "cancun"
    kwargs = {}
    if name is not None:
        kwargs["contract_name"] = name
    return deployer.deploy(*args, **kwargs)


@pytest.fixture(autouse=True)
def wallet_v3_env(env):
    # Pull the repository's selected local/Base environment into every v3 test.
    return env


@pytest.fixture
def owner():
    return boa.env.generate_address("wallet_v3_owner")


@pytest.fixture
def manager():
    return boa.env.generate_address("wallet_v3_manager")


@pytest.fixture
def recipient():
    return boa.env.generate_address("wallet_v3_recipient")


@pytest.fixture
def stranger():
    return boa.env.generate_address("wallet_v3_stranger")


@pytest.fixture
def wallet(owner):
    return deploy_v3("contracts/walletsV3/UserWalletV3.vy", owner)


@pytest.fixture
def token():
    return deploy_v3(
        "contracts/walletsV3/mocks/MockReentrantToken.vy",
        "Wallet V3 Token",
        "WV3",
        18,
    )


@pytest.fixture
def action_policies():
    return [
        (1, 10**30),
        (10, 10**30),
        (11, 10**30),
        (12, 10**30),
        (13, 0),
        (14, 0),
        (20, 10**30),
        (21, 10**30),
        (30, 10**30),
        (255, 0),
    ]


@pytest.fixture
def config_factory(owner, manager, recipient, action_policies):
    def factory(
        wallet,
        *,
        managers=None,
        recipients=None,
        tokens=None,
        actions=None,
    ):
        manager_values = [manager] if managers is None else managers
        recipient_values = [recipient] if recipients is None else recipients
        token_values = [] if tokens is None else tokens
        action_values = action_policies if actions is None else actions
        return deploy_v3(
            "contracts/walletsV3/UserWalletConfigV3.vy",
            wallet.address,
            manager_values,
            recipient_values,
            token_values,
            action_values,
        )

    return factory


@pytest.fixture
def config(wallet, token, config_factory):
    return config_factory(
        wallet,
        tokens=[(token.address, 10**24, 10**24)],
    )


@pytest.fixture
def configured_wallet(wallet, config, owner):
    wallet.replaceConfig(config.address, sender=owner)
    return wallet


def install_runtime_shim(label, runtime):
    """Install bounded EVM return-data machinery at a deterministic test address.

    These shims express ABI-invalid return lengths that typed Vyper functions
    cannot emit. Runtime `PUSH1 size PUSH1 0 RETURN` returns zero-filled data
    of the requested size for every selector.
    """
    address = boa.env.generate_address(label)
    boa.env.set_code(address, runtime)
    return address


@pytest.fixture
def malformed_word_candidate():
    return install_runtime_shim("v3_malformed_31", bytes.fromhex("601f6000f3"))


@pytest.fixture
def oversized_word_candidate():
    return install_runtime_shim("v3_oversized_33", bytes.fromhex("60216000f3"))
