import pytest
import boa
from eth_account import Account
from eth_account.messages import encode_typed_data

from constants import EIGHTEEN_DECIMALS, MAX_UINT256, ZERO_ADDRESS
from config.BluePrint import PARAMS
from contracts.core.userWallet import UserWalletConfig
from conf_utils import filter_logs, set_live_cheque_settings


@pytest.fixture(scope="module")
def setupAgentTestAsset(user_wallet, alpha_token, alpha_token_whale, mock_ripe, switchboard_alpha):
    def setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _user_wallet=user_wallet,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=0,
        _shouldCheckYield=False,
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
            sender=switchboard_alpha.address
        )
        return _amount

    yield setupAgentTestAsset


@pytest.fixture
def valid_transfer_recipient(user_wallet_config, migrator, sally):
    if user_wallet_config.indexOfWhitelist(sally) == 0:
        user_wallet_config.addWhitelistAddrViaMigrator(sally, sender=migrator.address)
    return sally


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


@pytest.fixture(scope="module")
def user_wallet_signature_helper():
    return boa.load(
        "contracts/core/agent/UserWalletSignatureHelper.vy",
        name="user_wallet_signature_helper",
    )


@pytest.fixture(scope="module")
def agent_sender_special_sig_helper():
    return boa.load(
        "contracts/core/agent/AgentSenderSpecialSigHelper.vy",
        name="agent_sender_special_sig_helper",
    )


@pytest.fixture(scope="module")
def signed_agent_sender(undy_hq_deploy, test_signer, fork, starter_agent, switchboard_alpha):
    sender = boa.load(
        "contracts/core/agent/AgentSenderGeneric.vy",
        undy_hq_deploy,
        test_signer.address,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"],
        PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
        name="signed_agent_sender",
    )
    starter_agent.addSender(sender, sender=switchboard_alpha.address)
    return sender


@pytest.fixture(scope="module")
def signed_agent_sender_special(
    undy_hq_deploy,
    test_signer,
    fork,
    starter_agent,
    switchboard_alpha,
    mock_green_token,
    mock_savings_green_token,
):
    sender = boa.load(
        "contracts/core/agent/AgentSenderSpecial.vy",
        undy_hq_deploy,
        test_signer.address,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"],
        PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
        mock_green_token.address,
        mock_savings_green_token.address,
        name="signed_agent_sender_special",
    )
    starter_agent.addSender(sender, sender=switchboard_alpha.address)
    return sender


@pytest.fixture(scope="module")
def signed_agent_sender_special_admin(undy_hq_deploy, test_signer, fork, starter_agent, switchboard_alpha):
    sender = boa.load(
        "contracts/core/agent/AgentSenderSpecialAdmin.vy",
        undy_hq_deploy,
        test_signer.address,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"],
        PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
        name="signed_agent_sender_special_admin",
    )
    starter_agent.addSender(sender, sender=switchboard_alpha.address)
    return sender


def _set_instant_cheque_settings(
    cheque_book,
    user_wallet,
    owner,
    createChequeSettings,
    _instant_usd_threshold,
    _expensive_delay_blocks=1,
    _can_manager_pay=True,
    _can_be_pulled=False,
):
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    timelock = wallet_config.timeLock()
    min_expensive_delay = cheque_book.MIN_EXPENSIVE_CHEQUE_DELAY()
    settings = createChequeSettings(
        _instantUsdThreshold=_instant_usd_threshold,
        _expensiveDelayBlocks=max(_expensive_delay_blocks, timelock, min_expensive_delay),
        _defaultExpiryBlocks=timelock,
        _canManagersCreateCheques=True,
        _canManagerPay=_can_manager_pay,
        _canBePulled=_can_be_pulled,
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *settings, sender=owner)
    return settings


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
    nonce_before = starter_agent_sender.currentNonce(user_wallet.address)
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
    assert starter_agent_sender.currentNonce(user_wallet.address) == nonce_before


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
    valid_transfer_recipient,
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

    # Create transfer instruction to an explicitly valid non-owner recipient.
    instruction = createActionInstruction(
        action=1,  # TRANSFER
        asset=mock_dex_asset.address,
        target=valid_transfer_recipient,
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


def test_batch_actions_signed_helper_hash_executes(
    setupAgentTestAsset,
    createActionInstruction,
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    alice,
    mock_dex_asset,
    whale,
    valid_transfer_recipient,
    test_signer,
    create_signature_struct,
):
    setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _lego_id=3,
    )

    instruction = createActionInstruction(
        action=1,
        asset=mock_dex_asset.address,
        target=valid_transfer_recipient,
        amount=3 * EIGHTEEN_DECIMALS,
    )
    digest, nonce, expiration = user_wallet_signature_helper.getBatchActionsHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        [instruction],
    )
    signature = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    nonce_before = signed_agent_sender.currentNonce(user_wallet.address)

    assert signed_agent_sender.performBatchActions(
        starter_agent.address,
        user_wallet.address,
        [instruction],
        signature,
        sender=alice,
    )
    assert signed_agent_sender.currentNonce(user_wallet.address) == nonce_before + 1


