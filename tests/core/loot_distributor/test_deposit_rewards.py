"""
Test LootDistributor deposit rewards functionality
"""
import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


def test_add_deposit_rewards(setup_contracts):
    """Test adding deposit rewards"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    governance = ctx['governance']
    
    # Fund bob with tokens
    alpha_token.transfer(bob, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Approve loot distributor
    alpha_token.approve(loot.address, 500 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Add deposit rewards
    loot.addDepositRewards(500 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Check event
    events = filter_logs(loot, "DepositRewardsAdded")
    assert len(events) == 1
    assert events[0].asset == alpha_token.address
    assert events[0].amount == 500 * EIGHTEEN_DECIMALS
    assert events[0].adder == bob
    
    # Verify state
    assert loot.depositRewards() == 500 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(loot.address) == 500 * EIGHTEEN_DECIMALS


def test_add_deposit_rewards_no_asset_configured(setup_contracts, setUserWalletConfig):
    """Test adding deposit rewards when no asset is configured"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob = ctx['bob']
    
    # Remove deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=ZERO_ADDRESS)
    
    # Try to add rewards - should do nothing
    loot.addDepositRewards(500 * EIGHTEEN_DECIMALS, sender=bob)
    
    # No rewards should be added
    assert loot.depositRewards() == 0


