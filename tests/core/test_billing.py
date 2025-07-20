import boa
import pytest

from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS
from conf_utils import filter_logs

ONE_WEEK_IN_BLOCKS = ONE_DAY_IN_BLOCKS * 7


##########################
# Pull Payment As Cheque #
##########################


def test_pullPaymentAsCheque_success_basic(
    billing, bob, alice, alpha_token, alpha_token_whale, user_wallet, cheque_book, mock_ripe
):
    """Test successful pull payment as cheque with basic setup"""
    # Setup cheque settings with canBePulled enabled
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled - Enable pull payments
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)  # $1 per token
    
    # Create cheque with canBePulled enabled
    amount = 50 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,  # canManagerPay
        True,  # canBePulled - Enable for this specific cheque
        sender=bob
    )
    
    # Advance time to unlock the cheque
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Fund the wallet
    alpha_token.transfer(user_wallet.address, amount, sender=alpha_token_whale)
    
    # Alice pulls payment
    initial_balance = alpha_token.balanceOf(alice)
    tx_amount, tx_usd_value = billing.pullPaymentAsCheque(
        user_wallet.address,
        alpha_token.address,
        amount,
        sender=alice
    )
    
    # Verify payment was pulled
    assert tx_amount == amount
    assert tx_usd_value == amount  # $1 per token
    assert alpha_token.balanceOf(alice) == initial_balance + amount
    
    # Verify event
    events = filter_logs(billing, "ChequePaymentPulled")
    assert len(events) == 1
    event = events[0]
    assert event.asset == alpha_token.address
    assert event.amount == amount
    assert event.usdValue == amount
    assert event.chequeRecipient == alice
    assert event.userWallet == user_wallet.address


def test_pullPaymentAsCheque_fails_not_user_wallet(
    billing, alice, alpha_token
):
    """Test that pull payment fails when address is not a user wallet"""
    invalid_wallet = boa.env.generate_address()
    
    with boa.reverts("not a user wallet"):
        billing.pullPaymentAsCheque(
            invalid_wallet,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            sender=alice
        )


def test_pullPaymentAsCheque_fails_cheque_settings_disabled(
    billing, bob, alice, alpha_token, user_wallet, cheque_book, mock_ripe
):
    """Test that pull payment fails when cheque settings canBePulled is disabled"""
    # Setup cheque settings with canBePulled disabled
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled - Disable pull payments globally
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheque - canBePulled must be False when global setting is disabled
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,  # canBePulled
        sender=bob
    )
    
    # Alice tries to pull payment
    with boa.reverts("no perms"):
        billing.pullPaymentAsCheque(
            user_wallet.address,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            sender=alice
        )


def test_pullPaymentAsCheque_fails_cheque_canBePulled_disabled(
    billing, bob, alice, alpha_token, user_wallet, cheque_book, mock_ripe
):
    """Test that pull payment fails when specific cheque canBePulled is disabled"""
    # Setup cheque settings with canBePulled enabled globally
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled - Enable pull payments globally
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheque with canBePulled disabled
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,  # canBePulled - Disabled for this specific cheque
        sender=bob
    )
    
    # Alice tries to pull payment
    with boa.reverts("no perms"):
        billing.pullPaymentAsCheque(
            user_wallet.address,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            sender=alice
        )


def test_pullPaymentAsCheque_fails_no_cheque_exists(
    billing, bob, alice, alpha_token, user_wallet, cheque_book
):
    """Test that pull payment fails when no cheque exists for recipient"""
    # Setup cheque settings with canBePulled enabled
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )
    
    # Alice tries to pull payment without any cheque
    with boa.reverts("no perms"):
        billing.pullPaymentAsCheque(
            user_wallet.address,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            sender=alice
        )


def test_pullPaymentAsCheque_insufficient_funds_reverts(
    billing, bob, alice, alpha_token, user_wallet, cheque_book, mock_ripe
):
    """Test that pull payment reverts when wallet has insufficient funds"""
    # Setup cheque settings and create cheque
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheque
    amount = 50 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,
        sender=bob
    )
    
    # Advance time to unlock the cheque
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Don't fund the wallet - leave it empty
    
    # Alice tries to pull payment - should revert with insufficient funds
    with boa.reverts("insufficient funds"):
        billing.pullPaymentAsCheque(
            user_wallet.address,
            alpha_token.address,
            amount,
            sender=alice
        )