def test_new_generic_hashes_change_when_top_level_fields_mutate(
    createActionInstruction,
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    alice,
    bob,
    alpha_token,
    bravo_token,
):
    base_create = user_wallet_signature_helper.getCreateChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        10,
        1,
        2,
        True,
        False,
        7,
        1000,
    )[0]
    create_mutations = [
        (signed_agent_sender.address, bob, user_wallet.address, alice, alpha_token.address, 10, 1, 2, True, False, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, bob,
         alice, alpha_token.address, 10, 1, 2, True, False, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address,
         bob, alpha_token.address, 10, 1, 2, True, False, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address,
         alice, bravo_token.address, 10, 1, 2, True, False, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address,
         alice, alpha_token.address, 11, 1, 2, True, False, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address,
         alice, alpha_token.address, 10, 2, 2, True, False, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address,
         alice, alpha_token.address, 10, 1, 3, True, False, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address,
         alice, alpha_token.address, 10, 1, 2, False, False, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address,
         alice, alpha_token.address, 10, 1, 2, True, True, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address,
         alice, alpha_token.address, 10, 1, 2, True, False, 8, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address,
         alice, alpha_token.address, 10, 1, 2, True, False, 7, 1001),
    ]
    for args in create_mutations:
        assert user_wallet_signature_helper.getCreateChequeHash(*args)[0] != base_create

    base_pay = user_wallet_signature_helper.getPayChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        10,
        123,
        7,
        1000,
    )[0]
    pay_mutations = [
        (signed_agent_sender.address, bob, user_wallet.address, alice, alpha_token.address, 10, 123, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, bob, alice, alpha_token.address, 10, 123, 7, 1000),
        (signed_agent_sender.address, starter_agent.address, user_wallet.address, bob, alpha_token.address, 10, 123, 7, 1000),
        (signed_agent_sender.address, starter_agent.address,
         user_wallet.address, alice, bravo_token.address, 10, 123, 7, 1000),
        (signed_agent_sender.address, starter_agent.address,
         user_wallet.address, alice, alpha_token.address, 11, 123, 7, 1000),
        (signed_agent_sender.address, starter_agent.address,
         user_wallet.address, alice, alpha_token.address, 10, 124, 7, 1000),
        (signed_agent_sender.address, starter_agent.address,
         user_wallet.address, alice, alpha_token.address, 10, 123, 8, 1000),
        (signed_agent_sender.address, starter_agent.address,
         user_wallet.address, alice, alpha_token.address, 10, 123, 7, 1001),
    ]
    for args in pay_mutations:
        assert user_wallet_signature_helper.getPayChequeHash(*args)[0] != base_pay

    instruction = createActionInstruction(action=80)
    base_batch = user_wallet_signature_helper.getBatchActionsHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        [instruction],
        7,
        1000,
    )[0]
    assert user_wallet_signature_helper.getBatchActionsHash(
        signed_agent_sender.address,
        bob,
        user_wallet.address,
        [instruction],
        7,
        1000,
    )[0] != base_batch
    assert user_wallet_signature_helper.getBatchActionsHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        [createActionInstruction(action=81)],
        7,
        1000,
    )[0] != base_batch
    assert user_wallet_signature_helper.getBatchActionsHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        [instruction, createActionInstruction(action=82)],
        7,
        1000,
    )[0] != base_batch


def test_deleverage_hashes_are_mode_bound(
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    alice,
    alpha_token,
    bravo_token,
    test_signer,
    create_signature_struct,
):
    nonce = signed_agent_sender.currentNonce(user_wallet.address)
    expiration = boa.env.evm.patch.timestamp + 1000
    data_a = b"\x01" * 32
    specific_assets = [(1, alpha_token.address, 10)]
    other_specific_assets = [(1, bravo_token.address, 10)]

    specific_digest, specific_nonce, specific_expiration = user_wallet_signature_helper.getDeleverageHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        1,
        specific_assets,
        0,
        data_a,
        nonce,
        expiration,
    )
    assert specific_nonce == nonce
    assert specific_expiration == expiration

    assert user_wallet_signature_helper.getDeleverageHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        1,
        other_specific_assets,
        0,
        data_a,
        nonce,
        expiration,
    )[0] != specific_digest

    auto_digest = user_wallet_signature_helper.getDeleverageHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        1,
        [],
        10,
        data_a,
        nonce,
        expiration,
    )[0]
    assert auto_digest != specific_digest

    specific_sig = create_signature_struct(test_signer.unsafe_sign_hash(specific_digest).signature, nonce, expiration)
    with boa.reverts("invalid signer"):
        signed_agent_sender.deleverage(
            starter_agent.address,
            user_wallet.address,
            1,
            [],
            10,
            data_a,
            specific_sig,
            sender=alice,
        )
    assert signed_agent_sender.currentNonce(user_wallet.address) == nonce

    auto_sig = create_signature_struct(test_signer.unsafe_sign_hash(auto_digest).signature, nonce, expiration)
    with boa.reverts("invalid signer"):
        signed_agent_sender.deleverage(
            starter_agent.address,
            user_wallet.address,
            1,
            specific_assets,
            0,
            data_a,
            auto_sig,
            sender=alice,
        )
    assert signed_agent_sender.currentNonce(user_wallet.address) == nonce

    with boa.reverts("invalid mode"):
        user_wallet_signature_helper.getDeleverageHash(
            signed_agent_sender.address,
            starter_agent.address,
            user_wallet.address,
            1,
            [],
            0,
            data_a,
            nonce,
            expiration,
        )

    with boa.reverts("invalid mode"):
        user_wallet_signature_helper.getDeleverageHash(
            signed_agent_sender.address,
            starter_agent.address,
            user_wallet.address,
            1,
            specific_assets,
            10,
            data_a,
            nonce,
            expiration,
        )


def test_deleverage_signatures_succeed_for_specific_and_auto_modes(
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    alice,
    lego_ripe,
    lego_book,
    mock_ripe,
    mock_green_token,
    mock_usdc,
    test_signer,
    create_signature_struct,
):
    lego_id = lego_book.getRegId(lego_ripe)
    mock_ripe.setPrice(mock_green_token, EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc, EIGHTEEN_DECIMALS)

    specific_debt = 80 * EIGHTEEN_DECIMALS
    specific_repay = 12 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(user_wallet.address, specific_debt)
    specific_assets = [(1, mock_usdc.address, specific_repay)]
    nonce = signed_agent_sender.currentNonce(user_wallet.address)
    digest, sig_nonce, expiration = user_wallet_signature_helper.getDeleverageHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        lego_id,
        specific_assets,
        0,
        b"",
        nonce,
        boa.env.evm.patch.timestamp + 1000,
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, sig_nonce, expiration)

    repaid, usd_value = signed_agent_sender.deleverage(
        starter_agent.address,
        user_wallet.address,
        lego_id,
        specific_assets,
        0,
        b"",
        sig,
        sender=alice,
    )
    assert repaid == specific_repay
    assert usd_value == specific_repay
    assert signed_agent_sender.currentNonce(user_wallet.address) == nonce + 1

    auto_debt = 45 * EIGHTEEN_DECIMALS
    auto_amount = 100 * EIGHTEEN_DECIMALS
    mock_ripe.setUserDebt(user_wallet.address, auto_debt)
    nonce = signed_agent_sender.currentNonce(user_wallet.address)
    digest, sig_nonce, expiration = user_wallet_signature_helper.getDeleverageHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        lego_id,
        [],
        auto_amount,
        b"",
        nonce,
        boa.env.evm.patch.timestamp + 1000,
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, sig_nonce, expiration)

    repaid, usd_value = signed_agent_sender.deleverage(
        starter_agent.address,
        user_wallet.address,
        lego_id,
        [],
        auto_amount,
        b"",
        sig,
        sender=alice,
    )
    assert repaid == auto_debt
    assert usd_value == auto_debt
    assert signed_agent_sender.currentNonce(user_wallet.address) == nonce + 1


