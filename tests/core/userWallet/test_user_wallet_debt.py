import pytest
import boa

from contracts.core.userWallet import UserWallet
from contracts.core.userWallet import UserWalletConfig
from constants import EIGHTEEN_DECIMALS, MAX_UINT256, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setupDebtTest(user_wallet, mock_dex_lego, mock_dex_asset, lego_book, mock_ripe, switchboard_alpha, whale):
    def setupDebtTest():
        lego_id = lego_book.getRegId(mock_dex_lego.address)
        
        # Set price for asset
        mock_ripe.setPrice(mock_dex_asset, 2 * EIGHTEEN_DECIMALS)  # $2
        
        # Transfer some tokens to the user wallet
        amount = 1000 * EIGHTEEN_DECIMALS
        mock_dex_asset.transfer(user_wallet, amount, sender=whale)
        
        # Register asset in wallet config
        wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
        wallet_config.updateAssetData(lego_id, mock_dex_asset, False, sender=switchboard_alpha.address)
        
        # Set access for mock_dex_lego (required for collateral operations)
        mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)

        return amount

    yield setupDebtTest


########################
# Add Collateral Tests #
########################


def test_add_collateral_basic(setupDebtTest, user_wallet, bob, mock_dex_asset):
    """Test basic add collateral functionality"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Check initial balance
    initial_balance = mock_dex_asset.balanceOf(user_wallet)
    initial_asset_data = user_wallet.assetData(mock_dex_asset.address)
    
    # Add collateral
    collateral_amount = 200 * EIGHTEEN_DECIMALS
    amount_deposited, usd_value = user_wallet.addCollateral(
        lego_id,
        mock_dex_asset.address,
        collateral_amount,
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values
    assert amount_deposited == collateral_amount
    assert usd_value == 400 * EIGHTEEN_DECIMALS  # 200 tokens * $2
    
    # Check balance decreased (tokens sent to lego)
    assert mock_dex_asset.balanceOf(user_wallet) == initial_balance - collateral_amount
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 40  # ADD_COLLATERAL operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == ZERO_ADDRESS  # Empty address for collateral ops
    assert log.amount1 == collateral_amount
    assert log.amount2 == 0
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob
    
    # Check storage updated
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    assert asset_data.assetBalance == initial_balance - collateral_amount
    assert asset_data.usdValue == (initial_balance - collateral_amount) * 2  # Remaining balance * $2


def test_add_collateral_max_value(setupDebtTest, user_wallet, bob, mock_dex_asset):
    """Test adding collateral with MAX_UINT256 to use entire balance"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Get current balance
    current_balance = mock_dex_asset.balanceOf(user_wallet)
    
    # Add all as collateral using max value
    amount_deposited, usd_value = user_wallet.addCollateral(
        lego_id,
        mock_dex_asset.address,
        MAX_UINT256,  # Use entire balance
        b"",
        sender=bob
    )
    
    # Verify entire balance was used
    assert amount_deposited == current_balance
    assert usd_value == current_balance * 2  # All tokens * $2
    assert mock_dex_asset.balanceOf(user_wallet) == 0
    
    # Check storage shows zero balance
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    assert asset_data.assetBalance == 0
    assert asset_data.usdValue == 0


