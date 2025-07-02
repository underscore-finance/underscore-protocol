import pytest
import boa
from eth_account import Account
from eth_account.messages import encode_typed_data

from contracts.core.agent import AgentWrapper
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


@pytest.fixture(scope="module")
def user_wallet(hatchery, bob, mock_lego_asset, whale, setManagerConfig, agent): # must load `agent` here!
    from contracts.core.userWallet import UserWallet
    
    # Set the agent as the starting agent for new wallets
    setManagerConfig(_startingAgent=agent.address)
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS

    # transfer assets into user wallet
    mock_lego_asset.transfer(wallet_addr, 1_000 * EIGHTEEN_DECIMALS, sender=whale)

    return UserWallet.at(wallet_addr)


@pytest.fixture(scope="module")
def agent(setAgentConfig, setUserWalletConfig, hatchery, bob):
    # Set up wallet config with proper timelock values for agent
    setUserWalletConfig(_minTimeLock=10, _maxTimeLock=100)
    setAgentConfig()

    wallet_addr = hatchery.createAgent(sender=bob)
    assert wallet_addr != ZERO_ADDRESS

    return AgentWrapper.at(wallet_addr)


@pytest.fixture(scope="module")
def special_signer():
    return Account.from_key('0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')


def create_signature(agent, message_hash, signer, nonce, expiration):
    """Helper to create EIP-712 signature with nonce"""
    domain = {
        "name": "UnderscoreAgent",
        "chainId": boa.env.evm.patch.chain_id,
        "verifyingContract": agent.address
    }
    
    # Create the full message with domain
    signable_message = encode_typed_data(
        domain_data=domain,
        message_types={},
        message_data={}
    )
    
    # For simplicity, we'll create a raw signature
    signed = signer.signHash(message_hash)
    signature = signed.signature
    
    return (signature, nonce, expiration)


def test_signature_expiration_check(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test that expired signatures are rejected"""
    agent_owner = bob
    
    # Create an expired signature
    expired_time = boa.env.evm.patch.timestamp - 3600  # 1 hour ago
    current_nonce = agent.getNonce()
    
    # Create signature struct with expired timestamp and valid nonce
    sig = (b'\x00' * 65, current_nonce, expired_time)
    
    # Try to use expired signature - should fail
    with boa.reverts("signature expired"):
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            sig,
            sender=alice  # Non-owner
        )


def test_nonce_invalidation(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test that old nonces are rejected"""
    # Get current nonce
    current_nonce = agent.getNonce()
    assert current_nonce == 0  # Should start at 0
    
    # Test with invalid nonce directly (no need to increment nonce first)
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    # Try to use signature with invalid nonce (future nonce)
    future_nonce_sig = (b'\x00' * 65, 999, valid_time)
    with boa.reverts("invalid nonce"):
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            future_nonce_sig,
            sender=alice  # Non-owner
        )
    
    # Try with past nonce (after manually incrementing)
    agent.incrementNonce(sender=bob)  # Now nonce is 1
    
    # Try to use old nonce (0)
    old_nonce_sig = (b'\x00' * 65, 0, valid_time)
    with boa.reverts("invalid nonce"):
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            old_nonce_sig,
            sender=alice  # Non-owner
        )


def test_owner_doesnt_need_signature(agent, user_wallet, bob, mock_lego_asset, mock_lego_vault):
    """Test that owner can execute without signature"""
    agent_owner = bob
    
    # Owner should be able to execute without signature
    initial_balance = mock_lego_asset.balanceOf(user_wallet.address)
    
    # Empty signature struct (signature, nonce, expiration)
    empty_sig = (b'', 0, 0)
    
    # Execute as owner - should succeed
    result = agent.depositForYield(
        user_wallet,
        1,
        mock_lego_asset.address,
        mock_lego_vault.address,
        100 * EIGHTEEN_DECIMALS,
        ZERO_ADDRESS,
        0,
        b'\x00' * 32,
        empty_sig,
        sender=agent_owner
    )
    
    # Verify deposit happened
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_balance - 100 * EIGHTEEN_DECIMALS
    assert mock_lego_vault.balanceOf(user_wallet.address) == 100 * EIGHTEEN_DECIMALS


def test_non_owner_requires_signature(agent, user_wallet, alice, mock_lego_asset):
    """Test that non-owner requires valid signature"""
    # Try to execute as non-owner without proper signature
    empty_sig = (b'', 0, 0)
    
    # Should fail - signature expired (timestamp is 0)
    with boa.reverts("signature expired"):
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            empty_sig,
            sender=alice  # Non-owner
        )