def _mutated_hash_arg_variants(value, alt_address, fallback_address):
    if isinstance(value, bool):
        return [not value]
    if isinstance(value, int):
        return [value + 1]
    if isinstance(value, bytes):
        if len(value) == 0:
            return []
        return [b"\x02" * len(value)]
    if isinstance(value, list):
        if len(value) == 0:
            return []
        variants = []
        for item_idx, item in enumerate(value):
            for mutated_item in _mutated_hash_arg_variants(item, alt_address, fallback_address):
                mutated = list(value)
                mutated[item_idx] = mutated_item
                variants.append(mutated)
        variants.append(list(value) + [value[0]])
        return variants
    if isinstance(value, tuple):
        variants = []
        for item_idx, item in enumerate(value):
            for mutated_item in _mutated_hash_arg_variants(item, alt_address, fallback_address):
                mutated = list(value)
                mutated[item_idx] = mutated_item
                variants.append(tuple(mutated))
        return variants
    return [fallback_address if value == alt_address else alt_address]


def _assert_helper_digest_changes_for_each_top_level_arg(getter, args, alt_address, fallback_address):
    base = getter(*args)[0]
    for idx, value in enumerate(args):
        for mutated_value in _mutated_hash_arg_variants(value, alt_address, fallback_address):
            mutated_args = list(args)
            mutated_args[idx] = mutated_value
            assert getter(
                *mutated_args)[0] != base, f"{getter} arg {idx} mutation did not change digest: {mutated_value!r}"


