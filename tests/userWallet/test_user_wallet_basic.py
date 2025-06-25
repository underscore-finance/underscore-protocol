import pytest
import boa

from contracts.core.userWallet import UserWallet
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def user_wallet(setUserWalletConfig, hatchery, bob):
    setUserWalletConfig()
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


@pytest.fixture
def setup_wallet_with_tokens(user_wallet, mock_lego, mock_lego_asset, mock_lego_vault, mock_lego_asset_alt, whale):
    """Setup user wallet with tokens for testing"""
    # Transfer tokens to user wallet
    mock_lego_asset.transfer(user_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=whale)
    mock_lego_asset_alt.transfer(user_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=whale)
    
    # Note: Access control is handled automatically by UserWallet when calling protected functions
    # The UserWallet will call MockLego's setLegoAccess when needed
    
    return user_wallet, mock_lego, mock_lego_asset, mock_lego_vault, mock_lego_asset_alt


# tests


def test_deposit_for_yield(setup_wallet_with_tokens, bob):
    """Test depositing assets into yield vault"""
    user_wallet, mock_lego, asset, vault, _ = setup_wallet_with_tokens
    owner = bob
    
    # Initial balances
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    initial_vault_balance = vault.balanceOf(user_wallet.address)
    
    # Deposit 100 tokens
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call depositForYield
    assetAmount, vaultToken, vaultTokenAmountReceived = user_wallet.depositForYield(
        1,  # legoId for MockLego
        asset.address,
        vault.address,
        deposit_amount,
        sender=owner
    )
    
    # Get events
    yield_deposit_logs = filter_logs(user_wallet, "YieldDeposit")
    
    # Verify return values
    assert assetAmount == deposit_amount
    assert vaultToken == vault.address
    assert vaultTokenAmountReceived == deposit_amount
    
    # Verify balances
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance - deposit_amount
    assert vault.balanceOf(user_wallet.address) == initial_vault_balance + deposit_amount
    
    # Verify events
    assert len(yield_deposit_logs) == 1
    event = yield_deposit_logs[0]
    assert event.asset == asset.address
    assert event.assetAmount == deposit_amount
    assert event.vaultToken == vault.address
    assert event.vaultTokenAmount == deposit_amount
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_withdraw_from_yield(setup_wallet_with_tokens, bob):
    """Test withdrawing assets from yield vault"""
    user_wallet, mock_lego, asset, vault, _ = setup_wallet_with_tokens
    owner = bob
    
    # First deposit some tokens
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    user_wallet.depositForYield(1, asset.address, vault.address, deposit_amount, sender=owner)
    
    # Initial balances after deposit
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    initial_vault_balance = vault.balanceOf(user_wallet.address)
    
    # Withdraw 50 tokens
    withdraw_amount = 50 * EIGHTEEN_DECIMALS
    
    # Call withdrawFromYield
    underlyingAmount, underlyingToken, vaultTokenAmountWithdrawn = user_wallet.withdrawFromYield(
        1,  # legoId for MockLego
        vault.address,
        withdraw_amount,
        sender=owner
    )
    
    # Get events
    withdrawal_logs = filter_logs(user_wallet, "YieldWithdrawal")
    
    # Verify return values
    assert underlyingAmount == withdraw_amount
    assert underlyingToken == asset.address
    assert vaultTokenAmountWithdrawn == withdraw_amount
    
    # Verify balances
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance + withdraw_amount
    assert vault.balanceOf(user_wallet.address) == initial_vault_balance - withdraw_amount
    
    # Verify events
    assert len(withdrawal_logs) == 1
    event = withdrawal_logs[0]
    assert event.vaultToken == vault.address
    assert event.vaultTokenAmountBurned == withdraw_amount
    assert event.underlyingAsset == asset.address
    assert event.underlyingAmountReceived == withdraw_amount
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_rebalance_yield_position(setup_wallet_with_tokens, bob):
    """Test rebalancing between yield positions"""
    user_wallet, mock_lego, asset, vault, asset_alt = setup_wallet_with_tokens
    owner = bob
    
    # For this test, we'll rebalance from vault back to the asset
    # (MockLego has a bug where altVaultToken is not in valid tokens list)
    
    # First deposit into vault
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    user_wallet.depositForYield(1, asset.address, vault.address, deposit_amount, sender=owner)
    
    # Initial balances
    initial_vault_balance = vault.balanceOf(user_wallet.address)
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    
    # Rebalance 50 tokens from vault back to asset
    rebalance_amount = 50 * EIGHTEEN_DECIMALS
    
    # Clear previous events by getting them
    _ = user_wallet.get_logs()
    
    # Call rebalanceYieldPosition - using asset as the "toVault" for simplicity
    underlyingAmount, underlyingToken, vaultTokenAmount = user_wallet.rebalanceYieldPosition(
        1,  # fromLegoId
        vault.address,  # fromVault
        1,  # toLegoId (same MockLego)
        asset.address,  # toVault (using asset as a vault for this test)
        rebalance_amount,
        sender=owner
    )
    
    # Get events (rebalance emits both withdrawal and deposit events)
    withdrawal_logs = filter_logs(user_wallet, "YieldWithdrawal")
    deposit_logs = filter_logs(user_wallet, "YieldDeposit")
    
    # Verify return values
    assert underlyingAmount == rebalance_amount
    assert underlyingToken == asset.address
    assert vaultTokenAmount == rebalance_amount
    
    # Verify balances - vault should decrease, asset should increase
    assert vault.balanceOf(user_wallet.address) == initial_vault_balance - rebalance_amount
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance + rebalance_amount
    
    # Verify withdrawal event (from vault)
    assert len(withdrawal_logs) == 1
    withdrawal_event = withdrawal_logs[0]
    assert withdrawal_event.vaultToken == vault.address
    assert withdrawal_event.vaultTokenAmountBurned == rebalance_amount
    assert withdrawal_event.underlyingAsset == asset.address
    assert withdrawal_event.underlyingAmountReceived == rebalance_amount
    assert withdrawal_event.legoId == 1
    assert withdrawal_event.legoAddr == mock_lego.address
    assert withdrawal_event.signer == owner
    assert withdrawal_event.isSignerAgent == False
    
    # Verify deposit event (to asset as "vault")
    assert len(deposit_logs) == 1  # Only one from rebalance (we cleared events)
    rebalance_deposit_event = deposit_logs[0]  # First event is from rebalance
    assert rebalance_deposit_event.asset == asset.address
    assert rebalance_deposit_event.assetAmount == rebalance_amount
    assert rebalance_deposit_event.vaultToken == asset.address  # Using asset as "vault"
    assert rebalance_deposit_event.vaultTokenAmount == rebalance_amount
    assert rebalance_deposit_event.legoId == 1
    assert rebalance_deposit_event.legoAddr == mock_lego.address
    assert rebalance_deposit_event.signer == owner
    assert rebalance_deposit_event.isSignerAgent == False