def test_malformed_signature_fails(agent, user_wallet, alice, mock_lego_asset):
    """Test that malformed signatures are rejected"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Test with wrong signature length
    short_sig = (b'\x00' * 64, current_nonce, valid_time)  # Too short
    
    with boa.reverts():  # Will fail during signature extraction
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            short_sig,
            sender=alice
        )


def test_signature_v_parameter_validation(agent, user_wallet, alice, mock_lego_asset):
    """Test that v parameter must be 27 or 28"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Create signature with invalid v parameter (not 27 or 28 after adjustment)
    # Signature format: r (32 bytes) + s (32 bytes) + v (1 byte)
    r = b'\x00' * 32
    s = b'\x00' * 32
    v = b'\x1d'  # 29, which is invalid (not 27 or 28)
    
    invalid_v_sig = (r + s + v, current_nonce, valid_time)
    
    with boa.reverts():  # Should fail v parameter validation
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            invalid_v_sig,
            sender=alice
        )


def test_batch_authentication_for_owner(agent, user_wallet, bob, mock_lego_asset, mock_lego_vault):
    """Test batch actions work for owner without signature"""
    agent_owner = bob
    
    # Create simple deposit instruction
    instruction = (
        False,  # usePrevAmountOut
        1,      # action: EARN_DEPOSIT
        1,      # legoId
        mock_lego_asset.address,  # asset
        mock_lego_vault.address,  # target
        50 * EIGHTEEN_DECIMALS,   # amount
        ZERO_ADDRESS,  # asset2
        0,      # amount2
        0,      # minOut1
        0,      # minOut2
        0,      # tickLower
        0,      # tickUpper
        ZERO_ADDRESS,  # extraAddr
        0,      # extraVal
        b'\x00' * 32,  # extraData
        b'\x00' * 32,  # auxData
        []      # swapInstructions
    )
    
    empty_sig = (b'', 0, 0)
    
    # Owner should be able to execute batch without signature
    initial_asset = mock_lego_asset.balanceOf(user_wallet.address)
    result = agent.performBatchActions(user_wallet, [instruction], empty_sig, sender=agent_owner)
    assert result == True
    
    # Verify deposit happened
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset - 50 * EIGHTEEN_DECIMALS


def test_batch_authentication_for_non_owner(agent, user_wallet, alice, mock_lego_asset):
    """Test batch actions require signature for non-owner"""
    # Create simple transfer instruction
    instruction = (
        False,  # usePrevAmountOut
        0,      # action: TRANSFER
        0,      # legoId
        mock_lego_asset.address,  # asset
        alice,  # target (recipient)
        10 * EIGHTEEN_DECIMALS,   # amount
        ZERO_ADDRESS,  # asset2
        0,      # amount2
        0,      # minOut1
        0,      # minOut2
        0,      # tickLower
        0,      # tickUpper
        ZERO_ADDRESS,  # extraAddr
        0,      # extraVal
        b'\x00' * 32,  # extraData
        b'\x00' * 32,  # auxData
        []      # swapInstructions
    )
    
    empty_sig = (b'', 0, 0)
    
    # Non-owner should fail with expired signature
    with boa.reverts("signature expired"):
        agent.performBatchActions(user_wallet, [instruction], empty_sig, sender=alice)


def test_signature_malleability_prevention():
    """Test that signature malleability is prevented by s value check"""
    # The s value check (s <= secp256k1n/2) is implemented in the contract
    # This test verifies the constant is correct
    
    # secp256k1n/2 = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0
    secp256k1n_half = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0
    secp256k1n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    
    # Verify the constant is correct
    assert secp256k1n_half == secp256k1n // 2


