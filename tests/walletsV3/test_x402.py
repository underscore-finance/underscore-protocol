import json

import boa
import pytest
from eth_abi import encode
from eth.exceptions import Revert
from eth_utils import keccak
from web3 import Web3

from config.BluePrint import TOKENS, WHALES
from conf_env import FORKS
from conftest import deploy_v3
from test_mpp import attach_payment


pytestmark = pytest.mark.fork("base")

USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
PINNED_BLOCK = 34_642_981
PINNED_BLOCK_HASH = "0xcf93c5606c59a6e58a0524e0c46fd79c9cb94c8e876ac4dc5657e5f6af52d662"
PINNED_TIMESTAMP = 1_756_075_309
PINNED_BASE_FEE = 774_425
DOMAIN_SEPARATOR = bytes.fromhex(
    "02fa7265e7c5d81118673727957699e4d68f74cd74b7db77da710fe8a2c7834f"
)
TRANSFER_TYPEHASH = bytes.fromhex(
    "7c7c6cdb67a18743f49ec6fa9b35f50d52ed05cbed4cc592e13b44501c1a2267"
)
CANCEL_TYPEHASH = keccak(text="CancelAuthorization(address authorizer,bytes32 nonce)")
MAGIC = bytes.fromhex("1626ba7e")
INVALID = bytes.fromhex("ffffffff")

USDC_ABI = json.dumps(
    [
        {
            "type": "function",
            "name": "name",
            "stateMutability": "view",
            "inputs": [],
            "outputs": [{"type": "string"}],
        },
        {
            "type": "function",
            "name": "version",
            "stateMutability": "view",
            "inputs": [],
            "outputs": [{"type": "string"}],
        },
        {
            "type": "function",
            "name": "DOMAIN_SEPARATOR",
            "stateMutability": "view",
            "inputs": [],
            "outputs": [{"type": "bytes32"}],
        },
        {
            "type": "function",
            "name": "TRANSFER_WITH_AUTHORIZATION_TYPEHASH",
            "stateMutability": "view",
            "inputs": [],
            "outputs": [{"type": "bytes32"}],
        },
        {
            "type": "function",
            "name": "authorizationState",
            "stateMutability": "view",
            "inputs": [{"type": "address"}, {"type": "bytes32"}],
            "outputs": [{"type": "bool"}],
        },
        {
            "type": "function",
            "name": "balanceOf",
            "stateMutability": "view",
            "inputs": [{"type": "address"}],
            "outputs": [{"type": "uint256"}],
        },
        {
            "type": "function",
            "name": "transfer",
            "stateMutability": "nonpayable",
            "inputs": [{"type": "address"}, {"type": "uint256"}],
            "outputs": [{"type": "bool"}],
        },
        {
            "type": "function",
            "name": "transferWithAuthorization",
            "stateMutability": "nonpayable",
            "inputs": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
                {"name": "signature", "type": "bytes"},
            ],
            "outputs": [],
        },
    ]
)


@pytest.fixture
def base_payment_stack(wallet, owner, recipient, config_factory, fork):
    assert fork == "base"
    assert FORKS["base"]["block"] == PINNED_BLOCK
    assert Web3.to_checksum_address(TOKENS["base"]["USDC"]) == Web3.to_checksum_address(
        USDC_ADDRESS
    )
    usdc = boa.loads_abi(USDC_ABI, name="BaseUSDC").at(USDC_ADDRESS)
    helper = deploy_v3("contracts/walletsV3/rails/X402Helper.vy", USDC_ADDRESS)
    extender = deploy_v3(
        "contracts/walletsV3/extenders/PaymentExtender.vy",
        helper.address,
    )
    config = config_factory(
        wallet,
        recipients=[recipient],
        tokens=[(USDC_ADDRESS, 10**12, 10**12)],
    )
    wallet.replaceConfig(config.address, sender=owner)
    attach_payment(wallet, extender, helper, owner)
    usdc.transfer(
        wallet.address,
        2_000_000,
        sender=WHALES["base"]["USDC"],
    )
    return {
        "wallet": wallet,
        "owner": owner,
        "destination": recipient,
        "operator": boa.env.generate_address("base_x402_operator"),
        "usdc": usdc,
        "helper": helper,
        "extender": extender,
    }