def test_swap_tokens(setup_wallet_with_tokens, bob):
    """Test swapping tokens"""
    user_wallet, mock_lego, asset, _, asset_alt = setup_wallet_with_tokens
    owner = bob
    
    # Initial balances
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = asset_alt.balanceOf(user_wallet.address)
    
    # Swap 100 tokens
    swap_amount = 100 * EIGHTEEN_DECIMALS
    
    # Create swap instruction as tuple (legoId, amountIn, minAmountOut, tokenPath, poolPath)
    swap_instructions = [(
        1,  # legoId
        swap_amount,  # amountIn
        0,  # minAmountOut
        [asset.address, asset_alt.address],  # tokenPath
        []  # poolPath
    )]
    
    # Call swapTokens
    tokenIn, amountIn, tokenOut, amountOut = user_wallet.swapTokens(swap_instructions, sender=owner)
    
    # Get events
    overall_swap_logs = filter_logs(user_wallet, "OverallSwapPerformed")
    specific_swap_logs = filter_logs(user_wallet, "SpecificSwapInstructionPerformed")
    
    # Verify return values
    assert tokenIn == asset.address
    assert amountIn == swap_amount
    assert tokenOut == asset_alt.address
    assert amountOut == swap_amount  # 1:1 in mock
    
    # Verify balances (1:1 swap in mock)
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance - swap_amount
    assert asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + swap_amount
    
    # Verify overall swap event
    assert len(overall_swap_logs) == 1
    overall_event = overall_swap_logs[0]
    assert overall_event.tokenIn == asset.address
    assert overall_event.tokenInAmount == swap_amount
    assert overall_event.tokenOut == asset_alt.address
    assert overall_event.tokenOutAmount == swap_amount
    assert overall_event.numLegos == 1
    assert overall_event.numInstructions == 1
    assert overall_event.signer == owner
    assert overall_event.isSignerAgent == False
    
    # Verify specific swap event
    assert len(specific_swap_logs) == 1
    specific_event = specific_swap_logs[0]
    assert specific_event.tokenIn == asset.address
    assert specific_event.tokenInAmount == swap_amount
    assert specific_event.tokenOut == asset_alt.address
    assert specific_event.tokenOutAmount == swap_amount
    assert specific_event.numTokens == 2
    assert specific_event.numPools == 0
    assert specific_event.legoId == 1
    assert specific_event.legoAddr == mock_lego.address
    assert specific_event.signer == owner
    assert specific_event.isSignerAgent == False