def test_all_signature_helper_hashes_change_when_top_level_fields_mutate(
    createActionInstruction,
    starter_agent,
    signed_agent_sender,
    signed_agent_sender_special,
    signed_agent_sender_special_admin,
    user_wallet_signature_helper,
    agent_sender_special_sig_helper,
    user_wallet,
    alice,
    bob,
    alpha_token,
    bravo_token,
):
    nonce = 7
    expiration = 1000
    data_a = b"\x01" * 32
    swap_instruction = (3, 10, 1, [alpha_token.address, bravo_token.address], [bob])
    action_instruction = createActionInstruction(
        action=1,
        asset=alpha_token.address,
        target=alice,
        amount=10,
        extraData=data_a,
    )

    generic_common = [signed_agent_sender.address, starter_agent.address, user_wallet.address]
    generic_cases = [
        (user_wallet_signature_helper.getTransferFundsHash, generic_common +
         [alice, alpha_token.address, 10, nonce, expiration]),
        (user_wallet_signature_helper.getCreateAndPayChequeHash,
         generic_common + [alice, alpha_token.address, 10, nonce, expiration]),
        (user_wallet_signature_helper.getCreateChequeHash, generic_common +
         [alice, alpha_token.address, 10, 1, 2, True, False, nonce, expiration]),
        (user_wallet_signature_helper.getPayChequeHash, generic_common +
         [alice, alpha_token.address, 10, 123, nonce, expiration]),
        (user_wallet_signature_helper.getDepositForYieldHash, generic_common +
         [3, alpha_token.address, bravo_token.address, 10, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getWithdrawFromYieldHash, generic_common +
         [3, alpha_token.address, 10, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getRebalanceYieldPositionHash, generic_common +
         [3, alpha_token.address, 4, bravo_token.address, 10, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getSwapTokensHash, generic_common + [[swap_instruction], nonce, expiration]),
        (user_wallet_signature_helper.getMintOrRedeemAssetHash, generic_common +
         [3, alpha_token.address, bravo_token.address, 10, 1, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getConfirmMintOrRedeemAssetHash, generic_common +
         [3, alpha_token.address, bravo_token.address, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getAddCollateralHash, generic_common +
         [3, alpha_token.address, 10, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getRemoveCollateralHash, generic_common +
         [3, alpha_token.address, 10, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getBorrowHash, generic_common +
         [3, alpha_token.address, 10, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getRepayDebtHash, generic_common +
         [3, alpha_token.address, 10, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getConvertWethToEthHash, generic_common + [10, nonce, expiration]),
        (user_wallet_signature_helper.getConvertEthToWethHash, generic_common + [10, nonce, expiration]),
        (user_wallet_signature_helper.getAddLiquidityHash, generic_common +
         [3, bob, alpha_token.address, bravo_token.address, 10, 11, 1, 2, 3, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getRemoveLiquidityHash, generic_common +
         [3, bob, alpha_token.address, bravo_token.address, alice, 10, 1, 2, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getAddLiquidityConcentratedHash, generic_common +
         [3, bob, 99, alice, alpha_token.address, bravo_token.address, 10, 11, -10, 10, 1, 2, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getRemoveLiquidityConcentratedHash, generic_common +
         [3, bob, 99, alice, alpha_token.address, bravo_token.address, 10, 1, 2, data_a, nonce, expiration]),
        (user_wallet_signature_helper.getClaimIncentivesHash, generic_common +
         [3, alpha_token.address, 10, [data_a], nonce, expiration]),
        (user_wallet_signature_helper.getConfirmWhitelistAddrHash, generic_common + [alice, nonce, expiration]),
        (user_wallet_signature_helper.getCancelPendingWhitelistAddrHash, generic_common + [alice, nonce, expiration]),
        (user_wallet_signature_helper.getRemoveWhitelistAddrHash, generic_common + [alice, nonce, expiration]),
        (user_wallet_signature_helper.getRemoveSelfAsManagerHash, generic_common + [nonce, expiration]),
        (user_wallet_signature_helper.getClaimAllLootHash, generic_common + [nonce, expiration]),
        (user_wallet_signature_helper.getClaimRevShareAndBonusLootHash, generic_common + [nonce, expiration]),
        (user_wallet_signature_helper.getClaimDepositRewardsHash, generic_common + [nonce, expiration]),
        (user_wallet_signature_helper.getBatchActionsHash, generic_common + [[action_instruction], nonce, expiration]),
    ]
    for getter, args in generic_cases:
        _assert_helper_digest_changes_for_each_top_level_arg(getter, args, ZERO_ADDRESS, bob)

    collateral_asset = (1, alpha_token.address, 10)
    deleverage_asset = (1, alpha_token.address, 10)
    deposit_position = (3, alpha_token.address, 10, bravo_token.address)
    withdraw_position = (3, alpha_token.address, 10)
    transfer_data = (alpha_token.address, 10, alice)
    cheque = (alice, alpha_token.address, 10, 1, 2, False, True)
    special_common = [signed_agent_sender_special.address, starter_agent.address, user_wallet.address]
    admin_common = [signed_agent_sender_special_admin.address, starter_agent.address, user_wallet.address]
    special_cases = [
        (agent_sender_special_sig_helper.getAddCollateralAndBorrowHash, special_common +
         [1, [collateral_asset], 10, True, False, [swap_instruction], deposit_position, nonce, expiration]),
        (agent_sender_special_sig_helper.getRepayAndWithdrawHash, special_common +
         [1, [deleverage_asset], withdraw_position, [swap_instruction], alpha_token.address, 10, [collateral_asset], nonce, expiration]),
        (agent_sender_special_sig_helper.getRebalanceYieldPositionsWithSwapHash, special_common +
         [[withdraw_position], [swap_instruction], [deposit_position], [transfer_data], nonce, expiration]),
        (agent_sender_special_sig_helper.getClaimIncentivesAndSwapHash, special_common +
         [3, alpha_token.address, 10, [data_a], [swap_instruction], [deposit_position], 1, [collateral_asset], nonce, expiration]),
        (agent_sender_special_sig_helper.getIssuePullChequesHash, admin_common + [[cheque], nonce, expiration]),
        (agent_sender_special_sig_helper.getWhitelistMaintenanceHash,
         admin_common + [[alice], [bob], [bravo_token.address], nonce, expiration]),
        (agent_sender_special_sig_helper.getHarvestAndIssueChequeHash, admin_common +
         [3, alpha_token.address, 10, [data_a], [swap_instruction], cheque, nonce, expiration]),
    ]
    for getter, args in special_cases:
        _assert_helper_digest_changes_for_each_top_level_arg(getter, args, ZERO_ADDRESS, bob)


def test_special_workflows_100_103_require_wrapper_bound_hashes(
    signed_agent_sender_special,
    agent_sender_special_sig_helper,
    starter_agent,
    user_wallet,
    alice,
    bob,
    test_signer,
    create_signature_struct,
):
    yield_position = (0, ZERO_ADDRESS, 0, ZERO_ADDRESS)
    withdraw_position = (0, ZERO_ADDRESS, 0)

    wrong_digest, wrong_nonce, wrong_expiration = agent_sender_special_sig_helper.getAddCollateralAndBorrowHash(
        signed_agent_sender_special.address,
        bob,
        user_wallet.address,
        0,
        [],
        0,
        True,
        False,
        [],
        yield_position,
    )
    wrong_sig = create_signature_struct(test_signer.unsafe_sign_hash(
        wrong_digest).signature, wrong_nonce, wrong_expiration)
    nonce_before = signed_agent_sender_special.currentNonce(user_wallet.address)
    with boa.reverts("invalid signer"):
        signed_agent_sender_special.addCollateralAndBorrow(
            starter_agent.address,
            user_wallet.address,
            0,
            [],
            0,
            True,
            False,
            [],
            yield_position,
            wrong_sig,
            sender=alice,
        )
    assert signed_agent_sender_special.currentNonce(user_wallet.address) == nonce_before

    digest, nonce, expiration = agent_sender_special_sig_helper.getAddCollateralAndBorrowHash(
        signed_agent_sender_special.address,
        starter_agent.address,
        user_wallet.address,
        0,
        [],
        0,
        True,
        False,
        [],
        yield_position,
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    signed_agent_sender_special.addCollateralAndBorrow(
        starter_agent.address,
        user_wallet.address,
        0,
        [],
        0,
        True,
        False,
        [],
        yield_position,
        sig,
        sender=alice,
    )
    assert signed_agent_sender_special.currentNonce(user_wallet.address) == nonce_before + 1

    digest, nonce, expiration = agent_sender_special_sig_helper.getRepayAndWithdrawHash(
        signed_agent_sender_special.address,
        starter_agent.address,
        user_wallet.address,
        0,
        [],
        withdraw_position,
        [],
        ZERO_ADDRESS,
        MAX_UINT256,
        [],
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    signed_agent_sender_special.repayAndWithdraw(
        starter_agent.address,
        user_wallet.address,
        0,
        [],
        withdraw_position,
        [],
        ZERO_ADDRESS,
        MAX_UINT256,
        [],
        sig,
        sender=alice,
    )
    assert signed_agent_sender_special.currentNonce(user_wallet.address) == nonce_before + 2

    digest, nonce, expiration = agent_sender_special_sig_helper.getRebalanceYieldPositionsWithSwapHash(
        signed_agent_sender_special.address,
        starter_agent.address,
        user_wallet.address,
        [],
        [],
        [],
        [],
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    signed_agent_sender_special.rebalanceYieldPositionsWithSwap(
        starter_agent.address,
        user_wallet.address,
        [],
        [],
        [],
        [],
        sig,
        sender=alice,
    )
    assert signed_agent_sender_special.currentNonce(user_wallet.address) == nonce_before + 3

    digest, nonce, expiration = agent_sender_special_sig_helper.getClaimIncentivesAndSwapHash(
        signed_agent_sender_special.address,
        starter_agent.address,
        user_wallet.address,
        0,
        ZERO_ADDRESS,
        MAX_UINT256,
        [],
        [],
        [],
        0,
        [],
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    signed_agent_sender_special.claimIncentivesAndSwap(
        starter_agent.address,
        user_wallet.address,
        0,
        ZERO_ADDRESS,
        MAX_UINT256,
        [],
        [],
        [],
        0,
        [],
        sig,
        sender=alice,
    )
    assert signed_agent_sender_special.currentNonce(user_wallet.address) == nonce_before + 4


def test_special_repay_and_withdraw_executes_deleverage_leg(
    signed_agent_sender_special,
    agent_sender_special_sig_helper,
    starter_agent,
    user_wallet,
    alice,
    lego_ripe,
    lego_book,
    mock_ripe,
    mock_green_token,
    mock_usdc,
    test_signer,
    create_signature_struct,
):
    lego_id = lego_book.getRegId(lego_ripe)
    debt = 70 * EIGHTEEN_DECIMALS
    repay_amount = 11 * EIGHTEEN_DECIMALS
    deleverage_assets = [(1, mock_usdc.address, repay_amount)]
    withdraw_position = (0, ZERO_ADDRESS, 0)
    mock_ripe.setPrice(mock_green_token, EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc, EIGHTEEN_DECIMALS)
    mock_ripe.setUserDebt(user_wallet.address, debt)

    nonce = signed_agent_sender_special.currentNonce(user_wallet.address)
    digest, sig_nonce, expiration = agent_sender_special_sig_helper.getRepayAndWithdrawHash(
        signed_agent_sender_special.address,
        starter_agent.address,
        user_wallet.address,
        lego_id,
        deleverage_assets,
        withdraw_position,
        [],
        ZERO_ADDRESS,
        MAX_UINT256,
        [],
        nonce,
        boa.env.evm.patch.timestamp + 1000,
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, sig_nonce, expiration)

    signed_agent_sender_special.repayAndWithdraw(
        starter_agent.address,
        user_wallet.address,
        lego_id,
        deleverage_assets,
        withdraw_position,
        [],
        ZERO_ADDRESS,
        MAX_UINT256,
        [],
        sig,
        sender=alice,
    )

    assert mock_ripe.userDebt(user_wallet.address) == debt - repay_amount
    assert signed_agent_sender_special.currentNonce(user_wallet.address) == nonce + 1


def test_special_repay_and_withdraw_deleverage_counts_as_manager_action_for_cooldown(
    signed_agent_sender_special,
    agent_sender_special_sig_helper,
    starter_agent,
    user_wallet,
    user_wallet_config,
    alice,
    lego_ripe,
    lego_book,
    mock_ripe,
    mock_green_token,
    mock_usdc,
    whale,
    high_command,
    createManagerSettings,
    createManagerLimits,
    test_signer,
    create_signature_struct,
):
    lego_id = lego_book.getRegId(lego_ripe)
    debt = 70 * EIGHTEEN_DECIMALS
    deleverage_repay = 11 * EIGHTEEN_DECIMALS
    direct_repay = 1 * EIGHTEEN_DECIMALS
    deleverage_assets = [(1, mock_usdc.address, deleverage_repay)]
    withdraw_position = (0, ZERO_ADDRESS, 0)
    mock_ripe.setPrice(mock_green_token, EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_usdc, EIGHTEEN_DECIMALS)

    with boa.env.anchor():
        mock_ripe.setUserDebt(user_wallet.address, debt)
        mock_green_token.transfer(user_wallet.address, direct_repay, sender=whale)

        original_settings = user_wallet_config.managerSettings(starter_agent.address)
        updated_settings = createManagerSettings(
            _startBlock=original_settings.startBlock,
            _expiryBlock=original_settings.expiryBlock,
            _limits=createManagerLimits(_txCooldownBlocks=1),
            _legoPerms=original_settings.legoPerms,
            _swapPerms=original_settings.swapPerms,
            _whitelistPerms=original_settings.whitelistPerms,
            _transferPerms=original_settings.transferPerms,
            _allowedAssets=list(original_settings.allowedAssets),
            _canClaimLoot=original_settings.canClaimLoot,
        )
        user_wallet_config.updateManager(starter_agent.address, updated_settings, sender=high_command.address)

        nonce = signed_agent_sender_special.currentNonce(user_wallet.address)
        digest, sig_nonce, expiration = agent_sender_special_sig_helper.getRepayAndWithdrawHash(
            signed_agent_sender_special.address,
            starter_agent.address,
            user_wallet.address,
            lego_id,
            deleverage_assets,
            withdraw_position,
            [],
            mock_green_token.address,
            direct_repay,
            [],
            nonce,
            boa.env.evm.patch.timestamp + 1000,
        )
        sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, sig_nonce, expiration)

        with boa.reverts("no permission"):
            signed_agent_sender_special.repayAndWithdraw(
                starter_agent.address,
                user_wallet.address,
                lego_id,
                deleverage_assets,
                withdraw_position,
                [],
                mock_green_token.address,
                direct_repay,
                [],
                sig,
                sender=alice,
            )

        assert mock_ripe.userDebt(user_wallet.address) == debt
        assert signed_agent_sender_special.currentNonce(user_wallet.address) == nonce


@pytest.mark.parametrize(
    ("confirm_addrs", "cancel_pending_addrs", "remove_addrs"),
    [
        ([ZERO_ADDRESS], [], []),
        ([], [ZERO_ADDRESS], []),
        ([], [], [ZERO_ADDRESS]),
    ],
)
def test_special_admin_whitelist_maintenance_rejects_empty_address_without_nonce_change(
    signed_agent_sender_special_admin,
    starter_agent,
    user_wallet,
    alice,
    create_signature_struct,
    confirm_addrs,
    cancel_pending_addrs,
    remove_addrs,
):
    nonce_before = signed_agent_sender_special_admin.currentNonce(user_wallet.address)
    sig = create_signature_struct(
        b"\x00" * 65,
        nonce_before,
        boa.env.evm.patch.timestamp + 1000,
    )

    with boa.reverts("empty addr"):
        signed_agent_sender_special_admin.whitelistMaintenance(
            starter_agent.address,
            user_wallet.address,
            confirm_addrs,
            cancel_pending_addrs,
            remove_addrs,
            sig,
            sender=alice,
        )

    assert signed_agent_sender_special_admin.currentNonce(user_wallet.address) == nonce_before


@pytest.mark.parametrize(
    ("list_name", "confirm_addrs", "cancel_pending_addrs", "remove_addrs"),
    [
        ("confirm", ["addr"], [], []),
        ("cancel", [], ["addr"], []),
        ("remove", [], [], ["addr"]),
    ],
)
@pytest.mark.parametrize("invalid_addr_name", ["wallet", "owner", "wallet_config"])
def test_special_admin_whitelist_maintenance_rejects_reserved_address_without_nonce_change(
    signed_agent_sender_special_admin,
    starter_agent,
    user_wallet,
    user_wallet_config,
    alice,
    create_signature_struct,
    list_name,
    confirm_addrs,
    cancel_pending_addrs,
    remove_addrs,
    invalid_addr_name,
):
    invalid_addr = {
        "wallet": user_wallet.address,
        "owner": user_wallet_config.owner(),
        "wallet_config": user_wallet_config.address,
    }[invalid_addr_name]
    if list_name == "confirm":
        confirm_addrs = [invalid_addr]
    elif list_name == "cancel":
        cancel_pending_addrs = [invalid_addr]
    else:
        remove_addrs = [invalid_addr]

    nonce_before = signed_agent_sender_special_admin.currentNonce(user_wallet.address)
    sig = create_signature_struct(
        b"\x00" * 65,
        nonce_before,
        boa.env.evm.patch.timestamp + 1000,
    )

    with boa.reverts("invalid addr"):
        signed_agent_sender_special_admin.whitelistMaintenance(
            starter_agent.address,
            user_wallet.address,
            confirm_addrs,
            cancel_pending_addrs,
            remove_addrs,
            sig,
            sender=alice,
        )

    assert signed_agent_sender_special_admin.currentNonce(user_wallet.address) == nonce_before


def test_special_admin_workflows_104_106_require_wrapper_bound_signed_hashes(
    setupAgentTestAsset,
    signed_agent_sender_special_admin,
    agent_sender_special_sig_helper,
    starter_agent,
    user_wallet,
    user_wallet_config,
    cheque_book,
    kernel,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    test_signer,
    create_signature_struct,
    createChequeSettings,
    env,
):
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _expensive_delay_blocks=5,
        _can_manager_pay=False,
        _can_be_pulled=True,
    )

    pull_recipient = env.generate_address("signed_admin_pull_cheque")
    harvest_recipient = env.generate_address("signed_admin_harvest_cheque")
    whitelist_addr = env.generate_address("signed_admin_whitelist")
    amount = 5 * EIGHTEEN_DECIMALS
    pull_cheques = [(pull_recipient, alpha_token.address, amount, 0, 0, False, True)]
    harvest_cheque = (harvest_recipient, alpha_token.address, amount, 0, 0, False, True)

    bad_flags_nonce = signed_agent_sender_special_admin.currentNonce(user_wallet.address)
    with boa.reverts("invalid pull cheque flags"):
        signed_agent_sender_special_admin.issuePullCheques(
            starter_agent.address,
            user_wallet.address,
            [(pull_recipient, alpha_token.address, amount, 0, 0, True, False)],
            (b"\x00" * 65, bad_flags_nonce, boa.env.evm.patch.timestamp + 1000),
            sender=alice,
        )
    assert signed_agent_sender_special_admin.currentNonce(user_wallet.address) == bad_flags_nonce

    wrong_digest, wrong_nonce, wrong_expiration = agent_sender_special_sig_helper.getIssuePullChequesHash(
        signed_agent_sender_special_admin.address,
        bob,
        user_wallet.address,
        pull_cheques,
    )
    wrong_sig = create_signature_struct(test_signer.unsafe_sign_hash(
        wrong_digest).signature, wrong_nonce, wrong_expiration)
    nonce_before = signed_agent_sender_special_admin.currentNonce(user_wallet.address)
    with boa.reverts("invalid signer"):
        signed_agent_sender_special_admin.issuePullCheques(
            starter_agent.address,
            user_wallet.address,
            pull_cheques,
            wrong_sig,
            sender=alice,
        )
    assert signed_agent_sender_special_admin.currentNonce(user_wallet.address) == nonce_before

    digest, nonce, expiration = agent_sender_special_sig_helper.getIssuePullChequesHash(
        signed_agent_sender_special_admin.address,
        starter_agent.address,
        user_wallet.address,
        pull_cheques,
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    signed_agent_sender_special_admin.issuePullCheques(
        starter_agent.address,
        user_wallet.address,
        pull_cheques,
        sig,
        sender=alice,
    )
    assert signed_agent_sender_special_admin.currentNonce(user_wallet.address) == nonce_before + 1
    pull_cheque = user_wallet_config.cheques(pull_recipient)
    assert pull_cheque.active == True
    assert pull_cheque.canManagerPay == False
    assert pull_cheque.canBePulled == True

    kernel.addPendingWhitelistAddr(user_wallet.address, whitelist_addr, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    wrong_digest, wrong_nonce, wrong_expiration = agent_sender_special_sig_helper.getWhitelistMaintenanceHash(
        signed_agent_sender_special_admin.address,
        bob,
        user_wallet.address,
        [whitelist_addr],
        [],
        [],
    )
    wrong_sig = create_signature_struct(test_signer.unsafe_sign_hash(
        wrong_digest).signature, wrong_nonce, wrong_expiration)
    with boa.reverts("invalid signer"):
        signed_agent_sender_special_admin.whitelistMaintenance(
            starter_agent.address,
            user_wallet.address,
            [whitelist_addr],
            [],
            [],
            wrong_sig,
            sender=alice,
        )
    assert signed_agent_sender_special_admin.currentNonce(user_wallet.address) == nonce_before + 1

    digest, nonce, expiration = agent_sender_special_sig_helper.getWhitelistMaintenanceHash(
        signed_agent_sender_special_admin.address,
        starter_agent.address,
        user_wallet.address,
        [whitelist_addr],
        [],
        [],
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    signed_agent_sender_special_admin.whitelistMaintenance(
        starter_agent.address,
        user_wallet.address,
        [whitelist_addr],
        [],
        [],
        sig,
        sender=alice,
    )
    assert signed_agent_sender_special_admin.currentNonce(user_wallet.address) == nonce_before + 2
    assert user_wallet_config.indexOfWhitelist(whitelist_addr) != 0

    wrong_digest, wrong_nonce, wrong_expiration = agent_sender_special_sig_helper.getHarvestAndIssueChequeHash(
        signed_agent_sender_special_admin.address,
        bob,
        user_wallet.address,
        0,
        ZERO_ADDRESS,
        MAX_UINT256,
        [],
        [],
        harvest_cheque,
    )
    wrong_sig = create_signature_struct(test_signer.unsafe_sign_hash(
        wrong_digest).signature, wrong_nonce, wrong_expiration)
    with boa.reverts("invalid signer"):
        signed_agent_sender_special_admin.harvestAndIssueCheque(
            starter_agent.address,
            user_wallet.address,
            0,
            ZERO_ADDRESS,
            MAX_UINT256,
            [],
            [],
            harvest_cheque,
            wrong_sig,
            sender=alice,
        )
    assert signed_agent_sender_special_admin.currentNonce(user_wallet.address) == nonce_before + 2

    digest, nonce, expiration = agent_sender_special_sig_helper.getHarvestAndIssueChequeHash(
        signed_agent_sender_special_admin.address,
        starter_agent.address,
        user_wallet.address,
        0,
        ZERO_ADDRESS,
        MAX_UINT256,
        [],
        [],
        harvest_cheque,
    )
    sig = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    signed_agent_sender_special_admin.harvestAndIssueCheque(
        starter_agent.address,
        user_wallet.address,
        0,
        ZERO_ADDRESS,
        MAX_UINT256,
        [],
        [],
        harvest_cheque,
        sig,
        sender=alice,
    )
    assert signed_agent_sender_special_admin.currentNonce(user_wallet.address) == nonce_before + 3
    issued_cheque = user_wallet_config.cheques(harvest_recipient)
    assert issued_cheque.active == True
    assert issued_cheque.amount == amount


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
    valid_transfer_recipient,
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
            target=valid_transfer_recipient,
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
        target=valid_transfer_recipient,
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


def test_create_and_pay_cheque_signature_hash_differs_from_transfer(
    user_wallet_signature_helper,
    starter_agent,
    signed_agent_sender,
    user_wallet,
    alice,
    alpha_token,
):
    amount = 15 * EIGHTEEN_DECIMALS
    instant_digest, instant_nonce, instant_expiration = user_wallet_signature_helper.getCreateAndPayChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
    )
    transfer_digest, transfer_nonce, transfer_expiration = user_wallet_signature_helper.getTransferFundsHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
    )

    assert instant_digest != transfer_digest
    assert instant_nonce == transfer_nonce
    assert instant_expiration == transfer_expiration


def test_create_and_pay_cheque_valid_signature_succeeds(
    setupAgentTestAsset,
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    test_signer,
    create_signature_struct,
    createChequeSettings,
):
    amount = 20 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _expensive_delay_blocks=5,
    )

    digest, nonce, expiration = user_wallet_signature_helper.getCreateAndPayChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
    )
    signature = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    recipient_balance_before = alpha_token.balanceOf(alice)
    current_nonce = signed_agent_sender.currentNonce(user_wallet.address)

    amount_paid, usd_value = signed_agent_sender.createAndPayCheque(
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        signature,
        sender=alice
    )

    assert amount_paid == amount
    assert usd_value == amount
    assert alpha_token.balanceOf(alice) == recipient_balance_before + amount
    assert signed_agent_sender.currentNonce(user_wallet.address) == current_nonce + 1
    assert user_wallet_config.cheques(alice).active == False


def test_create_and_pay_cheque_rejects_transfer_signature(
    setupAgentTestAsset,
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    test_signer,
    create_signature_struct,
    createChequeSettings,
):
    amount = 10 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _expensive_delay_blocks=5,
    )

    digest, nonce, expiration = user_wallet_signature_helper.getTransferFundsHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
    )
    signature = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    current_nonce = signed_agent_sender.currentNonce(user_wallet.address)

    with boa.reverts("invalid signer"):
        signed_agent_sender.createAndPayCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            amount,
            signature,
            sender=alice
        )

    assert signed_agent_sender.currentNonce(user_wallet.address) == current_nonce


def test_wrapper_bound_signature_cannot_replay_across_wrappers(
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    alpha_token,
    alice,
    test_signer,
    create_signature_struct,
    undy_hq_deploy,
    switchboard_alpha,
):
    amount = 5 * EIGHTEEN_DECIMALS
    digest, nonce, expiration = user_wallet_signature_helper.getCreateAndPayChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
    )
    signature = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)

    other_agent = boa.load(
        "contracts/core/agent/AgentWrapper.vy",
        undy_hq_deploy,
        1,
        [signed_agent_sender],
        name="other_agent_wrapper",
    )
    current_nonce = signed_agent_sender.currentNonce(user_wallet.address)

    with boa.reverts("invalid signer"):
        signed_agent_sender.createAndPayCheque(
            other_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            amount,
            signature,
            sender=alice
        )

    assert signed_agent_sender.currentNonce(user_wallet.address) == current_nonce


def test_non_manager_wrapper_signature_reverts_downstream_no_perms(
    setupAgentTestAsset,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    alpha_token,
    alpha_token_whale,
    valid_transfer_recipient,
    alice,
    test_signer,
    create_signature_struct,
    undy_hq_deploy,
    switchboard_alpha,
):
    amount = 4 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=25 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    other_agent = boa.load(
        "contracts/core/agent/AgentWrapper.vy",
        undy_hq_deploy,
        1,
        [signed_agent_sender],
        name="non_manager_agent_wrapper",
    )

    digest, nonce, expiration = user_wallet_signature_helper.getTransferFundsHash(
        signed_agent_sender.address,
        other_agent.address,
        user_wallet.address,
        valid_transfer_recipient,
        alpha_token.address,
        amount,
    )
    signature = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    current_nonce = signed_agent_sender.currentNonce(user_wallet.address)

    with boa.reverts("no permission"):
        signed_agent_sender.transferFunds(
            other_agent.address,
            user_wallet.address,
            valid_transfer_recipient,
            alpha_token.address,
            amount,
            signature,
            sender=alice,
        )
    assert signed_agent_sender.currentNonce(user_wallet.address) == current_nonce


def test_pay_cheque_signature_expected_creation_block_zero_reverts(
    setupAgentTestAsset,
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    test_signer,
    create_signature_struct,
    createChequeSettings,
):
    amount = 11 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _expensive_delay_blocks=5,
    )

    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
        True,
        False,
        sender=bob
    )
    assert user_wallet_config.cheques(alice).active == True

    digest, nonce, expiration = user_wallet_signature_helper.getPayChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
        0,
    )
    signature = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)
    current_nonce = signed_agent_sender.currentNonce(user_wallet.address)

    with boa.reverts("invalid expected block"):
        signed_agent_sender.payCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            amount,
            0,
            signature,
            sender=alice
        )

    assert signed_agent_sender.currentNonce(user_wallet.address) == current_nonce
    assert user_wallet_config.cheques(alice).active == True


def test_pay_cheque_signature_expected_creation_block_blocks_stale_replay(
    setupAgentTestAsset,
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    test_signer,
    create_signature_struct,
    createChequeSettings,
):
    amount = 11 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _expensive_delay_blocks=5,
    )

    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
        True,
        False,
        sender=bob
    )
    creation_block_1 = user_wallet_config.cheques(alice).creationBlock
    digest, nonce, expiration = user_wallet_signature_helper.getPayChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        creation_block_1,
        0,
        0,
    )
    stale_signature = create_signature_struct(test_signer.unsafe_sign_hash(digest).signature, nonce, expiration)

    cheque_book.cancelCheque(user_wallet.address, alice, sender=bob)
    boa.env.time_travel(blocks=1)
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
        True,
        False,
        sender=bob
    )
    creation_block_2 = user_wallet_config.cheques(alice).creationBlock
    assert creation_block_2 != creation_block_1
    current_nonce = signed_agent_sender.currentNonce(user_wallet.address)

    with boa.reverts("stale cheque"):
        signed_agent_sender.payCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            amount,
            creation_block_1,
            stale_signature,
            sender=alice
        )
    assert signed_agent_sender.currentNonce(user_wallet.address) == current_nonce

    fresh_digest, fresh_nonce, fresh_expiration = user_wallet_signature_helper.getPayChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        creation_block_2,
        0,
        0,
    )
    fresh_signature = create_signature_struct(test_signer.unsafe_sign_hash(
        fresh_digest).signature, fresh_nonce, fresh_expiration)

    amount_paid, usd_value = signed_agent_sender.payCheque(
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        creation_block_2,
        fresh_signature,
        sender=alice
    )
    assert amount_paid == amount
    assert usd_value == amount
    assert user_wallet_config.cheques(alice).active == False


