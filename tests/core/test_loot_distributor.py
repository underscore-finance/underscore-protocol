import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS, ACTION_TYPE
from contracts.core.userWallet import UserWallet


#####################
# Ambassador Config #
#####################


def test_get_ambassador_config_with_asset_config(loot_distributor, ambassador_wallet, user_wallet, alpha_token, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test getAmbassadorConfig when asset config is set in mission control """
    
    # Create ambassador rev share config
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=50_00,      # 50%
        _rewardsRatio=45_00,   # 45%
        _yieldRatio=40_00,     # 40%
    )
    
    # Create yield config with bonus ratio and underlying asset
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=alpha_token.address,
        _ambassadorBonusRatio=10_00,  # 10%
    )
    
    # Set asset config with ambassador settings
    setAssetConfig(
        alpha_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Get ambassador config
    config = loot_distributor.getAmbassadorConfig(user_wallet.address, alpha_token.address)
    
    # Verify the config
    assert config.ambassador == ambassador_wallet.address
    assert config.ambassadorRevShare.swapRatio == 50_00
    assert config.ambassadorRevShare.rewardsRatio == 45_00
    assert config.ambassadorRevShare.yieldRatio == 40_00
    assert config.ambassadorBonusRatio == 10_00
    assert config.underlyingAsset == alpha_token.address
    assert config.decimals == alpha_token.decimals()  # Should get decimals from the token


def test_get_ambassador_config_no_asset_config(loot_distributor, ambassador_wallet, user_wallet, alpha_token, setUserWalletConfig, createAmbassadorRevShare):
    """ Test getAmbassadorConfig when no asset config is set (defaults to global config) """
    
    # Create global ambassador rev share settings
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,      # 30%
        _rewardsRatio=25_00,   # 25%
        _yieldRatio=20_00,     # 20%
    )
    
    # Set user wallet config with global ambassador settings
    setUserWalletConfig(
        _ambassadorRevShare=ambassadorRevShare,
        _defaultYieldAmbassadorBonusRatio=5_00,  # 5% global bonus ratio
    )
    
    # Get ambassador config (no specific asset config set)
    config = loot_distributor.getAmbassadorConfig(user_wallet.address, alpha_token.address)
    
    # Verify the config uses global defaults
    assert config.ambassador == ambassador_wallet.address
    assert config.ambassadorRevShare.swapRatio == 30_00
    assert config.ambassadorRevShare.rewardsRatio == 25_00
    assert config.ambassadorRevShare.yieldRatio == 20_00
    assert config.ambassadorBonusRatio == 5_00  # Global bonus ratio
    assert config.underlyingAsset == ZERO_ADDRESS  # No underlying asset in global config
    assert config.decimals == alpha_token.decimals()  # Should get decimals from the token


def test_get_ambassador_config_with_vault_registration(loot_distributor, ambassador_wallet, user_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, ledger, setUserWalletConfig, createAmbassadorRevShare):
    """ Test getAmbassadorConfig when there is a registered vault token (with underlying asset, decimals info) """
    
    # Set up global defaults first
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=15_00,      # 15%
        _rewardsRatio=12_00,   # 12%
        _yieldRatio=10_00,     # 10%
    )
    
    setUserWalletConfig(
        _ambassadorRevShare=ambassadorRevShare,
        _defaultYieldAmbassadorBonusRatio=3_00,  # 3% global bonus ratio
    )
    
    # Register vault token by making a deposit
    yield_underlying_token.approve(mock_yield_lego, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1_000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Verify vault token registration
    vault_token = ledger.vaultTokens(yield_vault_token)
    assert vault_token.legoId == 1
    assert vault_token.underlyingAsset == yield_underlying_token.address
    assert vault_token.decimals == yield_vault_token.decimals()
    
    # Get ambassador config for vault token (no specific config set)
    config = loot_distributor.getAmbassadorConfig(user_wallet.address, yield_vault_token.address)
    
    # Verify the config uses global defaults for rev share but vault registration for underlying/decimals
    assert config.ambassador == ambassador_wallet.address
    assert config.ambassadorRevShare.swapRatio == 15_00  # From global defaults
    assert config.ambassadorRevShare.rewardsRatio == 12_00  # From global defaults
    assert config.ambassadorRevShare.yieldRatio == 10_00  # From global defaults
    assert config.ambassadorBonusRatio == 3_00  # From global defaults

    # These should come from the vault token registration
    assert config.underlyingAsset == yield_underlying_token.address
    assert config.decimals == yield_vault_token.decimals()


####################
# Protocol Revenue #
####################


# add loot from swap or rewards


def test_add_loot_from_swap_fees(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, setAssetConfig, createAmbassadorRevShare):
    """ Test addLootFromSwapOrRewards for swap fees with ambassador rev share """
    
    # Set up ambassador config with 30% swap fee share
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,      # 30%
        _rewardsRatio=25_00,   # 25%
        _yieldRatio=20_00,     # 20%
    )
    
    setAssetConfig(
        alpha_token,
        _ambassadorRevShare=ambassadorRevShare,
    )
    
    # Transfer tokens to user wallet and approve loot distributor
    fee_amount = 100 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor.address, fee_amount, sender=user_wallet.address)
    
    # Check initial state
    assert loot_distributor.totalClaimableLoot(alpha_token) == 0
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == 0
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 0
    
    # Add loot from swap
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    # Verify ambassador gets 30% of the fee
    expected_ambassador_fee = fee_amount * 30_00 // 100_00  # 30 tokens
    assert loot_distributor.totalClaimableLoot(alpha_token) == expected_ambassador_fee
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == expected_ambassador_fee
    
    # Verify asset registration
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 2  # Starts at 1, not 0
    assert loot_distributor.claimableAssets(ambassador_wallet, 1) == alpha_token.address
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 1


def test_add_loot_from_rewards_fees(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, setAssetConfig, createAmbassadorRevShare):
    """ Test addLootFromSwapOrRewards for rewards fees with different rev share ratio """
    
    # Set up ambassador config with 50% rewards fee share
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,      # 30%
        _rewardsRatio=50_00,   # 50% for rewards
        _yieldRatio=20_00,     # 20%
    )
    
    setAssetConfig(
        alpha_token,
        _ambassadorRevShare=ambassadorRevShare,
    )
    
    # Transfer tokens to user wallet and approve
    fee_amount = 200 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor.address, fee_amount, sender=user_wallet.address)
    
    # Add loot from rewards action
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.REWARDS,
        sender=user_wallet.address
    )
    
    # Verify ambassador gets 50% of the fee for rewards
    expected_ambassador_fee = fee_amount * 50_00 // 100_00  # 100 tokens
    assert loot_distributor.totalClaimableLoot(alpha_token) == expected_ambassador_fee
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == expected_ambassador_fee


def test_add_loot_multiple_assets(loot_distributor, user_wallet, ambassador_wallet, alpha_token, bravo_token, alpha_token_whale, bravo_token_whale, setAssetConfig, createAmbassadorRevShare):
    """ Test adding loot from multiple assets to verify claimableAssets tracking """
    
    # Set up ambassador config for both tokens
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=40_00,      # 40%
        _rewardsRatio=40_00,   # 40%
        _yieldRatio=40_00,     # 40%
    )
    
    setAssetConfig(alpha_token, _ambassadorRevShare=ambassadorRevShare)
    setAssetConfig(bravo_token, _ambassadorRevShare=ambassadorRevShare)
    
    # Transfer and approve alpha token
    alpha_fee = 100 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, alpha_fee, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor.address, alpha_fee, sender=user_wallet.address)
    
    # Transfer and approve bravo token
    bravo_fee = 50 * EIGHTEEN_DECIMALS
    bravo_token.transfer(user_wallet, bravo_fee, sender=bravo_token_whale)
    bravo_token.approve(loot_distributor.address, bravo_fee, sender=user_wallet.address)
    
    # Add loot from alpha token
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        alpha_fee,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    # Add loot from bravo token
    loot_distributor.addLootFromSwapOrRewards(
        bravo_token,
        bravo_fee,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    # Verify claimable amounts
    expected_alpha_fee = alpha_fee * 40_00 // 100_00  # 40 tokens
    expected_bravo_fee = bravo_fee * 40_00 // 100_00  # 20 tokens
    
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == expected_alpha_fee
    assert loot_distributor.claimableLoot(ambassador_wallet, bravo_token) == expected_bravo_fee
    
    # Verify asset registration
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 3  # Starts at 1, so 1 + 2 assets = 3
    
    # Check both assets are registered
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 1
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, bravo_token) == 2
    
    assert loot_distributor.claimableAssets(ambassador_wallet, 1) == alpha_token.address
    assert loot_distributor.claimableAssets(ambassador_wallet, 2) == bravo_token.address
    
    # Verify total claimable
    assert loot_distributor.totalClaimableLoot(alpha_token) == expected_alpha_fee
    assert loot_distributor.totalClaimableLoot(bravo_token) == expected_bravo_fee


def test_add_loot_accumulates_for_same_asset(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, setAssetConfig, createAmbassadorRevShare):
    """ Test that multiple calls for same asset accumulate claimable loot correctly """
    
    # Set up ambassador config
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=25_00,      # 25%
        _rewardsRatio=25_00,   # 25%
        _yieldRatio=25_00,     # 25%
    )
    
    setAssetConfig(alpha_token, _ambassadorRevShare=ambassadorRevShare)
    
    # Transfer larger amount to user wallet
    total_amount = 400 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, total_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor.address, total_amount, sender=user_wallet.address)
    
    # First fee
    first_fee = 100 * EIGHTEEN_DECIMALS
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        first_fee,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    expected_first = first_fee * 25_00 // 100_00  # 25 tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == expected_first
    
    # Second fee (different action type)
    second_fee = 200 * EIGHTEEN_DECIMALS
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        second_fee,
        ACTION_TYPE.REWARDS,
        sender=user_wallet.address
    )
    
    expected_second = second_fee * 25_00 // 100_00  # 50 tokens
    total_expected = expected_first + expected_second  # 75 tokens
    
    # Verify accumulation
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == total_expected
    assert loot_distributor.totalClaimableLoot(alpha_token) == total_expected
    
    # Asset should only be registered once
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 2  # Still just 1 asset registered
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 1


def test_add_loot_multiple_ambassadors(loot_distributor, hatchery, env, alpha_token, bravo_token, alpha_token_whale, bravo_token_whale, setAssetConfig, createAmbassadorRevShare):
    """ Test adding loot with multiple ambassadors to verify separate tracking """
    
    # Create two new ambassadors
    ambassador1_eoa = env.generate_address("ambassador1")
    ambassador2_eoa = env.generate_address("ambassador2")
    
    # Create ambassador wallets (no ambassador for them)
    ambassador1_addr = hatchery.createUserWallet(ambassador1_eoa, ZERO_ADDRESS, False, 1, sender=ambassador1_eoa)
    ambassador1_wallet = UserWallet.at(ambassador1_addr)
    
    ambassador2_addr = hatchery.createUserWallet(ambassador2_eoa, ZERO_ADDRESS, False, 1, sender=ambassador2_eoa)
    ambassador2_wallet = UserWallet.at(ambassador2_addr)
    
    # Create user wallets with different ambassadors
    user1_eoa = env.generate_address("user1")
    user2_eoa = env.generate_address("user2")
    
    user1_addr = hatchery.createUserWallet(user1_eoa, ambassador1_wallet, False, 1, sender=user1_eoa)
    user1_wallet = UserWallet.at(user1_addr)
    
    user2_addr = hatchery.createUserWallet(user2_eoa, ambassador2_wallet, False, 1, sender=user2_eoa)
    user2_wallet = UserWallet.at(user2_addr)
    
    # Set up different rev shares for different assets
    ambassadorRevShare1 = createAmbassadorRevShare(
        _swapRatio=30_00,      # 30% for ambassador1
        _rewardsRatio=30_00,
        _yieldRatio=30_00,
    )
    
    ambassadorRevShare2 = createAmbassadorRevShare(
        _swapRatio=50_00,      # 50% for ambassador2
        _rewardsRatio=50_00,
        _yieldRatio=50_00,
    )
    
    setAssetConfig(alpha_token, _ambassadorRevShare=ambassadorRevShare1)
    setAssetConfig(bravo_token, _ambassadorRevShare=ambassadorRevShare2)
    
    # Transfer tokens to users and approve
    fee_amount = 100 * EIGHTEEN_DECIMALS
    
    # User1 swaps alpha token
    alpha_token.transfer(user1_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor.address, fee_amount, sender=user1_wallet.address)
    
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=user1_wallet.address
    )
    
    # User2 swaps bravo token
    bravo_token.transfer(user2_wallet, fee_amount, sender=bravo_token_whale)
    bravo_token.approve(loot_distributor.address, fee_amount, sender=user2_wallet.address)
    
    loot_distributor.addLootFromSwapOrRewards(
        bravo_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=user2_wallet.address
    )
    
    # User1 also swaps bravo token (same asset, different ambassador)
    bravo_token.transfer(user1_wallet, fee_amount, sender=bravo_token_whale)
    bravo_token.approve(loot_distributor.address, fee_amount, sender=user1_wallet.address)
    
    loot_distributor.addLootFromSwapOrRewards(
        bravo_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=user1_wallet.address
    )
    
    # Verify ambassador1's claimable loot
    expected_alpha_fee = fee_amount * 30_00 // 100_00  # 30 tokens
    expected_bravo_fee = fee_amount * 50_00 // 100_00  # 50 tokens (50% of bravo)
    
    assert loot_distributor.claimableLoot(ambassador1_wallet, alpha_token) == expected_alpha_fee
    assert loot_distributor.claimableLoot(ambassador1_wallet, bravo_token) == expected_bravo_fee
    
    # Verify ambassador2's claimable loot
    assert loot_distributor.claimableLoot(ambassador2_wallet, alpha_token) == 0  # Didn't process alpha
    assert loot_distributor.claimableLoot(ambassador2_wallet, bravo_token) == expected_bravo_fee
    
    # Verify asset registration for ambassador1
    assert loot_distributor.numClaimableAssets(ambassador1_wallet) == 3  # alpha and bravo
    assert loot_distributor.indexOfClaimableAsset(ambassador1_wallet, alpha_token) == 1
    assert loot_distributor.indexOfClaimableAsset(ambassador1_wallet, bravo_token) == 2
    
    # Verify asset registration for ambassador2
    assert loot_distributor.numClaimableAssets(ambassador2_wallet) == 2  # only bravo
    assert loot_distributor.indexOfClaimableAsset(ambassador2_wallet, alpha_token) == 0  # Not registered
    assert loot_distributor.indexOfClaimableAsset(ambassador2_wallet, bravo_token) == 1
    
    # Verify total claimable amounts
    assert loot_distributor.totalClaimableLoot(alpha_token) == expected_alpha_fee  # Only ambassador1
    assert loot_distributor.totalClaimableLoot(bravo_token) == expected_bravo_fee * 2  # Both ambassadors


#######################
# Ambassadors Rewards #
#######################


def test_add_loot_from_yield_profit_with_fee_and_bonus(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test addLootFromYieldProfit with both performance fee and yield bonus """
    
    # Set up ambassador config with yield fee share and bonus ratio
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,
        _rewardsRatio=30_00,
        _yieldRatio=40_00,     # 40% of performance fees go to ambassador
    )
    
    # Create yield config with bonus ratio
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=10_00,  # 10% bonus on yield profit
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Seed loot distributor with underlying tokens for bonus payments
    seed_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(loot_distributor, seed_amount, sender=yield_underlying_token_whale)
    
    # Register vault token by making a deposit (creates price per share)
    deposit_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        deposit_amount,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Simulate yield profit
    performance_fee = 20 * EIGHTEEN_DECIMALS  # 20 vault tokens as performance fee
    total_yield_amount = 100 * EIGHTEEN_DECIMALS  # 100 vault tokens total yield
    
    # Transfer the performance fee to loot distributor (simulating it was already collected)
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Verify ambassador gets 40% of the performance fee
    expected_fee_share = performance_fee * 40_00 // 100_00  # 8 vault tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == expected_fee_share
    
    # Verify ambassador gets 10% bonus in underlying tokens
    # Price per share is 1.0, so 100 vault tokens = 100 underlying tokens
    expected_bonus = total_yield_amount * 10_00 // 100_00  # 10 underlying tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == expected_bonus
    
    # Verify total claimable
    assert loot_distributor.totalClaimableLoot(yield_vault_token) == expected_fee_share
    assert loot_distributor.totalClaimableLoot(yield_underlying_token) == expected_bonus
    
    # Verify asset registration
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 3  # vault and underlying tokens
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, yield_vault_token) == 1
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, yield_underlying_token) == 2


