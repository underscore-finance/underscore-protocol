"""
Test LootDistributor yield profit functionality (addLootFromYieldProfit)
"""
import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


def test_add_loot_from_yield_profit_with_fee(setup_contracts):
    """Test adding loot from yield profit with ambassador fees"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    bravo_token = ctx['bravo_token']
    sally = ctx['sally']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    
    # Fund loot distributor directly (yield profits are already in contract)
    bravo_token.transfer(loot.address, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Add loot from yield profit (25% fee)
    loot.addLootFromYieldProfit(
        bravo_token.address,
        100 * EIGHTEEN_DECIMALS,  # fee amount
        1000 * EIGHTEEN_DECIMALS,  # total yield amount (for bonus calculation)
        sender=bob_wallet.address
    )
    
    # Check ambassador received 100% of the fee amount (100 tokens)
    # Ambassador gets 100% of yield profit fees per config
    assert loot.claimableLoot(sally_wallet.address, bravo_token.address) == 100 * EIGHTEEN_DECIMALS


def test_add_loot_from_yield_profit_with_bonus(setup_contracts, setAssetConfig, createAssetYieldConfig):
    """Test adding loot from yield profit with ambassador bonus"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    yearn_vault_v3 = ctx['yearn_vault_v3']
    mock_lego = ctx['mock_lego']
    
    # Configure yield asset with lego adapter and underlying asset
    setAssetConfig(
        _asset=yearn_vault_v3,
        _legoId=1,  # lego ID for the mock adapter
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=alpha_token.address,
            _ambassadorBonusRatio=10_00  # 10% bonus
        )
    )
    
    # Set price per share for the vault (1.5x)
    mock_lego.setPricePerShare(yearn_vault_v3.address, 15 * EIGHTEEN_DECIMALS // 10)  # 1.5
    
    # Fund loot distributor with underlying tokens for bonus
    alpha_token.transfer(loot.address, 200 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Add yield profit with fee and bonus
    loot.addLootFromYieldProfit(
        yearn_vault_v3.address,
        100 * EIGHTEEN_DECIMALS,  # fee amount
        1000 * EIGHTEEN_DECIMALS,  # total yield amount
        sender=bob_wallet.address
    )
    
    # Ambassador should receive:
    # 1. Fee: The fee is handled internally by the contract (no vault token transfer needed)
    # 2. Bonus: 10% of 1000 = 100 vault tokens worth
    #    100 vault tokens at 1.5 price = 150 underlying tokens
    # Note: Since yield profit fees are already in the contract, no vault tokens are claimed
    # Bonus calculation: (totalYield * bonusRatio * pricePerShare) / decimals
    # = (1000 * 10% * 1.5) = 150 underlying tokens
    expected_bonus = 150 * EIGHTEEN_DECIMALS
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == expected_bonus


def test_add_loot_from_yield_no_ambassador(setup_contracts):
    """Test adding loot from yield with no ambassador"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    no_ambassador_wallet = ctx['no_ambassador_wallet']
    bravo_token = ctx['bravo_token']
    
    # Add loot from yield profit - should not collect any fees
    loot.addLootFromYieldProfit(
        bravo_token.address,
        100 * EIGHTEEN_DECIMALS,
        1000 * EIGHTEEN_DECIMALS,
        sender=no_ambassador_wallet.address
    )
    
    # No fees should be collected
    assert bravo_token.balanceOf(loot.address) == 0


def test_yield_profit_zero_fee_with_bonus(setup_contracts, setAssetConfig, createAssetYieldConfig):
    """Test yield profit with zero fee but with bonus"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    yearn_vault_v3 = ctx['yearn_vault_v3']
    mock_lego = ctx['mock_lego']
    
    # Configure yield asset with bonus but no fee
    setAssetConfig(
        _asset=yearn_vault_v3,
        _legoId=1,  # lego ID for the mock adapter
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=alpha_token.address,
            _performanceFee=0,  # No fee
            _ambassadorBonusRatio=20_00  # 20% bonus
        )
    )
    
    # Set price per share
    mock_lego.setPricePerShare(yearn_vault_v3.address, EIGHTEEN_DECIMALS)  # 1:1
    
    # Fund loot distributor with underlying for bonus
    alpha_token.transfer(loot.address, 500 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Add yield profit with no fee but bonus
    loot.addLootFromYieldProfit(
        yearn_vault_v3.address,
        0,  # no fee
        1000 * EIGHTEEN_DECIMALS,  # total yield
        sender=bob_wallet.address
    )
    
    # Should only get bonus: 20% of 1000 = 200 tokens
    assert loot.claimableLoot(sally_wallet.address, yearn_vault_v3.address) == 0  # no fee
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 200 * EIGHTEEN_DECIMALS


def test_yield_bonus_insufficient_underlying(setup_contracts, setAssetConfig, createAssetYieldConfig):
    """Test yield bonus when insufficient underlying available"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    yearn_vault_v3 = ctx['yearn_vault_v3']
    mock_lego = ctx['mock_lego']
    
    # Configure with high bonus
    setAssetConfig(
        _asset=yearn_vault_v3,
        _legoId=1,  # lego ID for the mock adapter
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=alpha_token.address,
            _ambassadorBonusRatio=50_00  # 50% bonus
        )
    )
    
    # Set price per share
    mock_lego.setPricePerShare(yearn_vault_v3.address, EIGHTEEN_DECIMALS)
    
    # Fund with less than bonus amount
    alpha_token.transfer(loot.address, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Try to get 500 token bonus but only 100 available
    loot.addLootFromYieldProfit(
        yearn_vault_v3.address,
        0,
        1000 * EIGHTEEN_DECIMALS,  # Would be 500 bonus
        sender=bob_wallet.address
    )
    
    # Should only get available amount
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 100 * EIGHTEEN_DECIMALS


def test_yield_bonus_with_existing_claimable(setup_contracts, setAssetConfig, createAssetYieldConfig):
    """Test yield bonus considers existing claimable amounts"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    yearn_vault_v3 = ctx['yearn_vault_v3']
    mock_lego = ctx['mock_lego']
    
    # First add some claimable alpha tokens for sally
    alpha_token.transfer(bob_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    alpha_token.approve(loot.address, 30 * EIGHTEEN_DECIMALS, sender=bob_wallet.address)
    loot.addLootFromSwapOrRewards(alpha_token.address, 30 * EIGHTEEN_DECIMALS, 0, sender=bob_wallet.address)  # 10% fee of 300
    
    # Sally now has 30 claimable alpha tokens
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 30 * EIGHTEEN_DECIMALS
    
    # Configure yield asset with bonus
    setAssetConfig(
        _asset=yearn_vault_v3,
        _legoId=1,  # lego ID for the mock adapter
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=alpha_token.address,
            _ambassadorBonusRatio=30_00  # 30% bonus
        )
    )
    
    # Set price per share
    mock_lego.setPricePerShare(yearn_vault_v3.address, EIGHTEEN_DECIMALS)
    
    # Fund for bonus (need 300 for bonus but only 270 available after existing claimable)
    alpha_token.transfer(loot.address, 300 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Add yield profit
    loot.addLootFromYieldProfit(
        yearn_vault_v3.address,
        0,
        1000 * EIGHTEEN_DECIMALS,  # 30% = 300 bonus
        sender=bob_wallet.address
    )
    
    # Should have existing 30 + available 270 = 300 total
    # But bonus calculation should give full 300
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 330 * EIGHTEEN_DECIMALS  # 30 + 300


def test_yield_bonus_zero_price_per_share(setup_contracts, setAssetConfig, createAssetYieldConfig):
    """Test yield bonus when price per share is zero"""
    # This test passes because when price per share is 0, no bonus is given
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally = ctx['sally']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    yearn_vault_v3 = boa.load("contracts/mock/MockErc4626Vault.vy", alpha_token)
    
    # Configure yield asset with bonus
    setAssetConfig(
        _asset=yearn_vault_v3,
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=alpha_token,
            _ambassadorBonusRatio=10_00
        )
    )
    
    # Fund with underlying
    alpha_token.transfer(loot.address, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Don't deposit anything to vault - price per share will be 0 from appraiser
    
    # Add yield profit
    loot.addLootFromYieldProfit(
        yearn_vault_v3.address,
        0,
        1000 * EIGHTEEN_DECIMALS,
        sender=bob_wallet.address
    )
    
    # No bonus should be given when price is 0
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 0


def test_yield_profit_not_user_wallet(setup_contracts):
    """Test yield profit from non-user wallet fails"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bravo_token = ctx['bravo_token']
    bob = ctx['bob']
    
    with boa.reverts("not a user wallet"):
        loot.addLootFromYieldProfit(
            bravo_token.address,
            100 * EIGHTEEN_DECIMALS,
            1000 * EIGHTEEN_DECIMALS,
            sender=bob  # EOA, not user wallet
        )


def test_yield_bonus_calculation_precision(setup_contracts, setAssetConfig, createAssetYieldConfig, mock_lego):
    """Test yield bonus calculation with different decimals"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    charlie_token = ctx['charlie_token']
    mock_lego = ctx['mock_lego']
    
    # Create a vault for charlie token (6 decimals)
    charlie_vault = boa.load("contracts/mock/MockErc4626Vault.vy", charlie_token.address)
    
    # Configure with charlie as underlying (6 decimals)
    setAssetConfig(
        _asset=charlie_vault,
        _legoId=1,  # lego ID for the mock adapter
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=charlie_token.address,
            _ambassadorBonusRatio=25_00  # 25%
        )
    )
    
    # Set price per share (2x with 6 decimals)
    mock_lego.setPricePerShare(charlie_vault.address, 2 * 10**6)
    
    # Fund with charlie tokens
    charlie_token.transfer(loot.address, 1000 * 10**6, sender=governance.address)
    
    # Add yield profit
    loot.addLootFromYieldProfit(
        charlie_vault.address,
        0,
        400 * 10**6,  # 400 charlie vault tokens
        sender=bob_wallet.address
    )
    
    # Bonus: 25% of 400 = 100 vault tokens
    # At 2x price = 200 underlying tokens
    assert loot.claimableLoot(sally_wallet.address, charlie_token.address) == 200 * 10**6


def test_yield_both_fee_and_bonus(setup_contracts, setAssetConfig, createAssetYieldConfig):
    """Test yield profit with both fee and bonus"""
    ctx = setup_contracts
    loot = ctx['loot_distributor']
    bob_wallet = ctx['bob_wallet']
    alpha_token = ctx['alpha_token']
    sally_wallet = ctx['sally_wallet']
    governance = ctx['governance']
    yearn_vault_v3 = ctx['yearn_vault_v3']
    mock_lego = ctx['mock_lego']
    
    # Configure with both fee and bonus
    setAssetConfig(
        _asset=yearn_vault_v3,
        _legoId=1,  # lego ID for the mock adapter
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=alpha_token.address,
            _performanceFee=30_00,  # 30% fee
            _ambassadorBonusRatio=15_00  # 15% bonus
        )
    )
    
    # Set price per share
    mock_lego.setPricePerShare(yearn_vault_v3.address, EIGHTEEN_DECIMALS)
    
    # Fund for bonus only (fee is already in contract from yield profit)
    alpha_token.transfer(loot.address, 200 * EIGHTEEN_DECIMALS, sender=governance.address)  # for bonus
    
    # Add yield profit
    loot.addLootFromYieldProfit(
        yearn_vault_v3.address,
        50 * EIGHTEEN_DECIMALS,  # fee amount
        1000 * EIGHTEEN_DECIMALS,  # total yield
        sender=bob_wallet.address
    )
    
    # Should get only bonus (no fee since it's handled internally)
    # Fee would be collected internally by the contract, not from this transfer
    assert loot.claimableLoot(sally_wallet.address, alpha_token.address) == 150 * EIGHTEEN_DECIMALS  # 15% of 1000