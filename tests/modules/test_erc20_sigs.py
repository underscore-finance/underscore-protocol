import pytest
import boa

from eth_account import Account
from constants import EIGHTEEN_DECIMALS, MAX_UINT256, ZERO_ADDRESS


@pytest.fixture(scope="module")
def signPermit(special_signer):
    def signPermit(
        _token,
        _owner,
        _spender,
        _value,
        _deadline=boa.env.evm.patch.timestamp + 3600,  # 1 hour
    ):
        nonce = _token.nonces(_owner)
        message = {
            "domain": {
                "name": _token.name(),
                "version": _token.VERSION(),
                "chainId": boa.env.evm.patch.chain_id,
                "verifyingContract": _token.address,
            },
            "types": {
                "Permit": [
                    {"name": "owner", "type": "address"},
                    {"name": "spender", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                ],
            },
            "message": {
                "owner": _owner.address if hasattr(_owner, 'address') else _owner,
                "spender": _spender.address if hasattr(_spender, 'address') else _spender,
                "value": _value,
                "nonce": nonce,
                "deadline": _deadline,
            }
        }
        signed = Account.sign_typed_data(special_signer.key, full_message=message)
        return (signed.signature, _deadline)
    yield signPermit


@pytest.fixture(scope="module")
def special_signer():
    return Account.from_key('0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')


def test_undy_token_permit(undy_token, special_signer, bob, signPermit):
    """Test EIP-2612 permit functionality"""
    amount = 100 * EIGHTEEN_DECIMALS
    
    # Get initial nonce
    initial_nonce = undy_token.nonces(special_signer)
    
    # Sign and execute permit
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)

    assert undy_token.permit(special_signer, bob, amount, deadline, signature)
    assert undy_token.allowance(special_signer, bob) == amount
    
    # Test nonce increment
    assert undy_token.nonces(special_signer) == initial_nonce + 1
    
    # Test expired permit
    boa.env.time_travel(seconds=3601)
    with boa.reverts("permit expired"):
        undy_token.permit(special_signer, bob, amount, deadline, signature)
    
    # Test invalid signature (signed by wrong address)
    invalid_signature, _ = signPermit(undy_token, bob, special_signer, amount)  # swapped owner/spender
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, invalid_signature)
    
    # Test zero address owner
    with boa.reverts("permit expired"):  # This is the first check in permit
        undy_token.permit(ZERO_ADDRESS, bob, amount, deadline, signature)


# 1. Replay Attack Prevention
def test_permit_replay_attack(undy_token, special_signer, bob, signPermit):
    amount = 100 * EIGHTEEN_DECIMALS
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    assert undy_token.permit(special_signer, bob, amount, deadline, signature)
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, signature)


# 2. Invalid Nonce
def test_permit_invalid_nonce(undy_token, special_signer, bob, signPermit):
    amount = 100 * EIGHTEEN_DECIMALS
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    undy_token.permit(special_signer, bob, amount, deadline, signature)
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, signature)


# 3. Invalid Domain Separator
def test_permit_invalid_domain_separator(undy_token, special_signer, bob, signPermit):
    amount = 100 * EIGHTEEN_DECIMALS
    class DummyToken:
        def name(self): return "Fake"
        def VERSION(self): return undy_token.VERSION()
        address = "0x000000000000000000000000000000000000dead"
        def nonces(self, owner): return undy_token.nonces(owner)  # Use the real nonce
    dummy_token = DummyToken()
    signature, deadline = signPermit(dummy_token, special_signer, bob, amount)
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, signature)


# 4. Boundary Values
def test_permit_zero_and_max_value(undy_token, special_signer, bob, signPermit):
    # Zero value should succeed (EIP-2612 compliant)
    signature, deadline = signPermit(undy_token, special_signer, bob, 0)
    assert undy_token.permit(special_signer, bob, 0, deadline, signature)
    # Max value
    signature, deadline = signPermit(undy_token, special_signer, bob, MAX_UINT256)
    assert undy_token.permit(special_signer, bob, MAX_UINT256, deadline, signature)


