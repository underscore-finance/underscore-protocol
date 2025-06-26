import pytest
import boa

from contracts.core.userWallet import UserWallet
from contracts.core.agent import AgentWrapper
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


@pytest.fixture(scope="module")
def user_wallet(hatchery, bob, mock_lego_asset, mock_lego_asset_alt, whale, agent): # must load `agent` here!
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS

    # transfer assets into user wallet
    mock_lego_asset.transfer(wallet_addr, 1_000 * EIGHTEEN_DECIMALS, sender=whale)
    mock_lego_asset_alt.transfer(wallet_addr, 1_000 * EIGHTEEN_DECIMALS, sender=whale)

    return UserWallet.at(wallet_addr)


@pytest.fixture(scope="module")
def agent(setAgentConfig, setUserWalletConfig, hatchery, bob):
    setAgentConfig()

    wallet_addr = hatchery.createAgent(sender=bob)
    assert wallet_addr != ZERO_ADDRESS

    setUserWalletConfig(_defaultAgent=wallet_addr)
    return AgentWrapper.at(wallet_addr)


# tests


def test_agent_deposit_for_yield(user_wallet, bob, agent, mock_lego_asset, mock_lego_vault):
    """Test depositing assets into yield vault"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    
    # Deposit 100 tokens
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call depositForYield
    assetAmount, vaultToken, vaultTokenAmountReceived = agent.depositForYield(
        user_wallet,
        1,  # legoId for MockLego
        mock_lego_asset.address,
        mock_lego_vault.address,
        deposit_amount,
        sender=agent_owner
    )
    
    # Verify return values
    assert assetAmount == deposit_amount
    assert vaultToken == mock_lego_vault.address
    assert vaultTokenAmountReceived == deposit_amount
    
    # Verify balances
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - deposit_amount
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance + deposit_amount


def test_agent_withdraw_from_yield(user_wallet, bob, agent, mock_lego_asset, mock_lego_vault):
    """Test withdrawing assets from yield vault through agent"""
    agent_owner = bob
    
    # First deposit some tokens
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    agent.depositForYield(user_wallet, 1, mock_lego_asset.address, mock_lego_vault.address, deposit_amount, sender=agent_owner)
    
    # Initial balances after deposit
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    
    # Withdraw 50 tokens
    withdraw_amount = 50 * EIGHTEEN_DECIMALS
    
    # Call withdrawFromYield
    underlyingAmount, underlyingToken, vaultTokenAmountWithdrawn = agent.withdrawFromYield(
        user_wallet,
        1,  # legoId for MockLego
        mock_lego_vault.address,
        withdraw_amount,
        sender=agent_owner
    )
    
    # Verify return values
    assert underlyingAmount == withdraw_amount
    assert underlyingToken == mock_lego_asset.address
    assert vaultTokenAmountWithdrawn == withdraw_amount
    
    # Verify balances
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance + withdraw_amount
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance - withdraw_amount


def test_agent_rebalance_yield_position(user_wallet, bob, agent, mock_lego_asset, mock_lego_vault, mock_lego_asset_alt):
    """Test rebalancing between yield positions through agent"""
    agent_owner = bob
    
    # First deposit into vault
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    agent.depositForYield(user_wallet, 1, mock_lego_asset.address, mock_lego_vault.address, deposit_amount, sender=agent_owner)
    
    # Initial balances
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    
    # Rebalance 50 tokens from vault back to asset
    rebalance_amount = 50 * EIGHTEEN_DECIMALS
    
    # Call rebalanceYieldPosition - using asset as the "toVault" for simplicity
    underlyingAmount, underlyingToken, vaultTokenAmount = agent.rebalanceYieldPosition(
        user_wallet,
        1,  # fromLegoId
        mock_lego_vault.address,  # fromVault
        1,  # toLegoId (same MockLego)
        mock_lego_asset.address,  # toVault (using asset as a vault for this test)
        rebalance_amount,
        sender=agent_owner
    )
    
    # Verify return values
    assert underlyingAmount == rebalance_amount
    assert underlyingToken == mock_lego_asset.address
    assert vaultTokenAmount == rebalance_amount
    
    # Verify balances - vault should decrease, asset should increase
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance - rebalance_amount
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance + rebalance_amount


def test_agent_swap_tokens(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt):
    """Test swapping tokens through agent"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    
    # Swap 100 tokens
    swap_amount = 100 * EIGHTEEN_DECIMALS
    
    # Create swap instruction as tuple (legoId, amountIn, minAmountOut, tokenPath, poolPath)
    swap_instructions = [(
        1,  # legoId
        swap_amount,  # amountIn
        0,  # minAmountOut
        [mock_lego_asset.address, mock_lego_asset_alt.address],  # tokenPath
        []  # poolPath
    )]
    
    # Call swapTokens
    tokenIn, amountIn, tokenOut, amountOut = agent.swapTokens(
        user_wallet,
        swap_instructions,
        sender=agent_owner
    )
    
    # Verify return values
    assert tokenIn == mock_lego_asset.address
    assert amountIn == swap_amount
    assert tokenOut == mock_lego_asset_alt.address
    assert amountOut == swap_amount  # 1:1 in mock
    
    # Verify balances (1:1 swap in mock)
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - swap_amount
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + swap_amount