def test_pullPaymentAsCheque_with_vault_withdrawal(
    billing, bob, alice, alpha_token, alpha_token_whale, user_wallet, cheque_book, mock_ripe,
    alpha_token_vault
):
    """Test pull payment that requires withdrawal from vault"""
    # Setup cheque settings
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheque
    amount = 50 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,
        sender=bob
    )
    
    # Advance time to unlock the cheque
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Fund the wallet with tokens and deposit into vault
    total_funds = 60 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet.address, total_funds, sender=alpha_token_whale)
    
    # Deposit 40 tokens into vault, keep 20 in wallet
    user_wallet.depositForYield(
        1,  # legoId for mock_yield_lego
        alpha_token.address,
        alpha_token_vault.address,
        40 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    # Verify initial state
    assert alpha_token.balanceOf(user_wallet.address) == 20 * EIGHTEEN_DECIMALS
    assert alpha_token_vault.balanceOf(user_wallet.address) > 0
    
    # Verify price per share is 1:1 (initial deposit ratio)
    # No need to set - vault automatically calculates based on assets/shares
    
    # Alice pulls payment (needs 50 but only 20 in wallet, so 30 from vault)
    initial_alice_balance = alpha_token.balanceOf(alice)
    tx_amount, tx_usd_value = billing.pullPaymentAsCheque(
        user_wallet.address,
        alpha_token.address,
        amount,
        sender=alice
    )
    
    # Verify payment was pulled
    assert tx_amount == amount
    assert tx_usd_value == amount
    assert alpha_token.balanceOf(alice) == initial_alice_balance + amount
    
    # Verify vault tokens were withdrawn
    assert alpha_token_vault.balanceOf(user_wallet.address) < 40 * EIGHTEEN_DECIMALS
    
    # Verify event
    events = filter_logs(billing, "ChequePaymentPulled")
    assert len(events) == 1


def test_pullPaymentAsCheque_with_multiple_vaults(
    billing, bob, alice, alpha_token, alpha_token_whale, user_wallet, cheque_book, mock_ripe,
    alpha_token_vault, alpha_token_vault_2, alpha_token_vault_3
):
    """Test pull payment that withdraws from multiple vaults"""
    # Setup cheque settings
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheque
    amount = 100 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,
        sender=bob
    )
    
    # Advance time to unlock the cheque
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Fund the wallet and split across vaults
    total_funds = 120 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet.address, total_funds, sender=alpha_token_whale)
    
    # Deposit into multiple vaults: 30 in each vault, keep 30 in wallet
    user_wallet.depositForYield(
        1,  # legoId
        alpha_token.address,
        alpha_token_vault.address,
        30 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    user_wallet.depositForYield(
        1,  # legoId
        alpha_token.address,
        alpha_token_vault_2.address,
        30 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    user_wallet.depositForYield(
        1,  # legoId
        alpha_token.address,
        alpha_token_vault_3.address,
        30 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    # Verify initial state
    assert alpha_token.balanceOf(user_wallet.address) == 30 * EIGHTEEN_DECIMALS
    
    # Verify price per share is 1:1 for all vaults (initial deposit ratio)
    # No need to set - vaults automatically calculate based on assets/shares
    
    # Alice pulls payment (needs 100: 30 from wallet + 70 from vaults)
    initial_alice_balance = alpha_token.balanceOf(alice)
    tx_amount, tx_usd_value = billing.pullPaymentAsCheque(
        user_wallet.address,
        alpha_token.address,
        amount,
        sender=alice
    )
    
    # Verify payment was pulled
    assert tx_amount == amount
    assert tx_usd_value == amount
    assert alpha_token.balanceOf(alice) == initial_alice_balance + amount
    
    # Verify withdrawals happened from vaults
    total_remaining_in_vaults = (
        alpha_token_vault.balanceOf(user_wallet.address) +
        alpha_token_vault_2.balanceOf(user_wallet.address) +
        alpha_token_vault_3.balanceOf(user_wallet.address)
    )
    assert total_remaining_in_vaults < 90 * EIGHTEEN_DECIMALS


def test_pullPaymentAsCheque_partial_funds_reverts(
    billing, bob, alice, alpha_token, alpha_token_whale, user_wallet, cheque_book, mock_ripe
):
    """Test that pull payment reverts when wallet has partial funds (cheques require full payment)"""
    # Setup cheque settings
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheque for 100 tokens
    cheque_amount = 100 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        cheque_amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,
        sender=bob
    )
    
    # Advance time to unlock the cheque
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Fund the wallet with only partial amount (60 tokens instead of 100)
    partial_amount = 60 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet.address, partial_amount, sender=alpha_token_whale)
    
    # Verify wallet has partial funds
    assert alpha_token.balanceOf(user_wallet.address) == partial_amount
    
    # Alice tries to pull full cheque amount - should revert since cheques don't support partial payments
    with boa.reverts("insufficient funds"):
        billing.pullPaymentAsCheque(
            user_wallet.address,
            alpha_token.address,
            cheque_amount,
            sender=alice
        )


def test_pullPaymentAsCheque_with_yield_gains(
    billing, bob, alice, alpha_token, alpha_token_whale, user_wallet, cheque_book,
    mock_ripe, alpha_token_vault
):
    """Test pull payment when vault has generated yield"""
    # Setup cheque settings
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheque
    amount = 50 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,
        sender=bob
    )
    
    # Advance time to unlock the cheque
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Fund the wallet and deposit all into vault
    alpha_token.transfer(user_wallet.address, amount, sender=alpha_token_whale)
    
    user_wallet.depositForYield(
        1,  # legoId
        alpha_token.address,
        alpha_token_vault.address,
        amount,
        sender=bob
    )
    
    # Simulate yield generation: add 20% to vault
    yield_amount = 10 * EIGHTEEN_DECIMALS
    alpha_token.transfer(alpha_token_vault.address, yield_amount, sender=alpha_token_whale)
    
    # Price per share automatically reflects yield (1.2:1)
    # Vault now has 60 tokens (50 + 10 yield) backing 50 shares = 1.2x
    
    # Check vault state before withdrawal
    shares_before = alpha_token_vault.balanceOf(user_wallet.address)
    assert shares_before == amount  # 50 shares
    assets_before = alpha_token_vault.convertToAssets(shares_before)
    assert assets_before == 60 * EIGHTEEN_DECIMALS  # 60 tokens due to yield
    
    # Alice pulls payment
    initial_balance = alpha_token.balanceOf(alice)
    
    # Debug: check what's happening with vault
    wallet_balance_before = alpha_token.balanceOf(user_wallet.address)
    vault_balance_before = alpha_token.balanceOf(alpha_token_vault.address)
    
    tx_amount, tx_usd_value = billing.pullPaymentAsCheque(
        user_wallet.address,
        alpha_token.address,
        amount,
        sender=alice
    )
    
    # Verify payment was pulled
    assert tx_amount == amount
    assert tx_usd_value == amount
    assert alpha_token.balanceOf(alice) == initial_balance + amount
    
    # Verify vault was used and all shares were redeemed
    # The 1% buffer (50.5 tokens needed) causes the calculation to require ~42 shares
    # But since we only have 50 shares total, and the vault has 60 tokens,
    # preparePayment will withdraw all available shares to ensure we get enough
    shares_after = alpha_token_vault.balanceOf(user_wallet.address)
    assert shares_after == 0  # All shares withdrawn due to buffer calculation
    
    # Verify the vault gave us all 60 tokens (50 + 10 yield)
    vault_balance_after = alpha_token.balanceOf(alpha_token_vault.address)
    assert vault_balance_after == 0  # Vault completely emptied
    
    # The wallet should have received the 10 token yield bonus
    wallet_final_balance = alpha_token.balanceOf(user_wallet.address)
    assert wallet_final_balance == 10 * EIGHTEEN_DECIMALS  # 10 tokens of yield remain in wallet


