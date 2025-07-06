"""
Test LootDistributor claim loot functionality
"""
import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


def test_claim_loot_single_asset(setup_contracts):
    """Test claiming loot for a single asset"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    
    # Get sally's wallet from context
    sally_wallet = ctx['sally_wallet']
    
    # Setup: Add loot
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 10 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    # Pass fee amount directly (10 for alpha)
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    
    # Check claimable
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 10 * EIGHTEEN_DECIMALS
    assert loot.getTotalClaimableAssets(sally_wallet.address) == 1
    
    # Claim loot
    initial_balance = alpha_token.balanceOf(sally_wallet.address)
    num_claimed = loot.claimLoot(sally_wallet.address, sender=sally)
    
    # Check event
    events = filter_logs(loot, "LootClaimed")
    assert len(events) == 1
    assert events[0].user == sally_wallet.address
    assert events[0].asset == alpha_token.address
    assert events[0].amount == 10 * EIGHTEEN_DECIMALS
    
    # Verify claim
    assert num_claimed == 1
    assert alpha_token.balanceOf(sally_wallet.address) == initial_balance + 10 * EIGHTEEN_DECIMALS
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 0
    assert loot.totalClaimableLoot(alpha_token.address) == 0


def test_claim_loot_insufficient_balance(setup_contracts):
    """Test claiming loot when contract has insufficient balance"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    
    # Get sally's wallet from context
    sally_wallet = ctx['sally_wallet']
    
    # Setup: Add loot but don't fund the contract fully
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 10 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    # Pass fee amount directly (10 for alpha)
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    
    # Remove some tokens from loot distributor
    alpha_token.transfer(governance, 5 * EIGHTEEN_DECIMALS, sender=loot.address)
    
    # Claim should transfer only available amount
    num_claimed = loot.claimLoot(sally_wallet.address, sender=sally)
    
    assert num_claimed == 1
    assert alpha_token.balanceOf(sally_wallet.address) == 5 * EIGHTEEN_DECIMALS  # Only 5 available
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 5 * EIGHTEEN_DECIMALS  # 5 still claimable


def test_claim_loot_empty_assets(setup_contracts):
    """Test claiming with no claimable assets"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    sally = ctx['sally']
    
    # Create wallet for sally with no loot
    sally_wallet_addr = ctx['hatchery'].createUserWallet(sally, ZERO_ADDRESS, False, 1, sender=sally)
    
    # Claim should return 0
    num_claimed = loot.claimLoot(sally_wallet_addr, sender=sally)
    assert num_claimed == 0


def test_get_total_claimable_assets(setup_contracts):
    """Test getTotalClaimableAssets view function"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    bravo_token = ctx['bravo_token']
    sally = ctx['sally']
    governance = ctx['governance']
    
    # Get sally's wallet from context
    sally_wallet = ctx['sally_wallet']
    
    # Initially no claimable assets
    assert loot.getTotalClaimableAssets(sally_wallet.address) == 0
    
    # Add loot for multiple assets
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    bravo_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    alpha_token.approve(loot.address, 10 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    bravo_token.approve(loot.address, 15 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    
    # Pass fee amounts directly
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    loot.addLootFromSwapOrRewards(bravo_token.address, 15 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    
    # Should have 2 claimable assets
    assert loot.getTotalClaimableAssets(sally_wallet.address) == 2
    
    # Remove balance from one asset
    alpha_token.transfer(governance, alpha_token.balanceOf(loot.address), sender=loot.address)
    
    # Should have 1 claimable asset (bravo only)
    assert loot.getTotalClaimableAssets(sally_wallet.address) == 1


def test_claim_loot_multiple_claims(setup_contracts):
    """Test multiple partial claims of the same asset"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    
    # Get sally's wallet from context
    sally_wallet = ctx['sally_wallet']
    
    # Add loot
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 10 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    # Pass fee amount directly (10 for alpha)
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    
    # Sally has 10 tokens claimable
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 10 * EIGHTEEN_DECIMALS
    
    # First claim - remove half the balance
    alpha_token.transfer(governance, 5 * EIGHTEEN_DECIMALS, sender=loot.address)
    
    num_claimed = loot.claimLoot(sally_wallet.address, sender=sally)
    assert num_claimed == 1
    assert alpha_token.balanceOf(sally_wallet.address) == 5 * EIGHTEEN_DECIMALS
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 5 * EIGHTEEN_DECIMALS
    
    # Fund again
    alpha_token.transfer(loot.address, 5 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Second claim - get remaining
    num_claimed = loot.claimLoot(sally_wallet.address, sender=sally)
    assert num_claimed == 1
    assert alpha_token.balanceOf(sally_wallet.address) == 10 * EIGHTEEN_DECIMALS
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 0


def test_claim_loot_with_empty_slots(setup_contracts):
    """Test claiming when there are empty slots in claimable assets array"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    bravo_token = ctx['bravo_token']
    charlie_token = ctx['charlie_token']
    sally = ctx['sally']
    governance = ctx['governance']
    
    # Get sally's wallet from context
    sally_wallet = ctx['sally_wallet']
    
    # Add loot for three assets with correct fee amounts
    # Alpha: 10% fee
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 10 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    
    # Bravo: 15% fee
    bravo_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    bravo_token.approve(loot.address, 15 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    loot.addLootFromSwapOrRewards(bravo_token.address, 15 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    
    # Charlie: 10% fee (default) - Note: charlie has 6 decimals
    charlie_decimals = 10 ** 6
    charlie_token.transfer(bob_wallet.address, 1000 * charlie_decimals, sender=governance.address)
    charlie_token.approve(loot.address, 10 * charlie_decimals, sender=bob_wallet.address)
    loot.addLootFromSwapOrRewards(charlie_token.address, 10 * charlie_decimals, 0, sender=bob_wallet.address)
    
    # Remove balance from middle asset (bravo)
    bravo_balance = bravo_token.balanceOf(loot.address)
    bravo_token.transfer(governance, bravo_balance, sender=loot.address)
    
    # Claim should skip bravo and claim alpha and charlie
    num_claimed = loot.claimLoot(sally_wallet.address, sender=sally)
    
    assert num_claimed == 2  # Only alpha and charlie
    assert alpha_token.balanceOf(sally_wallet.address) == 10 * EIGHTEEN_DECIMALS
    assert bravo_token.balanceOf(sally_wallet.address) == 0  # Skipped
    assert charlie_token.balanceOf(sally_wallet.address) == 10 * charlie_decimals


def test_asset_registration_persistence(setup_contracts):
    """Test that assets remain registered even after full claim"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    
    # Get sally's wallet from context
    sally_wallet = ctx['sally_wallet']
    
    # Add loot
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 10 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    # Pass fee amount directly (10 for alpha)
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    
    # Verify asset is registered
    assert loot.indexOfClaimableAsset(sally_wallet.address, alpha_token.address) == 1
    assert loot.numClaimableAssets(sally_wallet.address) == 2
    
    # Claim all
    loot.claimLoot(sally_wallet.address, sender=sally)
    
    # Asset should still be registered
    assert loot.indexOfClaimableAsset(sally_wallet.address, alpha_token.address) == 1
    assert loot.numClaimableAssets(sally_wallet.address) == 2
    assert loot.claimableAssets(sally_wallet.address, 1) == alpha_token.address
    
    # Can add more loot to same asset
    alpha_token.approve(loot.address, 10 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    
    # Should not create duplicate registration
    assert loot.numClaimableAssets(sally_wallet.address) == 2  # Still 2
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 10 * EIGHTEEN_DECIMALS