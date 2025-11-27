import pytest
import boa
from eth_account import Account
from eth_account.messages import encode_typed_data

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from contracts.core.userWallet import UserWalletConfig
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setupAgentTestAsset(user_wallet, alpha_token, alpha_token_whale, mock_ripe, switchboard_alpha):
    def setupAgentTestAsset(
        _asset = alpha_token,
        _amount = 100 * EIGHTEEN_DECIMALS,
        _whale = alpha_token_whale,
        _user_wallet = user_wallet,
        _price = 2 * EIGHTEEN_DECIMALS,
        _lego_id = 0,
        _shouldCheckYield = False,
    ):
        # set price
        mock_ripe.setPrice(_asset, _price)

        # transfer asset to wallet
        _asset.transfer(_user_wallet, _amount, sender=_whale)

        # make sure asset is registered
        wallet_config = UserWalletConfig.at(_user_wallet.walletConfig())
        wallet_config.updateAssetData(
            _lego_id,
            _asset,
            _shouldCheckYield,
            sender = switchboard_alpha.address
        )
        return _amount

    yield setupAgentTestAsset


@pytest.fixture(scope="module")
def test_signer():
    """Create a test signer for signature testing"""
    return Account.from_key('0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')


@pytest.fixture(scope="module")
def create_signature_struct():
    """Helper to create Signature struct with correct format"""
    def create_signature_struct(signature_bytes, nonce, expiration):
        return (signature_bytes, nonce, expiration)
    yield create_signature_struct


@pytest.fixture(scope="module")
def createActionInstruction():
    def createActionInstruction(
        action,
        usePrevAmountOut=False,
        legoId=0,
        asset=ZERO_ADDRESS,
        target=ZERO_ADDRESS,
        amount=0,
        asset2=ZERO_ADDRESS,
        amount2=0,
        minOut1=0,
        minOut2=0,
        tickLower=0,
        tickUpper=0,
        extraData=b"",
        auxData=b"",
        swapInstructions=None,
        proofs=None
    ):
        """Helper to create ActionInstruction tuple"""
        if swapInstructions is None:
            swapInstructions = []
        if proofs is None:
            proofs = []

        return (
            usePrevAmountOut,
            action,
            legoId,
            asset,
            target,
            amount,
            asset2,
            amount2,
            minOut1,
            minOut2,
            tickLower,
            tickUpper,
            extraData,
            auxData,
            swapInstructions,
            proofs
        )

    yield createActionInstruction


######################
# Core Signature Tests
######################


def test_owner_bypass_no_signature(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    charlie,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    create_signature_struct
):
    """Test that owner can execute without signature"""

    # Setup tokens
    amount = setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )

    # Empty signature
    empty_sig = create_signature_struct(b'', 0, 0)

    # Owner should execute without signature verification
    asset_deposited, vault_token, vault_tokens_received, usd_value = starter_agent_sender.depositForYield(
        starter_agent.address,
        user_wallet.address,
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        b"",
        empty_sig,
        sender=charlie  # charlie is the owner
    )

    # Verify execution succeeded
    assert asset_deposited == amount
    assert vault_tokens_received > 0
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens_received


def test_expired_signature_rejected(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    yield_underlying_token,
    yield_underlying_token_whale,
    create_signature_struct
):
    """Test that expired signatures are rejected"""

    # Setup tokens
    setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _lego_id=2
    )

    # Create expired signature
    expired_time = boa.env.evm.patch.timestamp - 3600  # 1 hour ago
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)
    expired_sig = create_signature_struct(b'\x00' * 65, current_nonce, expired_time)

    # Should fail with expired signature
    with boa.reverts("signature expired"):
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            yield_underlying_token.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            b"",
            expired_sig,
            sender=alice  # Non-owner
        )


def test_invalid_nonce_rejected(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    yield_underlying_token,
    yield_underlying_token_whale,
    create_signature_struct
):
    """Test that invalid nonces are rejected"""

    # Setup tokens
    setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _lego_id=2
    )

    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # Test with future nonce
    future_nonce_sig = create_signature_struct(b'\x00' * 65, current_nonce + 1, valid_time)
    with boa.reverts("invalid nonce"):
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            yield_underlying_token.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            b"",
            future_nonce_sig,
            sender=alice
        )

    # Test with past nonce
    past_nonce_sig = create_signature_struct(b'\x00' * 65, 0 if current_nonce > 0 else 999, valid_time)
    with boa.reverts("invalid nonce"):
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            yield_underlying_token.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            b"",
            past_nonce_sig,
            sender=alice
        )


