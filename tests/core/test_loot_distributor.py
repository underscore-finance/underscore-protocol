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


##############
# Claim Loot #
##############


@pytest.fixture(scope="module")
def setupClaimableLoot(setAssetConfig, createAmbassadorRevShare, loot_distributor, user_wallet, alpha_token, alpha_token_whale):
    def setupClaimableLoot(
            amount,
            token = alpha_token,
            token_whale = alpha_token_whale,
            rev_share_ratio=50_00,
        ):
        
        # Set up ambassador config
        ambassadorRevShare = createAmbassadorRevShare(
            _swapRatio=rev_share_ratio,
            _rewardsRatio=rev_share_ratio,
            _yieldRatio=rev_share_ratio,
        )
        
        setAssetConfig(
            token,
            _ambassadorRevShare=ambassadorRevShare,
        )
        
        # Transfer tokens to user wallet and approve
        token.transfer(user_wallet, amount, sender=token_whale)
        token.approve(loot_distributor.address, amount, sender=user_wallet.address)
        
        # Add loot from swap
        loot_distributor.addLootFromSwapOrRewards(
            token,
            amount,
            ACTION_TYPE.SWAP,
            sender=user_wallet.address
        )
        
        # Return the expected claimable amount
        return amount * rev_share_ratio // 100_00
    
    return setupClaimableLoot


def test_claim_loot_single_asset_full_balance(loot_distributor, ambassador_wallet, alpha_token, setupClaimableLoot, alice):
    """ Test claiming loot for single asset when full balance is available """
    
    # Setup claimable loot - 100 tokens with 50% rev share = 50 claimable
    fee_amount = 100 * EIGHTEEN_DECIMALS
    expected_claimable = setupClaimableLoot(fee_amount)
    
    # Verify setup
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == expected_claimable
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 2  # Starts at 1
    
    # Record balances before claim
    distributor_balance_before = alpha_token.balanceOf(loot_distributor)
    ambassador_balance_before = alpha_token.balanceOf(ambassador_wallet)
    
    # Claim loot (ambassador claiming their own loot)
    assets_claimed = loot_distributor.claimLoot(ambassador_wallet, sender=alice)
    
    # Verify claim results
    assert assets_claimed == 1  # 1 asset was claimed
    assert alpha_token.balanceOf(ambassador_wallet) == ambassador_balance_before + expected_claimable
    assert alpha_token.balanceOf(loot_distributor) == distributor_balance_before - expected_claimable
    
    # Verify loot was cleared
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == 0
    assert loot_distributor.totalClaimableLoot(alpha_token) == 0
    
    # Verify asset was deregistered
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 1  # Back to 1 (not using 0 index)
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 0


def test_claim_loot_multiple_assets(loot_distributor, ambassador_wallet, alpha_token, bravo_token, bravo_token_whale, setupClaimableLoot, alice):
    """ Test claiming loot for multiple assets """
    
    # Setup claimable loot for two assets
    expected_alpha = setupClaimableLoot(200 * EIGHTEEN_DECIMALS, rev_share_ratio=40_00)  # 40% = 80 tokens
    expected_bravo = setupClaimableLoot(150 * EIGHTEEN_DECIMALS, token=bravo_token, token_whale=bravo_token_whale, rev_share_ratio=60_00)  # 60% = 90 tokens
    
    # Verify setup
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == expected_alpha
    assert loot_distributor.claimableLoot(ambassador_wallet, bravo_token) == expected_bravo
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 3  # 1 + 2 assets
    
    # Claim all loot
    assets_claimed = loot_distributor.claimLoot(ambassador_wallet, sender=alice)
    
    # Verify both assets were claimed
    assert assets_claimed == 2
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == 0
    assert loot_distributor.claimableLoot(ambassador_wallet, bravo_token) == 0
    
    # Verify both assets were deregistered
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 1
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 0
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, bravo_token) == 0


def test_claim_loot_partial_balance_available(loot_distributor, ambassador_wallet, alpha_token, alpha_token_whale, setupClaimableLoot, alice):
    """ Test claiming loot when only partial balance is available in contract """
    
    # Setup claimable loot
    expected_claimable = setupClaimableLoot(100 * EIGHTEEN_DECIMALS)  # 50% = 50 tokens
    
    # Remove some tokens from loot distributor to simulate partial balance
    current_balance = alpha_token.balanceOf(loot_distributor)
    partial_amount = expected_claimable * 60 // 100  # Only 60% available
    alpha_token.transfer(alpha_token_whale, current_balance - partial_amount, sender=loot_distributor.address)
    
    # Verify reduced balance
    assert alpha_token.balanceOf(loot_distributor) == partial_amount
    
    # Claim loot
    assets_claimed = loot_distributor.claimLoot(ambassador_wallet, sender=alice)
    
    # Verify partial claim
    assert assets_claimed == 1
    assert alpha_token.balanceOf(ambassador_wallet) == partial_amount
    
    # Verify remaining claimable amount
    remaining_claimable = expected_claimable - partial_amount
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == remaining_claimable
    assert loot_distributor.totalClaimableLoot(alpha_token) == remaining_claimable
    
    # Asset should NOT be deregistered (still has claimable balance)
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 1