def test_add_loot_from_yield_profit_no_bonus_insufficient_balance(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test addLootFromYieldProfit when there's no underlying balance for bonus """
    
    # Set up ambassador config
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,
        _rewardsRatio=30_00,
        _yieldRatio=50_00,     # 50% of performance fees
    )
    
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=15_00,  # 15% bonus ratio
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Do NOT seed loot distributor with underlying tokens
    
    # Register vault token
    deposit_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        deposit_amount,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Simulate yield profit
    performance_fee = 10 * EIGHTEEN_DECIMALS
    total_yield_amount = 50 * EIGHTEEN_DECIMALS
    
    # Transfer fee to loot distributor
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Verify ambassador gets performance fee share
    expected_fee_share = performance_fee * 50_00 // 100_00  # 5 vault tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == expected_fee_share
    
    # Verify NO bonus was given (insufficient balance)
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == 0
    
    # Verify underlying token was not registered as claimable
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, yield_underlying_token) == 0


def test_add_loot_from_yield_profit_only_fee_no_bonus_config(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test addLootFromYieldProfit when bonus ratio is 0 """
    
    # Set up ambassador config with NO bonus ratio
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,
        _rewardsRatio=30_00,
        _yieldRatio=35_00,     # 35% of performance fees
    )
    
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=0,  # No bonus
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Seed distributor (even though no bonus will be paid)
    yield_underlying_token.transfer(loot_distributor, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Register vault token
    deposit_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        deposit_amount,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Simulate yield profit
    performance_fee = 30 * EIGHTEEN_DECIMALS
    total_yield_amount = 150 * EIGHTEEN_DECIMALS
    
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Verify only performance fee share
    expected_fee_share = performance_fee * 35_00 // 100_00  # 10.5 vault tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == expected_fee_share
    
    # Verify NO bonus (ratio is 0)
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == 0


def test_add_loot_from_yield_profit_zero_fee_with_bonus(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test addLootFromYieldProfit with zero performance fee but still gives bonus """
    
    # Set up ambassador config
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,
        _rewardsRatio=30_00,
        _yieldRatio=40_00,
    )
    
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=20_00,  # 20% bonus
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Seed distributor with underlying
    yield_underlying_token.transfer(loot_distributor, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Register vault token
    deposit_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        deposit_amount,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # No performance fee, but there was yield
    performance_fee = 0  # No fee charged
    total_yield_amount = 80 * EIGHTEEN_DECIMALS  # 80 vault tokens yield
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Verify no fee share (fee was 0)
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == 0
    
    # Verify bonus is still given
    expected_bonus = total_yield_amount * 20_00 // 100_00  # 16 underlying tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == expected_bonus


def test_add_loot_from_yield_profit_with_price_per_share_change(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test addLootFromYieldProfit when price per share has doubled """
    
    # Set up ambassador config
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,
        _rewardsRatio=30_00,
        _yieldRatio=50_00,  # 50% for cleaner numbers
    )
    
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=10_00,  # 10% bonus for easier calculation
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Seed distributor
    yield_underlying_token.transfer(loot_distributor, 2000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Initial deposit
    deposit_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        deposit_amount,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Double the vault value by transferring more underlying (simulates 100% yield)
    yield_underlying_token.transfer(yield_vault_token, 1_000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Now price per share should be 2.0
    price_per_share = mock_yield_lego.getPricePerShare(yield_vault_token, yield_vault_token.decimals())
    assert price_per_share == 2 * EIGHTEEN_DECIMALS  # 2.0
    
    # Simulate yield profit with round numbers
    performance_fee = 20 * EIGHTEEN_DECIMALS  # 20 vault tokens
    total_yield_amount = 100 * EIGHTEEN_DECIMALS  # 100 vault tokens
    
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Verify fee share
    expected_fee_share = performance_fee * 50_00 // 100_00  # 10 vault tokens (50% of 20)
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == expected_fee_share
    
    # Verify bonus calculation uses price per share
    # 100 vault tokens * 2.0 price per share = 200 underlying tokens worth
    # 10% of 200 = 20 underlying tokens
    expected_bonus = (total_yield_amount * price_per_share // EIGHTEEN_DECIMALS) * 10_00 // 100_00
    assert expected_bonus == 20 * EIGHTEEN_DECIMALS  # Clean 20 tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == expected_bonus


