from pathlib import Path

import boa
import pytest
from eth_utils import keccak
from vyper.compiler.settings import OptimizationLevel


REPO_ROOT = Path(__file__).resolve().parents[3]
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
    """The only deployment path for the historical wallet PoC artifacts."""
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
    # Pull the repository's selected local/Base environment into every PoC test.
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
    return deploy_v3("contracts/poc/userWallet/UserWalletV3.vy", owner)


@pytest.fixture
def token():
    return deploy_v3(
        "contracts/poc/userWallet/mocks/MockReentrantToken.vy",
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
            "contracts/poc/userWallet/UserWalletConfigV3.vy",
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


def install_config_probe_shim(shim_label, wallet, marker_size):
    """Install a selector-aware Config probe with one malformed marker return.

    The runtime returns the correct Config marker prefix with `marker_size`
    bytes for `configInterfaceMarker()` and an exact 32-byte wallet word for
    `wallet()`. This isolates the exact-length marker guard: the candidate is
    otherwise responsive and correctly wallet-bound.
    """
    marker_selector = keccak(text="configInterfaceMarker()")[:4]
    wallet_selector = keccak(text="wallet()")[:4]
    marker = keccak(text="underscore.user-wallet-config-v3-poc-v1")
    wallet_bytes = bytes.fromhex(str(wallet)[2:])
    code = bytearray()
    labels = {}
    fixups = []

    def emit(*values):
        code.extend(values)

    def push(raw):
        assert 1 <= len(raw) <= 32
        emit(0x5F + len(raw))
        code.extend(raw)

    def jump_to(label):
        emit(0x61)
        fixups.append((len(code), label))
        code.extend(b"\x00\x00")
        emit(0x57)

    # selector := calldata[0:4]
    emit(0x5F, 0x35)
    push((224).to_bytes(1, "big"))
    emit(0x1C)
    emit(0x80)
    push(marker_selector)
    emit(0x14)
    jump_to("marker")
    push(wallet_selector)
    emit(0x14)
    jump_to("wallet")
    emit(0x5F, 0x5F, 0xFD)

    labels["marker"] = len(code)
    emit(0x5B)
    push(marker)
    emit(0x5F, 0x52)
    if marker_size == 33:
        emit(0x5F)
        push(b"\x20")
        emit(0x53)
    push(marker_size.to_bytes(1, "big"))
    emit(0x5F, 0xF3)

    labels["wallet"] = len(code)
    emit(0x5B)
    push(wallet_bytes)
    emit(0x5F, 0x52)
    push(b"\x20")
    emit(0x5F, 0xF3)

    for position, target_label in fixups:
        code[position : position + 2] = labels[target_label].to_bytes(2, "big")
    return install_runtime_shim(shim_label, bytes(code))


@pytest.fixture
def malformed_word_candidate(wallet):
    return install_config_probe_shim("v3_malformed_31", wallet.address, 31)


@pytest.fixture
def oversized_word_candidate(wallet):
    return install_config_probe_shim("v3_oversized_33", wallet.address, 33)


@pytest.fixture
def oversized_token_return():
    return install_runtime_shim("v3_oversized_token_33", bytes.fromhex("60216000f3"))
