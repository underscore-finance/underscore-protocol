"""
Test LootDistributor transaction fee functionality (addLootFromSwapOrRewards)
"""
import pytest
import boa
from constants import EIGHTEEN_DECIMALS


def test_add_loot_from_swap_with_ambassador(setup_contracts):
    """Test adding loot from swap with ambassador fees"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    
    # Fund wallet with tokens
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Approve loot distributor
    alpha_token.approve(loot.address, 100 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    
    # Add loot from swap - passing the fee amount (10% of 100 = 10 tokens)
    # Note: This function expects the fee amount, not the transaction amount
    loot.addLootFromSwapOrRewards(
        alpha_token.address,
        10 * EIGHTEEN_DECIMALS,  # 10% fee of 100 tokens
        0,  # ActionType.SWAP
        sender=bob_wallet.address
    )
    
    # Check ambassador wallet received the full fee (10 tokens)
    sally_wallet = ctx['sally_wallet']
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 10 * EIGHTEEN_DECIMALS
    assert loot.totalClaimableLoot(alpha_token.address) == 10 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(loot.address) == 10 * EIGHTEEN_DECIMALS
    
    # Check asset was registered
    assert loot.numClaimableAssets(sally_wallet.address) == 2  # starts at 1
    assert loot.claimableAssets(sally_wallet.address, 1) == alpha_token.address
    assert loot.indexOfClaimableAsset(sally_wallet.address, alpha_token.address) == 1


def test_add_loot_from_rewards_with_ambassador(setup_contracts):
    """Test adding loot from rewards with ambassador fees"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    
    # Fund wallet with tokens
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Approve loot distributor
    alpha_token.approve(loot.address, 100 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    
    # Add loot from rewards - passing the fee amount (5% of 100 = 5 tokens)
    loot.addLootFromSwapOrRewards(
        alpha_token.address,
        5 * EIGHTEEN_DECIMALS,  # 5% fee of 100 tokens
        1,  # ActionType.REWARDS
        sender=bob_wallet.address
    )
    
    # Check ambassador received the full fee (5 tokens)
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 5 * EIGHTEEN_DECIMALS
    assert loot.totalClaimableLoot(alpha_token.address) == 5 * EIGHTEEN_DECIMALS


def test_add_loot_with_multiple_fees(setup_contracts):
    """Test adding loot from different actions accumulates correctly"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    bravo_token = ctx['bravo_token']
    sally = ctx['sally']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    
    # Fund wallet with tokens
    bravo_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Approve loot distributor
    bravo_token.approve(loot.address, 300 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    
    # Add loot from swap - passing the fee amount (15% of 100 = 15 tokens)
    loot.addLootFromSwapOrRewards(
        bravo_token.address,
        15 * EIGHTEEN_DECIMALS,  # 15% fee
        0,  # ActionType.SWAP
        sender=bob_wallet.address
    )
    
    # Add loot from rewards - passing the fee amount (20% of 100 = 20 tokens)
    loot.addLootFromSwapOrRewards(
        bravo_token.address,
        20 * EIGHTEEN_DECIMALS,  # 20% fee
        1,  # ActionType.REWARDS
        sender=bob_wallet.address
    )
    
    # Check total accumulated (15 + 20 = 35)
    assert loot.claimableLoot(sally_wallet.address, bravo_token.address) == 35 * EIGHTEEN_DECIMALS
    assert loot.totalClaimableLoot(bravo_token.address) == 35 * EIGHTEEN_DECIMALS


def test_add_loot_no_ambassador(setup_contracts):
    """Test adding loot with no ambassador results in no fees"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    no_ambassador_wallet = ctx['no_ambassador_wallet']
    alpha_token = ctx['alpha_token']
    governance = ctx['governance']
    
    # Fund wallet with tokens
    alpha_token.transfer(no_ambassador_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Approve loot distributor
    alpha_token.approve(loot.address, 100 * EIGHTEEN_DECIMALS, sender=no_ambassador_wallet.address)
    
    # Add loot from swap - even if we pass a fee amount, no ambassador means no distribution
    loot.addLootFromSwapOrRewards(
        alpha_token.address,
        10 * EIGHTEEN_DECIMALS,  # Would be 10% fee
        0,  # ActionType.SWAP
        sender=no_ambassador_wallet.address
    )
    
    # Fees are collected but not distributed (no ambassador)
    assert alpha_token.balanceOf(loot.address) == 10 * EIGHTEEN_DECIMALS
    # No claimable loot since there's no ambassador
    assert loot.totalClaimableLoot(alpha_token.address) == 0


def test_add_loot_insufficient_balance(setup_contracts):
    """Test adding loot with insufficient balance only transfers available"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    
    # Fund wallet with only 5 tokens
    alpha_token.transfer(bob_wallet.address, 5 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Approve more than balance
    alpha_token.approve(loot.address, 100 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    
    # Try to add 10 tokens of fee but wallet only has 5 total
    loot.addLootFromSwapOrRewards(
        alpha_token.address,
        10 * EIGHTEEN_DECIMALS,  # Request 10 tokens fee
        0,  # ActionType.SWAP
        sender=bob_wallet.address
    )
    
    # Should only collect what's available (5 tokens)
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 5 * EIGHTEEN_DECIMALS


def test_add_loot_not_user_wallet(setup_contracts):
    """Test adding loot from non-user wallet fails"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    
    # Try to add loot from EOA (not a user wallet)
    with boa.reverts("not a user wallet"):
        loot.addLootFromSwapOrRewards(
            alpha_token.address,
            100 * EIGHTEEN_DECIMALS,
            0,  # ActionType.SWAP
            sender=bob
        )


def test_add_loot_zero_amount(setup_contracts):
    """Test adding zero amount does nothing"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    governance = ctx['governance']
    
    # Fund wallet
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Try to add 0 loot
    loot.addLootFromSwapOrRewards(
        alpha_token.address,
        0,
        0,  # ActionType.SWAP
        sender=bob_wallet.address
    )
    
    # Nothing should happen
    assert alpha_token.balanceOf(loot.address) == 0


def test_ambassador_fee_ratio_capped(setup_contracts):
    """Test that ambassador fee ratio is capped at 100%"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    setAssetConfig = ctx['setAssetConfig']
    
    # Fund wallet
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Pass 100 tokens as the fee amount
    alpha_token.approve(loot.address, 100 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    
    # Add loot with 100 token fee
    loot.addLootFromSwapOrRewards(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,  # Full fee amount
        0,  # SWAP
        sender=bob_wallet.address
    )
    
    # Ambassador gets 100% of the fee (capped at 100%)
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 100 * EIGHTEEN_DECIMALS


def test_multiple_ambassadors_same_asset(setup_contracts):
    """Test multiple ambassadors can have loot for the same asset"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alice_wallet = ctx['alice_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    
    # Both wallets have same ambassador, add loot from both
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.transfer(alice_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    alpha_token.approve(loot.address, 100 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    alpha_token.approve(loot.address, 200 * EIGHTEEN_DECIMALS, sender=alice_wallet.address)
    
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)  # 10% fee
    loot.addLootFromSwapOrRewards(alpha_token.address, 20 * EIGHTEEN_DECIMALS, 0, sender=alice_wallet.address)  # 10% fee
    
    # Sally's wallet should have accumulated loot from both
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 30 * EIGHTEEN_DECIMALS  # 10 + 20
    assert loot.totalClaimableLoot(alpha_token.address) == 30 * EIGHTEEN_DECIMALS


def test_different_action_types(setup_contracts):
    """Test all different action types for fee calculation"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    bravo_token = ctx['bravo_token']
    sally = ctx['sally']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    
    # Fund wallet
    bravo_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    bravo_token.approve(loot.address, 500 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    
    # Test each action type with bravo token fees:
    # SWAP: 15%, REWARDS: 20%
    
    # Add from swap - 15% fee
    loot.addLootFromSwapOrRewards(bravo_token.address, 15 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    assert loot.claimableLoot(sally_wallet.address, bravo_token.address) == 15 * EIGHTEEN_DECIMALS
    
    # Add from rewards - 20% fee
    loot.addLootFromSwapOrRewards(bravo_token.address, 20 * EIGHTEEN_DECIMALS, 1, sender=bob_wallet.address)
    assert loot.claimableLoot(sally_wallet.address, bravo_token.address) == 35 * EIGHTEEN_DECIMALS  # 15 + 20
    
    # Any other action type defaults to yield profit fee (25% for bravo, but we're passing fee amount directly)
    loot.addLootFromSwapOrRewards(bravo_token.address, 10 * EIGHTEEN_DECIMALS, 99, sender=bob_wallet.address)
    assert loot.claimableLoot(sally_wallet.address, bravo_token.address) == 45 * EIGHTEEN_DECIMALS  # 15 + 20 + 10