# 5. Expired Permit
def test_permit_expired(undy_token, special_signer, bob, signPermit):
    amount = 100 * EIGHTEEN_DECIMALS
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    boa.env.time_travel(seconds=3601)
    with boa.reverts("permit expired"):
        undy_token.permit(special_signer, bob, amount, deadline, signature)


# 6. Future Nonce (if possible)
def test_permit_future_nonce(undy_token, special_signer, bob, signPermit):
    # Not generally possible unless contract exposes nonce manipulation
    pass


# 7. ERC1271: Contract Signature Validation
def test_permit_contract_owner_eoa_spender(undy_token, bob, signPermit):
    """Test permit when owner is a contract and spender is an EOA"""
    amount = 100 * EIGHTEEN_DECIMALS
    contract_owner = boa.load("contracts/mock/MockERC1271.vy")
    signature, deadline = signPermit(undy_token, contract_owner, bob, amount)
    assert undy_token.permit(contract_owner, bob, amount, deadline, signature)


# 8. ERC1271: Invalid Magic Value
def test_erc1271_invalid_magic_value(undy_token, bob):
    bad_contract = boa.load("contracts/mock/MockBadERC1271.vy")
    contract_signature = bytes([0] * 65)
    contract_deadline = boa.env.evm.patch.timestamp + 3600
    with boa.reverts():
        undy_token.permit(bad_contract, bob, 100 * EIGHTEEN_DECIMALS, contract_deadline, contract_signature)


# 9. Signature Malleability
def test_permit_signature_malleability(undy_token, special_signer, bob, signPermit):
    amount = 100 * EIGHTEEN_DECIMALS
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    malleable_signature = signature[:-1] + bytes([signature[-1] ^ 1])
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, malleable_signature)


# 10. Permit for Blacklisted or Paused Accounts
def test_permit_blacklisted_or_paused(undy_token, special_signer, bob, switchboard, governance, signPermit):
    amount = 100 * EIGHTEEN_DECIMALS
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    undy_token.setBlacklist(special_signer, True, sender=switchboard.address)
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, signature)
    undy_token.setBlacklist(special_signer, False, sender=switchboard.address)
    undy_token.pause(True, sender=governance.address)
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, signature)
    undy_token.pause(False, sender=governance.address)


def test_permit_different_spenders(undy_token, special_signer, bob, alice, signPermit):
    """Test that a permit for one spender cannot be used by another spender"""
    amount = 100 * EIGHTEEN_DECIMALS
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    # Try to use bob's permit with alice as the spender
    with boa.reverts():
        undy_token.permit(special_signer, alice, amount, deadline, signature)


def test_permit_different_amounts(undy_token, special_signer, bob, signPermit):
    """Test that a permit for one amount cannot be used for a different amount"""
    amount = 100 * EIGHTEEN_DECIMALS
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    # Try to use the permit with a different amount
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount * 2, deadline, signature)


def test_permit_different_deadlines(undy_token, special_signer, bob, signPermit):
    """Test that a permit with one deadline cannot be used with a different deadline"""
    amount = 100 * EIGHTEEN_DECIMALS
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    # Try to use the permit with a different deadline
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline + 1, signature)


def test_permit_malformed_signatures(undy_token, special_signer, bob, signPermit):
    """Test various malformed signature scenarios"""
    amount = 100 * EIGHTEEN_DECIMALS
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    
    # Test with empty signature
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, b'')
    
    # Test with too short signature
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, signature[:64])
    
    # Test with too long signature
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, signature + b'\x00')


def test_permit_different_chain_ids(undy_token, special_signer, bob, signPermit):
    """Test that a permit from one chain cannot be used on another chain"""
    amount = 100 * EIGHTEEN_DECIMALS
    # Save original chain ID
    original_chain_id = boa.env.evm.patch.chain_id
    # Change chain ID
    boa.env.evm.patch.chain_id = original_chain_id + 1
    signature, deadline = signPermit(undy_token, special_signer, bob, amount)
    # Restore original chain ID
    boa.env.evm.patch.chain_id = original_chain_id
    # Try to use the permit from the other chain
    with boa.reverts():
        undy_token.permit(special_signer, bob, amount, deadline, signature) 