def test_mint_asset_immediate(setup_wallet_with_tokens, bob):
    """Test minting asset immediately (no pending state)"""
    user_wallet, mock_lego, asset, vault, asset_alt = setup_wallet_with_tokens
    owner = bob
    
    # Initial balances
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = asset_alt.balanceOf(user_wallet.address)
    
    # Mint 100 tokens worth (1:1 ratio in mock)
    mint_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call mintOrRedeemAsset with _extraVal = 0 for immediate mint
    # Using asset as input and asset_alt as output to simulate a mint operation
    assetTokenAmount, outputAmount, isPending = user_wallet.mintOrRedeemAsset(
        1,  # legoId
        asset.address,  # tokenIn
        asset_alt.address,  # tokenOut (different token to simulate minting)
        mint_amount,  # amountIn
        mint_amount,  # minAmountOut
        boa.env.eoa,  # _extraAddr (not used)
        0,  # _extraVal = 0 for immediate execution
        b'\x00' * 32,  # _extraData
        sender=owner
    )
    
    # Get events
    mint_logs = filter_logs(user_wallet, "AssetMintedOrRedeemed")
    
    # Verify return values
    assert assetTokenAmount == mint_amount
    assert outputAmount == mint_amount
    assert isPending == False
    
    # Verify balances - asset decreased, asset_alt increased
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance - mint_amount
    assert asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + mint_amount
    
    # Verify events
    assert len(mint_logs) == 1
    event = mint_logs[0]
    assert event.tokenIn == asset.address
    assert event.tokenInAmount == mint_amount
    assert event.tokenOut == asset_alt.address
    assert event.tokenOutAmount == mint_amount
    assert event.isPending == False
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_mint_asset_pending_and_confirm(setup_wallet_with_tokens, bob):
    """Test minting asset with pending state and confirmation"""
    user_wallet, mock_lego, asset, vault, asset_alt = setup_wallet_with_tokens
    owner = bob
    
    # Initial balance
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = asset_alt.balanceOf(user_wallet.address)
    
    # Mint 100 tokens worth with pending state
    mint_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call mintOrRedeemAsset with _extraVal = 1 for pending mint
    assetTokenAmount, outputAmount, isPending = user_wallet.mintOrRedeemAsset(
        1,  # legoId
        asset.address,  # tokenIn
        asset_alt.address,  # tokenOut
        mint_amount,  # amountIn
        mint_amount,  # minAmountOut
        boa.env.eoa,  # _extraAddr
        1,  # _extraVal = 1 for pending state
        b'\x00' * 32,  # _extraData
        sender=owner
    )
    
    # Get events from first call
    mint_logs = filter_logs(user_wallet, "AssetMintedOrRedeemed")
    
    # Verify return values for pending state
    assert assetTokenAmount == 0  # No tokens moved yet
    assert outputAmount == 0  # No output yet
    assert isPending == True
    
    # Verify asset balance decreased but asset_alt hasn't increased yet
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance - mint_amount
    assert asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance
    
    # Verify pending mint was created in MockLego
    pending_mint = mock_lego.pendingMintOrRedeem(user_wallet.address)
    assert pending_mint[0] == asset.address  # tokenIn
    assert pending_mint[1] == asset_alt.address  # tokenOut
    assert pending_mint[2] == mint_amount  # amount
    
    # Confirm the mint - returns single uint256
    outputAmount2 = user_wallet.confirmMintOrRedeemAsset(
        1,  # legoId
        asset.address,  # tokenIn
        asset_alt.address,  # tokenOut
        sender=owner
    )
    
    # Get events from confirmation
    confirm_logs = filter_logs(user_wallet, "AssetMintedOrRedeemedConfirmed")
    
    # Verify return value from confirmation
    assert outputAmount2 == mint_amount  # Output tokens received
    
    # Verify asset_alt balance increased after confirmation
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance - mint_amount
    assert asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + mint_amount
    
    # Verify pending mint was cleared
    pending_mint_after = mock_lego.pendingMintOrRedeem(user_wallet.address)
    assert pending_mint_after[2] == 0  # amount should be 0
    
    # Verify mint event (from first call)
    assert len(mint_logs) == 1
    mint_event = mint_logs[0]
    assert mint_event.tokenIn == asset.address
    assert mint_event.tokenInAmount == 0  # No tokens actually transferred yet for pending
    assert mint_event.tokenOut == asset_alt.address
    assert mint_event.tokenOutAmount == 0  # No output yet for pending
    assert mint_event.isPending == True
    assert mint_event.legoId == 1
    assert mint_event.legoAddr == mock_lego.address
    assert mint_event.signer == owner
    assert mint_event.isSignerAgent == False
    
    # Verify confirmation event
    assert len(confirm_logs) == 1
    confirm_event = confirm_logs[0]
    assert confirm_event.tokenIn == asset.address
    assert confirm_event.tokenOut == asset_alt.address
    assert confirm_event.tokenOutAmount == mint_amount
    assert confirm_event.legoId == 1
    assert confirm_event.legoAddr == mock_lego.address
    assert confirm_event.signer == owner
    assert confirm_event.isSignerAgent == False