def test_claim_loot_zero_balance_available(loot_distributor, ambassador_wallet, alpha_token, alpha_token_whale, setupClaimableLoot, alice):
    """ Test claiming loot when no balance is available in contract """
    
    # Setup claimable loot
    expected_claimable = setupClaimableLoot(100 * EIGHTEEN_DECIMALS)  # 50% = 50 tokens
    
    # Remove all tokens from loot distributor
    current_balance = alpha_token.balanceOf(loot_distributor)
    alpha_token.transfer(alpha_token_whale, current_balance, sender=loot_distributor.address)
    
    # Verify zero balance
    assert alpha_token.balanceOf(loot_distributor) == 0
    
    # Claim loot - should fail because no assets can be claimed
    with boa.reverts("no assets claimed"):
        loot_distributor.claimLoot(ambassador_wallet, sender=alice)
    
    # Claimable amount remains unchanged
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == expected_claimable
    
    # Asset remains registered
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 1


def test_claim_loot_permission_check(loot_distributor, ambassador_wallet, setupClaimableLoot, alice, charlie):
    """ Test permission checks for claiming loot """
    
    # Setup claimable loot for ambassador_wallet (alice is owner)
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS)
    
    # Charlie (not owner) cannot claim
    with boa.reverts("no perms"):
        loot_distributor.claimLoot(ambassador_wallet, sender=charlie)
    
    # Alice (owner) can claim
    assets_claimed = loot_distributor.claimLoot(ambassador_wallet, sender=alice)
    assert assets_claimed == 1


def test_claim_loot_deregistration_with_multiple_assets(loot_distributor, ambassador_wallet, alpha_token, bravo_token, charlie_token, bravo_token_whale, charlie_token_whale, setupClaimableLoot, alice):
    """ Test asset deregistration logic when claiming multiple assets with different balances """
    
    # Setup three assets
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS)  # Alpha with default 50%
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS, token=bravo_token, token_whale=bravo_token_whale)  # Bravo with 50%
    setupClaimableLoot(100 * (10**6), token=charlie_token, token_whale=charlie_token_whale)  # Charlie 6 decimals with 50%
    
    # Verify the claimable amounts before removing tokens
    alpha_claimable = loot_distributor.claimableLoot(ambassador_wallet, alpha_token)
    bravo_claimable = loot_distributor.claimableLoot(ambassador_wallet, bravo_token)
    charlie_claimable = loot_distributor.claimableLoot(ambassador_wallet, charlie_token)
    
    # Remove some bravo tokens to create partial balance (keep only 40% of what's claimable)
    bravo_balance = bravo_token.balanceOf(loot_distributor)
    bravo_to_keep = bravo_claimable * 40 // 100
    bravo_token.transfer(bravo_token_whale, bravo_balance - bravo_to_keep, sender=loot_distributor.address)
    
    # Verify bravo has partial balance
    assert bravo_token.balanceOf(loot_distributor) == bravo_to_keep
    assert bravo_to_keep < bravo_claimable  # Ensure it's actually partial
    
    # Verify initial state - 3 assets registered
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 4  # 1 + 3 assets
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 1
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, bravo_token) == 2
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, charlie_token) == 3
    
    # Claim loot
    assets_claimed = loot_distributor.claimLoot(ambassador_wallet, sender=alice)
    
    # Verify claims
    assert assets_claimed == 3  # All 3 assets had transfers
    
    # Check remaining claimable amounts
    alpha_remaining = loot_distributor.claimableLoot(ambassador_wallet, alpha_token)
    bravo_remaining = loot_distributor.claimableLoot(ambassador_wallet, bravo_token)
    charlie_remaining = loot_distributor.claimableLoot(ambassador_wallet, charlie_token)
    
    # Alpha and Charlie should have 0 remaining (fully claimed)
    assert alpha_remaining == 0
    assert charlie_remaining == 0
    
    # Bravo should have remaining balance (partial claim)
    assert bravo_remaining == bravo_claimable - bravo_to_keep
    assert bravo_remaining > 0
    
    # Alpha and Charlie should be deregistered (fully claimed)
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 0
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, charlie_token) == 0
    
    # Bravo should remain registered (partial claim)
    # After deregistration of alpha and charlie, bravo should be at index 1
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, bravo_token) == 1
    
    # Verify final state - should have 2 (1 base + 1 remaining asset)
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 2


