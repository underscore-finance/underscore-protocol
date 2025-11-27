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
    lego_id = 3  # mock_dex_lego is always id 3
    
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
    # USD value is the max of input ($200) and output ($300) values
    assert usdValue == 300 * EIGHTEEN_DECIMALS  # max(100 * $2, 100 * $3)
    
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
    assert log.legoId == 3
    assert log.signer == bob


def test_swap_tokens_max_amount(setupSwapTest, user_wallet, bob, mock_dex_asset, mock_dex_asset_alt):
    """Test swapping with max_value to swap entire balance"""
    setupSwapTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
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
    lego_id = 3  # mock_dex_lego is always id 3
    
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
    lego_id = 3  # mock_dex_lego is always id 3
    
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
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set immediate mint/redeem mode
    mock_dex_lego.setImmediateMintOrRedeem(True)
    
    # Check initial balances
    initial_asset_balance = mock_dex_asset.balanceOf(user_wallet)
    initial_alt_balance = mock_dex_asset_alt.balanceOf(user_wallet)
    
    # Mint alt tokens using asset tokens
    mint_amount = 150 * EIGHTEEN_DECIMALS
    amount_in, outputAmount, isPending, usdValue = user_wallet.mintOrRedeemAsset(
        lego_id,
        mock_dex_asset.address,     # tokenIn
        mock_dex_asset_alt.address,  # tokenOut
        mint_amount,
        0,  # minAmountOut
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values for immediate mint
    assert amount_in == mint_amount  # 1:1 exchange
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
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set pending mint/redeem mode (not immediate)
    mock_dex_lego.setImmediateMintOrRedeem(False)
    
    # Check initial balances
    initial_asset_balance = mock_dex_asset.balanceOf(user_wallet)
    initial_alt_balance = mock_dex_asset_alt.balanceOf(user_wallet)
    
    # Initiate mint - should go to pending state
    mint_amount = 200 * EIGHTEEN_DECIMALS
    amount_in, outputAmount, isPending, usdValue = user_wallet.mintOrRedeemAsset(
        lego_id,
        mock_dex_asset.address,     # tokenIn
        mock_dex_asset_alt.address,  # tokenOut
        mint_amount,
        0,  # minAmountOut
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values for pending mint
    assert amount_in == mint_amount
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
    assert log.amount1 == amount_in
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
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set immediate mode for simplicity
    mock_dex_lego.setImmediateMintOrRedeem(True)
    
    # Get current balance
    current_balance = mock_dex_asset.balanceOf(user_wallet)
    
    # Mint using max value
    amount_in, outputAmount, isPending, usdValue = user_wallet.mintOrRedeemAsset(
        lego_id,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        MAX_UINT256,  # Use entire balance
        0,
        b"",
        sender=bob
    )
    
    # Verify entire balance was used
    assert amount_in == current_balance
    assert outputAmount == current_balance
    assert mock_dex_asset.balanceOf(user_wallet) == 0
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 2 * current_balance  # Had initial + minted


def test_redeem_asset_back_to_original(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt):
    """Test redeeming alt tokens back to original asset tokens"""
    setupSwapTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
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
    
    amount_in, outputAmount, isPending, usdValue = user_wallet.mintOrRedeemAsset(
        lego_id,
        mock_dex_asset_alt.address,  # tokenIn (redeeming alt)
        mock_dex_asset.address,      # tokenOut (getting asset back)
        redeem_amount,
        0,
        b"",
        sender=bob
    )
    
    # Verify redemption
    assert amount_in == redeem_amount  # 1:1 exchange
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


##############################
# Add/Remove Liquidity Tests #
##############################


def test_add_liquidity_basic(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt, mock_dex_lp_token, mock_ripe):
    """Test basic add liquidity functionality"""
    setupSwapTest()
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Set LP token price
    mock_ripe.setPrice(mock_dex_lp_token, 5 * EIGHTEEN_DECIMALS)  # $5 per LP token
    
    # Check initial balances
    initial_asset_balance = mock_dex_asset.balanceOf(user_wallet)
    initial_alt_balance = mock_dex_asset_alt.balanceOf(user_wallet)
    initial_lp_balance = mock_dex_lp_token.balanceOf(user_wallet)
    
    # Add liquidity with both tokens
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 150 * EIGHTEEN_DECIMALS
    lp_received, added_a, added_b, usd_value = user_wallet.addLiquidity(
        lego_id,
        mock_dex_lego.address,  # pool address
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        amount_a,
        amount_b,
        0,  # minAmountA
        0,  # minAmountB
        0,  # minLpAmount
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values
    assert added_a == amount_a
    assert added_b == amount_b
    assert lp_received == amount_a + amount_b  # MockDexLego mints LP tokens as sum of inputs
    assert usd_value == amount_a * 2 + amount_b * 3  # $2 per asset, $3 per alt
    
    # Check balances
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset_balance - amount_a
    assert mock_dex_asset_alt.balanceOf(user_wallet) == initial_alt_balance - amount_b
    assert mock_dex_lp_token.balanceOf(user_wallet) == initial_lp_balance + lp_received
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 30  # ADD_LIQ operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    assert log.amount1 == added_a
    assert log.amount2 == added_b
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob
    
    # Check storage updated
    lp_data = user_wallet.assetData(mock_dex_lp_token.address)
    assert lp_data.assetBalance == lp_received
    assert lp_data.isYieldAsset == False


def test_add_liquidity_single_sided(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt, mock_dex_lp_token, mock_ripe):
    """Test adding liquidity with only one token"""
    setupSwapTest()
    lego_id = 3
    
    # Set LP token price
    mock_ripe.setPrice(mock_dex_lp_token, 5 * EIGHTEEN_DECIMALS)
    
    # Add liquidity with only token A
    amount_a = 200 * EIGHTEEN_DECIMALS
    lp_received, added_a, added_b, usd_value = user_wallet.addLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        amount_a,
        0,  # No token B
        sender=bob
    )
    
    # Verify only token A was used
    assert added_a == amount_a
    assert added_b == 0
    assert lp_received == amount_a  # Only token A contributes to LP
    assert usd_value == amount_a * 2  # Only token A value
    
    # Check balances
    assert mock_dex_asset.balanceOf(user_wallet) == 1000 * EIGHTEEN_DECIMALS - amount_a
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 1000 * EIGHTEEN_DECIMALS  # Unchanged
    assert mock_dex_lp_token.balanceOf(user_wallet) == lp_received


def test_add_liquidity_max_values(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt, mock_dex_lp_token):
    """Test adding liquidity with MAX_UINT256 to use entire balances"""
    setupSwapTest()
    lego_id = 3
    
    # Get current balances
    asset_balance = mock_dex_asset.balanceOf(user_wallet)
    alt_balance = mock_dex_asset_alt.balanceOf(user_wallet)
    
    # Add liquidity with max values
    lp_received, added_a, added_b, usd_value = user_wallet.addLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        MAX_UINT256,  # Use all of token A
        MAX_UINT256,  # Use all of token B
        sender=bob
    )
    
    # Verify entire balances were used
    assert added_a == asset_balance
    assert added_b == alt_balance
    assert lp_received == asset_balance + alt_balance
    
    # Check balances are now zero
    assert mock_dex_asset.balanceOf(user_wallet) == 0
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 0
    assert mock_dex_lp_token.balanceOf(user_wallet) == lp_received


def test_remove_liquidity_basic(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt, mock_dex_lp_token):
    """Test basic remove liquidity functionality"""
    setupSwapTest()
    lego_id = 3
    
    # First add liquidity to get LP tokens
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 100 * EIGHTEEN_DECIMALS
    lp_received, _, _, _ = user_wallet.addLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        amount_a,
        amount_b,
        sender=bob
    )
    
    # Check LP balance
    assert mock_dex_lp_token.balanceOf(user_wallet) == lp_received
    
    # Remove half of the liquidity
    lp_to_remove = lp_received // 2
    received_a, received_b, lp_burned, usd_value = user_wallet.removeLiquidity(
        lego_id,
        mock_dex_lego.address,  # pool
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mock_dex_lp_token.address,
        lp_to_remove,
        0,  # minAmountA
        0,  # minAmountB
        b"",  # extraData
        sender=bob
    )
    
    # MockDexLego returns half of LP amount for each token
    expected_per_token = lp_to_remove // 2
    assert received_a == expected_per_token
    assert received_b == expected_per_token
    assert lp_burned == lp_to_remove
    assert usd_value == expected_per_token * 2 + expected_per_token * 3  # $2 + $3 per token
    
    # Check balances
    assert mock_dex_lp_token.balanceOf(user_wallet) == lp_received - lp_to_remove
    # Tokens should be returned
    assert mock_dex_asset.balanceOf(user_wallet) == 900 * EIGHTEEN_DECIMALS + expected_per_token
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 900 * EIGHTEEN_DECIMALS + expected_per_token
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 31  # REMOVE_LIQ operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    assert log.amount1 == received_a
    assert log.amount2 == received_b
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob


