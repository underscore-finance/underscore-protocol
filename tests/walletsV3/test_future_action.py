import hashlib
from pathlib import Path

import boa
from eth_utils import keccak

from conftest import REPO_ROOT, V3_COMPILER_ARGS, deploy_v3


ZERO = "0x0000000000000000000000000000000000000000"
STEP4_SOURCE_SHA256 = "d71ea665405494b0d9f4186e3a45e78104aaf0e97b7dcb0786c9dc1fb5f68039"
STEP4_RUNTIME_KECCAK = "f8aba82adac1b070be7ab8df6f82e588fd319c09572c9d7f2383a7a72a9834b4"
STEP4_RUNTIME_SIZE = 12_055


def test_s5_e8_future_asset_release_needs_no_core_change(
    wallet,
    token,
    owner,
    recipient,
    config_factory,
):
    core_path = REPO_ROOT / "contracts/walletsV3/UserWalletV3.vy"
    assert hashlib.sha256(core_path.read_bytes()).hexdigest() == STEP4_SOURCE_SHA256
    deployer = boa.load_partial(str(core_path), compiler_args=V3_COMPILER_ARGS)
    runtime = deployer.compiler_data.bytecode_runtime
    assert len(runtime) == STEP4_RUNTIME_SIZE
    assert keccak(runtime).hex() == STEP4_RUNTIME_KECCAK

    lego = deploy_v3("contracts/walletsV3/mocks/MockFutureActionLego.vy")
    protocol = deploy_v3("contracts/walletsV3/mocks/MockFutureActionProtocol.vy")
    extender = deploy_v3(
        "contracts/walletsV3/extenders/FutureActionExtender.vy",
        lego.address,
    )
    config = config_factory(
        wallet,
        recipients=[recipient],
        tokens=[(token.address, 10**24, 10**24)],
    )
    wallet.replaceConfig(config.address, sender=owner)
    selector = bytes(
        extender.releaseBond.prepare_calldata(
            wallet.address,
            protocol.address,
            token.address,
            1,
        )[:4]
    )
    wallet.attachExtender(
        (
            keccak(text="wallet-v3-future-family"),
            1,
            extender.address,
            lego.address,
            ZERO,
            ZERO,
            [(selector, 30, 3, 1)],
            [],
        ),
        sender=owner,
    )
    token.mint(protocol.address, 25)
    protocol.seedBond(wallet.address, token.address, 25)
    wallet.execute(
        extender.releaseBond.prepare_calldata(
            wallet.address,
            protocol.address,
            token.address,
            10,
        ),
        sender=owner,
    )
    assert protocol.bond(wallet.address, token.address) == 15
    assert token.balanceOf(wallet.address) == 10
    assert token.balanceOf(lego.address) == 0
    assert token.balanceOf(extender.address) == 0