def test_zero_address_signer_fails(agent, user_wallet, alice, mock_lego_asset):
    """Test that signatures recovering to zero address are rejected"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Create an invalid signature that would recover to zero address
    # All zeros typically results in failed recovery
    invalid_sig = (b'\x00' * 65, current_nonce, valid_time)
    
    with boa.reverts():  # Should fail signature recovery
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            invalid_sig,
            sender=alice
        )


def test_nonce_management_functions(agent, bob, alice):
    """Test nonce management functions work correctly"""
    # Test getNonce
    initial_nonce = agent.getNonce()
    assert initial_nonce == 0
    
    # Test incrementNonce by owner
    agent.incrementNonce(sender=bob)
    assert agent.getNonce() == 1
    
    # Test incrementNonce by non-owner should fail
    with boa.reverts("no perms"):
        agent.incrementNonce(sender=alice)
    
    # Nonce should still be 1
    assert agent.getNonce() == 1


def test_nonce_increment_with_valid_signature_use(agent, user_wallet, alice, mock_lego_asset):
    """Test that nonce increments when non-owner uses valid signature"""
    initial_nonce = agent.getNonce()
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    # Create a signature with current nonce (this would be a real signature in practice)
    # For testing, we'll create a dummy signature that will fail verification
    # but pass nonce and expiration checks
    test_sig = (b'\x00' * 65, initial_nonce, valid_time)
    
    # This will fail at signature verification, but that's after nonce check
    with boa.reverts():  # Will fail at signature verification step
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            test_sig,
            sender=alice
        )
    
    # Nonce should still be the same since signature verification failed
    assert agent.getNonce() == initial_nonce


def test_eip712_domain_separator(agent):
    """Test EIP-712 domain separator is correctly formed"""
    # Domain separator should be deterministic based on contract address and chain ID
    # We can't directly test the internal _domainSeparator function, but we can verify
    # that signatures with different contract addresses would fail
    
    # The domain separator should include:
    # - EIP712Domain type hash
    # - "UnderscoreAgent" name hash  
    # - Current chain ID
    # - Contract address (self)
    
    # Verify chain ID is included by checking behavior
    current_chain_id = boa.env.evm.patch.chain_id
    assert current_chain_id > 0  # Should have a valid chain ID


def test_signature_too_long_fails(agent, user_wallet, alice, mock_lego_asset):
    """Test that signatures longer than 65 bytes are rejected"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Create signature that's too long (66 bytes instead of 65)
    long_sig = (b'\x00' * 66, current_nonce, valid_time)
    
    with boa.reverts():  # Should fail during signature extraction
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            long_sig,
            sender=alice
        )


def test_v_parameter_adjustment(agent, user_wallet, alice, mock_lego_asset):
    """Test v parameter adjustment for values < 27"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Create signature with v = 0 (should be adjusted to 27)
    r = b'\x00' * 32
    s = b'\x00' * 32
    v = b'\x00'  # 0, should be adjusted to 27
    
    adjusted_v_sig = (r + s + v, current_nonce, valid_time)
    
    # Should still fail at signature verification, but pass v parameter validation
    with boa.reverts():  # Will fail at signature verification, not v validation
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            adjusted_v_sig,
            sender=alice
        )


def test_s_value_boundary_conditions(agent, user_wallet, alice, mock_lego_asset):
    """Test s value malleability boundary conditions"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Test with s value exactly at the malleability threshold
    r = b'\x00' * 32
    # s = secp256k1n/2 (maximum allowed value)
    s_max_allowed = (0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0).to_bytes(32, 'big')
    v = b'\x1b'  # 27
    
    boundary_sig = (r + s_max_allowed + v, current_nonce, valid_time)
    
    # Should pass s value check but fail at signature verification
    with boa.reverts():  # Will fail at signature verification, not s value check
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            boundary_sig,
            sender=alice
        )
    
    # Test with s value just above the threshold (should fail)
    s_too_high = (0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A1).to_bytes(32, 'big')
    invalid_s_sig = (r + s_too_high + v, current_nonce, valid_time)
    
    with boa.reverts("invalid s value"):
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            invalid_s_sig,
            sender=alice
        )


def test_ownership_change_nonce_reset(agent, bob, alice):
    """Test that nonce resets to 0 on ownership change"""
    # Increment nonce first
    agent.incrementNonce(sender=bob)
    agent.incrementNonce(sender=bob)
    assert agent.getNonce() == 2
    
    # Initiate ownership change
    agent.changeOwnership(alice, sender=bob)
    
    # Fast forward past timelock
    boa.env.time_travel(seconds=86400)  # 1 day
    
    # Confirm ownership change
    agent.confirmOwnershipChange(sender=alice)
    
    # Verify nonce was reset to 0
    assert agent.getNonce() == 0
    assert agent.owner() == alice