def test_add_collateral(setup_wallet_with_tokens, bob):
    """Test adding collateral"""
    user_wallet, mock_lego, asset, _, _ = setup_wallet_with_tokens
    owner = bob
    
    # Initial balance
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    
    # Add 100 tokens as collateral
    collateral_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call addCollateral
    amount_added = user_wallet.addCollateral(
        1,  # legoId
        asset.address,
        collateral_amount,
        sender=owner
    )
    
    # Get events
    collateral_logs = filter_logs(user_wallet, "CollateralAdded")
    
    # Verify return value
    assert amount_added == collateral_amount
    
    # Verify balance decreased (collateral locked)
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance - collateral_amount
    
    # Note: MockLego doesn't track collateral state, it just burns the tokens
    
    # Verify events
    assert len(collateral_logs) == 1
    event = collateral_logs[0]
    assert event.asset == asset.address
    assert event.amountDeposited == collateral_amount
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_remove_collateral(setup_wallet_with_tokens, bob):
    """Test removing collateral"""
    user_wallet, mock_lego, asset, _, _ = setup_wallet_with_tokens
    owner = bob
    
    # First add collateral
    collateral_amount = 100 * EIGHTEEN_DECIMALS
    user_wallet.addCollateral(1, asset.address, collateral_amount, sender=owner)
    
    # Initial balance after adding collateral
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    
    # Remove 50 tokens of collateral
    remove_amount = 50 * EIGHTEEN_DECIMALS
    
    # Call removeCollateral
    amount_removed = user_wallet.removeCollateral(
        1,  # legoId
        asset.address,
        remove_amount,
        sender=owner
    )
    
    # Get events
    remove_logs = filter_logs(user_wallet, "CollateralRemoved")
    
    # Verify return value
    assert amount_removed == remove_amount
    
    # Verify balance increased (collateral returned)
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance + remove_amount
    
    # Note: MockLego doesn't track collateral state, it just mints the tokens back
    
    # Verify events
    assert len(remove_logs) == 1
    event = remove_logs[0]
    assert event.asset == asset.address
    assert event.amountRemoved == remove_amount
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_borrow(setup_wallet_with_tokens, mock_lego_debt_token, bob):
    """Test borrowing against collateral"""
    user_wallet, mock_lego, asset, _, _ = setup_wallet_with_tokens
    owner = bob
    
    # First add collateral
    collateral_amount = 200 * EIGHTEEN_DECIMALS
    user_wallet.addCollateral(1, asset.address, collateral_amount, sender=owner)
    
    # Initial debt token balance
    initial_debt_balance = mock_lego_debt_token.balanceOf(user_wallet.address)
    
    # Borrow 100 debt tokens
    borrow_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call borrow - returns single uint256
    amount_borrowed = user_wallet.borrow(
        1,  # legoId
        mock_lego_debt_token.address,
        borrow_amount,
        sender=owner
    )
    
    # Get events
    borrow_logs = filter_logs(user_wallet, "NewBorrow")
    
    # Verify return value
    assert amount_borrowed == borrow_amount
    
    # Verify debt token balance increased
    assert mock_lego_debt_token.balanceOf(user_wallet.address) == initial_debt_balance + borrow_amount
    
    # Note: MockLego doesn't track debt state, it just mints the debt tokens
    
    # Verify events
    assert len(borrow_logs) == 1
    event = borrow_logs[0]
    assert event.borrowAsset == mock_lego_debt_token.address
    assert event.borrowAmount == borrow_amount
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_repay_debt(setup_wallet_with_tokens, mock_lego_debt_token, bob):
    """Test repaying borrowed debt"""
    user_wallet, mock_lego, asset, _, _ = setup_wallet_with_tokens
    owner = bob
    
    # Setup: Add collateral and borrow
    collateral_amount = 200 * EIGHTEEN_DECIMALS
    user_wallet.addCollateral(1, asset.address, collateral_amount, sender=owner)
    
    borrow_amount = 100 * EIGHTEEN_DECIMALS
    # borrow returns single uint256
    user_wallet.borrow(1, mock_lego_debt_token.address, borrow_amount, sender=owner)
    
    # Initial debt token balance after borrowing
    initial_debt_balance = mock_lego_debt_token.balanceOf(user_wallet.address)
    
    # Repay 50 debt tokens
    repay_amount = 50 * EIGHTEEN_DECIMALS
    
    # Call repayDebt
    amount_repaid = user_wallet.repayDebt(
        1,  # legoId
        mock_lego_debt_token.address,
        repay_amount,
        sender=owner
    )
    
    # Get events
    repay_logs = filter_logs(user_wallet, "DebtRepayment")
    
    # Verify return value
    assert amount_repaid == repay_amount
    
    # Verify debt token balance decreased
    assert mock_lego_debt_token.balanceOf(user_wallet.address) == initial_debt_balance - repay_amount
    
    # Note: MockLego doesn't track debt state, it just burns the repaid tokens
    
    # Verify events
    assert len(repay_logs) == 1
    event = repay_logs[0]
    assert event.paymentAsset == mock_lego_debt_token.address
    assert event.repaidAmount == repay_amount
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_claim_rewards(setup_wallet_with_tokens, bob):
    """Test claiming rewards"""
    user_wallet, mock_lego, asset, _, _ = setup_wallet_with_tokens
    owner = bob
    
    # MockLego doesn't have a setRewards function, it just mints the requested reward amount
    # For this test, we'll just verify that claiming rewards mints tokens
    reward_amount = 50 * EIGHTEEN_DECIMALS
    
    # Initial balance
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    
    # Call claimRewards
    rewards_claimed = user_wallet.claimRewards(
        1,  # legoId
        asset.address,  # rewardToken
        reward_amount,  # rewardAmount
        sender=owner
    )
    
    # Get events
    rewards_logs = filter_logs(user_wallet, "RewardsClaimed")
    
    # Verify return value
    assert rewards_claimed == reward_amount
    
    # Verify balance increased by reward amount
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance + reward_amount
    
    # Note: MockLego doesn't track rewards state, it just mints the reward tokens
    
    # Verify events
    assert len(rewards_logs) == 1
    event = rewards_logs[0]
    assert event.rewardToken == asset.address
    assert event.rewardAmount == reward_amount
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_add_liquidity(setup_wallet_with_tokens, mock_lego_lp_token, bob):
    """Test adding liquidity"""
    user_wallet, mock_lego, asset, _, asset_alt = setup_wallet_with_tokens
    owner = bob
    
    # Initial balances
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = asset_alt.balanceOf(user_wallet.address)
    initial_lp_balance = mock_lego_lp_token.balanceOf(user_wallet.address)
    
    # Add liquidity with 100 of each token
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 100 * EIGHTEEN_DECIMALS
    
    # Call addLiquidity
    lp_amount, actual_amount_a, actual_amount_b = user_wallet.addLiquidity(
        1,  # legoId
        boa.env.eoa,  # pool (not used in mock)
        asset.address,  # tokenA
        asset_alt.address,  # tokenB
        amount_a,  # amountA
        amount_b,  # amountB
        0,  # minAmountA
        0,  # minAmountB
        0,  # minLpOut
        sender=owner
    )
    
    # Get events
    liquidity_logs = filter_logs(user_wallet, "LiquidityAdded")
    
    # Verify return values
    assert actual_amount_a == amount_a
    assert actual_amount_b == amount_b
    expected_lp = amount_a + amount_b
    assert lp_amount == expected_lp
    
    # Verify token balances decreased
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance - amount_a
    assert asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance - amount_b
    
    # Verify LP tokens were minted (mock mints sum of amounts)
    assert mock_lego_lp_token.balanceOf(user_wallet.address) == initial_lp_balance + expected_lp
    
    # Verify events
    assert len(liquidity_logs) == 1
    event = liquidity_logs[0]
    assert event.pool == boa.env.eoa
    assert event.tokenA == asset.address
    assert event.amountA == amount_a
    assert event.tokenB == asset_alt.address
    assert event.amountB == amount_b
    assert event.lpToken == mock_lego_lp_token.address
    assert event.lpAmountReceived == expected_lp
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_remove_liquidity(setup_wallet_with_tokens, mock_lego_lp_token, bob):
    """Test removing liquidity"""
    user_wallet, mock_lego, asset, _, asset_alt = setup_wallet_with_tokens
    owner = bob
    
    # First add liquidity
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 100 * EIGHTEEN_DECIMALS
    user_wallet.addLiquidity(
        1, boa.env.eoa, asset.address, asset_alt.address,
        amount_a, amount_b, 0, 0, 0, sender=owner
    )
    
    # Initial balances after adding liquidity
    initial_asset_balance = asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = asset_alt.balanceOf(user_wallet.address)
    initial_lp_balance = mock_lego_lp_token.balanceOf(user_wallet.address)
    
    # Remove half the liquidity
    lp_to_remove = initial_lp_balance // 2
    
    # Call removeLiquidity - MockLego returns (amountA, amountB, lpBurned)
    amount_a_received, amount_b_received, lp_burned = user_wallet.removeLiquidity(
        1,  # legoId
        boa.env.eoa,  # pool (not used in mock)
        asset.address,  # tokenA
        asset_alt.address,  # tokenB
        mock_lego_lp_token.address,  # lpToken
        lp_to_remove,  # lpAmount
        0,  # minAmountA
        0,  # minAmountB
        sender=owner
    )
    
    # Get events
    remove_logs = filter_logs(user_wallet, "LiquidityRemoved")
    
    # Verify return values
    assert lp_burned == lp_to_remove
    expected_return = lp_to_remove // 2
    assert amount_a_received == expected_return
    assert amount_b_received == expected_return
    
    # Verify LP tokens were burned
    assert mock_lego_lp_token.balanceOf(user_wallet.address) == initial_lp_balance - lp_to_remove
    
    # Verify tokens were returned (mock returns half of LP amount to each)
    assert asset.balanceOf(user_wallet.address) == initial_asset_balance + expected_return
    assert asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + expected_return
    
    # Verify events
    assert len(remove_logs) == 1
    event = remove_logs[0]
    assert event.pool == boa.env.eoa
    assert event.tokenA == asset.address
    assert event.amountAReceived == expected_return
    assert event.tokenB == asset_alt.address
    assert event.amountBReceived == expected_return
    assert event.lpToken == mock_lego_lp_token.address
    assert event.lpAmountBurned == lp_to_remove
    assert event.legoId == 1
    assert event.legoAddr == mock_lego.address
    assert event.signer == owner
    assert event.isSignerAgent == False