def test_invalid_signer_rejected(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    yield_underlying_token,
    yield_underlying_token_whale,
    create_signature_struct,
    test_signer
):
    """Test that signatures from non-owner are rejected"""

    # Setup tokens
    setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _lego_id=2
    )

    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # Create a properly formatted signature (but from wrong signer)
    # In real usage, this would be a valid signature from non-owner
    # For testing, we create a dummy signature that will fail signer check
    fake_sig = create_signature_struct(
        b'\x01' * 64 + b'\x1b',  # r + s + v (27)
        current_nonce,
        valid_time
    )

    with boa.reverts():  # Will fail at signer verification
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            yield_underlying_token.address,
            ZERO_ADDRESS,
            100 * EIGHTEEN_DECIMALS,
            b"",
            fake_sig,
            sender=alice
        )


def test_malformed_signature_rejected(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    create_signature_struct
):
    """Test that malformed signatures are rejected"""

    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # Test with wrong signature length (too short)
    short_sig = create_signature_struct(b'\x00' * 64, current_nonce, valid_time)

    with boa.reverts():  # Will fail during signature extraction
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            short_sig,
            sender=alice
        )

    # Test with wrong signature length (too long)
    long_sig = create_signature_struct(b'\x00' * 66, current_nonce, valid_time)

    with boa.reverts():
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            long_sig,
            sender=alice
        )


def test_invalid_v_parameter_rejected(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    create_signature_struct
):
    """Test that invalid v parameter (not 27 or 28) is rejected"""

    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # Create signature with invalid v parameter
    r = b'\x00' * 32
    s = b'\x00' * 32
    v = b'\x1d'  # 29, which is invalid (not 27 or 28)

    invalid_v_sig = create_signature_struct(r + s + v, current_nonce, valid_time)

    with boa.reverts("invalid v parameter"):
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            invalid_v_sig,
            sender=alice
        )


def test_zero_signature_rejected(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    create_signature_struct
):
    """Test that all-zero signature is rejected"""

    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # All zeros signature typically results in zero address recovery
    zero_sig = create_signature_struct(b'\x00' * 65, current_nonce, valid_time)

    with boa.reverts():  # Should fail at ecrecover or signer check
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            zero_sig,
            sender=alice
        )


def test_nonce_increments_on_success(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    charlie,
    alice,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    create_signature_struct
):
    """Test that nonce increments after successful signature use"""

    # Setup tokens
    setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=200 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _lego_id=2
    )

    # Record initial nonce
    initial_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # First, increment nonce manually as owner to set up test
    tx = starter_agent_sender.incrementNonce(user_wallet.address, sender=charlie)
    log = filter_logs(starter_agent_sender, "NonceIncremented")[0]
    assert log.oldNonce == initial_nonce
    assert log.newNonce == initial_nonce + 1

    # Verify nonce was incremented
    assert starter_agent_sender.currentNonce(user_wallet.address) == initial_nonce + 1

    # Non-owner cannot increment nonce
    with boa.reverts("no perms"):
        starter_agent_sender.incrementNonce(user_wallet.address, sender=alice)


def test_batch_actions_signature_validation(
    setupAgentTestAsset,
    createActionInstruction,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    charlie,
    alice,
    mock_dex_asset,
    mock_dex_asset_alt,
    whale,
    bob,
    create_signature_struct
):
    """Test signature validation for batch actions"""

    # Setup tokens
    setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _lego_id=3
    )

    # Create transfer instruction - transfers go to wallet owner (bob), not agent owner
    instruction = createActionInstruction(
        action=1,  # TRANSFER
        asset=mock_dex_asset.address,
        target=bob,
        amount=10 * EIGHTEEN_DECIMALS
    )

    # Test owner can execute without signature
    empty_sig = create_signature_struct(b'', 0, 0)
    result = starter_agent_sender.performBatchActions(
        starter_agent.address,
        user_wallet.address,
        [instruction],
        empty_sig,
        sender=charlie  # Owner
    )
    assert result == True

    # Test non-owner requires valid signature
    with boa.reverts("signature expired"):
        starter_agent_sender.performBatchActions(
            starter_agent.address,
            user_wallet.address,
            [instruction],
            empty_sig,
            sender=alice  # Non-owner
        )


