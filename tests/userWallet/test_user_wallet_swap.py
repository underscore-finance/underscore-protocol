import pytest
import boa

from contracts.core.userWallet import UserWallet
from contracts.core.userWallet import UserWalletConfig
from constants import EIGHTEEN_DECIMALS, MAX_UINT256
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setupSwapTest(user_wallet, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt, lego_book, mock_ripe, switchboard_alpha, whale):
    def setupSwapTest():
        lego_id = lego_book.getRegId(mock_dex_lego.address)
        
        # Set prices for assets
        mock_ripe.setPrice(mock_dex_asset, 2 * EIGHTEEN_DECIMALS) # $2
        mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS) # $3
        
        # Transfer some tokens to the user wallet
        amount = 1000 * EIGHTEEN_DECIMALS
        mock_dex_asset.transfer(user_wallet, amount, sender=whale)
        mock_dex_asset_alt.transfer(user_wallet, amount, sender=whale)
        
        # Register assets in wallet config
        wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
        wallet_config.updateAssetData(lego_id, mock_dex_asset, False, sender=switchboard_alpha.address)
        wallet_config.updateAssetData(lego_id, mock_dex_asset_alt, False, sender=switchboard_alpha.address)

        return amount

    yield setupSwapTest


###################
# Swap / Exchange #
###################


def test_swap_tokens_basic(setupSwapTest, user_wallet, bob, mock_dex_asset, mock_dex_asset_alt):
    """Test basic token swap functionality"""
    setupSwapTest()
    lego_id = 2  # mock_dex_lego is always id 2
    
    # Prepare swap instruction
    swap_amount = 100 * EIGHTEEN_DECIMALS
    min_amount_out = 90 * EIGHTEEN_DECIMALS  # Allow 10% slippage
    instruction = (
        lego_id,
        swap_amount,
        min_amount_out,
        [mock_dex_asset.address, mock_dex_asset_alt.address],  # tokenPath
        []  # poolPath (not used in mock)
    )
    
    # Get initial balances
    initial_asset_balance = mock_dex_asset.balanceOf(user_wallet)
    initial_alt_balance = mock_dex_asset_alt.balanceOf(user_wallet)
    
    # Perform swap
    tokenIn, amountIn, tokenOut, amountOut, usdValue = user_wallet.swapTokens([instruction], sender=bob)
    
    # Verify return values
    assert tokenIn == mock_dex_asset.address
    assert amountIn == swap_amount
    assert tokenOut == mock_dex_asset_alt.address
    assert amountOut == swap_amount  # MockDexLego does 1:1 swap
    assert usdValue == 200 * EIGHTEEN_DECIMALS  # 100 tokens * $2
    
    # Check balances
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset_balance - swap_amount
    assert mock_dex_asset_alt.balanceOf(user_wallet) == initial_alt_balance + swap_amount
    
    # Check events
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 20  # SWAP operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    assert log.amount1 == swap_amount
    assert log.amount2 == swap_amount
    assert log.usdValue == usdValue
    assert log.legoId == 1  # Number of unique legos used
    assert log.signer == bob


def test_swap_tokens_max_amount(setupSwapTest, user_wallet, bob, mock_dex_asset, mock_dex_asset_alt):
    """Test swapping with max_value to swap entire balance"""
    setupSwapTest()
    lego_id = 2  # mock_dex_lego is always id 2
    
    # Get current balance
    current_balance = mock_dex_asset.balanceOf(user_wallet)
    
    # Prepare swap instruction with max amount
    instruction = (
        lego_id,
        MAX_UINT256,  # Use max to swap entire balance
        0,  # min amount out
        [mock_dex_asset.address, mock_dex_asset_alt.address],
        []
    )
    
    # Perform swap
    tokenIn, amountIn, tokenOut, amountOut, usdValue = user_wallet.swapTokens([instruction], sender=bob)
    
    # Verify it swapped the entire balance
    assert amountIn == current_balance
    assert amountOut == current_balance  # 1:1 swap in mock
    assert mock_dex_asset.balanceOf(user_wallet) == 0
    