def test_remove_liquidity_max_value(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt, mock_dex_lp_token):
    """Test removing all liquidity with MAX_UINT256"""
    setupSwapTest()
    lego_id = 3
    
    # First add liquidity
    lp_received, _, _, _ = user_wallet.addLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        200 * EIGHTEEN_DECIMALS,
        300 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    # Remove all liquidity using max value
    received_a, received_b, lp_burned, _ = user_wallet.removeLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mock_dex_lp_token.address,
        MAX_UINT256,  # Remove all
        sender=bob
    )
    
    # Verify all LP tokens were burned
    assert lp_burned == lp_received
    assert mock_dex_lp_token.balanceOf(user_wallet) == 0
    
    # MockDexLego returns half of LP amount for each token
    expected_per_token = lp_received // 2
    assert received_a == expected_per_token
    assert received_b == expected_per_token


def test_add_remove_liquidity_cycle(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt, mock_dex_lp_token):
    """Test multiple add/remove liquidity cycles"""
    setupSwapTest()
    lego_id = 3
    
    initial_asset = mock_dex_asset.balanceOf(user_wallet)
    initial_alt = mock_dex_asset_alt.balanceOf(user_wallet)
    
    # Cycle 1: Add liquidity
    lp1, _, _, _ = user_wallet.addLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    assert mock_dex_lp_token.balanceOf(user_wallet) == lp1
    
    # Cycle 2: Remove half
    user_wallet.removeLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mock_dex_lp_token.address,
        lp1 // 2,
        sender=bob
    )
    
    assert mock_dex_lp_token.balanceOf(user_wallet) == lp1 // 2
    
    # Cycle 3: Add more liquidity
    lp2, _, _, _ = user_wallet.addLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        50 * EIGHTEEN_DECIMALS,
        50 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    total_lp = lp1 // 2 + lp2
    assert mock_dex_lp_token.balanceOf(user_wallet) == total_lp
    
    # Cycle 4: Remove all remaining
    user_wallet.removeLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mock_dex_lp_token.address,
        MAX_UINT256,
        sender=bob
    )
    
    assert mock_dex_lp_token.balanceOf(user_wallet) == 0