def authorize(stack, commitment_id, amount, nonce, valid_after, valid_before):
    stack["wallet"].execute(
        stack["extender"].authorizeExternalExact.prepare_calldata(
            stack["wallet"].address,
            commitment_id,
            USDC_ADDRESS,
            amount,
            stack["destination"],
            valid_after,
            valid_before,
            nonce,
        ),
        sender=stack["owner"],
    )


def test_s4_e2_base_constants_preflight_and_real_usdc_bytes_signature_pull(
    base_payment_stack,
):
    stack = base_payment_stack
    upstream = Web3(Web3.HTTPProvider(FORKS["base"]["rpc_url"]))
    block = upstream.eth.get_block(PINNED_BLOCK)
    assert bytes(block.hash) == bytes.fromhex(PINNED_BLOCK_HASH[2:])
    assert block.timestamp == PINNED_TIMESTAMP
    assert block.baseFeePerGas == PINNED_BASE_FEE
    assert stack["usdc"].name() == "USD Coin"
    assert stack["usdc"].version() == "2"
    assert stack["usdc"].DOMAIN_SEPARATOR() == DOMAIN_SEPARATOR
    assert stack["usdc"].TRANSFER_WITH_AUTHORIZATION_TYPEHASH() == TRANSFER_TYPEHASH

    now = boa.env.evm.patch.timestamp
    commitment_id = keccak(text="base-real-usdc-pull")
    nonce = keccak(text="base-real-usdc-pull-nonce")
    amount = 100_000
    authorize(stack, commitment_id, amount, nonce, now - 1, now + 3_600)
    digest = stack["helper"].digest(
        stack["wallet"].address,
        stack["destination"],
        amount,
        now - 1,
        now + 3_600,
        nonce,
    )
    assert stack["wallet"].isValidSignature(
        digest,
        b"ignored-by-rail-wallet",
        sender=USDC_ADDRESS,
    ) == MAGIC
    before = stack["usdc"].balanceOf(stack["destination"])
    stack["usdc"].transferWithAuthorization(
        stack["wallet"].address,
        stack["destination"],
        amount,
        now - 1,
        now + 3_600,
        nonce,
        b"ignored-by-rail-wallet",
        sender=stack["operator"],
    )
    assert stack["usdc"].balanceOf(stack["destination"]) == before + amount
    assert stack["wallet"].reserved(USDC_ADDRESS) == amount
    stack["wallet"].syncExternalPull(commitment_id, sender=stack["operator"])
    assert stack["wallet"].commitment(commitment_id).state == 2
    assert stack["wallet"].reserved(USDC_ADDRESS) == 0


def test_s4_e3_rail_signature_exact_digest_caller_bounds_and_time(
    base_payment_stack,
):
    stack = base_payment_stack
    now = boa.env.evm.patch.timestamp
    commitment_id = keccak(text="base-signature-boundaries")
    nonce = keccak(text="base-signature-boundaries-nonce")
    amount = 10
    authorize(stack, commitment_id, amount, nonce, now - 1, now + 100)
    digest = stack["wallet"].commitment(commitment_id).digest

    assert stack["wallet"].isValidSignature(digest, b"", sender=stack["operator"]) == INVALID
    assert stack["wallet"].isValidSignature(b"\xff" * 32, b"", sender=USDC_ADDRESS) == INVALID
    cancel_struct_hash = keccak(
        encode(
            ["bytes32", "address", "bytes32"],
            [CANCEL_TYPEHASH, stack["wallet"].address, nonce],
        )
    )
    cancellation_digest = keccak(
        b"\x19\x01" + DOMAIN_SEPARATOR + cancel_struct_hash
    )
    assert (
        stack["wallet"].isValidSignature(
            cancellation_digest,
            b"",
            sender=USDC_ADDRESS,
        )
        == INVALID
    )

    selector = keccak(text="isValidSignature(bytes32,bytes)")[:4]
    malformed = selector + digest
    with pytest.raises(Revert):
        boa.env.raw_call(stack["wallet"].address, sender=USDC_ADDRESS, data=malformed)
    oversized = selector + encode(["bytes32", "bytes"], [digest, b"x" * 257])
    with pytest.raises(Revert):
        boa.env.raw_call(stack["wallet"].address, sender=USDC_ADDRESS, data=oversized)

    equal_after_id = keccak(text="equal-valid-after")
    equal_after_nonce = keccak(text="equal-valid-after-nonce")
    authorize(stack, equal_after_id, 1, equal_after_nonce, now, now + 100)
    equal_after_digest = stack["wallet"].commitment(equal_after_id).digest
    assert stack["wallet"].isValidSignature(
        equal_after_digest,
        b"",
        sender=USDC_ADDRESS,
    ) == INVALID

    boa.env.time_travel(seconds=100)
    assert stack["wallet"].isValidSignature(digest, b"", sender=USDC_ADDRESS) == INVALID
    boa.env.time_travel(seconds=1)
    assert stack["wallet"].isValidSignature(digest, b"", sender=USDC_ADDRESS) == INVALID


