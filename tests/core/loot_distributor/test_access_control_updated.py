"""
Test access control for LootDistributor functions
"""
import pytest
import boa
from constants import EIGHTEEN_DECIMALS


def test_update_deposit_points_access_control(setup_contracts, switchboard_alpha, ledger):
    """Test access control for updateDepositPoints (switchboard only)"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    bob = ctx['bob']
    alice = ctx['alice']
    
    # Only switchboard can call updateDepositPoints
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)  # Should work
    
    # Others cannot call it
    with boa.reverts("no perms"):
        loot.updateDepositPoints(bob_wallet.address, sender=bob)
    
    with boa.reverts("no perms"):
        loot.updateDepositPoints(bob_wallet.address, sender=alice)


def test_update_deposit_points_with_data_access_control(setup_contracts, switchboard_alpha, ledger):
    """Test access control for updateDepositPointsWithData (multiple valid callers)"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alice_wallet = ctx['alice_wallet']
    bob = ctx['bob']
    alice = ctx['alice']
    
    # Switchboard can call it
    loot.updateDepositPointsWithData(
        bob_wallet.address,
        1000 * EIGHTEEN_DECIMALS,
        True,
        sender=switchboard_alpha.address
    )
    
    # User wallet can call it for itself
    loot.updateDepositPointsWithData(
        bob_wallet.address,
        1100 * EIGHTEEN_DECIMALS,
        True,
        sender=bob_wallet.address
    )
    
    # User wallet config can call it (this would be tested if we had wallet config instances)
    # For now, we test that EOAs cannot call it for other wallets
    # The call will revert because bob (EOA) doesn't have a wallet() function
    with boa.reverts():  # Generic revert since EOA doesn't have wallet() function
        loot.updateDepositPointsWithData(
            alice_wallet.address,
            1200 * EIGHTEEN_DECIMALS,
            True,
            sender=bob  # EOA trying to update another wallet
        )


def test_claim_permissions(setup_contracts, switchboard_alpha):
    """Test claim permissions (owner or switchboard)"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alice_wallet = ctx['alice_wallet']
    bob = ctx['bob']
    alice = ctx['alice']
    sally = ctx['sally']
    alpha_token = ctx['alpha_token']
    governance = ctx['governance']
    
    # Setup some claimable loot
    alpha_token.transfer(bob_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 10 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)
    
    # Owner can claim
    loot.claimLoot(alice_wallet.address, sender=alice)  # Alice claiming for her own wallet
    
    # Switchboard can claim for anyone
    loot.claimLoot(bob_wallet.address, sender=switchboard_alpha.address)
    
    # Non-owner cannot claim for others
    with boa.reverts("no perms"):
        loot.claimLoot(alice_wallet.address, sender=bob)  # Bob trying to claim for Alice


def test_deposit_rewards_permissions(setup_contracts, switchboard_alpha):
    """Test deposit rewards claim permissions"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    alice_wallet = ctx['alice_wallet']
    alice = ctx['alice']
    bob = ctx['bob']
    alpha_token = ctx['alpha_token']
    governance = ctx['governance']
    ledger = ctx.get('ledger')
    
    # Add some deposit rewards
    alpha_token.approve(loot.address, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
    loot.addDepositRewards(100 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Give Alice some points if ledger is available
    if ledger:
        user_points = (1000 * EIGHTEEN_DECIMALS, 0, boa.env.evm.patch.block_number)
        global_points = (1000 * EIGHTEEN_DECIMALS, 0, boa.env.evm.patch.block_number)
        ledger.setUserAndGlobalPoints(alice_wallet.address, user_points, global_points, sender=loot.address)
        boa.env.time_travel(blocks=100)
    
    # Owner can claim
    loot.claimDepositRewards(alice_wallet.address, sender=alice)
    
    # Switchboard can claim
    loot.claimDepositRewards(alice_wallet.address, sender=switchboard_alpha.address)
    
    # Non-owner cannot claim
    with boa.reverts("no perms"):
        loot.claimDepositRewards(alice_wallet.address, sender=bob)


def test_not_user_wallet_restrictions(setup_contracts):
    """Test that EOAs cannot call user-wallet-only functions"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob = ctx['bob']
    alice = ctx['alice']
    alpha_token = ctx['alpha_token']
    bravo_token = ctx['bravo_token']
    
    # EOAs cannot call these functions
    with boa.reverts("not a user wallet"):
        loot.claimLoot(bob, sender=bob)
    
    with boa.reverts("not a user wallet"):
        loot.claimDepositRewards(alice, sender=alice)
    
    with boa.reverts("not a user wallet"):
        loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob)
    
    with boa.reverts("not a user wallet"):
        loot.addLootFromYieldProfit(bravo_token.address, 5 * EIGHTEEN_DECIMALS, 100 * EIGHTEEN_DECIMALS, sender=alice)