def test_agent_mint_asset_immediate(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt):
    """Test minting asset immediately (no pending state) through agent"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    
    # Mint 100 tokens worth (1:1 ratio in mock)
    mint_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call mintOrRedeemAsset with _extraVal = 0 for immediate mint
    assetTokenAmount, outputAmount, isPending = agent.mintOrRedeemAsset(
        user_wallet,
        1,  # legoId
        mock_lego_asset.address,  # tokenIn
        mock_lego_asset_alt.address,  # tokenOut
        mint_amount,  # amountIn
        mint_amount,  # minAmountOut
        boa.env.eoa,  # _extraAddr (not used)
        0,  # _extraVal = 0 for immediate execution
        b'\x00' * 32,  # _extraData
        sender=agent_owner
    )
    
    # Verify return values
    assert assetTokenAmount == mint_amount
    assert outputAmount == mint_amount
    assert isPending == False
    
    # Verify balances - asset decreased, asset_alt increased
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - mint_amount
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + mint_amount


def test_agent_mint_asset_pending_and_confirm(user_wallet, bob, agent, mock_lego, mock_lego_asset, mock_lego_asset_alt):
    """Test minting asset with pending state and confirmation through agent"""
    agent_owner = bob
    
    # Initial balance
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    
    # Mint 100 tokens worth with pending state
    mint_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call mintOrRedeemAsset with _extraVal = 1 for pending mint
    assetTokenAmount, outputAmount, isPending = agent.mintOrRedeemAsset(
        user_wallet,
        1,  # legoId
        mock_lego_asset.address,  # tokenIn
        mock_lego_asset_alt.address,  # tokenOut
        mint_amount,  # amountIn
        mint_amount,  # minAmountOut
        boa.env.eoa,  # _extraAddr
        1,  # _extraVal = 1 for pending state
        b'\x00' * 32,  # _extraData
        sender=agent_owner
    )
    
    # Verify return values for pending state
    assert assetTokenAmount == 0  # No tokens moved yet
    assert outputAmount == 0  # No output yet
    assert isPending == True
    
    # Verify asset balance decreased but asset_alt hasn't increased yet
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - mint_amount
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance
    
    # Verify pending mint was created in MockLego
    pending_mint = mock_lego.pendingMintOrRedeem(user_wallet.address)
    assert pending_mint[0] == mock_lego_asset.address  # tokenIn
    assert pending_mint[1] == mock_lego_asset_alt.address  # tokenOut
    assert pending_mint[2] == mint_amount  # amount
    
    # Confirm the mint - returns single uint256
    outputAmount2 = agent.confirmMintOrRedeemAsset(
        user_wallet,
        1,  # legoId
        mock_lego_asset.address,  # tokenIn
        mock_lego_asset_alt.address,  # tokenOut
        sender=agent_owner
    )
    
    # Verify return value from confirmation
    assert outputAmount2 == mint_amount  # Output tokens received
    
    # Verify asset_alt balance increased after confirmation
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - mint_amount
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + mint_amount
    
    # Verify pending mint was cleared
    pending_mint_after = mock_lego.pendingMintOrRedeem(user_wallet.address)
    assert pending_mint_after[2] == 0  # amount should be 0


def test_agent_add_collateral(user_wallet, bob, agent, mock_lego_asset):
    """Test adding collateral through agent"""
    agent_owner = bob
    
    # Initial balance
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    
    # Add 100 tokens as collateral
    collateral_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call addCollateral
    amount_added = agent.addCollateral(
        user_wallet,
        1,  # legoId
        mock_lego_asset.address,
        collateral_amount,
        sender=agent_owner
    )
    
    # Verify return value
    assert amount_added == collateral_amount
    
    # Verify balance decreased (collateral locked)
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - collateral_amount


def test_agent_remove_collateral(user_wallet, bob, agent, mock_lego_asset):
    """Test removing collateral through agent"""
    agent_owner = bob
    
    # First add collateral
    collateral_amount = 100 * EIGHTEEN_DECIMALS
    agent.addCollateral(user_wallet, 1, mock_lego_asset.address, collateral_amount, sender=agent_owner)
    
    # Initial balance after adding collateral
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    
    # Remove 50 tokens of collateral
    remove_amount = 50 * EIGHTEEN_DECIMALS
    
    # Call removeCollateral
    amount_removed = agent.removeCollateral(
        user_wallet,
        1,  # legoId
        mock_lego_asset.address,
        remove_amount,
        sender=agent_owner
    )
    
    # Verify return value
    assert amount_removed == remove_amount
    
    # Verify balance increased (collateral returned)
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance + remove_amount


def test_agent_borrow(user_wallet, bob, agent, mock_lego_asset, mock_lego_debt_token):
    """Test borrowing against collateral through agent"""
    agent_owner = bob
    
    # First add collateral
    collateral_amount = 200 * EIGHTEEN_DECIMALS
    agent.addCollateral(user_wallet, 1, mock_lego_asset.address, collateral_amount, sender=agent_owner)
    
    # Initial debt token balance
    initial_debt_balance = mock_lego_debt_token.balanceOf(user_wallet.address)
    
    # Borrow 100 debt tokens
    borrow_amount = 100 * EIGHTEEN_DECIMALS
    
    # Call borrow - returns single uint256
    amount_borrowed = agent.borrow(
        user_wallet,
        1,  # legoId
        mock_lego_debt_token.address,
        borrow_amount,
        sender=agent_owner
    )
    
    # Verify return value
    assert amount_borrowed == borrow_amount
    
    # Verify debt token balance increased
    assert mock_lego_debt_token.balanceOf(user_wallet.address) == initial_debt_balance + borrow_amount


def test_agent_repay_debt(user_wallet, bob, agent, mock_lego_asset, mock_lego_debt_token):
    """Test repaying borrowed debt through agent"""
    agent_owner = bob
    
    # Setup: Add collateral and borrow
    collateral_amount = 200 * EIGHTEEN_DECIMALS
    agent.addCollateral(user_wallet, 1, mock_lego_asset.address, collateral_amount, sender=agent_owner)
    
    borrow_amount = 100 * EIGHTEEN_DECIMALS
    agent.borrow(user_wallet, 1, mock_lego_debt_token.address, borrow_amount, sender=agent_owner)
    
    # Initial debt token balance after borrowing
    initial_debt_balance = mock_lego_debt_token.balanceOf(user_wallet.address)
    
    # Repay 50 debt tokens
    repay_amount = 50 * EIGHTEEN_DECIMALS
    
    # Call repayDebt
    amount_repaid = agent.repayDebt(
        user_wallet,
        1,  # legoId
        mock_lego_debt_token.address,
        repay_amount,
        sender=agent_owner
    )
    
    # Verify return value
    assert amount_repaid == repay_amount
    
    # Verify debt token balance decreased
    assert mock_lego_debt_token.balanceOf(user_wallet.address) == initial_debt_balance - repay_amount


def test_agent_claim_rewards(user_wallet, bob, agent, mock_lego_asset):
    """Test claiming rewards through agent"""
    agent_owner = bob
    
    # MockLego doesn't have a setRewards function, it just mints the requested reward amount
    reward_amount = 50 * EIGHTEEN_DECIMALS
    
    # Initial balance
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    
    # Call claimRewards
    rewards_claimed = agent.claimRewards(
        user_wallet,
        1,  # legoId
        mock_lego_asset.address,  # rewardToken
        reward_amount,  # rewardAmount
        sender=agent_owner
    )
    
    # Verify return value
    assert rewards_claimed == reward_amount
    
    # Verify balance increased by reward amount
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance + reward_amount


def test_agent_add_liquidity(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt, mock_lego_lp_token):
    """Test adding liquidity through agent"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    initial_lp_balance = mock_lego_lp_token.balanceOf(user_wallet.address)
    
    # Add liquidity with 100 of each token
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 100 * EIGHTEEN_DECIMALS
    
    # Call addLiquidity
    lp_amount, actual_amount_a, actual_amount_b = agent.addLiquidity(
        user_wallet,
        1,  # legoId
        boa.env.eoa,  # pool (not used in mock)
        mock_lego_asset.address,  # tokenA
        mock_lego_asset_alt.address,  # tokenB
        amount_a,  # amountA
        amount_b,  # amountB
        0,  # minAmountA
        0,  # minAmountB
        0,  # minLpOut
        sender=agent_owner
    )
    
    # Verify return values
    assert actual_amount_a == amount_a
    assert actual_amount_b == amount_b
    expected_lp = amount_a + amount_b
    assert lp_amount == expected_lp
    
    # Verify token balances decreased
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - amount_a
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance - amount_b
    
    # Verify LP tokens were minted (mock mints sum of amounts)
    assert mock_lego_lp_token.balanceOf(user_wallet.address) == initial_lp_balance + expected_lp