def test_canPullPaymentAsCheque_view_function(
    billing, bob, alice, charlie, sally, alpha_token, user_wallet, cheque_book, mock_ripe
):
    """Test canPullPaymentAsCheque view function showing all combinations of settings"""
    # Initially no cheque exists
    assert billing.canPullPaymentAsCheque(user_wallet.address, alice) == False
    
    # Set price
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Test Case 1: Both global and cheque canBePulled are False
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        False,  # canBePulled - DISABLED globally
        sender=bob
    )
    
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,  # canBePulled - DISABLED for cheque
        sender=bob
    )
    
    # Both false = cannot pull
    assert billing.canPullPaymentAsCheque(user_wallet.address, alice) == False
    
    # Test Case 2: Enable global canBePulled, existing alice cheque still has canBePulled=False
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled - ENABLED globally
        sender=bob
    )
    
    # Alice: Global true, but Cheque false (from earlier) = cannot pull
    assert billing.canPullPaymentAsCheque(user_wallet.address, alice) == False
    
    # Test Case 3: Create cheque with both global and cheque canBePulled=True
    cheque_book.createCheque(
        user_wallet.address,
        charlie,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,  # canBePulled - ENABLED for cheque
        sender=bob
    )
    
    # Charlie: Global true, Cheque true = CAN PULL
    assert billing.canPullPaymentAsCheque(user_wallet.address, charlie) == True
    
    # Test Case 4: Create cheque with global True but cheque False
    cheque_book.createCheque(
        user_wallet.address,
        sally,
        alpha_token.address,
        50 * EIGHTEEN_DECIMALS,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        False,  # canBePulled - DISABLED for cheque
        sender=bob
    )
    
    # Sally: Global true, Cheque false = cannot pull
    assert billing.canPullPaymentAsCheque(user_wallet.address, sally) == False
    
    # Summary of results:
    # - Both must be true for pull payment to be allowed
    # - Global False + Cheque False = Cannot pull (alice)
    # - Global True + Cheque False = Cannot pull (alice after settings change, sally)
    # - Global True + Cheque True = CAN PULL (charlie)
    # NOTE: When global canBePulled is False, you cannot create a cheque with canBePulled=True