def test_s4_e4_and_e5_used_unsynced_expiry_unused_expiry_and_replay(
    base_payment_stack,
):
    stack = base_payment_stack
    now = boa.env.evm.patch.timestamp
    used_id = keccak(text="used-unsynced")
    used_nonce = keccak(text="used-unsynced-nonce")
    authorize(stack, used_id, 20, used_nonce, now - 1, now + 10)
    stack["usdc"].transferWithAuthorization(
        stack["wallet"].address,
        stack["destination"],
        20,
        now - 1,
        now + 10,
        used_nonce,
        b"x",
        sender=stack["operator"],
    )
    boa.env.time_travel(seconds=10)
    with boa.reverts():
        stack["wallet"].expireExternalExact(used_id, sender=stack["operator"])
    stack["wallet"].syncExternalPull(used_id, sender=stack["operator"])
    used_digest = stack["wallet"].commitment(used_id).digest
    assert (
        stack["wallet"].isValidSignature(
            used_digest,
            b"",
            sender=USDC_ADDRESS,
        )
        == INVALID
    )
    with boa.reverts():
        authorize(
            stack,
            used_id,
            1,
            keccak(text="used-id-new-nonce"),
            now - 1,
            now + 100,
        )
    with boa.reverts():
        authorize(
            stack,
            keccak(text="used-nonce-new-id"),
            1,
            used_nonce,
            now - 1,
            now + 100,
        )

    unused_id = keccak(text="unused-expiry")
    unused_nonce = keccak(text="unused-expiry-nonce")
    now = boa.env.evm.patch.timestamp
    authorize(stack, unused_id, 20, unused_nonce, now - 1, now + 10)
    with boa.reverts():
        stack["wallet"].expireExternalExact(unused_id, sender=stack["operator"])
    boa.env.time_travel(seconds=10)
    stack["wallet"].expireExternalExact(unused_id, sender=stack["operator"])
    assert stack["wallet"].commitment(unused_id).state == 3
    unused_digest = stack["wallet"].commitment(unused_id).digest
    assert (
        stack["wallet"].isValidSignature(
            unused_digest,
            b"",
            sender=USDC_ADDRESS,
        )
        == INVALID
    )

    with boa.reverts():
        authorize(stack, unused_id, 1, keccak(text="new-nonce"), now - 1, now + 100)
    with boa.reverts():
        authorize(stack, keccak(text="new-id"), 1, unused_nonce, now - 1, now + 100)
    with boa.reverts():
        stack["wallet"].syncExternalPull(unused_id, sender=stack["operator"])


def test_s4_e3_erc165_is_narrow(base_payment_stack):
    wallet = base_payment_stack["wallet"]
    assert wallet.supportsInterface(bytes.fromhex("01ffc9a7"))
    assert wallet.supportsInterface(MAGIC)
    assert not wallet.supportsInterface(bytes.fromhex("ffffffff"))
    assert not wallet.supportsInterface(bytes.fromhex("12345678"))