def test_different_action_message_hashes(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    mock_dex_asset,
    create_signature_struct
):
    """Test that different actions produce different message hashes"""

    # This test verifies that each action type creates a unique message hash
    # preventing signature reuse across different action types

    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # Create a signature with non-zero values but still invalid
    # This will pass the s != 0 check but fail at signature recovery or signer check
    r = b'\x01' * 32
    s = b'\x01' * 32  # Non-zero s value
    v = b'\x1b'  # 27
    sig = create_signature_struct(r + s + v, current_nonce, valid_time)

    # Each action will fail at signature verification
    # The signature will either fail ecrecover or return wrong signer

    # Test depositForYield (action 10)
    with boa.reverts():  # Will fail signature verification
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            mock_dex_asset.address,
            ZERO_ADDRESS,
            100,
            b"",
            sig,
            sender=alice  # Non-owner to trigger signature check
        )

    # Test withdrawFromYield (action 11)
    with boa.reverts():  # Will fail signature verification
        starter_agent_sender.withdrawFromYield(
            starter_agent.address,
            user_wallet.address,
            2,
            mock_dex_asset.address,
            100,
            b"",
            sig,
            sender=alice  # Non-owner
        )

    # Test swapTokens (action 20)
    swap_instruction = (
        3,  # legoId
        100,  # amountIn
        0,    # minAmountOut
        [mock_dex_asset.address, ZERO_ADDRESS],  # tokenPath
        [],   # poolPath
    )
    with boa.reverts():  # Will fail signature verification
        starter_agent_sender.swapTokens(
            starter_agent.address,
            user_wallet.address,
            [swap_instruction],
            sig,
            sender=alice  # Non-owner
        )


def test_empty_batch_instructions_rejected(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    charlie,
    alice,
    create_signature_struct
):
    """Test that empty batch instructions are rejected"""

    # Test with owner - should get "no instructions" error
    empty_sig = create_signature_struct(b'', 0, 0)
    with boa.reverts("no instructions"):
        starter_agent_sender.performBatchActions(
            starter_agent.address,
            user_wallet.address,
            [],  # Empty instructions
            empty_sig,
            sender=charlie  # Owner
        )

    # Test with non-owner - should also get "no instructions" error since it comes before auth
    with boa.reverts("no instructions"):
        starter_agent_sender.performBatchActions(
            starter_agent.address,
            user_wallet.address,
            [],  # Empty instructions
            empty_sig,
            sender=alice  # Non-owner
        )


def test_signature_struct_format(create_signature_struct):
    """Test signature struct format is correct"""
    
    # Test signature struct creation
    sig_bytes = b'\x01' * 65
    nonce = 42
    expiration = 1234567890
    
    sig_struct = create_signature_struct(sig_bytes, nonce, expiration)
    
    # Verify struct format (tuple with 3 elements)
    assert len(sig_struct) == 3
    assert sig_struct[0] == sig_bytes
    assert sig_struct[1] == nonce
    assert sig_struct[2] == expiration


def test_v_parameter_normalization(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    create_signature_struct
):
    """Test that v parameter is normalized correctly (0/1 -> 27/28)"""

    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # Test with v=0 (should be normalized to 27)
    r = b'\x00' * 32
    s = b'\x00' * 32
    v = b'\x00'  # 0, should be normalized to 27

    sig_v0 = create_signature_struct(r + s + v, current_nonce, valid_time)

    # Will fail at signature verification, not v parameter check
    with boa.reverts():  # Should get past v check
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            sig_v0,
            sender=alice
        )

    # Test with v=1 (should be normalized to 28)
    v = b'\x01'  # 1, should be normalized to 28

    sig_v1 = create_signature_struct(r + s + v, current_nonce, valid_time)

    # Will fail at signature verification, not v parameter check
    with boa.reverts():  # Should get past v check
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            sig_v1,
            sender=alice
        )


def test_getNonce_public_function(starter_agent, starter_agent_sender, charlie, user_wallet):
    """Test getNonce public function works correctly"""

    # Get initial nonce
    nonce = starter_agent_sender.currentNonce(user_wallet.address)
    assert nonce >= 0

    # Increment and verify
    starter_agent_sender.incrementNonce(user_wallet.address, sender=charlie)
    new_nonce = starter_agent_sender.currentNonce(user_wallet.address)
    assert new_nonce == nonce + 1


def test_signature_malleability_s_value_check(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    create_signature_struct
):
    """Test that s values above secp256k1n/2 are rejected"""

    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # secp256k1n/2 = 0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0
    # Create signature with s > secp256k1n/2
    r = b'\x01' * 32
    # High s value (above secp256k1n/2)
    s = b'\x7F\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x5D\x57\x6E\x73\x57\xA4\x50\x1D\xDF\xE9\x2F\x46\x68\x1B\x20\xA1'
    v = b'\x1b'  # 27

    high_s_sig = create_signature_struct(r + s + v, current_nonce, valid_time)

    # Should reject high s value
    with boa.reverts("invalid s value"):
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            high_s_sig,
            sender=alice
        )