def test_agent_remove_liquidity(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt, mock_lego_lp_token):
    """Test removing liquidity through agent"""
    agent_owner = bob
    
    # First add liquidity
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 100 * EIGHTEEN_DECIMALS
    agent.addLiquidity(
        user_wallet, 1, boa.env.eoa, mock_lego_asset.address, mock_lego_asset_alt.address,
        amount_a, amount_b, 0, 0, 0, sender=agent_owner
    )
    
    # Initial balances after adding liquidity
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    initial_lp_balance = mock_lego_lp_token.balanceOf(user_wallet.address)
    
    # Remove half the liquidity
    lp_to_remove = initial_lp_balance // 2
    
    # Call removeLiquidity - MockLego returns (amountA, amountB, lpBurned)
    amount_a_received, amount_b_received, lp_burned = agent.removeLiquidity(
        user_wallet,
        1,  # legoId
        boa.env.eoa,  # pool (not used in mock)
        mock_lego_asset.address,  # tokenA
        mock_lego_asset_alt.address,  # tokenB
        mock_lego_lp_token.address,  # lpToken
        lp_to_remove,  # lpAmount
        0,  # minAmountA
        0,  # minAmountB
        sender=agent_owner
    )
    
    # Verify return values
    assert lp_burned == lp_to_remove
    expected_return = lp_to_remove // 2
    assert amount_a_received == expected_return
    assert amount_b_received == expected_return
    
    # Verify LP tokens were burned
    assert mock_lego_lp_token.balanceOf(user_wallet.address) == initial_lp_balance - lp_to_remove
    
    # Verify tokens were returned (mock returns half of LP amount to each)
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance + expected_return
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + expected_return