def test_add_deposit_rewards_insufficient_balance(setup_contracts):
    """Test adding deposit rewards with insufficient balance"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    governance = ctx['governance']
    
    # Fund bob with only 100 tokens
    alpha_token.transfer(bob, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Approve more than balance
    alpha_token.approve(loot.address, 500 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Try to add 500 - should only add 100
    loot.addDepositRewards(500 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Should only add available amount
    assert loot.depositRewards() == 100 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(loot.address) == 100 * EIGHTEEN_DECIMALS


def test_add_deposit_rewards_multiple_additions(setup_contracts):
    """Test multiple additions of deposit rewards accumulate"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    alice = ctx['alice']
    governance = ctx['governance']
    
    # Fund both users
    alpha_token.transfer(bob, 300 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.transfer(alice, 200 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Bob adds 300
    alpha_token.approve(loot.address, 300 * EIGHTEEN_DECIMALS, sender=bob)
    loot.addDepositRewards(300 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Alice adds 200
    alpha_token.approve(loot.address, 200 * EIGHTEEN_DECIMALS, sender=alice)
    loot.addDepositRewards(200 * EIGHTEEN_DECIMALS, sender=alice)
    
    # Total should be 500
    assert loot.depositRewards() == 500 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(loot.address) == 500 * EIGHTEEN_DECIMALS


def test_add_deposit_rewards_zero_amount(setup_contracts):
    """Test adding zero deposit rewards"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob = ctx['bob']
    
    # Add zero rewards
    loot.addDepositRewards(0, sender=bob)
    
    # Nothing should happen
    assert loot.depositRewards() == 0


# Test claim deposit rewards

def test_claim_deposit_rewards_single_user(setup_contracts, ledger):
    """Test claiming deposit rewards for a single user"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    governance = ctx['governance']
    
    # Add deposit rewards
    alpha_token.transfer(bob, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 1000 * EIGHTEEN_DECIMALS, sender=bob)
    loot.addDepositRewards(1000 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Set user points (simulate deposit points accumulation)
    # PointsData struct: (usdValue, depositPoints, lastUpdate)
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        100 * EIGHTEEN_DECIMALS,   # depositPoints - 100 points
        boa.env.evm.patch.block_number  # lastUpdate
    )
    global_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        100 * EIGHTEEN_DECIMALS,   # depositPoints - Only this user has points
        boa.env.evm.patch.block_number  # lastUpdate
    )
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # Claim rewards
    initial_balance = alpha_token.balanceOf(bob_wallet.address)
    amount_claimed = loot.claimDepositRewards(bob_wallet.address, sender=bob)
    
    # Check event
    events = filter_logs(loot, "DepositRewardsClaimed")
    assert len(events) == 1
    assert events[0].user == bob_wallet.address
    assert events[0].asset == alpha_token.address
    assert events[0].amount == 1000 * EIGHTEEN_DECIMALS
    
    # Verify claim
    assert amount_claimed == 1000 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(bob_wallet.address) == initial_balance + 1000 * EIGHTEEN_DECIMALS
    assert loot.depositRewards() == 0
    
    # Verify points were zeroed
    updated_user_points, updated_global_points = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert updated_user_points.depositPoints == 0
    assert updated_global_points.depositPoints == 0


def test_claim_deposit_rewards_proportional_distribution(setup_contracts, ledger):
    """Test proportional distribution of deposit rewards"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alice_wallet = ctx['alice_wallet']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    alice = ctx['alice']
    governance = ctx['governance']
    
    # Add deposit rewards
    alpha_token.transfer(bob, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 1000 * EIGHTEEN_DECIMALS, sender=bob)
    loot.addDepositRewards(1000 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Set points - Bob has 75%, Alice has 25%
    bob_points = (
        750 * EIGHTEEN_DECIMALS,  # usdValue
        75 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    alice_points = (
        250 * EIGHTEEN_DECIMALS,  # usdValue
        25 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    global_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        100 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    
    ledger.setUserAndGlobalPoints(bob_wallet.address, bob_points, global_points, sender=loot.address)
    ledger.setUserAndGlobalPoints(alice_wallet.address, alice_points, global_points, sender=loot.address)
    
    # Bob claims first (should get 750 tokens)
    bob_claimed = loot.claimDepositRewards(bob_wallet.address, sender=bob)
    assert bob_claimed == 750 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(bob_wallet.address) == 750 * EIGHTEEN_DECIMALS
    
    # Update global points after Bob's claim
    updated_global = (
        250 * EIGHTEEN_DECIMALS,  # usdValue
        25 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    ledger.setUserAndGlobalPoints(alice_wallet.address, alice_points, updated_global, sender=loot.address)
    
    # Alice claims remaining (should get 250 tokens)
    alice_claimed = loot.claimDepositRewards(alice_wallet.address, sender=alice)
    assert alice_claimed == 250 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(alice_wallet.address) == 250 * EIGHTEEN_DECIMALS
    
    # All rewards claimed
    assert loot.depositRewards() == 0


def test_claim_deposit_rewards_no_points(setup_contracts):
    """Test claiming rewards with no points returns 0"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    governance = ctx['governance']
    
    # Add deposit rewards
    alpha_token.transfer(bob, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 1000 * EIGHTEEN_DECIMALS, sender=bob)
    loot.addDepositRewards(1000 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Don't set any points - user has 0 points
    
    # Try to claim
    amount_claimed = loot.claimDepositRewards(bob_wallet.address, sender=bob)
    assert amount_claimed == 0
    assert alpha_token.balanceOf(bob_wallet.address) == 0
    assert loot.depositRewards() == 1000 * EIGHTEEN_DECIMALS  # Unchanged


def test_claim_deposit_rewards_no_rewards_available(setup_contracts, ledger):
    """Test claiming when no rewards are available"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    bob = ctx['bob']
    
    # Set points but don't add rewards
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        100 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    global_points = user_points
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # Try to claim
    amount_claimed = loot.claimDepositRewards(bob_wallet.address, sender=bob)
    assert amount_claimed == 0


def test_claim_deposit_rewards_no_deposit_asset(setup_contracts, ledger, setUserWalletConfig):
    """Test claiming when no deposit rewards asset is configured"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    bob = ctx['bob']
    
    # Remove deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=ZERO_ADDRESS)
    
    # Set points
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        100 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, user_points, sender=loot.address)
    
    # Try to claim
    amount_claimed = loot.claimDepositRewards(bob_wallet.address, sender=bob)
    assert amount_claimed == 0


def test_claim_deposit_rewards_permission_check(setup_contracts, switchboard_alpha):
    """Test permission checks for claiming deposit rewards"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alice = ctx['alice']
    
    # Alice cannot claim Bob's rewards
    with boa.reverts("no perms"):
        loot.claimDepositRewards(bob_wallet.address, sender=alice)
    
    # Switchboard can claim
    amount = loot.claimDepositRewards(bob_wallet.address, sender=switchboard_alpha.address)
    assert amount == 0  # No rewards, but call succeeds


def test_claim_deposit_rewards_not_user_wallet(setup_contracts):
    """Test claiming for non-user wallet fails"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob = ctx['bob']
    
    with boa.reverts("not a user wallet"):
        loot.claimDepositRewards(bob, sender=bob)


def test_claim_deposit_rewards_updates_points_first(setup_contracts, ledger):
    """Test that claiming updates deposit points before calculating share"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    governance = ctx['governance']
    
    # Add rewards
    alpha_token.transfer(bob, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 1000 * EIGHTEEN_DECIMALS, sender=bob)
    loot.addDepositRewards(1000 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Set initial points from current block (will advance blocks later)
    initial_block = boa.env.evm.patch.block_number
    user_points = (
        500 * EIGHTEEN_DECIMALS,  # usdValue
        50 * EIGHTEEN_DECIMALS,  # depositPoints
        initial_block
    )
    global_points = user_points
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # Advance 100 blocks to accumulate more points
    boa.env.time_travel(blocks=100)
    
    # Claim should update points first (adding 100 blocks worth)
    amount_claimed = loot.claimDepositRewards(bob_wallet.address, sender=bob)
    
    # Should get all rewards (only user)
    assert amount_claimed == 1000 * EIGHTEEN_DECIMALS
    
    # Points should be zeroed after claim
    updated_user, updated_global = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert updated_user.depositPoints == 0
    assert updated_global.depositPoints == 0


def test_claim_deposit_rewards_precision(setup_contracts, ledger):
    """Test precision in reward distribution"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alice_wallet = ctx['alice_wallet']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    alice = ctx['alice']
    governance = ctx['governance']
    
    # Add odd amount of rewards
    alpha_token.transfer(bob, 333 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 333 * EIGHTEEN_DECIMALS, sender=bob)
    loot.addDepositRewards(333 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Set points with odd ratio
    bob_points = (
        666 * EIGHTEEN_DECIMALS,  # usdValue
        666 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    alice_points = (
        334 * EIGHTEEN_DECIMALS,  # usdValue
        334 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    global_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        1000 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    
    ledger.setUserAndGlobalPoints(bob_wallet.address, bob_points, global_points, sender=loot.address)
    ledger.setUserAndGlobalPoints(alice_wallet.address, alice_points, global_points, sender=loot.address)
    
    # Bob claims (666/1000 * 333 = 221.778...)
    bob_claimed = loot.claimDepositRewards(bob_wallet.address, sender=bob)
    assert bob_claimed == 221778000000000000000  # Rounded down
    
    # Update global points
    updated_global = (
        334 * EIGHTEEN_DECIMALS,  # usdValue
        334 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    ledger.setUserAndGlobalPoints(alice_wallet.address, alice_points, updated_global, sender=loot.address)
    
    # Alice claims remaining
    alice_claimed = loot.claimDepositRewards(alice_wallet.address, sender=alice)
    
    # Total claimed should not exceed total rewards
    assert bob_claimed + alice_claimed <= 333 * EIGHTEEN_DECIMALS
    
    # Small dust may remain due to rounding
    remaining = loot.depositRewards()
    assert remaining < EIGHTEEN_DECIMALS  # Less than 1 token dust


def test_claim_deposit_rewards_insufficient_balance(setup_contracts, ledger):
    """Test claiming when contract has insufficient balance"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    governance = ctx['governance']
    
    # Add rewards
    alpha_token.transfer(bob, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 1000 * EIGHTEEN_DECIMALS, sender=bob)
    loot.addDepositRewards(1000 * EIGHTEEN_DECIMALS, sender=bob)
    
    # Set points
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        100 * EIGHTEEN_DECIMALS,  # depositPoints
        boa.env.evm.patch.block_number
    )
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, user_points, sender=loot.address)
    
    # Remove half the tokens
    alpha_token.transfer(governance, 500 * EIGHTEEN_DECIMALS, sender=loot.address)
    
    # Claim should only transfer available
    amount_claimed = loot.claimDepositRewards(bob_wallet.address, sender=bob)
    assert amount_claimed == 500 * EIGHTEEN_DECIMALS
    
    # depositRewards tracking should be updated by full amount
    assert loot.depositRewards() == 500 * EIGHTEEN_DECIMALS  # 1000 - 500 claimed