def test_interleaved_transfer_pay_cheque_and_claim_loot_nonces(
    setupAgentTestAsset,
    starter_agent,
    signed_agent_sender,
    user_wallet_signature_helper,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    valid_transfer_recipient,
    test_signer,
    create_signature_struct,
    createChequeSettings,
):
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _expensive_delay_blocks=5,
    )

    cheque_amount = 6 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        cheque_amount,
        0,
        0,
        True,
        False,
        sender=bob,
    )
    creation_block = user_wallet_config.cheques(alice).creationBlock
    expiration = boa.env.evm.patch.timestamp + 3600
    nonce_0 = signed_agent_sender.currentNonce(user_wallet.address)

    transfer_digest, _, _ = user_wallet_signature_helper.getTransferFundsHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        valid_transfer_recipient,
        alpha_token.address,
        2 * EIGHTEEN_DECIMALS,
        nonce_0,
        expiration,
    )
    stale_pay_digest, _, _ = user_wallet_signature_helper.getPayChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        cheque_amount,
        creation_block,
        nonce_0,
        expiration,
    )
    transfer_sig = create_signature_struct(test_signer.unsafe_sign_hash(
        transfer_digest).signature, nonce_0, expiration)
    stale_pay_sig = create_signature_struct(test_signer.unsafe_sign_hash(
        stale_pay_digest).signature, nonce_0, expiration)

    signed_agent_sender.transferFunds(
        starter_agent.address,
        user_wallet.address,
        valid_transfer_recipient,
        alpha_token.address,
        2 * EIGHTEEN_DECIMALS,
        transfer_sig,
        sender=alice,
    )
    assert signed_agent_sender.currentNonce(user_wallet.address) == nonce_0 + 1

    with boa.reverts("invalid nonce"):
        signed_agent_sender.payCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            cheque_amount,
            creation_block,
            stale_pay_sig,
            sender=alice,
        )

    pay_digest, nonce_1, pay_expiration = user_wallet_signature_helper.getPayChequeHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        cheque_amount,
        creation_block,
    )
    pay_sig = create_signature_struct(test_signer.unsafe_sign_hash(pay_digest).signature, nonce_1, pay_expiration)
    signed_agent_sender.payCheque(
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        cheque_amount,
        creation_block,
        pay_sig,
        sender=alice,
    )
    assert signed_agent_sender.currentNonce(user_wallet.address) == nonce_0 + 2

    claim_digest, nonce_2, claim_expiration = user_wallet_signature_helper.getClaimAllLootHash(
        signed_agent_sender.address,
        starter_agent.address,
        user_wallet.address,
    )
    claim_sig = create_signature_struct(test_signer.unsafe_sign_hash(
        claim_digest).signature, nonce_2, claim_expiration)
    signed_agent_sender.claimAllLoot(
        starter_agent.address,
        user_wallet.address,
        claim_sig,
        sender=alice,
    )
    assert signed_agent_sender.currentNonce(user_wallet.address) == nonce_0 + 3

    with boa.reverts("invalid nonce"):
        signed_agent_sender.transferFunds(
            starter_agent.address,
            user_wallet.address,
            valid_transfer_recipient,
            alpha_token.address,
            2 * EIGHTEEN_DECIMALS,
            transfer_sig,
            sender=alice,
        )