def test_agent_multiple_operations_sequence(user_wallet, bob, agent, mock_lego_asset, mock_lego_vault, mock_lego_asset_alt, mock_lego_debt_token):
    """Test a sequence of multiple operations through agent to ensure they work together"""
    agent_owner = bob
    
    # 1. Deposit into yield vault
    deposit_amount = 200 * EIGHTEEN_DECIMALS
    agent.depositForYield(user_wallet, 1, mock_lego_asset.address, mock_lego_vault.address, deposit_amount, sender=agent_owner)
    assert mock_lego_vault.balanceOf(user_wallet.address) == deposit_amount
    
    # 2. Add collateral
    collateral_amount = 100 * EIGHTEEN_DECIMALS
    agent.addCollateral(user_wallet, 1, mock_lego_asset.address, collateral_amount, sender=agent_owner)
    # MockLego doesn't track collateral, just verify the wallet balance decreased
    assert mock_lego_asset.balanceOf(user_wallet.address) < 1000 * EIGHTEEN_DECIMALS  # Started with 1000, used some for deposit and collateral
    
    # 3. Borrow against collateral
    borrow_amount = 50 * EIGHTEEN_DECIMALS
    agent.borrow(user_wallet, 1, mock_lego_debt_token.address, borrow_amount, sender=agent_owner)
    assert mock_lego_debt_token.balanceOf(user_wallet.address) == borrow_amount
    
    # 4. Swap some tokens
    swap_amount = 100 * EIGHTEEN_DECIMALS
    swap_instructions = [(
        1,  # legoId
        swap_amount,  # amountIn
        0,  # minAmountOut
        [mock_lego_asset.address, mock_lego_asset_alt.address],  # tokenPath
        []  # poolPath
    )]
    agent.swapTokens(user_wallet, swap_instructions, sender=agent_owner)
    
    # 5. Add liquidity
    liq_amount = 50 * EIGHTEEN_DECIMALS
    agent.addLiquidity(
        user_wallet, 1, boa.env.eoa, mock_lego_asset.address, mock_lego_asset_alt.address,
        liq_amount, liq_amount, 0, 0, 0, sender=agent_owner
    )
    
    # 6. Withdraw from yield
    withdraw_amount = 100 * EIGHTEEN_DECIMALS
    agent.withdrawFromYield(user_wallet, 1, mock_lego_vault.address, withdraw_amount, sender=agent_owner)
    assert mock_lego_vault.balanceOf(user_wallet.address) == deposit_amount - withdraw_amount
    
    # All operations should have completed successfully
    assert True  # If we got here, all operations worked