def test_claim_loot_no_claimable_assets(loot_distributor, ambassador_wallet, alice):
    """ Test claiming when there are no claimable assets """
    
    # Verify no assets registered
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 0
    
    # Claim should fail because there are no claimable assets
    with boa.reverts("no claimable assets"):
        loot_distributor.claimLoot(ambassador_wallet, sender=alice)


# get claimable assets


def test_get_total_claimable_assets_no_assets(loot_distributor, ambassador_wallet):
    """ Test getTotalClaimableAssets when user has no claimable assets """
    
    # Should return 0 when no assets are registered
    assert loot_distributor.getTotalClaimableAssets(ambassador_wallet) == 0


def test_get_total_claimable_assets_single_asset(loot_distributor, ambassador_wallet, setupClaimableLoot):
    """ Test getTotalClaimableAssets with a single claimable asset """
    
    # Setup one claimable asset
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS)
    
    # Should return 1 asset
    assert loot_distributor.getTotalClaimableAssets(ambassador_wallet) == 1


def test_get_total_claimable_assets_multiple_assets(loot_distributor, ambassador_wallet, bravo_token, charlie_token, bravo_token_whale, charlie_token_whale, setupClaimableLoot):
    """ Test getTotalClaimableAssets with multiple claimable assets """
    
    # Setup three different assets
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS)  # Alpha token
    setupClaimableLoot(200 * EIGHTEEN_DECIMALS, token=bravo_token, token_whale=bravo_token_whale)
    setupClaimableLoot(50 * (10**6), token=charlie_token, token_whale=charlie_token_whale)  # 6 decimals
    
    # Should return 3 assets
    assert loot_distributor.getTotalClaimableAssets(ambassador_wallet) == 3


def test_get_total_claimable_assets_after_claiming(loot_distributor, ambassador_wallet, alpha_token, bravo_token, bravo_token_whale, setupClaimableLoot, alice):
    """ Test getTotalClaimableAssets after claiming and deregistering some assets """
    
    # Setup two assets
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS)  # Alpha - will be fully claimed
    setupClaimableLoot(200 * EIGHTEEN_DECIMALS, token=bravo_token, token_whale=bravo_token_whale)  # Bravo
    
    # Verify initial state
    assert loot_distributor.getTotalClaimableAssets(ambassador_wallet) == 2
    
    # Remove bravo tokens to create partial balance (keep only 30%)
    bravo_claimable = loot_distributor.claimableLoot(ambassador_wallet, bravo_token)
    bravo_balance = bravo_token.balanceOf(loot_distributor)
    bravo_to_keep = bravo_claimable * 30 // 100
    bravo_token.transfer(bravo_token_whale, bravo_balance - bravo_to_keep, sender=loot_distributor.address)
    
    # Verify getTotalClaimableAssets before claiming
    # Since bravo still has some balance, it should still count
    assert loot_distributor.getTotalClaimableAssets(ambassador_wallet) == 2
    
    # Claim loot
    loot_distributor.claimLoot(ambassador_wallet, sender=alice)
    
    # After claim, bravo should have no balance left in distributor
    # because we only kept 30% of claimable amount, which was transferred during claim
    bravo_balance_in_distributor = bravo_token.balanceOf(loot_distributor)
    assert bravo_balance_in_distributor == 0
    
    # But bravo still has claimable amount tracked
    bravo_claimable_remaining = loot_distributor.claimableLoot(ambassador_wallet, bravo_token)
    assert bravo_claimable_remaining == bravo_claimable * 70 // 100  # 70% remains claimable
    
    # getTotalClaimableAssets returns 0 because there's no balance available
    # even though there's still claimable amount tracked
    assert loot_distributor.getTotalClaimableAssets(ambassador_wallet) == 0


##################
# Deposit Points #
##################