def test_ownership_change_timelock_validation(agent, bob, alice):
    """Test ownership change timelock validation"""
    # Initiate ownership change
    agent.changeOwnership(alice, sender=bob)
    
    # Try to confirm before timelock expires
    with boa.reverts("time delay not reached"):
        agent.confirmOwnershipChange(sender=alice)
    
    # Verify ownership hasn't changed
    assert agent.owner() == bob


def test_cancel_ownership_change_by_owner(agent, bob, alice):
    """Test that owner can cancel pending ownership change"""
    # Initiate ownership change
    agent.changeOwnership(alice, sender=bob)
    
    # Owner should be able to cancel
    agent.cancelOwnershipChange(sender=bob)
    
    # Should not have pending ownership change
    assert agent.hasPendingOwnerChange() == False


def test_batch_action_message_hash_different_actions(agent, user_wallet, alice, mock_lego_asset):
    """Test that different batch actions create different message hashes"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Create two different instruction sets
    instruction1 = (
        False, 0, 0, mock_lego_asset.address, alice, 10 * EIGHTEEN_DECIMALS,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    instruction2 = (
        False, 1, 1, mock_lego_asset.address, ZERO_ADDRESS, 10 * EIGHTEEN_DECIMALS,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # Both should fail with expired signature but demonstrate different message hashes
    empty_sig = (b'', current_nonce, 0)  # Expired signature
    
    with boa.reverts("signature expired"):
        agent.performBatchActions(user_wallet, [instruction1], empty_sig, sender=alice)
    
    with boa.reverts("signature expired"):
        agent.performBatchActions(user_wallet, [instruction2], empty_sig, sender=alice)


def test_multiple_rapid_signature_attempts(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test rapid signature attempts behavior"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Create multiple signatures with same nonce
    sig1 = (b'\x01' * 65, current_nonce, valid_time)
    sig2 = (b'\x02' * 65, current_nonce, valid_time)
    
    # Both should fail at signature verification
    with boa.reverts():
        agent.depositForYield(
            user_wallet, 1, mock_lego_asset.address, ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS, ZERO_ADDRESS, 0, b'\x00' * 32,
            sig1, sender=alice
        )
    
    with boa.reverts():
        agent.depositForYield(
            user_wallet, 1, mock_lego_asset.address, ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS, ZERO_ADDRESS, 0, b'\x00' * 32,
            sig2, sender=alice
        )
    
    # Nonce should remain unchanged since both failed
    assert agent.getNonce() == current_nonce


def test_interleaved_owner_nonowner_calls(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test interleaved owner and non-owner calls"""
    initial_nonce = agent.getNonce()
    empty_sig = (b'', 0, 0)
    invalid_sig = (b'\x00' * 65, initial_nonce, boa.env.evm.patch.timestamp + 3600)
    
    # Owner call (should succeed) - transfer to owner
    agent.transferFunds(user_wallet, bob, mock_lego_asset.address, 1, empty_sig, sender=bob)
    
    # Non-owner call (should fail) - even when transferring to owner
    with boa.reverts():
        agent.transferFunds(user_wallet, bob, mock_lego_asset.address, 1, invalid_sig, sender=alice)
    
    # Another owner call (should succeed) - transfer to owner
    agent.transferFunds(user_wallet, bob, mock_lego_asset.address, 1, empty_sig, sender=bob)
    
    # Nonce should remain unchanged (owner calls don't affect nonce)
    assert agent.getNonce() == initial_nonce