def test_multiple_operations_sequence(setup_wallet_with_tokens, mock_lego_debt_token, bob):
    """Test a sequence of multiple operations to ensure they work together"""
    user_wallet, mock_lego, asset, vault, asset_alt = setup_wallet_with_tokens
    owner = bob
    
    # 1. Deposit into yield vault
    deposit_amount = 200 * EIGHTEEN_DECIMALS
    user_wallet.depositForYield(1, asset.address, vault.address, deposit_amount, sender=owner)
    assert vault.balanceOf(user_wallet.address) == deposit_amount
    
    # 2. Add collateral
    collateral_amount = 100 * EIGHTEEN_DECIMALS
    user_wallet.addCollateral(1, asset.address, collateral_amount, sender=owner)
    # MockLego doesn't track collateral, just verify the wallet balance decreased
    assert asset.balanceOf(user_wallet.address) < 1000 * EIGHTEEN_DECIMALS  # Started with 1000, used some for deposit and collateral
    
    # 3. Borrow against collateral
    borrow_amount = 50 * EIGHTEEN_DECIMALS
    user_wallet.borrow(1, mock_lego_debt_token.address, borrow_amount, sender=owner)
    assert mock_lego_debt_token.balanceOf(user_wallet.address) == borrow_amount
    
    # 4. Swap some tokens
    swap_amount = 100 * EIGHTEEN_DECIMALS
    swap_instructions = [(
        1,  # legoId
        swap_amount,  # amountIn
        0,  # minAmountOut
        [asset.address, asset_alt.address],  # tokenPath
        []  # poolPath
    )]
    user_wallet.swapTokens(swap_instructions, sender=owner)
    
    # 5. Add liquidity
    liq_amount = 50 * EIGHTEEN_DECIMALS
    user_wallet.addLiquidity(
        1, boa.env.eoa, asset.address, asset_alt.address,
        liq_amount, liq_amount, 0, 0, 0, sender=owner
    )
    
    # 6. Withdraw from yield
    withdraw_amount = 100 * EIGHTEEN_DECIMALS
    user_wallet.withdrawFromYield(1, vault.address, withdraw_amount, sender=owner)
    assert vault.balanceOf(user_wallet.address) == deposit_amount - withdraw_amount
    
    # All operations should have completed successfully
    assert True  # If we got here, all operations worked