def test_swap_tokens_multi_instruction(setupSwapTest, user_wallet, bob, mock_dex_asset, mock_dex_asset_alt):
    """Test swapping with multiple instructions (chained swaps)"""
    setupSwapTest()
    lego_id = 2  # mock_dex_lego is always id 2
    
    # First swap some asset to alt
    swap_amount_1 = 50 * EIGHTEEN_DECIMALS
    instruction_1 = (
        lego_id,
        swap_amount_1,
        0,
        [mock_dex_asset.address, mock_dex_asset_alt.address],
        []
    )
    
    # Then swap the alt back to asset
    swap_amount_2 = 30 * EIGHTEEN_DECIMALS
    instruction_2 = (
        lego_id,
        swap_amount_2,
        0,
        [mock_dex_asset_alt.address, mock_dex_asset.address],
        []
    )
    
    initial_asset = mock_dex_asset.balanceOf(user_wallet)
    initial_alt = mock_dex_asset_alt.balanceOf(user_wallet)
    
    # Perform multi-instruction swap
    tokenIn, amountIn, tokenOut, amountOut, usdValue = user_wallet.swapTokens(
        [instruction_1, instruction_2], 
        sender=bob
    )
    
    # Verify results
    assert tokenIn == mock_dex_asset.address  # First input
    assert tokenOut == mock_dex_asset.address  # Final output
    assert amountIn == swap_amount_1

    # In chained swaps, the output is the full amount from first swap
    assert amountOut == swap_amount_1  # MockDexLego swaps 1:1
    
    # Check final balances
    # Started with asset, swapped 50 to alt, then swapped 50 alt back to asset (chained swaps use full amount)
    # Net: no change in either balance since we swapped out and back
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset
    assert mock_dex_asset_alt.balanceOf(user_wallet) == initial_alt


def test_swap_updates_asset_data(setupSwapTest, user_wallet, bob, mock_dex_asset, mock_dex_asset_alt):
    """Test that swap properly updates asset data in storage"""
    setupSwapTest()
    lego_id = 2  # mock_dex_lego is always id 2
    
    # Check initial asset data
    initial_asset_data = user_wallet.assetData(mock_dex_asset.address)
    initial_alt_data = user_wallet.assetData(mock_dex_asset_alt.address)
    
    # Perform swap
    swap_amount = 200 * EIGHTEEN_DECIMALS
    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_dex_asset.address, mock_dex_asset_alt.address],
        []
    )
    
    user_wallet.swapTokens([instruction], sender=bob)
    
    # Check updated asset data
    final_asset_data = user_wallet.assetData(mock_dex_asset.address)
    final_alt_data = user_wallet.assetData(mock_dex_asset_alt.address)
    
    # Asset balance should decrease
    assert final_asset_data.assetBalance == initial_asset_data.assetBalance - swap_amount
    # Alt asset balance should increase  
    assert final_alt_data.assetBalance == initial_alt_data.assetBalance + swap_amount
    
    # USD values should be updated
    assert final_asset_data.usdValue == final_asset_data.assetBalance * 2  # $2 per token
    assert final_alt_data.usdValue == final_alt_data.assetBalance * 3  # $3 per token


###########################
# Mint/Redeem Asset Tests #
###########################