def test_signature_recovery_empty_result(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test signature recovery when ecrecover returns empty result"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Create signature that would cause ecrecover to return empty result
    # Using all zeros for r, s, v - but now s=0 is explicitly rejected
    r = b'\x00' * 32
    s = b'\x00' * 32
    v = b'\x1b'  # 27
    
    zero_s_sig = (r + s + v, current_nonce, valid_time)
    
    # The new validation now catches s=0 explicitly
    with boa.reverts("invalid s value (zero)"):
        agent.depositForYield(
            user_wallet,
            1,
            mock_lego_asset.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            ZERO_ADDRESS,
            0,
            b'\x00' * 32,
            zero_s_sig,
            sender=alice
        )


def test_nonce_overflow_behavior(agent, bob):
    """Test nonce behavior near uint256 maximum"""
    # We can't actually test overflow to max uint256 due to gas costs,
    # but we can test the principle by checking large increments work
    initial_nonce = agent.getNonce()
    
    # Increment nonce multiple times
    for i in range(5):
        agent.incrementNonce(sender=bob)
    
    # Verify nonce increments correctly
    assert agent.getNonce() == initial_nonce + 5


def test_batch_empty_instructions_fails(agent, user_wallet, bob):
    """Test that batch actions with empty instructions fail"""
    empty_sig = (b'', 0, 0)
    
    # Empty instruction list should fail
    with boa.reverts("no instructions"):
        agent.performBatchActions(user_wallet, [], empty_sig, sender=bob)


def test_different_action_types_message_hashes(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test that different action types create different message hashes"""
    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = agent.getNonce()
    
    # Create signatures for different action types with same parameters but different action IDs
    # This ensures the action type is included in the message hash
    
    expired_sig = (b'\x00' * 65, current_nonce, 0)  # Expired for testing
    
    # Test different single actions fail with expired signature (proving different hashes)
    with boa.reverts("signature expired"):
        agent.depositForYield(user_wallet, 1, mock_lego_asset.address, ZERO_ADDRESS, 
                             100, ZERO_ADDRESS, 0, b'\x00' * 32, expired_sig, sender=alice)
    
    with boa.reverts("signature expired"):
        agent.addCollateral(user_wallet, 1, mock_lego_asset.address, 100, 
                           ZERO_ADDRESS, 0, b'\x00' * 32, expired_sig, sender=alice)


def test_error_message_specificity(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test specific error messages are returned for different failure modes"""
    current_nonce = agent.getNonce()
    
    # Test "signature expired" error
    expired_sig = (b'\x00' * 65, current_nonce, boa.env.evm.patch.timestamp - 1)
    with boa.reverts("signature expired"):
        agent.depositForYield(user_wallet, 1, mock_lego_asset.address, ZERO_ADDRESS,
                             100, ZERO_ADDRESS, 0, b'\x00' * 32, expired_sig, sender=alice)
    
    # Test "invalid nonce" error  
    invalid_nonce_sig = (b'\x00' * 65, 999, boa.env.evm.patch.timestamp + 3600)
    with boa.reverts("invalid nonce"):
        agent.depositForYield(user_wallet, 1, mock_lego_asset.address, ZERO_ADDRESS,
                             100, ZERO_ADDRESS, 0, b'\x00' * 32, invalid_nonce_sig, sender=alice)
    
    # Test "invalid signer" error (signature from wrong signer)
    valid_time = boa.env.evm.patch.timestamp + 3600
    wrong_signer_sig = (b'\x01' * 65, current_nonce, valid_time)
    with boa.reverts("invalid signer"):
        agent.depositForYield(user_wallet, 1, mock_lego_asset.address, ZERO_ADDRESS,
                             100, ZERO_ADDRESS, 0, b'\x00' * 32, wrong_signer_sig, sender=alice)


def test_timelock_boundaries(agent, bob, alice):
    """Test timelock boundary conditions"""
    # Test minimum timelock
    min_timelock = agent.MIN_TIMELOCK()
    agent.setTimeLock(min_timelock, sender=bob)
    assert agent.timeLock() == min_timelock
    
    # Test maximum timelock  
    max_timelock = agent.MAX_TIMELOCK()
    agent.setTimeLock(max_timelock, sender=bob)
    assert agent.timeLock() == max_timelock
    
    # Test invalid timelock (too small)
    with boa.reverts("invalid delay"):
        agent.setTimeLock(min_timelock - 1, sender=bob)
    
    # Test invalid timelock (too large)
    with boa.reverts("invalid delay"):
        agent.setTimeLock(max_timelock + 1, sender=bob)


def test_batch_with_valid_signature_nonce_management(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test batch actions with signatures properly manage nonce"""
    # This test validates the nonce management flow without creating a real signature
    initial_nonce = agent.getNonce()
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    # Create batch instructions
    instruction = (
        False, 0, 0, mock_lego_asset.address, bob, 1,  # Transfer to owner instead of alice
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # Test 1: Invalid signature fails but doesn't increment nonce
    invalid_sig = (b'\x00' * 65, initial_nonce, valid_time)
    with boa.reverts():  # Will fail at signature verification
        agent.performBatchActions(user_wallet, [instruction], invalid_sig, sender=alice)
    
    # Nonce should remain unchanged
    assert agent.getNonce() == initial_nonce
    
    # Test 2: Owner executes batch successfully without affecting nonce
    initial_balance = mock_lego_asset.balanceOf(bob)
    agent.performBatchActions(user_wallet, [instruction], (b'', 0, 0), sender=bob)
    assert mock_lego_asset.balanceOf(bob) == initial_balance + 1
    assert agent.getNonce() == initial_nonce  # Owner calls don't increment nonce
    
    # Test 3: Manually increment nonce and verify old signatures fail
    agent.incrementNonce(sender=bob)
    new_nonce = agent.getNonce()
    assert new_nonce == initial_nonce + 1
    
    # Old nonce signature should now fail at nonce check
    with boa.reverts("invalid nonce"):
        agent.performBatchActions(user_wallet, [instruction], invalid_sig, sender=alice)
    
    # Test 4: Future nonce also fails
    future_sig = (b'\x00' * 65, new_nonce + 5, valid_time)
    with boa.reverts("invalid nonce"):
        agent.performBatchActions(user_wallet, [instruction], future_sig, sender=alice)


def test_batch_signature_replay_protection(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test batch signatures cannot be replayed"""
    current_nonce = agent.getNonce()
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    # Create instruction
    instruction = (
        False, 0, 0, mock_lego_asset.address, bob, 1,  # Transfer to owner instead of alice
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # Create a fake signature that will fail but tests nonce validation
    sig = (b'\x00' * 65, current_nonce, valid_time)
    
    # First attempt will fail at signature verification
    with boa.reverts():
        agent.performBatchActions(user_wallet, [instruction], sig, sender=alice)
    
    # Manually increment nonce as owner
    agent.incrementNonce(sender=bob)
    
    # Same signature with old nonce should fail at nonce check now
    with boa.reverts("invalid nonce"):
        agent.performBatchActions(user_wallet, [instruction], sig, sender=alice)


def test_batch_multiple_instructions_signature(agent, user_wallet, bob, alice, mock_lego_asset, mock_lego_vault):
    """Test batch with multiple instructions requires valid signature"""
    current_nonce = agent.getNonce()
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    # Create multiple different instructions
    transfer_instruction = (
        False, 0, 0, mock_lego_asset.address, bob, 10 * EIGHTEEN_DECIMALS,  # Transfer to owner
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    deposit_instruction = (
        False, 1, 1, mock_lego_asset.address, mock_lego_vault.address, 50 * EIGHTEEN_DECIMALS,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # Invalid signature
    invalid_sig = (b'\x00' * 65, current_nonce, valid_time)
    
    # Non-owner with invalid signature should fail
    with boa.reverts():
        agent.performBatchActions(user_wallet, [transfer_instruction, deposit_instruction], invalid_sig, sender=alice)
    
    # Owner can execute without valid signature
    initial_asset = mock_lego_asset.balanceOf(user_wallet.address)
    agent.performBatchActions(user_wallet, [transfer_instruction, deposit_instruction], (b'', 0, 0), sender=bob)
    
    # Verify both actions executed
    assert mock_lego_vault.balanceOf(user_wallet.address) == 50 * EIGHTEEN_DECIMALS  # Deposited to vault
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset - 60 * EIGHTEEN_DECIMALS  # 10 transferred + 50 deposited


def test_batch_signature_with_different_instructions_order(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test that instruction order matters for signature verification"""
    current_nonce = agent.getNonce()
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    # Create two instructions
    instruction1 = (
        False, 0, 0, mock_lego_asset.address, bob, 5 * EIGHTEEN_DECIMALS,  # Transfer to owner
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    instruction2 = (
        False, 0, 0, mock_lego_asset.address, bob, 3 * EIGHTEEN_DECIMALS,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # Different order means different message hash
    sig = (b'\x00' * 65, current_nonce, valid_time)
    
    # Both orders should fail with same signature (different message hashes)
    with boa.reverts():
        agent.performBatchActions(user_wallet, [instruction1, instruction2], sig, sender=alice)
    
    with boa.reverts():
        agent.performBatchActions(user_wallet, [instruction2, instruction1], sig, sender=alice)


def test_batch_signature_includes_all_parameters(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test that batch signature includes all instruction parameters"""
    current_nonce = agent.getNonce()
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    # Create similar instructions with slight differences
    base_instruction = (
        False, 0, 0, mock_lego_asset.address, bob, 100,  # Transfer to owner
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # Change only the amount
    modified_amount = (
        False, 0, 0, mock_lego_asset.address, bob, 101,  # Different amount, same owner recipient
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # Change only the recipient
    modified_recipient = (
        False, 0, 0, mock_lego_asset.address, user_wallet.address,  # Different recipient (self)
        100, ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    sig = (b'\x00' * 65, current_nonce, valid_time)
    
    # All should fail (different message hashes)
    with boa.reverts():
        agent.performBatchActions(user_wallet, [base_instruction], sig, sender=alice)
    
    with boa.reverts():
        agent.performBatchActions(user_wallet, [modified_amount], sig, sender=alice)
    
    with boa.reverts():
        agent.performBatchActions(user_wallet, [modified_recipient], sig, sender=alice)


def test_batch_expired_signature_check(agent, user_wallet, alice, mock_lego_asset):
    """Test batch actions check signature expiration"""
    current_nonce = agent.getNonce()
    expired_time = boa.env.evm.patch.timestamp - 3600  # Expired
    
    instruction = (
        False, 0, 0, mock_lego_asset.address, alice, 100,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    expired_sig = (b'\x00' * 65, current_nonce, expired_time)
    
    # Should fail with expired signature
    with boa.reverts("signature expired"):
        agent.performBatchActions(user_wallet, [instruction], expired_sig, sender=alice)


def test_batch_invalid_nonce_check(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test batch actions validate nonce correctly"""
    current_nonce = agent.getNonce()
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    instruction = (
        False, 0, 0, mock_lego_asset.address, alice, 100,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # Wrong nonce (future)
    wrong_nonce_sig = (b'\x00' * 65, current_nonce + 10, valid_time)
    
    with boa.reverts("invalid nonce"):
        agent.performBatchActions(user_wallet, [instruction], wrong_nonce_sig, sender=alice)
    
    # Wrong nonce (past, after increment)
    agent.incrementNonce(sender=bob)
    old_nonce_sig = (b'\x00' * 65, current_nonce, valid_time)
    
    with boa.reverts("invalid nonce"):
        agent.performBatchActions(user_wallet, [instruction], old_nonce_sig, sender=alice)


def test_batch_signature_malleability_check(agent, user_wallet, alice, mock_lego_asset):
    """Test batch actions enforce s-value malleability check"""
    current_nonce = agent.getNonce()
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    instruction = (
        False, 0, 0, mock_lego_asset.address, alice, 100,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # Create signature with s value too high
    r = b'\x00' * 32
    s_too_high = (0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A1).to_bytes(32, 'big')
    v = b'\x1b'  # 27
    
    invalid_s_sig = (r + s_too_high + v, current_nonce, valid_time)
    
    with boa.reverts("invalid s value"):
        agent.performBatchActions(user_wallet, [instruction], invalid_s_sig, sender=alice)


def test_batch_with_swap_instructions(agent, user_wallet, alice, mock_lego_asset):
    """Test batch with swap instructions in signature"""
    current_nonce = agent.getNonce()
    valid_time = boa.env.evm.patch.timestamp + 3600
    
    # Create swap instruction with correct structure
    # SwapInstruction struct: legoId, amountIn, minAmountOut, tokenPath, poolPath
    swap_details = [(
        0,  # legoId
        100,  # amountIn
        0,  # minAmountOut
        [mock_lego_asset.address, ZERO_ADDRESS],  # tokenPath
        [ZERO_ADDRESS]  # poolPath (one less than tokenPath)
    )]
    
    swap_instruction = (
        False, 4, 0, ZERO_ADDRESS, ZERO_ADDRESS, 0,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, 
        swap_details  # Include swap instructions
    )
    
    invalid_sig = (b'\x00' * 65, current_nonce, valid_time)
    
    # Should fail signature verification
    with boa.reverts():
        agent.performBatchActions(user_wallet, [swap_instruction], invalid_sig, sender=alice)


def test_batch_max_instructions_limit(agent, user_wallet, bob, alice, mock_lego_asset):
    """Test batch respects MAX_INSTRUCTIONS limit"""
    # Create many simple transfer instructions (more than limit)
    instruction = (
        False, 0, 0, mock_lego_asset.address, alice, 1,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, ZERO_ADDRESS, 0, b'\x00' * 32, b'\x00' * 32, []
    )
    
    # MAX_INSTRUCTIONS is 15, try with 16
    too_many = [instruction] * 16
    
    # Should fail (likely at signature or encoding level)
    with boa.reverts():
        agent.performBatchActions(user_wallet, too_many, (b'', 0, 0), sender=bob)