def test_add_collateral_multiple_deposits(setupDebtTest, user_wallet, bob, mock_dex_lego, mock_dex_asset):
    """Test multiple sequential collateral deposits"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    initial_balance = mock_dex_asset.balanceOf(user_wallet)
    
    # First deposit
    deposit1_amount = 100 * EIGHTEEN_DECIMALS
    amount1, usd1 = user_wallet.addCollateral(
        lego_id,
        mock_dex_asset.address,
        deposit1_amount,
        b"",
        sender=bob
    )
    
    assert amount1 == deposit1_amount
    assert mock_dex_asset.balanceOf(user_wallet) == initial_balance - deposit1_amount
    
    # Second deposit
    deposit2_amount = 150 * EIGHTEEN_DECIMALS
    amount2, usd2 = user_wallet.addCollateral(
        lego_id,
        mock_dex_asset.address,
        deposit2_amount,
        b"",
        sender=bob
    )
    
    assert amount2 == deposit2_amount
    assert mock_dex_asset.balanceOf(user_wallet) == initial_balance - deposit1_amount - deposit2_amount
    
    # Third deposit
    deposit3_amount = 50 * EIGHTEEN_DECIMALS
    amount3, usd3 = user_wallet.addCollateral(
        lego_id,
        mock_dex_asset.address,
        deposit3_amount,
        b"",
        sender=bob
    )
    
    assert amount3 == deposit3_amount
    
    # Verify final state
    total_deposited = deposit1_amount + deposit2_amount + deposit3_amount
    assert mock_dex_asset.balanceOf(user_wallet) == initial_balance - total_deposited
    
    # Check storage
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    assert asset_data.assetBalance == initial_balance - total_deposited


###########################
# Remove Collateral Tests #
###########################


def test_remove_collateral_basic(setupDebtTest, user_wallet, bob, mock_dex_asset):
    """Test basic remove collateral functionality"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # First add some collateral
    add_amount = 300 * EIGHTEEN_DECIMALS
    user_wallet.addCollateral(
        lego_id,
        mock_dex_asset.address,
        add_amount,
        b"",
        sender=bob
    )
    
    # Check balance after adding collateral
    balance_after_add = mock_dex_asset.balanceOf(user_wallet)
    
    # Remove some collateral
    remove_amount = 100 * EIGHTEEN_DECIMALS
    amount_removed, usd_value = user_wallet.removeCollateral(
        lego_id,
        mock_dex_asset.address,
        remove_amount,
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values
    assert amount_removed == remove_amount
    assert usd_value == 200 * EIGHTEEN_DECIMALS  # 100 tokens * $2
    
    # Check balance increased (tokens returned from lego)
    assert mock_dex_asset.balanceOf(user_wallet) == balance_after_add + remove_amount
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 41  # REMOVE_COLLATERAL operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == ZERO_ADDRESS  # Empty address for collateral ops
    assert log.amount1 == remove_amount
    assert log.amount2 == 0
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob
    
    # Check storage updated
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    assert asset_data.assetBalance == balance_after_add + remove_amount


def test_remove_collateral_partial(setupDebtTest, user_wallet, bob, mock_dex_asset):
    """Test removing partial collateral"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # First add some collateral
    add_amount = 500 * EIGHTEEN_DECIMALS
    user_wallet.addCollateral(
        lego_id,
        mock_dex_asset.address,
        add_amount,
        b"",
        sender=bob
    )
    
    balance_after_add = mock_dex_asset.balanceOf(user_wallet)
    
    # Remove partial amount
    remove_amount = 200 * EIGHTEEN_DECIMALS
    amount_removed, usd_value = user_wallet.removeCollateral(
        lego_id,
        mock_dex_asset.address,
        remove_amount,
        b"",
        sender=bob
    )
    
    # Verify partial removal
    assert amount_removed == remove_amount
    assert usd_value == 400 * EIGHTEEN_DECIMALS  # 200 tokens * $2
    assert mock_dex_asset.balanceOf(user_wallet) == balance_after_add + remove_amount


def test_add_remove_collateral_cycle(setupDebtTest, user_wallet, bob, mock_dex_asset):
    """Test adding and removing collateral in cycles"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    initial_balance = mock_dex_asset.balanceOf(user_wallet)
    
    # Cycle 1: Add 200, remove 50
    user_wallet.addCollateral(lego_id, mock_dex_asset.address, 200 * EIGHTEEN_DECIMALS, sender=bob)
    user_wallet.removeCollateral(lego_id, mock_dex_asset.address, 50 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Net: -150 tokens
    assert mock_dex_asset.balanceOf(user_wallet) == initial_balance - 150 * EIGHTEEN_DECIMALS
    
    # Cycle 2: Add 100, remove 200
    user_wallet.addCollateral(lego_id, mock_dex_asset.address, 100 * EIGHTEEN_DECIMALS, sender=bob)
    user_wallet.removeCollateral(lego_id, mock_dex_asset.address, 200 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Net: -150 + (-100 + 200) = -50 tokens
    assert mock_dex_asset.balanceOf(user_wallet) == initial_balance - 50 * EIGHTEEN_DECIMALS
    
    # Cycle 3: Remove 50 (no add)
    user_wallet.removeCollateral(lego_id, mock_dex_asset.address, 50 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Net: -50 + 50 = 0 (back to initial)
    assert mock_dex_asset.balanceOf(user_wallet) == initial_balance
    
    # Verify storage is consistent
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    assert asset_data.assetBalance == initial_balance


def test_collateral_operations_update_storage(setupDebtTest, user_wallet, bob, mock_dex_asset):
    """Test that collateral operations properly update asset data storage"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Check initial storage
    initial_data = user_wallet.assetData(mock_dex_asset.address)
    initial_balance = initial_data.assetBalance
    
    # Add collateral
    add_amount = 250 * EIGHTEEN_DECIMALS
    user_wallet.addCollateral(
        lego_id,
        mock_dex_asset.address,
        add_amount,
        sender=bob
    )
    
    # Check storage after add
    data_after_add = user_wallet.assetData(mock_dex_asset.address)
    assert data_after_add.assetBalance == initial_balance - add_amount
    assert data_after_add.usdValue == (initial_balance - add_amount) * 2  # $2 per token
    assert data_after_add.isYieldAsset == False
    
    # Remove collateral
    remove_amount = 100 * EIGHTEEN_DECIMALS
    user_wallet.removeCollateral(
        lego_id,
        mock_dex_asset.address,
        remove_amount,
        sender=bob
    )
    
    # Check storage after remove
    data_after_remove = user_wallet.assetData(mock_dex_asset.address)
    assert data_after_remove.assetBalance == initial_balance - add_amount + remove_amount
    assert data_after_remove.usdValue == (initial_balance - add_amount + remove_amount) * 2
    
    # Asset should still be registered
    assert user_wallet.indexOfAsset(mock_dex_asset.address) > 0


######################
# Borrow/Repay Tests #
######################


def test_borrow_basic(setupDebtTest, user_wallet, bob, mock_dex_debt_token, mock_ripe):
    """Test basic borrow functionality"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set price for debt token
    mock_ripe.setPrice(mock_dex_debt_token, 1 * EIGHTEEN_DECIMALS)  # $1 per debt token
    
    # Check initial balance (should be 0 for debt token)
    initial_balance = mock_dex_debt_token.balanceOf(user_wallet)
    assert initial_balance == 0
    
    # Borrow debt tokens
    borrow_amount = 300 * EIGHTEEN_DECIMALS
    amount_borrowed, usd_value = user_wallet.borrow(
        lego_id,
        mock_dex_debt_token.address,
        borrow_amount,
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values
    assert amount_borrowed == borrow_amount
    assert usd_value == 300 * EIGHTEEN_DECIMALS  # 300 tokens * $1
    
    # Check balance increased (debt tokens minted to wallet)
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow_amount
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 42  # BORROW operation
    assert log.asset1 == mock_dex_debt_token.address
    assert log.asset2 == ZERO_ADDRESS
    assert log.amount1 == borrow_amount
    assert log.amount2 == 0
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob
    
    # Check storage updated
    debt_data = user_wallet.assetData(mock_dex_debt_token.address)
    assert debt_data.assetBalance == borrow_amount
    assert debt_data.usdValue == usd_value
    assert debt_data.isYieldAsset == False
    
    # Debt token should be registered
    assert user_wallet.indexOfAsset(mock_dex_debt_token.address) > 0


def test_borrow_multiple_times(setupDebtTest, user_wallet, bob, mock_dex_debt_token, mock_ripe):
    """Test borrowing multiple times accumulates debt"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set price for debt token
    mock_ripe.setPrice(mock_dex_debt_token, 1 * EIGHTEEN_DECIMALS)  # $1
    
    # First borrow
    borrow1_amount = 100 * EIGHTEEN_DECIMALS
    amount1, usd1 = user_wallet.borrow(
        lego_id,
        mock_dex_debt_token.address,
        borrow1_amount,
        sender=bob
    )
    
    assert amount1 == borrow1_amount
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow1_amount
    
    # Second borrow
    borrow2_amount = 150 * EIGHTEEN_DECIMALS
    amount2, usd2 = user_wallet.borrow(
        lego_id,
        mock_dex_debt_token.address,
        borrow2_amount,
        sender=bob
    )
    
    assert amount2 == borrow2_amount
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow1_amount + borrow2_amount
    
    # Third borrow
    borrow3_amount = 50 * EIGHTEEN_DECIMALS
    amount3, usd3 = user_wallet.borrow(
        lego_id,
        mock_dex_debt_token.address,
        borrow3_amount,
        sender=bob
    )
    
    assert amount3 == borrow3_amount
    
    # Verify total borrowed
    total_borrowed = borrow1_amount + borrow2_amount + borrow3_amount
    assert mock_dex_debt_token.balanceOf(user_wallet) == total_borrowed
    
    # Check storage
    debt_data = user_wallet.assetData(mock_dex_debt_token.address)
    assert debt_data.assetBalance == total_borrowed
    assert debt_data.usdValue == total_borrowed  # $1 per token


def test_repay_debt_basic(setupDebtTest, user_wallet, bob, mock_dex_debt_token, mock_ripe):
    """Test basic debt repayment functionality"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set price for debt token
    mock_ripe.setPrice(mock_dex_debt_token, 1 * EIGHTEEN_DECIMALS)  # $1
    
    # First borrow some debt
    borrow_amount = 500 * EIGHTEEN_DECIMALS
    user_wallet.borrow(
        lego_id,
        mock_dex_debt_token.address,
        borrow_amount,
        sender=bob
    )
    
    balance_after_borrow = mock_dex_debt_token.balanceOf(user_wallet)
    assert balance_after_borrow == borrow_amount
    
    # Repay some debt
    repay_amount = 200 * EIGHTEEN_DECIMALS
    amount_repaid, usd_value = user_wallet.repayDebt(
        lego_id,
        mock_dex_debt_token.address,
        repay_amount,
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values
    assert amount_repaid == repay_amount
    assert usd_value == 200 * EIGHTEEN_DECIMALS  # 200 tokens * $1
    
    # Check balance decreased (debt tokens burned)
    assert mock_dex_debt_token.balanceOf(user_wallet) == balance_after_borrow - repay_amount
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 43  # REPAY_DEBT operation
    assert log.asset1 == mock_dex_debt_token.address
    assert log.asset2 == ZERO_ADDRESS
    assert log.amount1 == repay_amount
    assert log.amount2 == 0
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob
    
    # Check storage updated
    debt_data = user_wallet.assetData(mock_dex_debt_token.address)
    assert debt_data.assetBalance == balance_after_borrow - repay_amount
    assert debt_data.usdValue == (balance_after_borrow - repay_amount) * 1  # Remaining debt * $1


def test_repay_debt_max_value(setupDebtTest, user_wallet, bob, mock_dex_debt_token, mock_ripe):
    """Test repaying debt with MAX_UINT256 to repay entire balance"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set price for debt token
    mock_ripe.setPrice(mock_dex_debt_token, 1 * EIGHTEEN_DECIMALS)  # $1
    
    # First borrow some debt
    borrow_amount = 400 * EIGHTEEN_DECIMALS
    user_wallet.borrow(
        lego_id,
        mock_dex_debt_token.address,
        borrow_amount,
        sender=bob
    )
    
    current_balance = mock_dex_debt_token.balanceOf(user_wallet)
    
    # Repay with max value (should repay entire balance)
    amount_repaid, usd_value = user_wallet.repayDebt(
        lego_id,
        mock_dex_debt_token.address,
        MAX_UINT256,  # Repay all
        b"",
        sender=bob
    )
    
    # Verify entire balance was repaid
    assert amount_repaid == current_balance
    assert usd_value == current_balance  # All tokens * $1
    assert mock_dex_debt_token.balanceOf(user_wallet) == 0
    
    # Check storage shows zero balance
    debt_data = user_wallet.assetData(mock_dex_debt_token.address)
    assert debt_data.assetBalance == 0
    assert debt_data.usdValue == 0


def test_borrow_repay_cycle(setupDebtTest, user_wallet, bob, mock_dex_debt_token, mock_ripe):
    """Test cycles of borrowing and repaying debt"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set price for debt token
    mock_ripe.setPrice(mock_dex_debt_token, 1 * EIGHTEEN_DECIMALS)  # $1
    
    # Cycle 1: Borrow 300, repay 100
    user_wallet.borrow(lego_id, mock_dex_debt_token.address, 300 * EIGHTEEN_DECIMALS, sender=bob)
    user_wallet.repayDebt(lego_id, mock_dex_debt_token.address, 100 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Net: 200 debt tokens
    assert mock_dex_debt_token.balanceOf(user_wallet) == 200 * EIGHTEEN_DECIMALS
    
    # Cycle 2: Borrow 150, repay 250
    user_wallet.borrow(lego_id, mock_dex_debt_token.address, 150 * EIGHTEEN_DECIMALS, sender=bob)
    user_wallet.repayDebt(lego_id, mock_dex_debt_token.address, 250 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Net: 200 + 150 - 250 = 100 debt tokens
    assert mock_dex_debt_token.balanceOf(user_wallet) == 100 * EIGHTEEN_DECIMALS
    
    # Cycle 3: Repay remaining 100
    user_wallet.repayDebt(lego_id, mock_dex_debt_token.address, 100 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Net: 0 (all debt repaid)
    assert mock_dex_debt_token.balanceOf(user_wallet) == 0
    
    # Verify storage is consistent
    debt_data = user_wallet.assetData(mock_dex_debt_token.address)
    assert debt_data.assetBalance == 0
    assert debt_data.usdValue == 0


def test_borrow_with_collateral_workflow(setupDebtTest, user_wallet, bob, mock_dex_asset, mock_dex_debt_token, mock_ripe):
    """Test typical workflow: add collateral, borrow against it, repay debt, remove collateral"""
    setupDebtTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set price for debt token
    mock_ripe.setPrice(mock_dex_debt_token, 1 * EIGHTEEN_DECIMALS)  # $1
    
    initial_asset_balance = mock_dex_asset.balanceOf(user_wallet)
    
    # Step 1: Add collateral
    collateral_amount = 500 * EIGHTEEN_DECIMALS
    user_wallet.addCollateral(
        lego_id,
        mock_dex_asset.address,
        collateral_amount,
        sender=bob
    )
    
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset_balance - collateral_amount
    
    # Step 2: Borrow against collateral
    borrow_amount = 200 * EIGHTEEN_DECIMALS  # Borrow less than collateral value
    user_wallet.borrow(
        lego_id,
        mock_dex_debt_token.address,
        borrow_amount,
        sender=bob
    )
    
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow_amount
    
    # Step 3: Repay some debt
    repay_amount = 50 * EIGHTEEN_DECIMALS
    user_wallet.repayDebt(
        lego_id,
        mock_dex_debt_token.address,
        repay_amount,
        sender=bob
    )
    
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow_amount - repay_amount
    
    # Step 4: Remove some collateral (while still having debt)
    remove_collateral_amount = 100 * EIGHTEEN_DECIMALS
    user_wallet.removeCollateral(
        lego_id,
        mock_dex_asset.address,
        remove_collateral_amount,
        sender=bob
    )
    
    # Verify final state
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset_balance - collateral_amount + remove_collateral_amount
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow_amount - repay_amount
    
    # Check storage for both assets
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    debt_data = user_wallet.assetData(mock_dex_debt_token.address)
    
    assert asset_data.assetBalance == initial_asset_balance - collateral_amount + remove_collateral_amount
    assert debt_data.assetBalance == borrow_amount - repay_amount