def test_mint_redeem_asset_immediate(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt):
    """Test immediate mint/redeem functionality"""
    setupSwapTest()
    lego_id = 2  # mock_dex_lego is always id 2
    
    # Set immediate mint/redeem mode
    mock_dex_lego.setImmediateMintOrRedeem(True)
    
    # Check initial balances
    initial_asset_balance = mock_dex_asset.balanceOf(user_wallet)
    initial_alt_balance = mock_dex_asset_alt.balanceOf(user_wallet)
    
    # Mint alt tokens using asset tokens
    mint_amount = 150 * EIGHTEEN_DECIMALS
    tokenOutReceived, outputAmount, isPending, usdValue = user_wallet.mintOrRedeemAsset(
        lego_id,
        mock_dex_asset.address,     # tokenIn
        mock_dex_asset_alt.address,  # tokenOut
        mint_amount,
        0,  # minAmountOut
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values for immediate mint
    assert tokenOutReceived == mint_amount  # 1:1 exchange
    assert outputAmount == mint_amount
    assert isPending == False  # Immediate mode
    assert usdValue == 450 * EIGHTEEN_DECIMALS  # 150 tokens * $3
    
    # Check balances updated
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset_balance - mint_amount
    assert mock_dex_asset_alt.balanceOf(user_wallet) == initial_alt_balance + mint_amount
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 21  # MINT_REDEEM operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    assert log.amount1 == mint_amount
    assert log.amount2 == mint_amount
    assert log.usdValue == usdValue
    assert log.legoId == lego_id
    assert log.signer == bob
    
    # Check storage updated
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    alt_data = user_wallet.assetData(mock_dex_asset_alt.address)
    assert asset_data.assetBalance == initial_asset_balance - mint_amount
    assert alt_data.assetBalance == initial_alt_balance + mint_amount


def test_mint_redeem_asset_pending(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt):
    """Test pending mint/redeem that requires confirmation"""
    setupSwapTest()
    lego_id = 2  # mock_dex_lego is always id 2
    
    # Set pending mint/redeem mode (not immediate)
    mock_dex_lego.setImmediateMintOrRedeem(False)
    
    # Check initial balances
    initial_asset_balance = mock_dex_asset.balanceOf(user_wallet)
    initial_alt_balance = mock_dex_asset_alt.balanceOf(user_wallet)
    
    # Initiate mint - should go to pending state
    mint_amount = 200 * EIGHTEEN_DECIMALS
    tokenOutReceived, outputAmount, isPending, usdValue = user_wallet.mintOrRedeemAsset(
        lego_id,
        mock_dex_asset.address,     # tokenIn
        mock_dex_asset_alt.address,  # tokenOut
        mint_amount,
        0,  # minAmountOut
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values for pending mint
    assert tokenOutReceived == 0  # Nothing received yet
    assert outputAmount == 0
    assert isPending == True  # Pending mode
    assert usdValue == 0  # No value yet
    
    # Check that input tokens were taken but output not received yet
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset_balance - mint_amount
    assert mock_dex_asset_alt.balanceOf(user_wallet) == initial_alt_balance  # No change yet
    
    # Check event for pending mint
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 21  # MINT_REDEEM operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    # For pending, the event might show 0 for both amounts since nothing is finalized
    assert log.amount1 == 0
    assert log.amount2 == 0
    assert log.usdValue == 0
    
    # Now confirm the mint
    confirmedAmount, confirmedUsdValue = user_wallet.confirmMintOrRedeemAsset(
        lego_id,
        mock_dex_asset.address,     # tokenIn
        mock_dex_asset_alt.address,  # tokenOut
        b"",  # extraData
        sender=bob
    )
    
    # Verify confirmation results
    assert confirmedAmount == mint_amount  # Now received
    assert confirmedUsdValue == 600 * EIGHTEEN_DECIMALS  # 200 tokens * $3
    
    # Check final balances
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset_balance - mint_amount
    assert mock_dex_asset_alt.balanceOf(user_wallet) == initial_alt_balance + mint_amount
    
    # Check event for confirmation - need to filter logs again after confirmation
    confirm_log = filter_logs(user_wallet, "WalletAction")[0]
    assert confirm_log.op == 22  # CONFIRM_MINT_REDEEM operation
    assert confirm_log.asset1 == mock_dex_asset.address
    assert confirm_log.asset2 == mock_dex_asset_alt.address
    assert confirm_log.amount1 == 0  # No input on confirm
    assert confirm_log.amount2 == mint_amount  # Output received
    assert confirm_log.usdValue == confirmedUsdValue
    assert confirm_log.legoId == lego_id
    assert confirm_log.signer == bob


def test_mint_redeem_with_max_value(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt):
    """Test minting with MAX_UINT256 to use entire balance"""
    setupSwapTest()
    lego_id = 2  # mock_dex_lego is always id 2
    
    # Set immediate mode for simplicity
    mock_dex_lego.setImmediateMintOrRedeem(True)
    
    # Get current balance
    current_balance = mock_dex_asset.balanceOf(user_wallet)
    
    # Mint using max value
    tokenOutReceived, outputAmount, isPending, usdValue = user_wallet.mintOrRedeemAsset(
        lego_id,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        MAX_UINT256,  # Use entire balance
        0,
        b"",
        sender=bob
    )
    
    # Verify entire balance was used
    assert tokenOutReceived == current_balance
    assert outputAmount == current_balance
    assert mock_dex_asset.balanceOf(user_wallet) == 0
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 2 * current_balance  # Had initial + minted


def test_redeem_asset_back_to_original(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt):
    """Test redeeming alt tokens back to original asset tokens"""
    setupSwapTest()
    lego_id = 2  # mock_dex_lego is always id 2
    
    # Set immediate mode
    mock_dex_lego.setImmediateMintOrRedeem(True)
    
    # First mint some alt tokens
    mint_amount = 100 * EIGHTEEN_DECIMALS
    user_wallet.mintOrRedeemAsset(
        lego_id,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mint_amount,
        sender=bob
    )
    
    # Now redeem alt tokens back to asset
    redeem_amount = 50 * EIGHTEEN_DECIMALS
    initial_asset = mock_dex_asset.balanceOf(user_wallet)
    initial_alt = mock_dex_asset_alt.balanceOf(user_wallet)
    
    tokenOutReceived, outputAmount, isPending, usdValue = user_wallet.mintOrRedeemAsset(
        lego_id,
        mock_dex_asset_alt.address,  # tokenIn (redeeming alt)
        mock_dex_asset.address,      # tokenOut (getting asset back)
        redeem_amount,
        0,
        b"",
        sender=bob
    )
    
    # Verify redemption
    assert tokenOutReceived == redeem_amount  # 1:1 exchange
    assert outputAmount == redeem_amount
    assert isPending == False
    assert usdValue == 100 * EIGHTEEN_DECIMALS  # 50 tokens * $2
    
    # Check balances
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset + redeem_amount
    assert mock_dex_asset_alt.balanceOf(user_wallet) == initial_alt - redeem_amount
    
    # Check storage updated correctly
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    alt_data = user_wallet.assetData(mock_dex_asset_alt.address)
    assert asset_data.assetBalance == initial_asset + redeem_amount
    assert alt_data.assetBalance == initial_alt - redeem_amount