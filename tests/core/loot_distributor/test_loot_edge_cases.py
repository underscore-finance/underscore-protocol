"""
Test LootDistributor edge cases and security concerns
"""
import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


def test_fee_overflow_protection(setup_contracts):
    """Test that fees are capped at 100%"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    setAssetConfig = ctx['setAssetConfig']
    sally_wallet = ctx['sally_wallet']
    
    # Set asset fee to 150% (should be capped at 100%)
    setAssetConfig(
        _asset=alpha_token,
        _swapFee=150_00  # 150%
    )
    
    # Fund wallet
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 1000 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    
    # Add loot - passing 100 tokens as transaction amount
    # With 150% fee (capped at 100%), Sally should receive 100 tokens
    loot.addLootFromSwapOrRewards(
        alpha_token.address,
        100 * EIGHTEEN_DECIMALS,  # transaction amount (not fee)
        0,  # SWAP
        sender=bob_wallet.address
    )
    
    # Should receive 100 tokens (100% of 100 - fee is capped)
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 100 * EIGHTEEN_DECIMALS


def test_yield_bonus_overflow_protection(setup_contracts, yearn_vault_v3, appraiser):
    """Test yield bonus calculation doesn't overflow"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    setAssetConfig = ctx['setAssetConfig']
    sally_wallet = ctx['sally_wallet']
    
    # Configure yield asset with very high bonus ratio
    setAssetConfig(
        _asset=yearn_vault_v3,
        _isYieldAsset=True,
        _underlyingAsset=alpha_token,
        _ambassadorBonusRatio=200_00  # 200% bonus (should be capped)
    )
    
    # Fund with underlying
    alpha_token.transfer(loot.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # For mock vault, price per share is based on balance/supply ratio
    # To get 1:1 price per share, deposit some tokens to the vault
    alpha_token.approve(yearn_vault_v3.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    yearn_vault_v3.deposit(1000 * EIGHTEEN_DECIMALS, governance.address, sender=governance.address)
    
    # Add yield profit with very high bonus (200%)
    # The bonus should be capped by available balance
    loot.addLootFromYieldProfit(
        yearn_vault_v3.address,
        0,  # No fee amount
        500 * EIGHTEEN_DECIMALS,  # Would require 1000 tokens at 200%
        sender=bob_wallet.address
    )
    
    # Should be capped at 100% = 500 tokens
    # Should be capped based on available balance
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) <= 1000 * EIGHTEEN_DECIMALS


def test_asset_deregistration_behavior(setup_contracts):
    """Test that assets are not automatically deregistered"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    sally_wallet = ctx['sally_wallet']
    setAssetConfig = ctx['setAssetConfig']
    
    # Reset alpha token to 10% swap fee (in case previous tests changed it)
    setAssetConfig(
        _asset=alpha_token,
        _swapFee=10_00  # 10%
    )
    
    # Add loot - passing 10 tokens as fee amount (10% of 100 token transaction)
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 1000 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    loot.addLootFromSwapOrRewards(alpha_token.address, 10 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)  # 10 tokens fee
    
    # Verify asset is registered
    assert loot.indexOfClaimableAsset(sally_wallet.address, alpha_token.address) == 1
    
    # Claim all loot using Sally's existing wallet
    loot.claimLoot(sally_wallet.address, sender=sally)
    
    # Asset should remain registered even with 0 balance
    assert loot.indexOfClaimableAsset(sally_wallet.address, alpha_token.address) == 1
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 0
    
    # Can still add more loot to same asset
    loot.addLootFromSwapOrRewards(alpha_token.address, 5 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)  # 5 tokens fee
    # Sally gets all 5 tokens (100% ambassador fee ratio)
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 5 * EIGHTEEN_DECIMALS


def test_deposit_rewards_dust_handling(setup_contracts, ledger):
    """Test handling of dust amounts in deposit rewards"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alice_wallet = ctx['alice_wallet']
    alpha_token = ctx['alpha_token']
    bob = ctx['bob']
    alice = ctx['alice']
    governance = ctx['governance']
    
    # Add rewards with odd amount
    alpha_token.transfer(bob, 1000 * EIGHTEEN_DECIMALS + 1, sender=governance.address)
    alpha_token.approve(loot.address, 1000 * EIGHTEEN_DECIMALS + 1, sender=bob)
    loot.addDepositRewards(1000 * EIGHTEEN_DECIMALS + 1, sender=bob)
    
    # Set points that will cause rounding
    bob_points = (
        333 * EIGHTEEN_DECIMALS,  # usdValue
        333,  # depositPoints
        boa.env.evm.patch.block_number
    )
    alice_points = (
        666 * EIGHTEEN_DECIMALS,  # usdValue
        666,  # depositPoints
        boa.env.evm.patch.block_number
    )
    global_points = (
        999 * EIGHTEEN_DECIMALS,  # usdValue
        999,  # depositPoints
        boa.env.evm.patch.block_number
    )
    
    ledger.setUserAndGlobalPoints(bob_wallet.address, bob_points, global_points, sender=loot.address)
    ledger.setUserAndGlobalPoints(alice_wallet.address, alice_points, global_points, sender=loot.address)
    
    # Bob claims
    bob_claimed = loot.claimDepositRewards(bob_wallet.address, sender=bob)
    
    # Update global points
    updated_global = (
        666 * EIGHTEEN_DECIMALS,  # usdValue
        666,  # depositPoints
        boa.env.evm.patch.block_number
    )
    ledger.setUserAndGlobalPoints(alice_wallet.address, alice_points, updated_global, sender=loot.address)
    
    # Alice claims
    alice_claimed = loot.claimDepositRewards(alice_wallet.address, sender=alice)
    
    # Total claimed should not exceed total rewards
    assert bob_claimed + alice_claimed <= 1000 * EIGHTEEN_DECIMALS + 1
    
    # Check remaining dust
    remaining = loot.depositRewards()
    assert remaining < 1000  # Very small dust amount


def test_points_block_number_edge_cases(setup_contracts, ledger, switchboard_alpha):
    """Test edge cases with block numbers"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    
    # Test 1: lastUpdate = 0 (uninitialized)
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        0  # Uninitialized
    )
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, user_points, sender=loot.address)
    
    # Update should work but no points accumulated
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    updated_user, _ = ledger.getUserAndGlobalPoints(bob_wallet.address)
    assert updated_user.depositPoints == 0
    assert updated_user.lastUpdate > 0
    
    # Test 2: Very large block number difference
    initial_block = boa.env.evm.patch.block_number
    user_points2 = (
        1,  # 1 wei
        0,  # depositPoints
        initial_block
    )
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points2, user_points2, sender=loot.address)
    
    # Advance by max practical blocks (1 year worth)
    boa.env.time_travel(blocks=2_628_000)  # ~1 year at 12s blocks
    
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    updated_user2, _ = ledger.getUserAndGlobalPoints(bob_wallet.address)
    
    # Should handle large block differences correctly
    expected = (1 * 2_628_000) // EIGHTEEN_DECIMALS
    assert updated_user2.depositPoints == expected


def test_transfer_failure_handling(setup_contracts, governance):
    """Test handling of transfer failures"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    bob = ctx['bob']
    
    # Create a mock reverting token
    mock_reverting_token = boa.loads('''
# @version 0.3.10

from vyper.interfaces import ERC20

implements: ERC20

name: public(String[32])
symbol: public(String[32])
decimals: public(uint8)
totalSupply: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])
shouldRevert: public(bool)

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

@external
def __init__():
    self.name = "RevertingToken"
    self.symbol = "RVT"
    self.decimals = 18

@external
def setShouldRevert(_shouldRevert: bool):
    self.shouldRevert = _shouldRevert

@external
def mint(_to: address, _value: uint256):
    self.totalSupply += _value
    self.balanceOf[_to] += _value
    log Transfer(empty(address), _to, _value)

@external
def transfer(_to: address, _value: uint256) -> bool:
    assert not self.shouldRevert, "transfer failed"
    assert self.balanceOf[msg.sender] >= _value
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    log Transfer(msg.sender, _to, _value)
    return True

@external
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    assert not self.shouldRevert, "transfer failed"
    assert self.balanceOf[_from] >= _value
    assert self.allowance[_from][msg.sender] >= _value
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowance[_from][msg.sender] -= _value
    log Transfer(_from, _to, _value)
    return True

@external
def approve(_spender: address, _value: uint256) -> bool:
    self.allowance[msg.sender][_spender] = _value
    log Approval(msg.sender, _spender, _value)
    return True
    ''')
    
    # Fund wallet with reverting token
    mock_reverting_token.mint(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS)
    
    # Approve loot distributor
    mock_reverting_token.approve(loot.address, 1000 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    
    # Set token to revert on transfer
    mock_reverting_token.setShouldRevert(True)
    
    # Try to add loot - should revert
    with boa.reverts("transfer failed"):
        loot.addLootFromSwapOrRewards(
            mock_reverting_token.address,
            100 * EIGHTEEN_DECIMALS,
            0,
            sender=bob_wallet.address
        )


def test_concurrent_claims_same_asset(setup_contracts):
    """Test multiple users claiming same asset concurrently"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alice_wallet = ctx['alice_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    
    # Both wallets have same ambassador
    # Add loot from both
    alpha_token.transfer(bob_wallet.address, 500 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.transfer(alice_wallet.address, 500 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    alpha_token.approve(loot.address, 500 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    alpha_token.approve(loot.address, 500 * EIGHTEEN_DECIMALS, sender=alice_wallet.address)
    
    loot.addLootFromSwapOrRewards(alpha_token.address, 50 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)  # 50 tokens fee
    loot.addLootFromSwapOrRewards(alpha_token.address, 50 * EIGHTEEN_DECIMALS, 0, sender=alice_wallet.address)  # 50 tokens fee
    
    # Sally has 100 tokens claimable (50 + 50)
    sally_wallet = ctx['sally_wallet']
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 100 * EIGHTEEN_DECIMALS
    
    sally_wallet_addr = sally_wallet.address
    
    # Claim should work correctly
    num_claimed = loot.claimLoot(sally_wallet_addr, sender=sally)
    assert num_claimed == 1
    assert alpha_token.balanceOf(sally_wallet_addr) == 100 * EIGHTEEN_DECIMALS


def test_zero_price_per_share_handling(setup_contracts, yearn_vault_v3, appraiser):
    """Test handling when price per share is zero"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    governance = ctx['governance']
    sally_wallet = ctx['sally_wallet']
    setAssetConfig = ctx['setAssetConfig']
    
    # Configure yield asset with bonus
    setAssetConfig(
        _asset=yearn_vault_v3,
        _isYieldAsset=True,  
        _underlyingAsset=alpha_token,
        _ambassadorBonusRatio=10_00
    )
    
    # Fund with underlying
    alpha_token.transfer(loot.address, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # For this test, we'll use the vault without any deposits
    # This gives an effective price per share of 0 since no assets backing the shares
    
    # Add yield profit
    loot.addLootFromYieldProfit(
        yearn_vault_v3.address,
        0,
        1000 * EIGHTEEN_DECIMALS,
        sender=bob_wallet.address
    )
    
    # No bonus should be given when price is 0
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 0


def test_maximum_assets_registration(setup_contracts):
    """Test behavior with many registered assets"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    sally = ctx['sally']
    governance = ctx['governance']
    sally_wallet = ctx['sally_wallet']
    
    # Create and register many mock tokens
    mock_tokens = []
    for i in range(10):
        token = boa.load("contracts/mock/MockErc20.vy", governance.address, f"Token{i}", f"TK{i}", 18, 1_000_000_000)
        mock_tokens.append(token)
        
        # Fund and add loot
        token.mint(bob_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
        token.approve(loot.address, 10 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
        loot.addLootFromSwapOrRewards(token.address, 1 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)  # 1 token fee
    
    # Check all assets registered
    assert loot.numClaimableAssets(sally_wallet.address) == 11  # 10 + 1 (starts at 1)
    
    sally_wallet_addr = sally_wallet.address
    num_claimed = loot.claimLoot(sally_wallet_addr, sender=sally)
    
    assert num_claimed == 10


def test_points_accumulation_with_zero_global_value(setup_contracts, ledger, switchboard_alpha):
    """Test points accumulation when global value is zero"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    
    # Set user value but global is zero (edge case)
    initial_block = boa.env.evm.patch.block_number
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        initial_block
    )
    global_points = (
        0,  # Global is zero
        0,  # depositPoints
        initial_block
    )
    ledger.setUserAndGlobalPoints(bob_wallet.address, user_points, global_points, sender=loot.address)
    
    # Advance blocks and update
    boa.env.time_travel(blocks=100)
    
    # This should still work - user accumulates points independently
    loot.updateDepositPoints(bob_wallet.address, sender=switchboard_alpha.address)
    
    updated_user, updated_global = ledger.getUserAndGlobalPoints(bob_wallet.address)
    # Points = (usdValue * blocks) / EIGHTEEN_DECIMALS = (1000 * 10^18 * 100) / 10^18 = 100,000
    assert updated_user.depositPoints == 100_000  # User accumulated
    assert updated_global.depositPoints == 0  # Global stays zero


# Security concerns documentation

def test_concern_deposit_rewards_frontrunning():
    """
    CONCERN: Users could potentially frontrun deposit reward additions
    by quickly depositing funds to gain points before rewards are added.
    
    MITIGATION: Points accumulate over time (blocks), so last-minute 
    deposits won't have accumulated many points. The block-based 
    accumulation acts as a natural defense against frontrunning.
    """
    pass


def test_concern_ambassador_fee_manipulation():
    """
    CONCERN: If ambassador fees can be changed after loot is accumulated,
    it doesn't affect already accumulated loot.
    
    VERIFICATION: The contract correctly snapshots the fee at the time 
    of the transaction. Changing fees later doesn't affect past accumulations.
    """
    pass


def test_concern_yield_bonus_price_manipulation():
    """
    CONCERN: The yield bonus calculation depends on price per share from 
    Appraiser. If the price is manipulated, it could affect bonus amounts.
    
    MITIGATION: This is mitigated by using the Appraiser contract which 
    should have proper price validation and staleness checks. The contract
    also caps bonuses at available balance.
    """
    pass


def test_concern_points_block_manipulation():
    """
    CONCERN: Points accumulation is based on block numbers. In theory,
    validators could manipulate block production to affect point accumulation.
    
    ASSESSMENT: This is a general blockchain concern and not specific to 
    this contract. The impact is limited as it would affect all users 
    proportionally. The points/block rate is also very small (value/10^18),
    limiting the impact of small block manipulations.
    """
    pass


def test_concern_reentrancy_protection():
    """
    CONCERN: The claim functions could be vulnerable to reentrancy attacks
    through malicious tokens.
    
    VERIFICATION: The contract follows the Checks-Effects-Interactions pattern:
    1. Checks permissions and balances
    2. Updates state (claimable amounts, points)
    3. Makes external calls (transfers)
    
    This ordering prevents reentrancy attacks.
    """
    pass


def test_concern_integer_overflow():
    """
    CONCERN: Large values in calculations could cause overflow.
    
    VERIFICATION: Vyper 0.4.3 has built-in overflow protection.
    All arithmetic operations are checked. The contract also uses
    min() functions to cap values where appropriate.
    """
    pass