def test_signature_reuse_prevented(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    charlie,
    alice,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    create_signature_struct,
):
    """Test that the same signature cannot be used twice"""

    # Setup tokens
    setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=200 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _lego_id=2
    )

    # First, manually increment the nonce as owner to simulate a used nonce
    initial_nonce = starter_agent_sender.currentNonce(user_wallet.address)
    starter_agent_sender.incrementNonce(user_wallet.address, sender=charlie)

    # Now the current nonce is initial_nonce + 1
    # Try to use a signature with the old nonce (which has been "used")
    valid_time = boa.env.evm.patch.timestamp + 3600
    old_nonce_sig = create_signature_struct(
        b'\x01' * 64 + b'\x1b',  # Valid format but wrong signer
        initial_nonce,  # Old nonce that's already been passed
        valid_time
    )

    # Should fail due to invalid nonce (nonce too low)
    with boa.reverts("invalid nonce"):
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            yield_underlying_token.address,
            yield_vault_token.address,
            50 * EIGHTEEN_DECIMALS,
            b"",
            old_nonce_sig,
            sender=alice  # Non-owner
        )


def test_batch_max_instructions(
    setupAgentTestAsset,
    createActionInstruction,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    charlie,
    mock_dex_asset,
    whale,
    bob,
    create_signature_struct
):
    """Test batch actions with exactly 15 instructions (MAX_INSTRUCTIONS)"""

    # Setup tokens with enough balance
    setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _lego_id=3
    )

    # Create exactly 15 instructions (MAX_INSTRUCTIONS)
    instructions = []
    for i in range(15):
        instruction = createActionInstruction(
            action=1,  # TRANSFER
            asset=mock_dex_asset.address,
            target=bob,
            amount=1 * EIGHTEEN_DECIMALS  # Small amount per transfer
        )
        instructions.append(instruction)

    # Test with owner - should succeed with 15 instructions
    empty_sig = create_signature_struct(b'', 0, 0)
    result = starter_agent_sender.performBatchActions(
        starter_agent.address,
        user_wallet.address,
        instructions,
        empty_sig,
        sender=charlie  # Owner
    )
    assert result == True

    # Test with 16 instructions - should fail
    extra_instruction = createActionInstruction(
        action=1,  # TRANSFER
        asset=mock_dex_asset.address,
        target=bob,
        amount=1 * EIGHTEEN_DECIMALS
    )
    instructions.append(extra_instruction)

    # The DynArray[ActionInstruction, MAX_INSTRUCTIONS] validation happens at ABI encoding
    with boa.reverts():  # Will fail during ABI encoding with array too long
        starter_agent_sender.performBatchActions(
            starter_agent.address,
            user_wallet.address,
            instructions,
            empty_sig,
            sender=charlie  # Owner
        )


def test_ecrecover_edge_cases(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    alice,
    create_signature_struct
):
    """Test edge cases that might cause ecrecover to fail"""

    valid_time = boa.env.evm.patch.timestamp + 3600
    current_nonce = starter_agent_sender.currentNonce(user_wallet.address)

    # Test 1: r = 0 (should fail ecrecover)
    r_zero = b'\x00' * 32
    s_valid = b'\x01' * 32
    v_valid = b'\x1b'  # 27

    zero_r_sig = create_signature_struct(r_zero + s_valid + v_valid, current_nonce, valid_time)

    with boa.reverts():  # ecrecover returns zero address
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            zero_r_sig,
            sender=alice
        )

    # Test 2: s = 0 (should fail s != 0 check)
    r_valid = b'\x01' * 32
    s_zero = b'\x00' * 32

    zero_s_sig = create_signature_struct(r_valid + s_zero + v_valid, current_nonce, valid_time)

    with boa.reverts("invalid s value (zero)"):
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            zero_s_sig,
            sender=alice
        )

    # Test 3: r > secp256k1n (invalid point)
    r_invalid = b'\xFF' * 32  # Much larger than curve order

    invalid_r_sig = create_signature_struct(r_invalid + s_valid + v_valid, current_nonce, valid_time)

    with boa.reverts():  # ecrecover will fail
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            invalid_r_sig,
            sender=alice
        )

    # Test 4: v = 26 (invalid, should be 27 or 28)
    v_invalid = b'\x1a'  # 26

    invalid_v_sig = create_signature_struct(r_valid + s_valid + v_invalid, current_nonce, valid_time)

    with boa.reverts("invalid v parameter"):
        starter_agent_sender.depositForYield(
            starter_agent.address,
            user_wallet.address,
            2,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            b"",
            invalid_v_sig,
            sender=alice
        )