def test_liquidity_operations_update_storage(setupSwapTest, user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt, mock_dex_lp_token, mock_ripe):
    """Test that liquidity operations properly update asset storage"""
    setupSwapTest()
    lego_id = 3
    
    # Set LP token price
    mock_ripe.setPrice(mock_dex_lp_token, 5 * EIGHTEEN_DECIMALS)
    
    # Check LP token not tracked initially
    assert user_wallet.indexOfAsset(mock_dex_lp_token.address) == 0
    
    # Add liquidity
    lp_received, _, _, _ = user_wallet.addLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        100 * EIGHTEEN_DECIMALS,
        100 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    # Check LP token is now tracked
    lp_index = user_wallet.indexOfAsset(mock_dex_lp_token.address)
    assert lp_index > 0
    assert user_wallet.assets(lp_index) == mock_dex_lp_token.address
    
    # Check LP token storage
    lp_data = user_wallet.assetData(mock_dex_lp_token.address)
    assert lp_data.assetBalance == lp_received
    assert lp_data.usdValue == lp_received * 5  # $5 per LP token
    assert lp_data.isYieldAsset == False
    
    # Remove all liquidity
    user_wallet.removeLiquidity(
        lego_id,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mock_dex_lp_token.address,
        MAX_UINT256,
        sender=bob
    )
    
    # LP token should be deregistered
    assert user_wallet.indexOfAsset(mock_dex_lp_token.address) == 0
    lp_data_after = user_wallet.assetData(mock_dex_lp_token.address)
    assert lp_data_after.assetBalance == 0
    assert lp_data_after.usdValue == 0