def test_update_deposit_points_basic(loot_distributor, user_wallet, ledger, switchboard_alpha):
    """ Test basic updateDepositPoints without value changes """
    
    # Set initial USD value with no points
    initial_block = boa.env.evm.patch.block_number
    user_points = (
        1000 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        initial_block  # lastUpdate
    )
    global_points = (
        5000 * EIGHTEEN_DECIMALS,  # usdValue (total across all users)
        0,  # depositPoints
        initial_block  # lastUpdate
    )
    ledger.setUserAndGlobalPoints(user_wallet.address, user_points, global_points, sender=loot_distributor.address)
    
    # Advance 100 blocks
    boa.env.time_travel(blocks=100)
    
    # Update points without value change
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Verify points accumulated and ledger storage updated
    updated_user, updated_global = ledger.getUserAndGlobalPoints(user_wallet.address)
    
    # User should have: (1000 * 10^18 * 100 blocks) / 10^18 = 100000 points
    assert updated_user.depositPoints == 100000
    assert updated_user.usdValue == 1000 * EIGHTEEN_DECIMALS  # Unchanged
    assert updated_user.lastUpdate == initial_block + 100
    
    # Global should have: (5000 * 10^18 * 100 blocks) / 10^18 = 500000 points
    assert updated_global.depositPoints == 500000
    assert updated_global.usdValue == 5000 * EIGHTEEN_DECIMALS  # Unchanged
    assert updated_global.lastUpdate == initial_block + 100


def test_update_deposit_points_with_new_value(loot_distributor, user_wallet, ledger):
    """ Test updateDepositPointsWithNewValue with USD value changes """
    
    # Set initial state
    initial_block = boa.env.evm.patch.block_number
    user_points = (
        500 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        initial_block
    )
    global_points = (
        2000 * EIGHTEEN_DECIMALS,  # usdValue
        0,  # depositPoints
        initial_block
    )
    ledger.setUserAndGlobalPoints(user_wallet.address, user_points, global_points, sender=loot_distributor.address)
    
    # Advance blocks using time_travel
    boa.env.time_travel(blocks=50)
    
    # Update with new value (user wallet calling directly)
    new_value = 800 * EIGHTEEN_DECIMALS
    loot_distributor.updateDepositPointsWithNewValue(
        user_wallet.address, 
        new_value,
        sender=user_wallet.address
    )
    
    # Check updated values - verify ledger storage
    updated_user, updated_global = ledger.getUserAndGlobalPoints(user_wallet.address)
    
    # User points: (500 * 10^18 * 50) / 10^18 = 25000
    assert updated_user.depositPoints == 25000
    assert updated_user.usdValue == new_value
    assert updated_user.lastUpdate == initial_block + 50
    
    # Global points: (2000 * 10^18 * 50) / 10^18 = 100000
    assert updated_global.depositPoints == 100000
    # Global value: 2000 - 500 + 800 = 2300
    assert updated_global.usdValue == 2300 * EIGHTEEN_DECIMALS
    assert updated_global.lastUpdate == initial_block + 50


def test_update_deposit_points_with_wallet_config(loot_distributor, user_wallet, user_wallet_config, ledger):
    """ Test updateDepositPointsWithNewValue called by wallet config """
    
    # Set initial state
    initial_block = boa.env.evm.patch.block_number
    user_points = (100 * EIGHTEEN_DECIMALS, 0, initial_block)
    global_points = (1000 * EIGHTEEN_DECIMALS, 0, initial_block)
    ledger.setUserAndGlobalPoints(user_wallet.address, user_points, global_points, sender=loot_distributor.address)
    
    # Advance blocks
    boa.env.time_travel(blocks=10)
    
    # Update via wallet config (valid caller due to isValidWalletConfig check)
    new_value = 200 * EIGHTEEN_DECIMALS
    loot_distributor.updateDepositPointsWithNewValue(
        user_wallet.address,
        new_value,
        sender=user_wallet_config.address
    )
    
    # Verify update succeeded
    updated_user, _ = ledger.getUserAndGlobalPoints(user_wallet.address)
    assert updated_user.depositPoints == 1000  # (100 * 10)
    assert updated_user.usdValue == new_value


def test_update_deposit_points_invalid_caller(loot_distributor, user_wallet, charlie):
    """ Test updateDepositPointsWithNewValue rejects invalid callers """
    
    # Charlie (not wallet owner or config) tries to update
    with boa.reverts("invalid config"):
        loot_distributor.updateDepositPointsWithNewValue(
            user_wallet.address,
            100 * EIGHTEEN_DECIMALS,
            sender=charlie
        )


