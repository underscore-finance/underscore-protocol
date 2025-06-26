import pytest
import boa

from contracts.core.userWallet import UserWallet
from contracts.core.agent import AgentOptimized
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
    return AgentOptimized.at(wallet_addr)


def create_action_instruction(
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
    extraAddr=ZERO_ADDRESS,
    extraVal=0,
    extraData=b'\x00' * 32,
    auxData=b'\x00' * 32,
    swapInstructions=None
):
    """Helper to create ActionInstruction tuple"""
    if swapInstructions is None:
        swapInstructions = []
    
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
        extraAddr,
        extraVal,
        extraData,
        auxData,
        swapInstructions
    )


# Basic batch tests

def test_batch_empty_instructions_fails(user_wallet, bob, agent):
    """Test that empty instruction array fails"""
    agent_owner = bob
    
    with boa.reverts():
        agent.performBatchActions(
            user_wallet,
            [],  # empty instructions
            sender=agent_owner
        )


def test_batch_single_deposit(user_wallet, bob, agent, mock_lego_asset, mock_lego_vault):
    """Test batch with single deposit action"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    
    # Create deposit instruction
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    instructions = [
        create_action_instruction(
            action=1,  # EARN_DEPOSIT
            legoId=1,
            asset=mock_lego_asset.address,
            target=mock_lego_vault.address,
            amount=deposit_amount
        )
    ]
    
    # Execute batch
    result = agent.performBatchActions(
        user_wallet,
        instructions,
        sender=agent_owner
    )
    
    assert result == True
    
    # Verify balances
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - deposit_amount
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance + deposit_amount


def test_batch_deposit_then_withdraw(user_wallet, bob, agent, mock_lego_asset, mock_lego_vault):
    """Test batch with deposit followed by withdrawal"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    
    # Create instructions: deposit 100, then withdraw 50
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    withdraw_amount = 50 * EIGHTEEN_DECIMALS
    
    instructions = [
        create_action_instruction(
            action=1,  # EARN_DEPOSIT
            legoId=1,
            asset=mock_lego_asset.address,
            target=mock_lego_vault.address,
            amount=deposit_amount
        ),
        create_action_instruction(
            action=2,  # EARN_WITHDRAW
            legoId=1,
            asset=mock_lego_vault.address,
            amount=withdraw_amount
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify final balances (deposited 100, withdrew 50, net vault +50)
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - 50 * EIGHTEEN_DECIMALS
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance + 50 * EIGHTEEN_DECIMALS


# Tests for usePrevAmountOut functionality

def test_batch_swap_then_deposit_with_prev_amount(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt, mock_lego_vault):
    """Test using swap output as deposit input"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    
    # Swap 100 asset to asset_alt, then deposit all received asset_alt
    swap_amount = 100 * EIGHTEEN_DECIMALS
    
    swap_instruction = (
        1,  # legoId
        swap_amount,  # amountIn
        0,  # minAmountOut
        [mock_lego_asset.address, mock_lego_asset_alt.address],  # tokenPath
        []  # poolPath
    )
    
    instructions = [
        create_action_instruction(
            action=4,  # SWAP
            swapInstructions=[swap_instruction]
        ),
        create_action_instruction(
            action=1,  # EARN_DEPOSIT
            usePrevAmountOut=True,  # Use swap output
            legoId=1,
            asset=mock_lego_asset_alt.address,
            target=mock_lego_vault.address,
            amount=0  # Will be overridden by prevAmountOut
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify: swapped 100 asset for asset_alt, then deposited all asset_alt
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - swap_amount
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance  # All swapped tokens deposited
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance + swap_amount  # MockLego 1:1 swap


def test_batch_withdraw_then_swap_with_prev_amount(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt, mock_lego_vault):
    """Test withdrawing from vault then swapping the withdrawn amount"""
    agent_owner = bob
    
    # First deposit some tokens
    deposit_amount = 200 * EIGHTEEN_DECIMALS
    agent.depositForYield(user_wallet, 1, mock_lego_asset.address, mock_lego_vault.address, deposit_amount, sender=agent_owner)
    
    # Initial balances after deposit
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    
    # Withdraw 100 and swap all withdrawn tokens
    withdraw_amount = 100 * EIGHTEEN_DECIMALS
    
    swap_instruction = (
        1,  # legoId
        0,  # amountIn - will be overridden by usePrevAmountOut
        0,  # minAmountOut
        [mock_lego_asset.address, mock_lego_asset_alt.address],  # tokenPath
        []  # poolPath
    )
    
    instructions = [
        create_action_instruction(
            action=2,  # EARN_WITHDRAW
            legoId=1,
            asset=mock_lego_vault.address,
            amount=withdraw_amount
        ),
        create_action_instruction(
            action=4,  # SWAP
            usePrevAmountOut=True,  # Use withdrawn amount
            swapInstructions=[swap_instruction]
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify: withdrew 100, swapped all to asset_alt
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance - withdraw_amount
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance  # All withdrawn tokens swapped
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + withdraw_amount


# Complex batch scenarios

def test_batch_complex_defi_strategy(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt, mock_lego_vault, mock_lego_debt_token):
    """Test complex DeFi strategy: deposit, add collateral, borrow, swap borrowed tokens"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    
    # Strategy amounts
    deposit_amount = 200 * EIGHTEEN_DECIMALS
    collateral_amount = 100 * EIGHTEEN_DECIMALS
    borrow_amount = 50 * EIGHTEEN_DECIMALS
    
    swap_instruction = (
        1,  # legoId
        0,  # amountIn - will use borrowed amount
        0,  # minAmountOut
        [mock_lego_debt_token.address, mock_lego_asset_alt.address],  # tokenPath
        []  # poolPath
    )
    
    instructions = [
        # 1. Deposit assets to vault
        create_action_instruction(
            action=1,  # EARN_DEPOSIT
            legoId=1,
            asset=mock_lego_asset.address,
            target=mock_lego_vault.address,
            amount=deposit_amount
        ),
        # 2. Add collateral
        create_action_instruction(
            action=7,  # ADD_COLLATERAL
            legoId=1,
            asset=mock_lego_asset.address,
            amount=collateral_amount
        ),
        # 3. Borrow against collateral
        create_action_instruction(
            action=9,  # BORROW
            legoId=1,
            asset=mock_lego_debt_token.address,
            amount=borrow_amount
        ),
        # 4. Swap borrowed tokens
        create_action_instruction(
            action=4,  # SWAP
            usePrevAmountOut=True,  # Use borrowed amount
            swapInstructions=[swap_instruction]
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify results
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - deposit_amount - collateral_amount
    assert mock_lego_debt_token.balanceOf(user_wallet.address) == 0  # All borrowed tokens swapped
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + borrow_amount  # Received from swap


def test_batch_liquidity_operations(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt, mock_lego_lp_token):
    """Test batch liquidity operations: add liquidity, then remove half"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    initial_lp_balance = mock_lego_lp_token.balanceOf(user_wallet.address)
    
    # Amounts
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 100 * EIGHTEEN_DECIMALS
    expected_lp = amount_a + amount_b  # MockLego mints sum
    lp_to_remove = expected_lp // 2
    
    # Pack LP token address into auxData for remove liquidity
    # Convert to int first, then to bytes32
    lp_token_packed = boa.eval(f"convert({int(mock_lego_lp_token.address, 16)}, bytes32)")
    
    instructions = [
        # 1. Add liquidity
        create_action_instruction(
            action=14,  # ADD_LIQ
            legoId=1,
            target=boa.env.eoa,  # pool (not used in mock)
            asset=mock_lego_asset.address,
            asset2=mock_lego_asset_alt.address,
            amount=amount_a,
            amount2=amount_b
        ),
        # 2. Remove half the liquidity
        create_action_instruction(
            action=15,  # REMOVE_LIQ
            usePrevAmountOut=False,  # Specify exact amount
            legoId=1,
            target=boa.env.eoa,  # pool
            asset=mock_lego_asset.address,
            asset2=mock_lego_asset_alt.address,
            amount=lp_to_remove,
            auxData=lp_token_packed
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify: added liquidity, then removed half
    # Net effect: -50 of each token, +100 LP tokens
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - 50 * EIGHTEEN_DECIMALS
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance - 50 * EIGHTEEN_DECIMALS
    assert mock_lego_lp_token.balanceOf(user_wallet.address) == initial_lp_balance + lp_to_remove


def test_batch_mint_pending_and_confirm(user_wallet, bob, agent, mock_lego, mock_lego_asset, mock_lego_asset_alt):
    """Test batch with pending mint and confirmation"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    
    mint_amount = 100 * EIGHTEEN_DECIMALS
    
    instructions = [
        # 1. Create pending mint
        create_action_instruction(
            action=5,  # MINT_REDEEM
            legoId=1,
            asset=mock_lego_asset.address,
            target=mock_lego_asset_alt.address,
            amount=mint_amount,
            minOut1=mint_amount,
            extraVal=1  # Pending state
        ),
        # 2. Confirm the mint
        create_action_instruction(
            action=6,  # CONFIRM_MINT_REDEEM
            legoId=1,
            asset=mock_lego_asset.address,
            target=mock_lego_asset_alt.address
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify: asset decreased, asset_alt increased after confirmation
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - mint_amount
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + mint_amount
    
    # Verify pending mint was cleared
    pending_mint = mock_lego.pendingMintOrRedeem(user_wallet.address)
    assert pending_mint[2] == 0  # amount should be 0


def test_batch_rebalance_with_confusing_amount2(user_wallet, bob, agent, mock_lego_asset, mock_lego_vault, mock_lego_asset_alt):
    """Test rebalance where amount2 is used as toLegoId"""
    agent_owner = bob
    
    # First deposit into vault
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    agent.depositForYield(user_wallet, 1, mock_lego_asset.address, mock_lego_vault.address, deposit_amount, sender=agent_owner)
    
    # Initial balances
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    
    rebalance_amount = 50 * EIGHTEEN_DECIMALS
    
    instructions = [
        create_action_instruction(
            action=3,  # EARN_REBALANCE
            legoId=1,  # fromLegoId
            asset=mock_lego_vault.address,  # fromVault
            amount2=1,  # toLegoId (NOT an amount! This is the confusing part)
            target=mock_lego_asset.address,  # toVault
            amount=rebalance_amount  # actual amount to rebalance
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify rebalance worked despite confusing parameter usage
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance - rebalance_amount
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance + rebalance_amount


def test_batch_chain_multiple_swaps(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt, mock_lego_vault):
    """Test chaining multiple swaps using prevAmountOut"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    
    swap_amount = 100 * EIGHTEEN_DECIMALS
    
    # Swap asset -> asset_alt -> vault token (all MockLego supported tokens)
    swap_instruction1 = (
        1,  # legoId
        swap_amount,  # amountIn
        0,  # minAmountOut
        [mock_lego_asset.address, mock_lego_asset_alt.address],  # tokenPath
        []  # poolPath
    )
    
    swap_instruction2 = (
        1,  # legoId
        0,  # amountIn - will use prev output
        0,  # minAmountOut
        [mock_lego_asset_alt.address, mock_lego_vault.address],  # tokenPath
        []  # poolPath
    )
    
    instructions = [
        create_action_instruction(
            action=4,  # SWAP
            swapInstructions=[swap_instruction1]
        ),
        create_action_instruction(
            action=4,  # SWAP
            usePrevAmountOut=True,
            swapInstructions=[swap_instruction2]
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify: asset decreased, vault token increased, asset_alt unchanged
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance - swap_amount
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance  # Intermediate token
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance + swap_amount  # Final output


def test_batch_max_instructions(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt):
    """Test batch with maximum allowed instructions"""
    agent_owner = bob
    
    # Create 15 instructions (MAX_INSTRUCTIONS)
    # Alternate between small swaps
    instructions = []
    swap_amount = 1 * EIGHTEEN_DECIMALS
    
    for i in range(15):
        if i % 2 == 0:
            # Swap asset to asset_alt
            swap_instruction = (
                1,  # legoId
                swap_amount,  # amountIn
                0,  # minAmountOut
                [mock_lego_asset.address, mock_lego_asset_alt.address],  # tokenPath
                []  # poolPath
            )
        else:
            # Swap asset_alt to asset
            swap_instruction = (
                1,  # legoId
                swap_amount,  # amountIn
                0,  # minAmountOut
                [mock_lego_asset_alt.address, mock_lego_asset.address],  # tokenPath
                []  # poolPath
            )
        
        instructions.append(
            create_action_instruction(
                action=4,  # SWAP
                swapInstructions=[swap_instruction]
            )
        )
    
    # Execute batch - should succeed
    result = agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    assert result == True


def test_batch_transfer_chain(user_wallet, bob, agent, mock_lego_asset, charlie):
    """Test chaining transfers with different amounts"""
    agent_owner = bob
    
    # Initial balance
    initial_balance = mock_lego_asset.balanceOf(user_wallet.address)
    
    instructions = [
        # Transfer 100 to charlie
        create_action_instruction(
            action=0,  # TRANSFER
            target=charlie,
            asset=mock_lego_asset.address,
            amount=100 * EIGHTEEN_DECIMALS
        ),
        # Transfer another 50 to charlie
        create_action_instruction(
            action=0,  # TRANSFER
            target=charlie,
            asset=mock_lego_asset.address,
            amount=50 * EIGHTEEN_DECIMALS
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify total transferred
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_balance - 150 * EIGHTEEN_DECIMALS
    assert mock_lego_asset.balanceOf(charlie) == 150 * EIGHTEEN_DECIMALS


def test_batch_invalid_action_fails(user_wallet, bob, agent):
    """Test that invalid action number fails"""
    agent_owner = bob
    
    instructions = [
        create_action_instruction(
            action=99,  # Invalid action
            amount=100
        )
    ]
    
    with boa.reverts():
        agent.performBatchActions(user_wallet, instructions, sender=agent_owner)


def test_batch_rewards_and_compound(user_wallet, bob, agent, mock_lego_asset, mock_lego_vault):
    """Test claiming rewards and compounding them"""
    agent_owner = bob
    
    # Initial balances
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_vault_balance = mock_lego_vault.balanceOf(user_wallet.address)
    
    reward_amount = 50 * EIGHTEEN_DECIMALS
    
    instructions = [
        # 1. Claim rewards
        create_action_instruction(
            action=11,  # REWARDS
            legoId=1,
            asset=mock_lego_asset.address,
            amount=reward_amount  # Note: this is the reward amount in this action
        ),
        # 2. Deposit claimed rewards
        create_action_instruction(
            action=1,  # EARN_DEPOSIT
            usePrevAmountOut=True,  # Use claimed rewards
            legoId=1,
            asset=mock_lego_asset.address,
            target=mock_lego_vault.address,
            amount=0  # Will be overridden
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify: claimed rewards and deposited them
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_asset_balance  # Claimed then deposited
    assert mock_lego_vault.balanceOf(user_wallet.address) == initial_vault_balance + reward_amount


# Edge case tests

def test_batch_use_prev_amount_without_prev_output(user_wallet, bob, agent, mock_lego_asset, charlie):
    """Test using prevAmountOut when no previous output exists"""
    agent_owner = bob
    
    # Initial balance
    initial_balance = mock_lego_asset.balanceOf(user_wallet.address)
    
    # Try to use prevAmountOut on first instruction (should use original amount)
    deposit_amount = 100 * EIGHTEEN_DECIMALS
    
    instructions = [
        create_action_instruction(
            action=0,  # TRANSFER
            usePrevAmountOut=True,  # No previous output, should use amount
            target=charlie,
            asset=mock_lego_asset.address,
            amount=deposit_amount
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify: transferred the specified amount (not 0)
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_balance - deposit_amount


def test_batch_with_signature_verification(user_wallet, bob, agent, mock_lego_asset, charlie):
    """Test batch actions work correctly with owner authentication"""
    agent_owner = bob
    
    # Initial balance
    initial_balance = mock_lego_asset.balanceOf(user_wallet.address)
    
    # Create simple transfer instruction
    instructions = [
        create_action_instruction(
            action=0,  # TRANSFER
            target=charlie,
            asset=mock_lego_asset.address,
            amount=50 * EIGHTEEN_DECIMALS
        )
    ]
    
    # Execute batch as owner (no signature needed)
    result = agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    assert result == True
    
    # Verify transfer happened
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_balance - 50 * EIGHTEEN_DECIMALS


def test_batch_liquidity_removal_limitation(user_wallet, bob, agent, mock_lego_asset, mock_lego_asset_alt, mock_lego_lp_token):
    """Test that demonstrates liquidity removal only passes tokenA amount forward"""
    agent_owner = bob
    
    # First add liquidity to have LP tokens
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 200 * EIGHTEEN_DECIMALS  # Different amount for tokenB
    agent.addLiquidity(
        user_wallet, 1, boa.env.eoa, mock_lego_asset.address, mock_lego_asset_alt.address,
        amount_a, amount_b, 0, 0, 0, sender=agent_owner
    )
    
    # Initial balances
    initial_lp_balance = mock_lego_lp_token.balanceOf(user_wallet.address)
    initial_asset_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_asset_alt_balance = mock_lego_asset_alt.balanceOf(user_wallet.address)
    
    # Remove all liquidity and try to use tokenB amount (but will get tokenA amount)
    lp_to_remove = initial_lp_balance
    lp_token_packed = boa.eval(f"convert({int(mock_lego_lp_token.address, 16)}, bytes32)")
    
    instructions = [
        # Remove liquidity - returns 50 tokenA and 50 tokenB (mock returns half of LP amount each)
        create_action_instruction(
            action=15,  # REMOVE_LIQ
            legoId=1,
            target=boa.env.eoa,
            asset=mock_lego_asset.address,
            asset2=mock_lego_asset_alt.address,
            amount=lp_to_remove,
            auxData=lp_token_packed
        ),
        # Try to swap "tokenB amount" but will actually use tokenA amount
        create_action_instruction(
            action=4,  # SWAP
            usePrevAmountOut=True,  # Will use tokenA amount, not tokenB!
            swapInstructions=[(
                1,
                0,  # amount will be overridden
                0,
                [mock_lego_asset_alt.address, mock_lego_asset.address],  # Trying to swap alt token
                []
            )]
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify: The swap used tokenA amount (lp_to_remove/2) not tokenB amount
    # MockLego returns half of LP amount for each token
    expected_token_a_from_removal = lp_to_remove // 2
    
    # The swap tried to swap tokenA amount of alt tokens (not tokenB amount)
    # So we should have: initial_alt + tokenB_from_removal - tokenA_amount_swapped
    assert mock_lego_asset_alt.balanceOf(user_wallet.address) == initial_asset_alt_balance + (lp_to_remove // 2) - expected_token_a_from_removal


def test_batch_all_actions_that_return_zero(user_wallet, bob, agent, mock_lego_asset, charlie):
    """Test batch with actions that return 0 (can't chain with usePrevAmountOut)"""
    agent_owner = bob
    
    # Initial balance
    initial_balance = mock_lego_asset.balanceOf(user_wallet.address)
    initial_charlie_balance = mock_lego_asset.balanceOf(charlie)
    
    instructions = [
        # Transfer returns the amount transferred
        create_action_instruction(
            action=0,  # TRANSFER
            target=charlie,
            asset=mock_lego_asset.address,
            amount=10 * EIGHTEEN_DECIMALS
        ),
        # Add collateral returns 0
        create_action_instruction(
            action=7,  # ADD_COLLATERAL
            legoId=1,
            asset=mock_lego_asset.address,
            amount=20 * EIGHTEEN_DECIMALS
        ),
        # Try to use prev amount (should be 0 from add collateral, so will use original amount)
        create_action_instruction(
            action=0,  # TRANSFER
            usePrevAmountOut=True,  # Will try to use prev amount, but since it's 0, will use amount
            target=charlie,
            asset=mock_lego_asset.address,
            amount=30 * EIGHTEEN_DECIMALS  # Will NOT be overridden since prevAmount is 0
        )
    ]
    
    # Execute batch
    agent.performBatchActions(user_wallet, instructions, sender=agent_owner)
    
    # Verify: all three actions happened (transfer 10, collateral 20, transfer 30)
    assert mock_lego_asset.balanceOf(user_wallet.address) == initial_balance - 10 * EIGHTEEN_DECIMALS - 20 * EIGHTEEN_DECIMALS - 30 * EIGHTEEN_DECIMALS
    assert mock_lego_asset.balanceOf(charlie) == initial_charlie_balance + 10 * EIGHTEEN_DECIMALS + 30 * EIGHTEEN_DECIMALS  # Both transfers