def test_pullPaymentAsCheque_deregisters_empty_vault(
    billing, bob, alice, alpha_token, alpha_token_whale, user_wallet, cheque_book,
    mock_ripe, alpha_token_vault
):
    """Test that empty vault assets are deregistered after withdrawal"""
    # Setup cheque settings
    cheque_book.setChequeSettings(
        user_wallet.address,
        0,  # maxNumActiveCheques
        0,  # maxChequeUsdValue
        100 * EIGHTEEN_DECIMALS,  # instantUsdThreshold
        0,  # perPeriodPaidUsdCap
        0,  # maxNumChequesPaidPerPeriod
        0,  # payCooldownBlocks
        0,  # perPeriodCreatedUsdCap
        0,  # maxNumChequesCreatedPerPeriod
        0,  # createCooldownBlocks
        ONE_MONTH_IN_BLOCKS,  # periodLength
        ONE_DAY_IN_BLOCKS,  # expensiveDelayBlocks
        0,  # defaultExpiryBlocks
        [],  # allowedAssets
        True,  # canManagersCreateCheques
        True,  # canManagerPay
        True,  # canBePulled
        sender=bob
    )
    
    # Set price for the asset
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    
    # Create cheque
    amount = 50 * EIGHTEEN_DECIMALS
    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        ONE_DAY_IN_BLOCKS,
        ONE_WEEK_IN_BLOCKS,
        True,
        True,
        sender=bob
    )
    
    # Advance time to unlock the cheque
    boa.env.time_travel(blocks=ONE_DAY_IN_BLOCKS + 1)
    
    # Fund the wallet and deposit all into vault
    alpha_token.transfer(user_wallet.address, amount, sender=alpha_token_whale)
    
    user_wallet.depositForYield(
        1,  # legoId
        alpha_token.address,
        alpha_token_vault.address,
        amount,
        sender=bob
    )
    
    # Verify vault is registered
    assert user_wallet.indexOfAsset(alpha_token_vault.address) > 0
    
    # Verify price per share is 1:1 (initial deposit ratio)
    # No need to set - vault automatically calculates based on assets/shares
    
    # Alice pulls full payment (empties the vault)
    tx_amount, tx_usd_value = billing.pullPaymentAsCheque(
        user_wallet.address,
        alpha_token.address,
        amount,
        sender=alice
    )
    
    # Verify payment was pulled
    assert tx_amount == amount
    
    # Verify vault was emptied and deregistered
    assert alpha_token_vault.balanceOf(user_wallet.address) == 0
    assert user_wallet.indexOfAsset(alpha_token_vault.address) == 0