def test_get_latest_deposit_points_view(loot_distributor):
    """ Test getLatestDepositPoints view function """

    boa.env.time_travel(blocks=60)
    current_block = boa.env.evm.patch.block_number
    
    # Test with valid values
    usd_value = 1000 * EIGHTEEN_DECIMALS
    last_update = current_block - 50
    
    # Calculate expected points: (1000 * 10^18 * 50) / 10^18 = 50000
    points = loot_distributor.getLatestDepositPoints(usd_value, last_update)
    assert points == 50000
    
    # Test with zero USD value
    points = loot_distributor.getLatestDepositPoints(0, last_update)
    assert points == 0
    
    # Test with zero last update
    points = loot_distributor.getLatestDepositPoints(usd_value, 0)
    assert points == 0
    
    # Test when last update is current block (no time elapsed)
    points = loot_distributor.getLatestDepositPoints(usd_value, current_block)
    assert points == 0
    
    # Test when last update is in future (should return 0)
    points = loot_distributor.getLatestDepositPoints(usd_value, current_block + 100)
    assert points == 0


def test_get_latest_deposit_points_precision(loot_distributor):
    """ Test getLatestDepositPoints maintains precision with small values """
    
    # Ensure we have enough blocks to work with
    boa.env.time_travel(blocks=EIGHTEEN_DECIMALS + 100)
    current_block = boa.env.evm.patch.block_number
    
    # Test with 1 wei value over many blocks
    points = loot_distributor.getLatestDepositPoints(1, current_block - EIGHTEEN_DECIMALS)
    assert points == 1  # (1 * 10^18) / 10^18 = 1
    
    # Test with value just below 1 full point
    blocks_elapsed = EIGHTEEN_DECIMALS - 1
    points = loot_distributor.getLatestDepositPoints(1, current_block - blocks_elapsed)
    assert points == 0  # Should truncate to 0


def test_is_valid_wallet_config_view(loot_distributor, user_wallet, user_wallet_config, mock_rando_contract):
    """ Test isValidWalletConfig view function """
    
    # Valid case: wallet config calling for its wallet
    assert loot_distributor.isValidWalletConfig(user_wallet, user_wallet_config) == True
    
    # Invalid case: random contract claiming to be config
    assert loot_distributor.isValidWalletConfig(user_wallet, mock_rando_contract) == False
    
    # Invalid case: config for different wallet
    assert loot_distributor.isValidWalletConfig(mock_rando_contract, user_wallet_config) == False
    
    # Invalid case: zero addresses
    assert loot_distributor.isValidWalletConfig(ZERO_ADDRESS, user_wallet_config) == False
    assert loot_distributor.isValidWalletConfig(user_wallet, ZERO_ADDRESS) == False


def test_deposit_points_accumulation_over_multiple_periods(loot_distributor, user_wallet, ledger, switchboard_alpha):
    """ Test deposit points accumulation over multiple time periods """
    
    # Set initial state
    initial_block = boa.env.evm.patch.block_number
    user_points = (1000 * EIGHTEEN_DECIMALS, 0, initial_block)
    global_points = (2000 * EIGHTEEN_DECIMALS, 0, initial_block)
    ledger.setUserAndGlobalPoints(user_wallet.address, user_points, global_points, sender=loot_distributor.address)
    
    # First update after 10 blocks
    boa.env.time_travel(blocks=10)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    user1, global1 = ledger.getUserAndGlobalPoints(user_wallet.address)
    assert user1.depositPoints == 10000  # (1000 * 10)
    assert global1.depositPoints == 20000  # (2000 * 10)
    
    # Second update after another 20 blocks
    boa.env.time_travel(blocks=20)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    user2, global2 = ledger.getUserAndGlobalPoints(user_wallet.address)
    assert user2.depositPoints == 30000  # 10000 + (1000 * 20)
    assert global2.depositPoints == 60000  # 20000 + (2000 * 20)


def test_deposit_points_idempotency_same_block(loot_distributor, user_wallet, ledger, switchboard_alpha):
    """ Test multiple updates in same block don't accumulate extra points """
    
    # Set initial state with existing points
    initial_block = boa.env.evm.patch.block_number
    user_points = (1000 * EIGHTEEN_DECIMALS, 10000, initial_block)
    global_points = (2000 * EIGHTEEN_DECIMALS, 20000, initial_block)
    ledger.setUserAndGlobalPoints(user_wallet.address, user_points, global_points, sender=loot_distributor.address)
    
    # First update
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Second update in same block
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Points should not change on second update
    updated_user, updated_global = ledger.getUserAndGlobalPoints(user_wallet.address)
    assert updated_user.depositPoints == 10000  # No change
    assert updated_global.depositPoints == 20000  # No change
    assert updated_user.lastUpdate == initial_block  # Same block