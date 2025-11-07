import pytest
import boa
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS, ACTION_TYPE
from contracts.core.userWallet import UserWallet, UserWalletConfig
from conf_utils import filter_logs


######################
# Loot Distro Config #
######################


def test_get_loot_distro_config_with_asset_config(loot_distributor, ambassador_wallet, user_wallet, alpha_token, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test getLootDistroConfig when asset config is set in mission control """
    
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
    config = loot_distributor.getLootDistroConfig(user_wallet.address, alpha_token.address)
    
    # Verify the config
    assert config.ambassador == ambassador_wallet.address
    assert config.ambassadorRevShare.swapRatio == 50_00
    assert config.ambassadorRevShare.rewardsRatio == 45_00
    assert config.ambassadorRevShare.yieldRatio == 40_00
    assert config.ambassadorBonusRatio == 10_00
    assert config.underlyingAsset == alpha_token.address
    assert config.decimals == alpha_token.decimals()  # Should get decimals from the token


def test_get_loot_distro_config_no_asset_config(loot_distributor, ambassador_wallet, user_wallet, alpha_token, setUserWalletConfig, createAmbassadorRevShare):
    """ Test getLootDistroConfig when no asset config is set (defaults to global config) """
    
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
    config = loot_distributor.getLootDistroConfig(user_wallet.address, alpha_token.address)
    
    # Verify the config uses global defaults
    assert config.ambassador == ambassador_wallet.address
    assert config.ambassadorRevShare.swapRatio == 30_00
    assert config.ambassadorRevShare.rewardsRatio == 25_00
    assert config.ambassadorRevShare.yieldRatio == 20_00
    assert config.ambassadorBonusRatio == 5_00  # Global bonus ratio
    assert config.underlyingAsset == ZERO_ADDRESS  # No underlying asset in global config
    assert config.decimals == alpha_token.decimals()  # Should get decimals from the token


def test_get_loot_distro_config_with_vault_registration(loot_distributor, ambassador_wallet, user_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, ledger, setUserWalletConfig, createAmbassadorRevShare):
    """ Test getLootDistroConfig when there is a registered vault token (with underlying asset, decimals info) """
    
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
    config = loot_distributor.getLootDistroConfig(user_wallet.address, yield_vault_token.address)
    
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


def test_add_loot_from_swap_fees(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, governance, setAssetConfig, createAmbassadorRevShare):
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

    # Check initial governance balance
    initial_gov_balance = alpha_token.balanceOf(governance.address)

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

    # Verify governance receives leftover 70% of the fee
    expected_gov_fee = fee_amount * 70_00 // 100_00  # 70 tokens
    assert alpha_token.balanceOf(governance.address) == initial_gov_balance + expected_gov_fee

    # Verify asset registration
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 2  # Starts at 1, not 0
    assert loot_distributor.claimableAssets(ambassador_wallet, 1) == alpha_token.address
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 1


def test_add_loot_from_rewards_fees(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, governance, setAssetConfig, createAmbassadorRevShare):
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

    # Check initial governance balance
    initial_gov_balance = alpha_token.balanceOf(governance.address)

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

    # Verify governance receives leftover 50% of the fee
    expected_gov_fee = fee_amount * 50_00 // 100_00  # 100 tokens
    assert alpha_token.balanceOf(governance.address) == initial_gov_balance + expected_gov_fee


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


def test_add_loot_from_yield_profit_with_fee_and_bonus(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, governance, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
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

    # Check initial governance balance
    initial_gov_balance = yield_vault_token.balanceOf(governance.address)

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

    # Verify governance receives leftover 60% of the performance fee
    expected_gov_fee = performance_fee * 60_00 // 100_00  # 12 vault tokens
    assert yield_vault_token.balanceOf(governance.address) == initial_gov_balance + expected_gov_fee

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


def test_add_loot_from_yield_profit_eligible_asset_gets_bonus(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test that assets eligible for yield bonus receive bonuses """
    
    # Set up ambassador config with yield fee share and bonus ratio
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,
        _rewardsRatio=30_00,
        _yieldRatio=40_00,     # 40% of performance fees go to ambassador
    )
    
    # Create yield config with bonus ratios
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=10_00,  # 10% bonus ratio
        _bonusRatio=20_00,            # 20% user bonus ratio
    )
    
    setAssetConfig(
        yield_vault_token,
        _legoId=1,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Ensure the asset is eligible for yield bonus (default is True in MockYieldLego)
    assert mock_yield_lego.isEligibleForYieldBonus(yield_vault_token) == True
    
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
    
    # Record initial balances
    initial_underlying_balance = yield_underlying_token.balanceOf(loot_distributor)
    
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
    
    # Verify bonuses WERE given in underlying tokens
    # User gets 20% of the total yield in underlying tokens
    expected_user_bonus = total_yield_amount * 20_00 // 100_00  # 20 underlying tokens
    assert loot_distributor.claimableLoot(user_wallet, yield_underlying_token) == expected_user_bonus
    
    # Ambassador gets 10% of the total yield in underlying tokens
    expected_ambassador_bonus = total_yield_amount * 10_00 // 100_00  # 10 underlying tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == expected_ambassador_bonus
    
    # Verify underlying balance stays the same (bonuses are allocated but not transferred yet)
    total_bonuses = expected_user_bonus + expected_ambassador_bonus
    assert yield_underlying_token.balanceOf(loot_distributor) == initial_underlying_balance
    
    # Verify total claimable
    assert loot_distributor.totalClaimableLoot(yield_vault_token) == expected_fee_share
    assert loot_distributor.totalClaimableLoot(yield_underlying_token) == total_bonuses
    
    # Verify both tokens are registered
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 3  # 1 base + vault token + underlying token
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, yield_vault_token) == 1
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, yield_underlying_token) == 2


def test_add_loot_from_yield_profit_non_eligible_asset_no_bonus(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test that assets not eligible for yield bonus do not receive bonuses """
    
    # Set up ambassador config with yield fee share and bonus ratio
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,
        _rewardsRatio=30_00,
        _yieldRatio=40_00,     # 40% of performance fees go to ambassador
    )
    
    # Create yield config with bonus ratios
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=10_00,  # 10% bonus ratio (should be ignored)
        _bonusRatio=20_00,            # 20% user bonus ratio (should be ignored)
    )
    
    setAssetConfig(
        yield_vault_token,
        _legoId=1,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Make the asset NOT eligible for yield bonus
    mock_yield_lego.setIsEligibleForYieldBonus(False)
    assert mock_yield_lego.isEligibleForYieldBonus(yield_vault_token) == False
    
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
    
    # Record initial balances
    initial_underlying_balance = yield_underlying_token.balanceOf(loot_distributor)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Verify ambassador gets 40% of the performance fee (fees still work)
    expected_fee_share = performance_fee * 40_00 // 100_00  # 8 vault tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == expected_fee_share
    
    # Verify NO bonus was given in underlying tokens (this is the key test)
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == 0
    assert loot_distributor.claimableLoot(user_wallet, yield_underlying_token) == 0
    
    # Verify underlying balance didn't change (no bonuses distributed)
    assert yield_underlying_token.balanceOf(loot_distributor) == initial_underlying_balance
    
    # Verify total claimable
    assert loot_distributor.totalClaimableLoot(yield_vault_token) == expected_fee_share
    assert loot_distributor.totalClaimableLoot(yield_underlying_token) == 0  # No bonuses
    
    # Verify only vault token is registered (no underlying token registration)
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 2  # 1 base + vault token only
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, yield_vault_token) == 1
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, yield_underlying_token) == 0  # Not registered


def test_add_loot_from_yield_profit_alt_bonus_asset_config(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, undy_token, whale, mock_yield_lego, mock_ripe, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test yield bonus with alternative bonus asset (UNDY token) configured at asset level """
    
    # Seed loot distributor with UNDY tokens for bonus payments
    undy_seed_amount = 5000 * EIGHTEEN_DECIMALS
    undy_token.transfer(loot_distributor, undy_seed_amount, sender=whale)
    
    # Set up prices
    undy_price = 5 * EIGHTEEN_DECIMALS  # $5 per UNDY
    underlying_price = 10 * EIGHTEEN_DECIMALS  # $10 per underlying token
    mock_ripe.setPrice(undy_token, undy_price)
    mock_ripe.setPrice(yield_underlying_token, underlying_price)
    
    # Set up ambassador config with yield fee share and bonus ratios
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,
        _rewardsRatio=30_00,
        _yieldRatio=50_00,     # 50% of performance fees go to ambassador
    )
    
    # Create yield config with UNDY as alt bonus asset
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=10_00,  # 10% ambassador bonus
        _bonusRatio=20_00,            # 20% user bonus
        _altBonusAsset=undy_token.address,  # Use UNDY as bonus asset
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
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
    
    # Transfer the performance fee to loot distributor
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Verify ambassador gets 50% of the performance fee in vault tokens
    expected_fee_share = performance_fee * 50_00 // 100_00  # 10 vault tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == expected_fee_share
    
    # Calculate expected UNDY bonuses
    # Total yield value = 100 vault tokens * 1.0 price per share * $10 underlying = $1000
    # User bonus: 20% of $1000 = $200 worth of UNDY = $200 / $5 = 40 UNDY
    # Ambassador bonus: 10% of $1000 = $100 worth of UNDY = $100 / $5 = 20 UNDY
    expected_user_bonus_undy = 40 * EIGHTEEN_DECIMALS
    expected_ambassador_bonus_undy = 20 * EIGHTEEN_DECIMALS
    
    assert loot_distributor.claimableLoot(user_wallet, undy_token) == expected_user_bonus_undy
    assert loot_distributor.claimableLoot(ambassador_wallet, undy_token) == expected_ambassador_bonus_undy
    
    # Verify total claimable
    assert loot_distributor.totalClaimableLoot(yield_vault_token) == expected_fee_share
    assert loot_distributor.totalClaimableLoot(undy_token) == expected_user_bonus_undy + expected_ambassador_bonus_undy
    
    # Verify UNDY balance hasn't changed yet (only allocated, not transferred)
    assert undy_token.balanceOf(loot_distributor) == undy_seed_amount


def test_add_loot_from_yield_profit_alt_bonus_asset_global_config(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, undy_token, whale, mock_yield_lego, mock_ripe, setUserWalletConfig, createAmbassadorRevShare):
    """ Test yield bonus with alternative bonus asset configured at global level """
    
    # Seed loot distributor with UNDY tokens
    undy_seed_amount = 3000 * EIGHTEEN_DECIMALS
    undy_token.transfer(loot_distributor, undy_seed_amount, sender=whale)
    
    # Set up prices
    undy_price = 2 * EIGHTEEN_DECIMALS  # $2 per UNDY
    underlying_price = 20 * EIGHTEEN_DECIMALS  # $20 per underlying token
    mock_ripe.setPrice(undy_token, undy_price)
    mock_ripe.setPrice(yield_underlying_token, underlying_price)
    
    # Create global ambassador rev share settings
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,
        _rewardsRatio=30_00,
        _yieldRatio=40_00,
    )
    
    # Set global config with UNDY as default alt bonus asset
    setUserWalletConfig(
        _ambassadorRevShare=ambassadorRevShare,
        _defaultYieldAmbassadorBonusRatio=5_00,  # 5% global ambassador bonus
        _defaultYieldBonusRatio=15_00,           # 15% global user bonus
        _defaultYieldAltBonusAsset=undy_token.address,  # UNDY as default bonus asset
    )
    
    # Don't set any asset config - will use global config entirely
    
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
    
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Verify fees
    expected_fee_share = performance_fee * 40_00 // 100_00  # 4 vault tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == expected_fee_share
    
    # Calculate expected UNDY bonuses using global ratios
    # Total yield value = 50 vault tokens * 1.0 price per share * $20 underlying = $1000
    # User bonus: 15% of $1000 = $150 worth of UNDY = $150 / $2 = 75 UNDY
    # Ambassador bonus: 5% of $1000 = $50 worth of UNDY = $50 / $2 = 25 UNDY
    expected_user_bonus_undy = 75 * EIGHTEEN_DECIMALS
    expected_ambassador_bonus_undy = 25 * EIGHTEEN_DECIMALS
    
    assert loot_distributor.claimableLoot(user_wallet, undy_token) == expected_user_bonus_undy
    assert loot_distributor.claimableLoot(ambassador_wallet, undy_token) == expected_ambassador_bonus_undy


def test_add_loot_from_yield_profit_alt_bonus_asset_no_ambassador(loot_distributor, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, undy_token, whale, mock_yield_lego, mock_ripe, setAssetConfig, createAssetYieldConfig, ledger, hatchery, charlie):
    """ Test yield bonus with alt bonus asset when there's no ambassador - user still gets bonus """
    
    # Create a new user wallet without ambassador (explicitly pass ZERO_ADDRESS as ambassador)
    wallet_addr = hatchery.createUserWallet(charlie, ZERO_ADDRESS, True, 1, sender=charlie)
    user_wallet_no_ambassador = UserWallet.at(wallet_addr)
   
    # Verify no ambassador is set
    assert ledger.ambassadors(user_wallet_no_ambassador) == ZERO_ADDRESS
    
    # Seed loot distributor with UNDY tokens
    undy_seed_amount = 2000 * EIGHTEEN_DECIMALS
    undy_token.transfer(loot_distributor, undy_seed_amount, sender=whale)
    
    # Set up prices
    mock_ripe.setPrice(undy_token, 4 * EIGHTEEN_DECIMALS)  # $4 per UNDY
    mock_ripe.setPrice(yield_underlying_token, 10 * EIGHTEEN_DECIMALS)  # $10
    
    # Create yield config with UNDY as alt bonus asset
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=10_00,  # Will be ignored since no ambassador
        _bonusRatio=25_00,            # 25% user bonus
        _altBonusAsset=undy_token.address,
    )
    
    setAssetConfig(yield_vault_token, _yieldConfig=yieldConfig)
    
    # Register vault token
    deposit_amount = 1_000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        deposit_amount,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Simulate yield profit (no performance fee since no ambassador)
    total_yield_amount = 80 * EIGHTEEN_DECIMALS
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        0,  # No performance fee
        total_yield_amount,
        sender=user_wallet_no_ambassador.address
    )
    
    # Calculate expected bonus
    # 80 vault tokens * $10 = $800 worth of yield
    # User bonus: 25% of $800 = $200 worth of UNDY
    # At $4 per UNDY = 50 UNDY tokens
    expected_user_bonus_undy = 50 * EIGHTEEN_DECIMALS
    
    # Verify user gets bonus even without ambassador
    assert loot_distributor.claimableLoot(user_wallet_no_ambassador.address, undy_token) == expected_user_bonus_undy
    assert loot_distributor.totalClaimableLoot(undy_token) == expected_user_bonus_undy
    
    # No vault tokens should be claimable (no fees)
    assert loot_distributor.totalClaimableLoot(yield_vault_token) == 0
    
    # Verify UNDY balance is still in the contract (claimable but not yet claimed)
    assert undy_token.balanceOf(loot_distributor) == undy_seed_amount


def test_add_loot_from_yield_profit_alt_bonus_asset_insufficient_balance(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, undy_token, whale, mock_yield_lego, mock_ripe, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test yield bonus with alt bonus asset when there's insufficient UNDY balance - user gets priority """
    
    # Seed loot distributor with LIMITED UNDY tokens
    undy_seed_amount = 30 * EIGHTEEN_DECIMALS  # Only 30 UNDY
    undy_token.transfer(loot_distributor, undy_seed_amount, sender=whale)
    
    # Set up prices
    mock_ripe.setPrice(undy_token, 1 * EIGHTEEN_DECIMALS)  # $1 per UNDY
    mock_ripe.setPrice(yield_underlying_token, 10 * EIGHTEEN_DECIMALS)  # $10
    
    # Set up config
    ambassadorRevShare = createAmbassadorRevShare(_yieldRatio=40_00)
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=20_00,  # 20% ambassador bonus
        _bonusRatio=30_00,            # 30% user bonus
        _altBonusAsset=undy_token.address,
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Register vault token
    yield_underlying_token.approve(mock_yield_lego, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Simulate large yield profit
    performance_fee = 10 * EIGHTEEN_DECIMALS
    total_yield_amount = 100 * EIGHTEEN_DECIMALS  # Large yield
    
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Calculate what bonuses WOULD be without balance constraints
    # Total yield value = 100 * 1.0 * $10 = $1000
    # User bonus: 30% of $1000 = $300 = 300 UNDY
    # Ambassador bonus: 20% of $1000 = $200 = 200 UNDY
    
    # With only 30 UNDY available and the new priority logic:
    # User gets their bonus first: min(300, 30) = 30 UNDY
    # Ambassador gets what's left: min(200, 0) = 0 UNDY
    
    user_bonus = loot_distributor.claimableLoot(user_wallet, undy_token)
    ambassador_bonus = loot_distributor.claimableLoot(ambassador_wallet, undy_token)
    
    # User gets all available UNDY
    assert user_bonus == undy_seed_amount
    assert ambassador_bonus == 0
    
    # Total distributed should equal available balance
    assert user_bonus + ambassador_bonus == undy_seed_amount
    
    # Verify UNDY balance is fully allocated (not transferred yet)
    assert undy_token.balanceOf(loot_distributor) == undy_seed_amount
    
    # Also verify ambassador gets their fee share in vault tokens
    expected_fee_share = performance_fee * 40_00 // 100_00  # 4 vault tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == expected_fee_share


def test_add_loot_from_yield_profit_deposit_rewards_reservation(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig, setUserWalletConfig):
    """ Test yield bonus respects deposit rewards reservation when bonus asset is same as deposit rewards asset """
    
    # Set up deposit rewards to use underlying token
    setUserWalletConfig(_depositRewardsAsset=yield_underlying_token.address)
    
    # Add deposit rewards
    deposit_rewards_amount = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(loot_distributor, deposit_rewards_amount, sender=yield_underlying_token_whale)
    loot_distributor.addDepositRewards(yield_underlying_token, deposit_rewards_amount, sender=yield_underlying_token_whale)
    
    # Seed additional underlying tokens for bonuses
    bonus_seed_amount = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(loot_distributor, bonus_seed_amount, sender=yield_underlying_token_whale)
    
    # Set up config for underlying asset bonuses
    ambassadorRevShare = createAmbassadorRevShare(_yieldRatio=40_00)
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=20_00,  # 20% ambassador bonus
        _bonusRatio=30_00,            # 30% user bonus
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Register vault token
    yield_underlying_token.approve(mock_yield_lego, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Verify initial state
    assert yield_underlying_token.balanceOf(loot_distributor) == deposit_rewards_amount + bonus_seed_amount
    assert loot_distributor.depositRewards().amount == deposit_rewards_amount
    
    # Simulate yield profit
    performance_fee = 10 * EIGHTEEN_DECIMALS
    total_yield_amount = 100 * EIGHTEEN_DECIMALS
    
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Calculate expected bonuses
    # Total yield in underlying: 100 underlying tokens
    # User bonus: 30% = 30 underlying tokens
    # Ambassador bonus: 20% = 20 underlying tokens
    # Total bonuses: 50 underlying tokens
    
    # Available for bonuses = 150 total - 50 reserved = 100 underlying
    # So all bonuses should be paid
    
    assert loot_distributor.claimableLoot(user_wallet, yield_underlying_token) == 30 * EIGHTEEN_DECIMALS
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == 20 * EIGHTEEN_DECIMALS
    
    # Verify deposit rewards are still protected
    assert loot_distributor.depositRewards().amount == deposit_rewards_amount
    
    # Verify total balance is correct (allocated bonuses are still in contract)
    assert yield_underlying_token.balanceOf(loot_distributor) == deposit_rewards_amount + bonus_seed_amount


def test_add_loot_from_yield_profit_deposit_rewards_limits_bonuses(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig, setUserWalletConfig):
    """ Test yield bonus is limited when deposit rewards take up most of the balance """
    
    # Set up deposit rewards to use underlying token
    setUserWalletConfig(_depositRewardsAsset=yield_underlying_token.address)
    
    # Add deposit rewards
    deposit_rewards_amount = 80 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(loot_distributor, deposit_rewards_amount, sender=yield_underlying_token_whale)
    loot_distributor.addDepositRewards(yield_underlying_token, deposit_rewards_amount, sender=yield_underlying_token_whale)
    
    # Seed only a small amount for bonuses
    bonus_seed_amount = 20 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(loot_distributor, bonus_seed_amount, sender=yield_underlying_token_whale)
    
    # Set up config
    ambassadorRevShare = createAmbassadorRevShare(_yieldRatio=40_00)
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=20_00,  # 20% ambassador bonus
        _bonusRatio=30_00,            # 30% user bonus
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Register vault token
    yield_underlying_token.approve(mock_yield_lego, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Verify initial state
    assert yield_underlying_token.balanceOf(loot_distributor) == deposit_rewards_amount + bonus_seed_amount
    
    # Simulate yield profit
    performance_fee = 10 * EIGHTEEN_DECIMALS
    total_yield_amount = 100 * EIGHTEEN_DECIMALS
    
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Calculate expected bonuses
    # Total yield in underlying: 100 underlying tokens
    # User wants: 30% = 30 underlying tokens
    # Ambassador wants: 20% = 20 underlying tokens
    
    # But only 20 available (100 total - 80 reserved)
    # User gets priority: min(30, 20) = 20
    # Ambassador gets: min(20, 0) = 0
    
    assert loot_distributor.claimableLoot(user_wallet, yield_underlying_token) == 20 * EIGHTEEN_DECIMALS
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == 0
    
    # Verify deposit rewards are still protected
    assert loot_distributor.depositRewards().amount == deposit_rewards_amount


def test_add_loot_from_yield_profit_vault_token_bonus(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, governance, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test yield bonus paid in vault tokens (in-kind) when no underlying or alt asset configured """
    
    # Seed vault tokens for bonuses
    yield_underlying_token.approve(mock_yield_lego, 2000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        2000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    vault_token_seed = 200 * EIGHTEEN_DECIMALS
    yield_vault_token.transfer(loot_distributor, vault_token_seed, sender=yield_underlying_token_whale)
    
    # Set up config with NO underlying asset and NO alt bonus asset
    ambassadorRevShare = createAmbassadorRevShare(_yieldRatio=40_00)
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=ZERO_ADDRESS,  # No underlying asset specified
        _ambassadorBonusRatio=15_00,     # 15% ambassador bonus
        _bonusRatio=25_00,               # 25% user bonus
        _altBonusAsset=ZERO_ADDRESS,     # No alt bonus asset
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Simulate yield profit
    performance_fee = 10 * EIGHTEEN_DECIMALS
    total_yield_amount = 100 * EIGHTEEN_DECIMALS
    
    # Transfer performance fee from user wallet to loot distributor
    yield_vault_token.transfer(user_wallet, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Calculate expected bonuses (in vault tokens)
    # User bonus: 25% of 100 = 25 vault tokens
    # Ambassador bonus: 15% of 100 = 15 vault tokens
    # Ambassador fee share: 40% of 10 = 4 vault tokens
    # Leftover fee to governance: 60% of 10 = 6 vault tokens

    assert loot_distributor.claimableLoot(user_wallet, yield_vault_token) == 25 * EIGHTEEN_DECIMALS
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == (15 + 4) * EIGHTEEN_DECIMALS

    # Verify leftover fee was sent to governance
    leftover_fee = performance_fee * 60_00 // 100_00  # 6 vault tokens
    assert yield_vault_token.balanceOf(governance.address) == leftover_fee

    # Verify vault token balance (initial seed minus governance transfer)
    assert yield_vault_token.balanceOf(loot_distributor) == vault_token_seed - leftover_fee


def test_add_loot_from_yield_profit_zero_price_scenario(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, undy_token, whale, mock_yield_lego, mock_ripe, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test yield bonus with alt asset when price is zero - should fall back to underlying asset """
    
    # Seed tokens
    undy_seed_amount = 1000 * EIGHTEEN_DECIMALS
    undy_token.transfer(loot_distributor, undy_seed_amount, sender=whale)
    
    underlying_seed_amount = 200 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(loot_distributor, underlying_seed_amount, sender=yield_underlying_token_whale)
    
    # Set up prices - UNDY price is 0
    mock_ripe.setPrice(undy_token, 0)  # Zero price!
    mock_ripe.setPrice(yield_underlying_token, 10 * EIGHTEEN_DECIMALS)  # $10
    
    # Set up config with UNDY as alt bonus asset
    ambassadorRevShare = createAmbassadorRevShare(_yieldRatio=40_00)
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=20_00,
        _bonusRatio=30_00,
        _altBonusAsset=undy_token.address,  # UNDY as alt asset
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Register vault token
    yield_underlying_token.approve(mock_yield_lego, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Simulate yield profit
    performance_fee = 10 * EIGHTEEN_DECIMALS
    total_yield_amount = 100 * EIGHTEEN_DECIMALS
    
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # When alt asset price is 0, _getAltBonusAssetAmount returns 0
    # This makes bonusAssetYieldRealized = 0, so NO bonuses are given
    
    # No UNDY bonuses because price is 0
    assert loot_distributor.claimableLoot(user_wallet, undy_token) == 0
    assert loot_distributor.claimableLoot(ambassador_wallet, undy_token) == 0
    
    # No underlying bonuses either (alt asset is still the bonus asset, just with 0 amount)
    assert loot_distributor.claimableLoot(user_wallet, yield_underlying_token) == 0
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_underlying_token) == 0
    
    # Ambassador still gets fee share in vault tokens
    expected_fee_share = performance_fee * 40_00 // 100_00  # 4 vault tokens
    assert loot_distributor.claimableLoot(ambassador_wallet, yield_vault_token) == expected_fee_share
    
    # Verify token balances unchanged
    assert undy_token.balanceOf(loot_distributor) == undy_seed_amount
    assert yield_underlying_token.balanceOf(loot_distributor) == underlying_seed_amount


def test_event_emissions_tx_fee_and_yield_bonus(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test TransactionFeePaid, AmbassadorTxFeePaid, YieldPerformanceFeePaid and YieldBonusPaid event emissions """
    
    # Register the vault token first
    yield_underlying_token.approve(mock_yield_lego, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token,
        1000 * EIGHTEEN_DECIMALS,
        yield_vault_token,
        sender=yield_underlying_token_whale,
    )
    
    # Seed tokens for bonuses
    yield_underlying_token.transfer(loot_distributor, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    yield_vault_token.transfer(loot_distributor, 100 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Set up config with yield bonuses
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=50_00,      # 50% swap fee
        _yieldRatio=40_00,     # 40% yield fee
    )
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _ambassadorBonusRatio=15_00,  # 15% ambassador bonus
        _bonusRatio=25_00,            # 25% user bonus
    )
    
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Test 1: TransactionFeePaid and AmbassadorTxFeePaid events from swap fee
    swap_fee = 10 * EIGHTEEN_DECIMALS
    yield_vault_token.transfer(user_wallet, swap_fee, sender=yield_underlying_token_whale)
    yield_vault_token.approve(loot_distributor, swap_fee, sender=user_wallet.address)
    
    loot_distributor.addLootFromSwapOrRewards(
        yield_vault_token,
        swap_fee,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    # Check events immediately after the transaction
    tx_fee_events = filter_logs(loot_distributor, 'TransactionFeePaid')
    assert len(tx_fee_events) == 1
    tx_fee_event = tx_fee_events[0]
    assert tx_fee_event.user == user_wallet.address
    assert tx_fee_event.asset == yield_vault_token.address
    assert tx_fee_event.feeAmount == swap_fee
    assert tx_fee_event.action == ACTION_TYPE.SWAP
    
    # Check AmbassadorTxFeePaid event
    ambassador_fee_events = filter_logs(loot_distributor, 'AmbassadorTxFeePaid')
    assert len(ambassador_fee_events) == 1
    ambassador_fee_event = ambassador_fee_events[0]
    assert ambassador_fee_event.asset == yield_vault_token.address
    assert ambassador_fee_event.totalFee == swap_fee
    assert ambassador_fee_event.ambassadorFeeRatio == 50_00  # 50%
    assert ambassador_fee_event.ambassadorFee == swap_fee * 50_00 // 100_00  # 5 tokens
    assert ambassador_fee_event.ambassador == ambassador_wallet.address
    assert ambassador_fee_event.action == ACTION_TYPE.SWAP
    
    # Test 2: YieldPerformanceFeePaid, AmbassadorTxFeePaid and YieldBonusPaid events from yield profit
    performance_fee = 2 * EIGHTEEN_DECIMALS
    total_yield = 10 * EIGHTEEN_DECIMALS
    
    # Transfer performance fee to loot distributor (simulating it already being there)
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield,
        sender=user_wallet.address
    )
    
    # Check events immediately after the transaction
    # YieldPerformanceFeePaid event
    yield_fee_events = filter_logs(loot_distributor, 'YieldPerformanceFeePaid')
    assert len(yield_fee_events) == 1
    yield_fee_event = yield_fee_events[0]
    assert yield_fee_event.user == user_wallet.address
    assert yield_fee_event.asset == yield_vault_token.address
    assert yield_fee_event.feeAmount == performance_fee
    assert yield_fee_event.yieldRealized == total_yield
    
    # AmbassadorTxFeePaid event for yield fee
    ambassador_fee_events = filter_logs(loot_distributor, 'AmbassadorTxFeePaid')
    assert len(ambassador_fee_events) == 1
    ambassador_fee_event = ambassador_fee_events[0]
    assert ambassador_fee_event.asset == yield_vault_token.address
    assert ambassador_fee_event.totalFee == performance_fee
    assert ambassador_fee_event.ambassadorFeeRatio == 40_00  # 40% yield fee
    assert ambassador_fee_event.ambassadorFee == performance_fee * 40_00 // 100_00  # 0.8 tokens
    assert ambassador_fee_event.ambassador == ambassador_wallet.address
    assert ambassador_fee_event.action == 0  # empty(ActionType) for yield
    
    # Check YieldBonusPaid events (should be 2: one for user, one for ambassador)
    yield_events = filter_logs(loot_distributor, 'YieldBonusPaid')
    assert len(yield_events) == 2
    
    # User bonus event
    user_event = yield_events[0]
    assert user_event.bonusAsset == yield_underlying_token.address  # bonuses paid in underlying
    assert user_event.bonusAmount == total_yield * 25_00 // 100_00  # 2.5 tokens
    assert user_event.bonusRatio == 25_00  # 25%
    assert user_event.yieldRealized == total_yield  # 10 underlying tokens worth
    assert user_event.recipient == user_wallet.address
    assert user_event.isAmbassador == False
    
    # Ambassador bonus event
    ambassador_event = yield_events[1]
    assert ambassador_event.bonusAsset == yield_underlying_token.address  # bonuses paid in underlying
    assert ambassador_event.bonusAmount == total_yield * 15_00 // 100_00  # 1.5 tokens
    assert ambassador_event.bonusRatio == 15_00  # 15%
    assert ambassador_event.yieldRealized == total_yield  # 10 underlying tokens worth
    assert ambassador_event.recipient == ambassador_wallet.address
    assert ambassador_event.isAmbassador == True


def test_add_loot_from_yield_profit_different_decimal_precision(loot_distributor, user_wallet, ambassador_wallet, charlie_token, charlie_token_vault, charlie_token_whale, delta_token, delta_token_vault, delta_token_whale, mock_yield_lego, mock_ripe, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test yield bonus with assets of different decimal precision (6, 8, 18 decimals) """
    
    # Charlie token has 6 decimals, Delta token has 8 decimals
    assert charlie_token.decimals() == 6
    assert delta_token.decimals() == 8
    
    # Set up prices
    mock_ripe.setPrice(charlie_token, 1 * EIGHTEEN_DECIMALS)  # $1 per CHARLIE (like USDC)
    mock_ripe.setPrice(delta_token, 50_000 * EIGHTEEN_DECIMALS)  # $50,000 per DELTA (like WBTC)
    
    # Seed tokens for bonuses
    charlie_amount = 10_000 * (10 ** 6)  # 10,000 CHARLIE tokens
    delta_amount = 2 * (10 ** 8)  # 2 DELTA tokens
    charlie_token.transfer(loot_distributor, charlie_amount, sender=charlie_token_whale)
    delta_token.transfer(loot_distributor, delta_amount, sender=delta_token_whale)
    
    # Test 1: Charlie vault (6 decimals) with Delta (8 decimals) as alt bonus asset
    ambassadorRevShare = createAmbassadorRevShare(_yieldRatio=40_00)
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=charlie_token.address,
        _ambassadorBonusRatio=10_00,  # 10%
        _bonusRatio=20_00,            # 20%
        _altBonusAsset=delta_token.address,  # Delta as alt bonus
    )
    
    setAssetConfig(
        charlie_token_vault,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Register Charlie vault
    charlie_token.approve(mock_yield_lego, 1000 * (10 ** 6), sender=charlie_token_whale)
    mock_yield_lego.depositForYield(charlie_token, 1000 * (10 ** 6), charlie_token_vault, sender=charlie_token_whale)
    
    # Simulate yield on Charlie vault
    performance_fee = 10 * (10 ** 6)  # 10 Charlie vault tokens
    total_yield_amount = 100 * (10 ** 6)  # 100 Charlie vault tokens
    
    charlie_token_vault.transfer(loot_distributor, performance_fee, sender=charlie_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        charlie_token_vault,
        performance_fee,
        total_yield_amount,
        sender=user_wallet.address
    )
    
    # Calculate expected Delta bonuses
    # Yield value: 100 CHARLIE = $100
    # User bonus: 20% of $100 = $20 worth of DELTA
    # At $50,000 per DELTA = 0.0004 DELTA = 40,000 units (8 decimals)
    expected_user_delta = 40_000  # 0.0004 DELTA
    
    # Ambassador bonus: 10% of $100 = $10 worth of DELTA
    # At $50,000 per DELTA = 0.0002 DELTA = 20,000 units
    expected_ambassador_delta = 20_000  # 0.0002 DELTA
    
    assert loot_distributor.claimableLoot(user_wallet, delta_token) == expected_user_delta
    assert loot_distributor.claimableLoot(ambassador_wallet, delta_token) == expected_ambassador_delta
    
    # Test 2: Delta vault (8 decimals) with underlying bonus
    yieldConfig2 = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=delta_token.address,
        _ambassadorBonusRatio=5_00,   # 5%
        _bonusRatio=15_00,            # 15%
    )
    
    setAssetConfig(
        delta_token_vault,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig2,
    )
    
    # Register Delta vault
    delta_token.approve(mock_yield_lego, 1 * (10 ** 8), sender=delta_token_whale)
    mock_yield_lego.depositForYield(delta_token, 1 * (10 ** 8), delta_token_vault, sender=delta_token_whale)
    
    # Simulate yield on Delta vault
    delta_yield = 1_000_000  # 0.01 Delta vault tokens (1% yield)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        delta_token_vault,
        0,  # No performance fee
        delta_yield,
        sender=user_wallet.address
    )
    
    # Calculate expected Delta bonuses (paid in underlying)
    # User bonus: 15% of 0.01 DELTA = 0.0015 DELTA = 150,000 units
    expected_user_delta_bonus = 150_000
    
    # Ambassador bonus: 5% of 0.01 DELTA = 0.0005 DELTA = 50,000 units
    expected_ambassador_delta_bonus = 50_000
    
    assert loot_distributor.claimableLoot(user_wallet, delta_token) == expected_user_delta + expected_user_delta_bonus
    assert loot_distributor.claimableLoot(ambassador_wallet, delta_token) == expected_ambassador_delta + expected_ambassador_delta_bonus


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
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
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
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
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
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
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
        loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
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
        loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=charlie)
    
    # Alice (owner) can claim
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
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
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
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
    
    # Claim should fail because there are no claimable assets - reverts at external level
    with boa.reverts("no assets claimed"):
        loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)


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
    loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
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


###################
# Deposit Rewards #
###################


# add deposit rewards


def test_add_deposit_rewards_basic(loot_distributor, alpha_token, alpha_token_whale, setUserWalletConfig):
    """ Test basic addDepositRewards functionality """
    
    # Configure alpha_token as the deposit rewards asset in MissionControl
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Check initial state
    initial_rewards = loot_distributor.depositRewards()
    assert initial_rewards.asset == ZERO_ADDRESS
    assert initial_rewards.amount == 0
    
    # Approve and add rewards
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    
    # Add deposit rewards
    loot_distributor.addDepositRewards(
        alpha_token.address,
        rewards_amount,
        sender=alpha_token_whale
    )
    
    # Verify storage updated
    updated_rewards = loot_distributor.depositRewards()
    assert updated_rewards.asset == alpha_token.address
    assert updated_rewards.amount == rewards_amount
    
    # Verify tokens transferred
    assert alpha_token.balanceOf(loot_distributor) == rewards_amount


def test_add_deposit_rewards_accumulates(loot_distributor, alpha_token, alpha_token_whale, setUserWalletConfig):
    """ Test that multiple addDepositRewards calls accumulate """
    
    # Configure deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # First addition
    first_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, first_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, first_amount, sender=alpha_token_whale)
    
    # Verify first addition
    rewards = loot_distributor.depositRewards()
    assert rewards.amount == first_amount
    
    # Second addition
    second_amount = 300 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, second_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, second_amount, sender=alpha_token_whale)
    
    # Verify accumulation
    rewards = loot_distributor.depositRewards()
    assert rewards.asset == alpha_token.address
    assert rewards.amount == first_amount + second_amount
    assert alpha_token.balanceOf(loot_distributor) == first_amount + second_amount


def test_add_deposit_rewards_invalid_asset(loot_distributor, alpha_token, bravo_token, alpha_token_whale, setUserWalletConfig):
    """ Test addDepositRewards rejects invalid asset """
    
    # Configure alpha_token as the deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Try to add rewards with wrong asset (bravo_token)
    rewards_amount = 100 * EIGHTEEN_DECIMALS
    bravo_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    
    # Should fail with invalid asset
    with boa.reverts("invalid asset"):
        loot_distributor.addDepositRewards(
            bravo_token.address,  # Wrong asset
            rewards_amount,
            sender=alpha_token_whale
        )


def test_add_deposit_rewards_no_configured_asset(loot_distributor, alpha_token, alpha_token_whale):
    """ Test addDepositRewards fails when no deposit rewards asset is configured """
    
    # Don't configure any deposit rewards asset
    # Try to add rewards
    rewards_amount = 100 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    
    # Should fail because no asset is configured
    with boa.reverts("invalid asset"):
        loot_distributor.addDepositRewards(
            alpha_token.address,
            rewards_amount,
            sender=alpha_token_whale
        )


def test_add_deposit_rewards_zero_amount(loot_distributor, alpha_token, charlie, setUserWalletConfig):
    """ Test addDepositRewards fails with zero amount """
    
    # Configure deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Charlie has no tokens, try to add rewards
    with boa.reverts("nothing to add"):
        loot_distributor.addDepositRewards(
            alpha_token.address,
            100 * EIGHTEEN_DECIMALS,  # Amount they don't have
            sender=charlie
        )


def test_add_deposit_rewards_partial_balance(loot_distributor, alpha_token, alpha_token_whale, charlie, setUserWalletConfig):
    """ Test addDepositRewards uses actual balance if less than requested """
    
    # Configure deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Give charlie some tokens but less than what they'll try to add
    actual_balance = 50 * EIGHTEEN_DECIMALS
    alpha_token.transfer(charlie, actual_balance, sender=alpha_token_whale)
    
    # Approve more than balance
    alpha_token.approve(loot_distributor.address, 1000 * EIGHTEEN_DECIMALS, sender=charlie)
    
    # Try to add more than balance
    loot_distributor.addDepositRewards(
        alpha_token.address,
        1000 * EIGHTEEN_DECIMALS,  # More than charlie has
        sender=charlie
    )
    
    # Should only add actual balance
    rewards = loot_distributor.depositRewards()
    assert rewards.amount == actual_balance
    assert alpha_token.balanceOf(loot_distributor) == actual_balance
    assert alpha_token.balanceOf(charlie) == 0


def test_add_deposit_rewards_changing_asset_requires_recovery(loot_distributor, alpha_token, bravo_token, alpha_token_whale, bravo_token_whale, setUserWalletConfig, switchboard_alpha):
    """ Test changing reward asset requires recovering previous rewards first """
    
    # Configure alpha_token as initial deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Add some alpha rewards
    alpha_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, alpha_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, alpha_amount, sender=alpha_token_whale)
    
    # Change config to bravo_token
    setUserWalletConfig(_depositRewardsAsset=bravo_token.address)
    
    # Try to add bravo rewards - should fail because alpha rewards still exist
    bravo_amount = 300 * EIGHTEEN_DECIMALS
    bravo_token.approve(loot_distributor.address, bravo_amount, sender=bravo_token_whale)
    
    with boa.reverts("asset mismatch"):
        loot_distributor.addDepositRewards(bravo_token.address, bravo_amount, sender=bravo_token_whale)
    
    # Recover alpha rewards first
    loot_distributor.recoverDepositRewards(alpha_token_whale, sender=switchboard_alpha.address)
    
    # Now adding bravo should work
    loot_distributor.addDepositRewards(bravo_token.address, bravo_amount, sender=bravo_token_whale)
    
    # Verify bravo is now the reward asset
    rewards = loot_distributor.depositRewards()
    assert rewards.asset == bravo_token.address
    assert rewards.amount == bravo_amount


def test_add_deposit_rewards_event_emission(loot_distributor, alpha_token, alpha_token_whale, setUserWalletConfig):
    """ Test DepositRewardsAdded event is emitted correctly """
    
    # Configure deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Add rewards
    rewards_amount = 750 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Check event using filter_logs
    event = filter_logs(loot_distributor, 'DepositRewardsAdded')[0]
    assert event.asset == alpha_token.address
    assert event.addedAmount == rewards_amount
    assert event.newTotalAmount == rewards_amount
    assert event.adder == alpha_token_whale
    
    # Add more rewards to test accumulation in event
    second_amount = 250 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, second_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, second_amount, sender=alpha_token_whale)
    
    # Check second event
    event = filter_logs(loot_distributor, 'DepositRewardsAdded')[0]
    assert event.asset == alpha_token.address
    assert event.addedAmount == second_amount
    assert event.newTotalAmount == rewards_amount + second_amount
    assert event.adder == alpha_token_whale


def test_add_deposit_rewards_multiple_contributors(loot_distributor, alpha_token, alpha_token_whale, env, setUserWalletConfig):
    """ Test multiple addresses can contribute deposit rewards """
    
    # Configure deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Create additional contributors
    contributor1 = env.generate_address("contributor1")
    contributor2 = env.generate_address("contributor2")
    
    # Fund contributors
    alpha_token.transfer(contributor1, 200 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    alpha_token.transfer(contributor2, 300 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # Contributor 1 adds rewards
    alpha_token.approve(loot_distributor.address, 200 * EIGHTEEN_DECIMALS, sender=contributor1)
    loot_distributor.addDepositRewards(alpha_token.address, 200 * EIGHTEEN_DECIMALS, sender=contributor1)
    
    # Contributor 2 adds rewards
    alpha_token.approve(loot_distributor.address, 300 * EIGHTEEN_DECIMALS, sender=contributor2)
    loot_distributor.addDepositRewards(alpha_token.address, 300 * EIGHTEEN_DECIMALS, sender=contributor2)
    
    # Alpha whale also adds
    alpha_token.approve(loot_distributor.address, 500 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, 500 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # Verify total
    rewards = loot_distributor.depositRewards()
    assert rewards.amount == 1000 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(loot_distributor) == 1000 * EIGHTEEN_DECIMALS


# recover deposit rewards


def test_recover_deposit_rewards_basic(loot_distributor, alpha_token, alpha_token_whale, charlie, switchboard_alpha, setUserWalletConfig):
    """ Test basic recoverDepositRewards functionality """
    
    # Configure and add deposit rewards
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Verify rewards exist
    rewards = loot_distributor.depositRewards()
    assert rewards.asset == alpha_token.address
    assert rewards.amount == rewards_amount
    
    initial_recipient_balance = alpha_token.balanceOf(charlie)
    
    # Recover rewards
    loot_distributor.recoverDepositRewards(charlie, sender=switchboard_alpha.address)
    
    # Verify rewards were recovered
    rewards = loot_distributor.depositRewards()
    assert rewards.asset == ZERO_ADDRESS
    assert rewards.amount == 0
    
    # Verify recipient received the tokens
    assert alpha_token.balanceOf(charlie) == initial_recipient_balance + rewards_amount
    assert alpha_token.balanceOf(loot_distributor) == 0


def test_recover_deposit_rewards_permission(loot_distributor, alpha_token, alpha_token_whale, charlie, bob, setUserWalletConfig):
    """ Test only switchboard can recover deposit rewards """
    
    # Configure and add deposit rewards
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Try to recover without permission
    with boa.reverts("no perms"):
        loot_distributor.recoverDepositRewards(charlie, sender=bob)
    
    # Try from alpha_token_whale (not switchboard)
    with boa.reverts("no perms"):
        loot_distributor.recoverDepositRewards(charlie, sender=alpha_token_whale)


def test_recover_deposit_rewards_no_rewards(loot_distributor, charlie, switchboard_alpha):
    """ Test recovery when no rewards exist """
    
    # Verify no rewards exist
    rewards = loot_distributor.depositRewards()
    assert rewards.asset == ZERO_ADDRESS
    assert rewards.amount == 0
    
    # Try to recover - should fail
    with boa.reverts("nothing to recover"):
        loot_distributor.recoverDepositRewards(charlie, sender=switchboard_alpha.address)


def test_recover_deposit_rewards_partial_balance(loot_distributor, alpha_token, alpha_token_whale, charlie, switchboard_alpha, setUserWalletConfig):
    """ Test recovery when contract has less balance than recorded rewards """
    
    # Configure and add deposit rewards
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Remove some tokens from the contract
    alpha_token.transfer(alpha_token_whale, 400 * EIGHTEEN_DECIMALS, sender=loot_distributor.address)
    
    # Verify partial balance
    assert alpha_token.balanceOf(loot_distributor) == 600 * EIGHTEEN_DECIMALS
    
    initial_recipient_balance = alpha_token.balanceOf(charlie)
    
    # Recover should only transfer available balance
    loot_distributor.recoverDepositRewards(charlie, sender=switchboard_alpha.address)
    
    # Verify only available balance was transferred
    assert alpha_token.balanceOf(charlie) == initial_recipient_balance + 600 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(loot_distributor) == 0
    
    # Verify rewards storage was cleared
    rewards = loot_distributor.depositRewards()
    assert rewards.asset == ZERO_ADDRESS
    assert rewards.amount == 0


def test_recover_deposit_rewards_event_emission(loot_distributor, alpha_token, alpha_token_whale, charlie, switchboard_alpha, setUserWalletConfig):
    """ Test DepositRewardsRecovered event is emitted correctly """
    
    # Configure and add deposit rewards
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 750 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Recover rewards
    loot_distributor.recoverDepositRewards(charlie, sender=switchboard_alpha.address)
    
    # Check event using filter_logs
    events = filter_logs(loot_distributor, 'DepositRewardsRecovered')[0]
    assert events.asset == alpha_token.address
    assert events.recipient == charlie
    assert events.amount == rewards_amount


def test_recover_deposit_rewards_zero_balance(loot_distributor, alpha_token, alpha_token_whale, charlie, switchboard_alpha, setUserWalletConfig):
    """ Test recovery when rewards exist but contract has zero balance """
    
    # Configure and add deposit rewards
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Remove all tokens from the contract
    alpha_token.transfer(alpha_token_whale, rewards_amount, sender=loot_distributor.address)
    assert alpha_token.balanceOf(loot_distributor) == 0
    
    initial_recipient_balance = alpha_token.balanceOf(charlie)
    
    # Recover should work but transfer 0
    loot_distributor.recoverDepositRewards(charlie, sender=switchboard_alpha.address)

    # Check event shows 0 amount
    event = filter_logs(loot_distributor, 'DepositRewardsRecovered')[0]
    assert event.amount == 0

    # Verify no tokens were transferred
    assert alpha_token.balanceOf(charlie) == initial_recipient_balance
    
    # Verify rewards storage was still cleared
    rewards = loot_distributor.depositRewards()
    assert rewards.asset == ZERO_ADDRESS
    assert rewards.amount == 0
    

def test_recover_deposit_rewards_allows_new_asset(loot_distributor, alpha_token, bravo_token, alpha_token_whale, bravo_token_whale, charlie, switchboard_alpha, setUserWalletConfig):
    """ Test recovery clears state allowing a new reward asset """
    
    # Configure alpha as initial rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Add alpha rewards
    alpha_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, alpha_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, alpha_amount, sender=alpha_token_whale)
    
    # Recover alpha rewards
    loot_distributor.recoverDepositRewards(charlie, sender=switchboard_alpha.address)
    
    # Configure bravo as new rewards asset
    setUserWalletConfig(_depositRewardsAsset=bravo_token.address)
    
    # Should be able to add bravo rewards now
    bravo_amount = 300 * EIGHTEEN_DECIMALS
    bravo_token.approve(loot_distributor.address, bravo_amount, sender=bravo_token_whale)
    loot_distributor.addDepositRewards(bravo_token.address, bravo_amount, sender=bravo_token_whale)
    
    # Verify bravo is now the reward asset
    rewards = loot_distributor.depositRewards()
    assert rewards.asset == bravo_token.address
    assert rewards.amount == bravo_amount


# claim deposit rewards


def test_claim_deposit_rewards_basic(loot_distributor, user_wallet, bob, alpha_token, alpha_token_whale, setUserWalletConfig, ledger, switchboard_alpha):
    """ Test basic claimDepositRewards functionality """
    
    # Configure deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Add deposit rewards
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Build up deposit points for user by updating with USD value
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    
    # Travel more blocks to accumulate points
    boa.env.time_travel(blocks=1000)
    
    # Update points to finalize accumulation
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    initial_balance = alpha_token.balanceOf(user_wallet.address)
    
    # Claim rewards
    user_rewards = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    
    # Verify user received rewards
    assert user_rewards != 0
    assert alpha_token.balanceOf(user_wallet.address) == initial_balance + user_rewards
    
    # Verify user points were cleared
    user_points, _ = ledger.getUserAndGlobalPoints(user_wallet.address)
    assert user_points.depositPoints == 0
    
    # Verify rewards reduced
    rewards = loot_distributor.depositRewards()
    assert rewards.amount == rewards_amount - user_rewards


def test_claim_deposit_rewards_multiple_users(loot_distributor, user_wallet, ambassador_wallet, alice, bob, alpha_token, alpha_token_whale, setUserWalletConfig, hatchery, charlie, switchboard_alpha):
    """ Test multiple users claiming deposit rewards """
    
    # Create another user wallet
    wallet2_addr = hatchery.createUserWallet(charlie, ambassador_wallet, False, 1, sender=charlie)
    wallet2 = UserWallet.at(wallet2_addr)
    
    # Configure deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Add deposit rewards - 1000 tokens to distribute
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Build up deposit points for user1 (100 USD value)
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    
    # Build up deposit points for user2 (300 USD value - exactly 3x more)
    loot_distributor.updateDepositPointsWithNewValue(wallet2.address, 300 * EIGHTEEN_DECIMALS, sender=wallet2.address)
    
    # Travel exactly 1000 blocks to accumulate points
    # User1: 100 USD * 1000 blocks = 100,000 points (divided by 1e18)
    # User2: 300 USD * 1000 blocks = 300,000 points (divided by 1e18)
    # Total: 400,000 points
    boa.env.time_travel(blocks=1000)
    
    # Update points to finalize
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    loot_distributor.updateDepositPoints(wallet2.address, sender=switchboard_alpha.address)
    
    # User1 claims first
    user1_rewards = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    
    # User2 claims second
    user2_rewards = loot_distributor.claimDepositRewards(wallet2.address, sender=charlie)
    
    # Verify exact proportional distribution
    # User1 should get 1/4 (25%) of rewards = 250 tokens
    assert user1_rewards == 250 * EIGHTEEN_DECIMALS
    
    # User2 should get 3/4 (75%) of rewards = 750 tokens
    assert user2_rewards == 750 * EIGHTEEN_DECIMALS
    
    # Verify total claimed equals the rewards amount
    assert user1_rewards + user2_rewards == rewards_amount


def test_claim_deposit_rewards_permission(loot_distributor, user_wallet, alice, alpha_token, alpha_token_whale, setUserWalletConfig):
    """ Test permission checks for claimDepositRewards """
    
    # Setup rewards and points
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Build points
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=1000)
    
    # Try to claim with wrong owner (alice owns ambassador_wallet, not user_wallet)
    with boa.reverts("no perms"):
        loot_distributor.claimDepositRewards(user_wallet.address, sender=alice)


def test_claim_deposit_rewards_no_rewards(loot_distributor, user_wallet, bob):
    """ Test claiming when no rewards are available """
    
    # Build up deposit points
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=1000)
    
    # Try to claim without rewards configured - should now revert at external level
    with boa.reverts("nothing to claim"):
        loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)


def test_claim_deposit_rewards_no_points(loot_distributor, user_wallet, bob, alpha_token, alpha_token_whale, setUserWalletConfig):
    """ Test claiming when user has no deposit points """
    
    # Configure and add rewards
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Try to claim without any points - should now revert at external level
    with boa.reverts("nothing to claim"):
        loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)


def test_claim_deposit_rewards_zero_user_share(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, setUserWalletConfig, hatchery, charlie, sally, switchboard_alpha):
    """ Test claiming when user's share rounds down to zero """
    
    # Create two fresh wallets
    fresh_wallet_addr = hatchery.createUserWallet(charlie, ZERO_ADDRESS, False, 1, sender=charlie)
    fresh_wallet = UserWallet.at(fresh_wallet_addr)
    
    another_wallet_addr = hatchery.createUserWallet(sally, ambassador_wallet, False, 1, sender=sally)
    another_wallet = UserWallet.at(another_wallet_addr)
    
    # Configure and add rewards
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Add very small rewards amount
    rewards_amount = 10  # Only 10 wei
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Build up massive global points with user_wallet
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 1000000 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=10000)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Give another wallet significant points to ensure global points remain
    loot_distributor.updateDepositPointsWithNewValue(another_wallet.address, 100000 * EIGHTEEN_DECIMALS, sender=another_wallet.address)
    boa.env.time_travel(blocks=1000)
    loot_distributor.updateDepositPoints(another_wallet.address, sender=switchboard_alpha.address)
    
    # Give fresh wallet minimal points
    loot_distributor.updateDepositPointsWithNewValue(fresh_wallet.address, 1, sender=fresh_wallet.address)
    boa.env.time_travel(blocks=1)
    loot_distributor.updateDepositPoints(fresh_wallet.address, sender=switchboard_alpha.address)
    
    # Fresh wallet's share will be so small it rounds to 0
    # With other wallets having points, global points will remain > 0
    # Try to claim - should now revert at external level because calculated reward is 0
    with boa.reverts("nothing to claim"):
        loot_distributor.claimDepositRewards(fresh_wallet.address, sender=charlie)


def test_claim_deposit_rewards_event_emission(loot_distributor, user_wallet, bob, alpha_token, alpha_token_whale, setUserWalletConfig, switchboard_alpha):
    """ Test DepositRewardsClaimed event is emitted correctly """
    
    # Setup rewards and points
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Build points
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 200 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=1000)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Claim rewards
    user_rewards = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    
    # Check event
    event = filter_logs(loot_distributor, 'DepositRewardsClaimed')[0]
    assert event.user == user_wallet.address
    assert event.asset == alpha_token.address
    assert event.userRewards == user_rewards
    assert event.remainingRewards == rewards_amount - user_rewards


def test_claim_deposit_rewards_partial_balance(loot_distributor, user_wallet, bob, alpha_token, alpha_token_whale, setUserWalletConfig, switchboard_alpha):
    """ Test claiming when contract has less balance than recorded rewards """
    
    # Setup rewards and points
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Remove some balance
    alpha_token.transfer(alpha_token_whale, 600 * EIGHTEEN_DECIMALS, sender=loot_distributor.address)
    
    # Build points
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=1000)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # User claims - should get their proportional share of available balance
    initial_balance = alpha_token.balanceOf(user_wallet.address)
    user_rewards = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    
    # Verify user got rewards based on available balance (400e18)
    assert user_rewards <= 400 * EIGHTEEN_DECIMALS
    assert alpha_token.balanceOf(user_wallet.address) == initial_balance + user_rewards


def test_claim_deposit_rewards_not_current_distributor(loot_distributor, user_wallet, governance, bob, alpha_token, alpha_token_whale, setUserWalletConfig, undy_hq, mock_ripe_token, mock_ripe):
    """ Test claiming fails if not the current loot distributor """
    
    # Setup rewards and points
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Build points
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=1000)
    
    # Deploy a new loot distributor (with ripeStakeRatio and ripeLockDuration)
    new_loot_distributor = boa.load("contracts/core/LootDistributor.vy", undy_hq, mock_ripe_token, mock_ripe, 80_00, 100)

    # Update undy hq with new loot distributor
    assert undy_hq.startAddressUpdateToRegistry(6, new_loot_distributor, sender=governance.address)
    boa.env.time_travel(blocks=undy_hq.registryChangeTimeLock())
    assert undy_hq.confirmAddressUpdateToRegistry(6, sender=governance.address)
    
    # Try to claim from old distributor - should fail
    with boa.reverts("not current loot distributor"):
        loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)


def test_claim_all_loot(loot_distributor, user_wallet, ambassador_wallet, alice, bob, alpha_token, alpha_token_whale, setUserWalletConfig, switchboard_alpha, setupClaimableLoot):
    """ Test claimAllLoot function that claims both rev share and deposit rewards """
    
    # Setup claimable loot for ambassador
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS)  # 50% = 50 tokens to ambassador
    
    # Setup deposit rewards
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    rewards_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Build up deposit points for ambassador wallet
    loot_distributor.updateDepositPointsWithNewValue(ambassador_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=ambassador_wallet.address)
    boa.env.time_travel(blocks=1000)
    loot_distributor.updateDepositPoints(ambassador_wallet.address, sender=switchboard_alpha.address)
    
    # Check initial balances
    initial_balance = alpha_token.balanceOf(ambassador_wallet)
    
    # Claim all loot (alice is the owner of ambassador wallet)
    result = loot_distributor.claimAllLoot(ambassador_wallet, sender=alice)
    assert result == True  # Should return True when something was claimed
    
    # Verify both rev share and deposit rewards were claimed
    final_balance = alpha_token.balanceOf(ambassador_wallet)
    assert final_balance > initial_balance + 50 * EIGHTEEN_DECIMALS  # Got both rev share and deposit rewards
    
    # Verify loot is cleared
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == 0
    
    # Verify last claim was updated
    assert loot_distributor.lastClaim(ambassador_wallet) == boa.env.evm.patch.block_number


def test_claim_all_loot_nothing_available(loot_distributor, user_wallet, bob):
    """ Test claimAllLoot when no loot or rewards are available """
    
    # No loot setup, no deposit rewards setup
    # Should return False
    result = loot_distributor.claimAllLoot(user_wallet, sender=bob)
    assert result == False  # Nothing was claimed
    
    # Verify last claim was NOT updated
    assert loot_distributor.lastClaim(user_wallet) == 0


def test_loot_claim_cool_off_period(loot_distributor, ambassador_wallet, alice, alpha_token, alpha_token_whale, setUserWalletConfig, setupClaimableLoot):
    """ Test that cool-off period prevents immediate re-claiming """
    
    # Setup claimable loot for ambassador
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS, token=alpha_token, token_whale=alpha_token_whale)
    
    # Set cool-off period to 100 blocks
    setUserWalletConfig(_lootClaimCoolOffPeriod=100)
    
    # Verify ambassador can claim initially
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == True
    
    # First claim should succeed
    loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
    # Immediately after claim, validation should fail due to cool-off
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == False
    
    # Trying to claim again should fail
    with boa.reverts("no perms"):
        loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
    # Travel 50 blocks (still within cool-off period)
    boa.env.time_travel(blocks=50)
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == False
    
    # Travel to one block before cool-off period ends
    boa.env.time_travel(blocks=49)  # Total 99 blocks
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == False  # Still can't claim
    
    # Travel to exactly the cool-off period boundary
    boa.env.time_travel(blocks=1)  # Total 100 blocks
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == True  # Can claim at boundary
    
    # Add more loot and claim again
    setupClaimableLoot(50 * EIGHTEEN_DECIMALS, token=alpha_token, token_whale=alpha_token_whale)
    loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
    # Cool-off period should apply again
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == False


def test_loot_claim_cool_off_period_zero(loot_distributor, ambassador_wallet, alice, alpha_token, alpha_token_whale, setUserWalletConfig, setupClaimableLoot):
    """ Test that zero cool-off period allows immediate re-claiming """
    
    # Setup claimable loot for ambassador
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS, token=alpha_token, token_whale=alpha_token_whale)
    
    # Set cool-off period to 0 (no cool-off)
    setUserWalletConfig(_lootClaimCoolOffPeriod=0)
    
    # First claim
    loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
    # With zero cool-off, validation should still pass
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == True
    
    # Add more loot
    setupClaimableLoot(50 * EIGHTEEN_DECIMALS, token=alpha_token, token_whale=alpha_token_whale)
    
    # Should be able to claim again immediately
    loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
    # And validation should still pass
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == True


def test_loot_claim_cool_off_applies_to_all_claim_functions(loot_distributor, user_wallet, ambassador_wallet, alice, bob, alpha_token, alpha_token_whale, setUserWalletConfig, switchboard_alpha, setupClaimableLoot):
    """ Test that cool-off period applies to all claim functions (claimRevShareAndBonusLoot, claimDepositRewards, claimAllLoot) """
    
    # Setup both rev share loot for ambassador and deposit rewards for user
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS, token=alpha_token, token_whale=alpha_token_whale)
    
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address, _lootClaimCoolOffPeriod=50)
    alpha_token.approve(loot_distributor.address, 500 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, 500 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # Build deposit points for user wallet
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=1000)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Test cool-off for ambassador (has rev share)
    assert loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice) > 0
    
    # Ambassador should be blocked by cool-off
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == False
    with boa.reverts("no perms"):
        loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
    # Test cool-off for user wallet (has deposit rewards)
    assert loot_distributor.claimDepositRewards(user_wallet, sender=bob) > 0
    
    # User should be blocked by cool-off
    assert loot_distributor.validateCanClaimLoot(user_wallet, bob) == False
    with boa.reverts("no perms"):
        loot_distributor.claimDepositRewards(user_wallet, sender=bob)
    
    # Travel past cool-off period
    boa.env.time_travel(blocks=51)
    
    # Both should be able to claim again
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == True
    assert loot_distributor.validateCanClaimLoot(user_wallet, bob) == True
    
    # Test claimAllLoot with ambassador
    setupClaimableLoot(50 * EIGHTEEN_DECIMALS, token=alpha_token, token_whale=alpha_token_whale)
    assert loot_distributor.claimAllLoot(ambassador_wallet, sender=alice) == True
    
    # Cool-off should apply again
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, alice) == False


def test_claim_deposit_rewards_twice(loot_distributor, user_wallet, ambassador_wallet, bob, alpha_token, alpha_token_whale, setUserWalletConfig, switchboard_alpha, hatchery, charlie, ledger):
    """ Test user cannot claim rewards twice """
    
    # Create another wallet to ensure global points remain
    another_wallet_addr = hatchery.createUserWallet(charlie, ambassador_wallet, False, 1, sender=charlie)
    another_wallet = UserWallet.at(another_wallet_addr)
    
    # Setup rewards and points
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor.address, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token.address, rewards_amount, sender=alpha_token_whale)
    
    # Build points for both wallets
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    loot_distributor.updateDepositPointsWithNewValue(another_wallet.address, 100 * EIGHTEEN_DECIMALS, sender=another_wallet.address)
    boa.env.time_travel(blocks=1000)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    loot_distributor.updateDepositPoints(another_wallet.address, sender=switchboard_alpha.address)
    
    # First claim succeeds
    loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    
    # Verify user's points are now 0
    user_points, global_points = ledger.getUserAndGlobalPoints(user_wallet.address)
    assert user_points.depositPoints == 0
    assert global_points.depositPoints > 0  # Global points remain due to another_wallet
    
    # Second claim should fail because user has no points
    with boa.reverts("nothing to claim"):
        loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)


########################
# Adjust Loot (Admin) #
########################


def test_adjust_loot_basic(loot_distributor, ambassador_wallet, alice, alpha_token, alpha_token_whale, switchboard_alpha, setupClaimableLoot):
    """ Test basic adjustLoot functionality for reducing cheater's claimable loot """
    
    # Setup claimable loot
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS, token=alpha_token, token_whale=alpha_token_whale)
    
    # Verify initial state
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == 50 * EIGHTEEN_DECIMALS  # 50% rev share
    assert loot_distributor.totalClaimableLoot(alpha_token) == 50 * EIGHTEEN_DECIMALS
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 2  # Starting from 1
    
    # Non-admin cannot adjust (will revert)
    with boa.reverts("no perms"):
        loot_distributor.adjustLoot(ambassador_wallet, alpha_token, 10 * EIGHTEEN_DECIMALS, sender=alice)
    
    # Admin reduces claimable amount (cheater caught!)
    new_amount = 10 * EIGHTEEN_DECIMALS
    result = loot_distributor.adjustLoot(ambassador_wallet, alpha_token, new_amount, sender=switchboard_alpha.address)
    assert result == True
    
    # Verify updated state
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == new_amount
    assert loot_distributor.totalClaimableLoot(alpha_token) == new_amount
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 2  # Still registered
    
    # User can still claim the reduced amount
    loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    assert alpha_token.balanceOf(ambassador_wallet) == new_amount


def test_adjust_loot_zero_and_deregistration(loot_distributor, ambassador_wallet, alice, alpha_token, bravo_token, alpha_token_whale, bravo_token_whale, switchboard_alpha, setupClaimableLoot):
    """ Test adjustLoot to zero removes asset registration and edge cases """
    
    # Setup claimable loot for two tokens
    setupClaimableLoot(100 * EIGHTEEN_DECIMALS, token=alpha_token, token_whale=alpha_token_whale)
    setupClaimableLoot(200 * EIGHTEEN_DECIMALS, token=bravo_token, token_whale=bravo_token_whale)
    
    # Verify initial state
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == 50 * EIGHTEEN_DECIMALS
    assert loot_distributor.claimableLoot(ambassador_wallet, bravo_token) == 100 * EIGHTEEN_DECIMALS
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 3  # Starting from 1, so 1 + 2 assets
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 1
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, bravo_token) == 2
    
    # Cannot adjust up (only down)
    result = loot_distributor.adjustLoot(ambassador_wallet, alpha_token, 60 * EIGHTEEN_DECIMALS, sender=switchboard_alpha.address)
    assert result == False
    
    # Cannot adjust if no claimable amount
    result = loot_distributor.adjustLoot(alice, alpha_token, 0, sender=switchboard_alpha.address)  # alice has no loot
    assert result == False
    
    # Adjust alpha to zero (complete removal)
    result = loot_distributor.adjustLoot(ambassador_wallet, alpha_token, 0, sender=switchboard_alpha.address)
    assert result == True
    
    # Verify alpha was deregistered
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == 0
    assert loot_distributor.totalClaimableLoot(alpha_token) == 0
    assert loot_distributor.numClaimableAssets(ambassador_wallet) == 2  # One less asset
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, alpha_token) == 0  # Deregistered
    
    # Bravo should have moved to index 1
    assert loot_distributor.indexOfClaimableAsset(ambassador_wallet, bravo_token) == 1
    assert loot_distributor.claimableAssets(ambassador_wallet, 1) == bravo_token.address
    
    # Cannot adjust already zero amount
    result = loot_distributor.adjustLoot(ambassador_wallet, alpha_token, 0, sender=switchboard_alpha.address)
    assert result == False
    
    # Test with empty addresses
    result = loot_distributor.adjustLoot(ZERO_ADDRESS, alpha_token, 0, sender=switchboard_alpha.address)
    assert result == False
    result = loot_distributor.adjustLoot(ambassador_wallet, ZERO_ADDRESS, 0, sender=switchboard_alpha.address)
    assert result == False


#################################
# Security & Permission Checks #
#################################


def test_manager_can_claim_loot_with_permission(loot_distributor, high_command, user_wallet, bob, charlie, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, mock_yield_lego, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, setAssetConfig, createAssetYieldConfig):
    """ Test that a manager with canClaimLoot permission can claim loot """
    
    # Configure yield asset with bonus
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _bonusRatio=30_00,  # 30% bonus for user
    )
    setAssetConfig(yield_vault_token, _yieldConfig=yieldConfig)
    
    # Seed loot distributor with underlying tokens for bonus payments
    yield_underlying_token.transfer(loot_distributor, 500 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Setup yield scenario to generate claimable loot for user_wallet
    yield_underlying_token.approve(mock_yield_lego, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(yield_underlying_token, 1000 * EIGHTEEN_DECIMALS, yield_vault_token, sender=yield_underlying_token_whale)
    
    # Simulate yield profit that generates loot for user_wallet
    performance_fee = 10 * EIGHTEEN_DECIMALS
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        100 * EIGHTEEN_DECIMALS,  # total yield
        sender=user_wallet.address
    )
    
    # Add manager with canClaimLoot permission
    high_command.addManager(
        user_wallet.address,
        charlie,  # manager
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],  # allowed assets
        True,  # canClaimLoot = True
        sender=bob  # bob is the owner of user_wallet
    )
    
    # Verify manager can claim loot for user_wallet
    initial_balance = yield_underlying_token.balanceOf(user_wallet)
    result = loot_distributor.claimRevShareAndBonusLoot(user_wallet.address, sender=charlie)
    assert result == 1  # 1 asset claimed
    
    # Verify tokens were transferred to user_wallet
    assert yield_underlying_token.balanceOf(user_wallet) > initial_balance
    
    # Verify state updated
    assert loot_distributor.lastClaim(user_wallet) == boa.env.evm.patch.block_number


def test_manager_cannot_claim_loot_without_permission(loot_distributor, high_command, user_wallet, bob, charlie, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, mock_yield_lego, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, setAssetConfig, createAssetYieldConfig):
    """ Test that a manager without canClaimLoot permission cannot claim loot """
    
    # Configure yield asset with bonus
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _bonusRatio=30_00,  # 30% bonus for user
    )
    setAssetConfig(yield_vault_token, _yieldConfig=yieldConfig)
    
    # Seed loot distributor with underlying tokens for bonus payments
    yield_underlying_token.transfer(loot_distributor, 500 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Setup yield scenario to generate claimable loot for user_wallet
    yield_underlying_token.approve(mock_yield_lego, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(yield_underlying_token, 1000 * EIGHTEEN_DECIMALS, yield_vault_token, sender=yield_underlying_token_whale)
    
    # Simulate yield profit that generates loot for user_wallet
    performance_fee = 10 * EIGHTEEN_DECIMALS
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        100 * EIGHTEEN_DECIMALS,  # total yield
        sender=user_wallet.address
    )
    
    # Add manager WITHOUT canClaimLoot permission
    high_command.addManager(
        user_wallet.address,
        charlie,  # manager
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],  # allowed assets
        False,  # canClaimLoot = False
        sender=bob  # bob is the owner of user_wallet
    )
    
    # Verify manager cannot claim loot
    with boa.reverts("no perms"):
        loot_distributor.claimRevShareAndBonusLoot(user_wallet.address, sender=charlie)
    
    # Verify no state changes (loot is still there)
    assert loot_distributor.claimableLoot(user_wallet, yield_underlying_token) > 0
    assert loot_distributor.lastClaim(user_wallet) == 0


def test_manager_can_claim_deposit_rewards_with_permission(loot_distributor, high_command, user_wallet, user_wallet_config, bob, charlie, alpha_token, alpha_token_whale, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, setUserWalletConfig):
    """ Test that a manager with canClaimLoot permission can claim deposit rewards """
    
    # Set deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    
    # Add deposit rewards
    rewards_amount = 100 * EIGHTEEN_DECIMALS
    alpha_token.approve(loot_distributor, rewards_amount, sender=alpha_token_whale)
    loot_distributor.addDepositRewards(alpha_token, rewards_amount, sender=alpha_token_whale)
    
    # Update deposit points for the user_wallet
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=user_wallet_config.address)
    boa.env.time_travel(seconds=7 * 24 * 60 * 60)  # 7 days
    
    # Add manager with canClaimLoot permission
    high_command.addManager(
        user_wallet.address,
        charlie,  # manager
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],  # allowed assets
        True,  # canClaimLoot = True
        sender=bob  # bob is the owner of user_wallet
    )
    
    # Manager can claim deposit rewards
    initial_balance = alpha_token.balanceOf(user_wallet)
    result = loot_distributor.claimDepositRewards(user_wallet.address, sender=charlie)
    assert result > 0  # Some rewards claimed
    
    # Verify tokens were transferred
    assert alpha_token.balanceOf(user_wallet) > initial_balance
    assert loot_distributor.lastClaim(user_wallet) == boa.env.evm.patch.block_number


def test_manager_can_claim_all_loot_with_permission(loot_distributor, high_command, user_wallet, user_wallet_config, bob, charlie, bravo_token, bravo_token_whale, createManagerLimits, createLegoPerms, createWhitelistPerms, createTransferPerms, mock_yield_lego, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, setUserWalletConfig, setAssetConfig, createAssetYieldConfig):
    """ Test that a manager with canClaimLoot permission can claim all loot types """
    
    # Set deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=bravo_token.address)
    
    # Configure yield asset with bonus
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _bonusRatio=30_00,  # 30% bonus for user
    )
    setAssetConfig(yield_vault_token, _yieldConfig=yieldConfig)
    
    # Seed loot distributor with underlying tokens for bonus payments
    yield_underlying_token.transfer(loot_distributor, 500 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Setup yield scenario to generate claimable loot for user_wallet
    yield_underlying_token.approve(mock_yield_lego, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(yield_underlying_token, 1000 * EIGHTEEN_DECIMALS, yield_vault_token, sender=yield_underlying_token_whale)
    
    # Simulate yield profit that generates loot
    performance_fee = 10 * EIGHTEEN_DECIMALS
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        100 * EIGHTEEN_DECIMALS,  # total yield
        sender=user_wallet.address
    )
    
    # Setup deposit rewards
    rewards_amount = 50 * EIGHTEEN_DECIMALS
    bravo_token.approve(loot_distributor, rewards_amount, sender=bravo_token_whale)
    loot_distributor.addDepositRewards(bravo_token, rewards_amount, sender=bravo_token_whale)
    
    # Update deposit points
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=user_wallet_config.address)
    boa.env.time_travel(seconds=7 * 24 * 60 * 60)  # 7 days
    
    # Add manager with canClaimLoot permission
    high_command.addManager(
        user_wallet.address,
        charlie,  # manager
        createManagerLimits(),
        createLegoPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],  # allowed assets
        True,  # canClaimLoot = True
        sender=bob  # bob is the owner of user_wallet
    )
    
    # Manager can claim all loot
    initial_underlying_balance = yield_underlying_token.balanceOf(user_wallet)
    initial_bravo_balance = bravo_token.balanceOf(user_wallet)
    
    result = loot_distributor.claimAllLoot(user_wallet.address, sender=charlie)
    assert result == True
    
    # Verify both token types were claimed
    assert yield_underlying_token.balanceOf(user_wallet) > initial_underlying_balance
    assert bravo_token.balanceOf(user_wallet) > initial_bravo_balance
    assert loot_distributor.lastClaim(user_wallet) == boa.env.evm.patch.block_number


def test_only_user_wallets_can_add_loot(loot_distributor, alice, alpha_token, alpha_token_whale, switchboard_alpha):
    """ Test that only user wallets can call addLootFromSwapOrRewards and addLootFromYieldProfit """
    
    # Fund non-wallet addresses
    alpha_token.transfer(alice, 100 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    alpha_token.transfer(switchboard_alpha.address, 100 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
    
    # Non-wallet cannot add loot from swap/rewards
    alpha_token.approve(loot_distributor, 10 * EIGHTEEN_DECIMALS, sender=alice)
    with boa.reverts("not a user wallet"):
        loot_distributor.addLootFromSwapOrRewards(
            alpha_token,
            10 * EIGHTEEN_DECIMALS,
            ACTION_TYPE.SWAP,
            sender=alice
        )
    
    # Non-wallet cannot add loot from yield profit
    with boa.reverts("not a user wallet"):
        loot_distributor.addLootFromYieldProfit(
            alpha_token,
            5 * EIGHTEEN_DECIMALS,
            50 * EIGHTEEN_DECIMALS,
            sender=alice
        )
    
    # Even switchboard cannot add loot (not a user wallet)
    alpha_token.approve(loot_distributor, 10 * EIGHTEEN_DECIMALS, sender=switchboard_alpha.address)
    with boa.reverts("not a user wallet"):
        loot_distributor.addLootFromSwapOrRewards(
            alpha_token,
            10 * EIGHTEEN_DECIMALS,
            ACTION_TYPE.REWARDS,
            sender=switchboard_alpha.address
        )


###############################
# RIPE Token Incentives Tests #
###############################


def test_ripe_token_as_deposit_rewards_asset(loot_distributor, user_wallet, bob, mock_ripe_token, governance, setUserWalletConfig, mock_ripe, switchboard_alpha):
    """ Test using RIPE token as deposit rewards asset """
    
    # Set mock_ripe price for RIPE token
    mock_ripe.setPrice(mock_ripe_token.address, 2 * EIGHTEEN_DECIMALS)  # $2 per RIPE
    
    # Configure RIPE token as deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=mock_ripe_token.address)
    
    # Add RIPE token rewards (governance has initial supply)
    rewards_amount = 5000 * EIGHTEEN_DECIMALS
    mock_ripe_token.approve(loot_distributor.address, rewards_amount, sender=governance.address)
    loot_distributor.addDepositRewards(mock_ripe_token.address, rewards_amount, sender=governance.address)
    
    # Build up deposit points for user
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    
    # Travel blocks to accumulate points
    boa.env.time_travel(blocks=2000)
    
    # Update points to finalize accumulation
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Claim rewards (should go through mock_ripe's depositIntoGovVault)
    user_rewards = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)

    # With 80% stake ratio: 80% staked, 20% sent directly
    assert user_rewards > 0
    staked_amount = user_rewards * 80_00 // 100_00
    direct_amount = user_rewards * 20_00 // 100_00

    # Verify 80% was staked in mock_ripe (acting as RipeTeller)
    assert mock_ripe_token.balanceOf(mock_ripe.address) == staked_amount

    # Verify 20% was sent directly to user wallet
    assert mock_ripe_token.balanceOf(user_wallet.address) == direct_amount

    # Verify rewards were deducted from deposit rewards
    rewards = loot_distributor.depositRewards()
    assert rewards.asset == mock_ripe_token.address
    assert rewards.amount == rewards_amount - user_rewards


def test_ripe_token_as_yield_alt_bonus_asset(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_ripe_token, governance, mock_yield_lego, mock_ripe, setUserWalletConfig, createAmbassadorRevShare):
    """ Test using RIPE token as default yield alt bonus asset """
    
    # Set mock_ripe price for RIPE token and yield underlying
    mock_ripe.setPrice(mock_ripe_token.address, 1 * EIGHTEEN_DECIMALS)  # $1 per RIPE
    mock_ripe.setPrice(yield_underlying_token.address, 10 * EIGHTEEN_DECIMALS)  # $10 per underlying
    
    # Transfer RIPE tokens to loot distributor for bonuses
    ripe_balance = 10000 * EIGHTEEN_DECIMALS
    mock_ripe_token.transfer(loot_distributor.address, ripe_balance, sender=governance.address)
    
    # Create ambassador rev share with all zeros (not testing rev share)
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=0,
        _rewardsRatio=0,
        _yieldRatio=0,
    )
    
    # Configure RIPE token as default yield alt bonus asset globally
    setUserWalletConfig(
        _ambassadorRevShare=ambassadorRevShare,
        _defaultYieldBonusRatio=20_00,  # 20% user bonus
        _defaultYieldAmbassadorBonusRatio=10_00,  # 10% ambassador bonus
        _defaultYieldAltBonusAsset=mock_ripe_token.address,  # RIPE as bonus asset
    )
    
    # Register vault token by making a deposit
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego.address, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token.address,
        deposit_amount,
        yield_vault_token.address,
        sender=yield_underlying_token_whale,
    )
    
    # Transfer vault tokens to user wallet
    vault_balance = 100 * EIGHTEEN_DECIMALS
    yield_vault_token.transfer(user_wallet.address, vault_balance, sender=yield_underlying_token_whale)
    
    # Simulate yield profit (100 underlying tokens profit)
    yield_profit = 100 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(loot_distributor.address, yield_profit, sender=yield_underlying_token_whale)
    
    # Call addLootFromYieldProfit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token.address,
        0,  # zero fee
        yield_profit,  # yield realized
        sender=user_wallet.address,
    )
    
    # Calculate expected RIPE bonus amounts
    # Yield profit value: 100 tokens * $10 = $1000
    # User bonus: $1000 * 20% = $200 worth of RIPE = 200 RIPE tokens
    # Ambassador bonus: $1000 * 10% = $100 worth of RIPE = 100 RIPE tokens
    
    # Check user's claimable RIPE
    user_claimable = loot_distributor.claimableLoot(user_wallet.address, mock_ripe_token.address)
    assert user_claimable == 200 * EIGHTEEN_DECIMALS
    
    # Check ambassador's claimable RIPE
    ambassador_claimable = loot_distributor.claimableLoot(ambassador_wallet.address, mock_ripe_token.address)
    assert ambassador_claimable == 100 * EIGHTEEN_DECIMALS
    
    # Get wallet owners for claiming
    user_wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    ambassador_wallet_config = UserWalletConfig.at(ambassador_wallet.walletConfig())
    
    # Check initial mock_ripe balance
    initial_ripe_balance = mock_ripe_token.balanceOf(mock_ripe.address)
    
    # User claims their RIPE bonus (200 RIPE total: 80% staked, 20% direct)
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(user_wallet.address, sender=user_wallet_config.owner())
    assert assets_claimed == 1  # Should have claimed 1 asset type (RIPE)

    # Verify 80% of user RIPE (160 RIPE) went to mock_ripe for staking
    user_staked = 200 * EIGHTEEN_DECIMALS * 80_00 // 100_00
    assert mock_ripe_token.balanceOf(mock_ripe.address) == initial_ripe_balance + user_staked

    # Verify 20% of user RIPE (40 RIPE) sent directly to user wallet
    user_direct = 200 * EIGHTEEN_DECIMALS * 20_00 // 100_00
    assert mock_ripe_token.balanceOf(user_wallet.address) == user_direct

    # Verify user's claimable is now zero
    assert loot_distributor.claimableLoot(user_wallet.address, mock_ripe_token.address) == 0

    # Ambassador claims their RIPE bonus (100 RIPE total: 80% staked, 20% direct)
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet.address, sender=ambassador_wallet_config.owner())
    assert assets_claimed == 1

    # Verify 80% of ambassador RIPE (80 RIPE) went to mock_ripe for staking
    ambassador_staked = 100 * EIGHTEEN_DECIMALS * 80_00 // 100_00
    total_staked = user_staked + ambassador_staked
    assert mock_ripe_token.balanceOf(mock_ripe.address) == initial_ripe_balance + total_staked

    # Verify 20% of ambassador RIPE (20 RIPE) sent directly to ambassador wallet
    ambassador_direct = 100 * EIGHTEEN_DECIMALS * 20_00 // 100_00
    assert mock_ripe_token.balanceOf(ambassador_wallet.address) == ambassador_direct

    # Verify ambassador's claimable is now zero
    assert loot_distributor.claimableLoot(ambassador_wallet.address, mock_ripe_token.address) == 0


def test_ripe_token_yield_bonus_user_only(loot_distributor, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_ripe_token, governance, mock_yield_lego, mock_ripe, setAssetConfig, createAssetYieldConfig, hatchery, charlie):
    """ Test RIPE token yield bonus for user only (no ambassador) """
    
    # Create user wallet without ambassador
    user_wallet_addr = hatchery.createUserWallet(charlie, ZERO_ADDRESS, False, 1, sender=charlie)
    user_wallet = UserWallet.at(user_wallet_addr)
    
    # Set mock_ripe prices
    mock_ripe.setPrice(mock_ripe_token.address, EIGHTEEN_DECIMALS // 2)  # $0.50 per RIPE
    mock_ripe.setPrice(yield_underlying_token.address, 20 * EIGHTEEN_DECIMALS)  # $20 per underlying
    
    # Transfer RIPE tokens to loot distributor
    mock_ripe_token.transfer(loot_distributor.address, 50000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Create yield config with RIPE as alt bonus asset (asset-specific config)
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _bonusRatio=30_00,  # 30% user bonus
        _ambassadorBonusRatio=0,  # No ambassador bonus
        _altBonusAsset=mock_ripe_token.address,
    )
    
    # Set asset config for vault token
    setAssetConfig(
        yield_vault_token,
        _yieldConfig=yieldConfig,
    )
    
    # Register vault token
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego.address, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token.address,
        deposit_amount,
        yield_vault_token.address,
        sender=yield_underlying_token_whale,
    )
    
    # Transfer vault tokens to user wallet
    yield_vault_token.transfer(user_wallet.address, 50 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Simulate yield profit
    yield_profit = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(loot_distributor.address, yield_profit, sender=yield_underlying_token_whale)
    
    # Call addLootFromYieldProfit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token.address,
        0,  # zero fee
        yield_profit,
        sender=user_wallet.address,
    )
    
    # Calculate expected RIPE bonus
    # Yield profit value: 50 tokens * $20 = $1000
    # User bonus: $1000 * 30% = $300 worth of RIPE = 600 RIPE tokens (at $0.50 each)
    
    user_claimable = loot_distributor.claimableLoot(user_wallet.address, mock_ripe_token.address)
    assert user_claimable == 600 * EIGHTEEN_DECIMALS
    
    # Check initial mock_ripe balance
    initial_ripe_balance = mock_ripe_token.balanceOf(mock_ripe.address)
    
    # User claims their RIPE bonus (600 RIPE total: 80% staked, 20% direct)
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(user_wallet.address, sender=charlie)
    assert assets_claimed == 1  # Should have claimed 1 asset type (RIPE)

    # Verify 80% of RIPE (480 RIPE) went to mock_ripe for staking
    staked_amount = 600 * EIGHTEEN_DECIMALS * 80_00 // 100_00
    assert mock_ripe_token.balanceOf(mock_ripe.address) == initial_ripe_balance + staked_amount

    # Verify 20% of RIPE (120 RIPE) sent directly to user wallet
    direct_amount = 600 * EIGHTEEN_DECIMALS * 20_00 // 100_00
    assert mock_ripe_token.balanceOf(user_wallet.address) == direct_amount

    # Verify user's claimable is now zero
    assert loot_distributor.claimableLoot(user_wallet.address, mock_ripe_token.address) == 0

    # Verify loot distributor balance decreased by full amount (600 RIPE total)
    assert mock_ripe_token.balanceOf(loot_distributor.address) == 50000 * EIGHTEEN_DECIMALS - 600 * EIGHTEEN_DECIMALS


def test_ripe_token_yield_bonus_ambassador_zero_rev_share(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_ripe_token, governance, mock_yield_lego, mock_ripe, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test RIPE token yield bonus for ambassador with zero rev share """
    
    # Set mock_ripe prices
    mock_ripe.setPrice(mock_ripe_token.address, 4 * EIGHTEEN_DECIMALS)  # $4 per RIPE
    mock_ripe.setPrice(yield_underlying_token.address, 100 * EIGHTEEN_DECIMALS)  # $100 per underlying
    
    # Transfer RIPE tokens to loot distributor
    mock_ripe_token.transfer(loot_distributor.address, 20000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Create ambassador rev share with all zeros
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=0,
        _rewardsRatio=0,
        _yieldRatio=0,  # Zero yield rev share
    )
    
    # Create yield config with RIPE as alt bonus asset and ambassador bonus
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _bonusRatio=15_00,  # 15% user bonus
        _ambassadorBonusRatio=25_00,  # 25% ambassador bonus (higher than user!)
        _altBonusAsset=mock_ripe_token.address,
    )
    
    # Set asset config
    setAssetConfig(
        yield_vault_token,
        _ambassadorRevShare=ambassadorRevShare,
        _yieldConfig=yieldConfig,
    )
    
    # Register vault token
    deposit_amount = 500 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego.address, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(
        yield_underlying_token.address,
        deposit_amount,
        yield_vault_token.address,
        sender=yield_underlying_token_whale,
    )
    
    # Transfer vault tokens to user wallet
    yield_vault_token.transfer(user_wallet.address, 25 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # Simulate yield profit
    yield_profit = 10 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(loot_distributor.address, yield_profit, sender=yield_underlying_token_whale)
    
    # Call addLootFromYieldProfit with zero fee (testing bonus only)
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token.address,
        0,  # zero fee (no rev share)
        yield_profit,
        sender=user_wallet.address,
    )
    
    # Calculate expected RIPE bonuses
    # Yield profit value: 10 tokens * $100 = $1000
    # User bonus: $1000 * 15% = $150 worth of RIPE = 37.5 RIPE tokens
    # Ambassador bonus: $1000 * 25% = $250 worth of RIPE = 62.5 RIPE tokens
    
    user_claimable = loot_distributor.claimableLoot(user_wallet.address, mock_ripe_token.address)
    assert user_claimable == 375 * EIGHTEEN_DECIMALS // 10  # 37.5 RIPE
    
    ambassador_claimable = loot_distributor.claimableLoot(ambassador_wallet.address, mock_ripe_token.address)
    assert ambassador_claimable == 625 * EIGHTEEN_DECIMALS // 10  # 62.5 RIPE
    
    # Verify no rev share was taken (only bonuses distributed)
    assert loot_distributor.claimableLoot(ambassador_wallet.address, yield_vault_token.address) == 0
    
    # Get wallet owners for claiming
    user_wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    ambassador_wallet_config = UserWalletConfig.at(ambassador_wallet.walletConfig())
    
    # Check initial mock_ripe balance
    initial_ripe_balance = mock_ripe_token.balanceOf(mock_ripe.address)
    
    # User claims their RIPE bonus (37.5 RIPE total: 80% staked, 20% direct)
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(user_wallet.address, sender=user_wallet_config.owner())
    assert assets_claimed == 1

    # Verify 80% of user RIPE (30 RIPE) went to mock_ripe for staking
    expected_user_amount = 375 * EIGHTEEN_DECIMALS // 10
    user_staked = expected_user_amount * 80_00 // 100_00
    assert mock_ripe_token.balanceOf(mock_ripe.address) == initial_ripe_balance + user_staked

    # Verify 20% of user RIPE (7.5 RIPE) sent directly to user wallet
    user_direct = expected_user_amount * 20_00 // 100_00
    assert mock_ripe_token.balanceOf(user_wallet.address) == user_direct

    # Ambassador claims their RIPE bonus (62.5 RIPE total: 80% staked, 20% direct)
    assets_claimed = loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet.address, sender=ambassador_wallet_config.owner())
    assert assets_claimed == 1

    # Verify 80% of ambassador RIPE (50 RIPE) went to mock_ripe for staking
    expected_ambassador_amount = 625 * EIGHTEEN_DECIMALS // 10
    ambassador_staked = expected_ambassador_amount * 80_00 // 100_00
    total_staked = user_staked + ambassador_staked
    assert mock_ripe_token.balanceOf(mock_ripe.address) == initial_ripe_balance + total_staked

    # Verify 20% of ambassador RIPE (12.5 RIPE) sent directly to ambassador wallet
    ambassador_direct = expected_ambassador_amount * 20_00 // 100_00
    assert mock_ripe_token.balanceOf(ambassador_wallet.address) == ambassador_direct

    # Verify both users' claimable is now zero
    assert loot_distributor.claimableLoot(user_wallet.address, mock_ripe_token.address) == 0
    assert loot_distributor.claimableLoot(ambassador_wallet.address, mock_ripe_token.address) == 0
    
    # Verify no yield vault tokens were claimed (only RIPE bonuses)
    assert loot_distributor.claimableLoot(ambassador_wallet.address, yield_vault_token.address) == 0


def test_ripe_token_deposit_rewards_with_multiple_users(loot_distributor, user_wallet, ambassador_wallet, mock_ripe_token, governance, setUserWalletConfig, mock_ripe, hatchery, charlie, sally, switchboard_alpha):
    """ Test RIPE token deposit rewards distributed among multiple users """
    
    # Create additional user wallet
    wallet2_addr = hatchery.createUserWallet(sally, ambassador_wallet, False, 1, sender=sally)
    wallet2 = UserWallet.at(wallet2_addr)
    
    # Set mock_ripe price
    mock_ripe.setPrice(mock_ripe_token.address, 5 * EIGHTEEN_DECIMALS)  # $5 per RIPE
    
    # Configure RIPE as deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=mock_ripe_token.address)
    
    # Add significant RIPE rewards
    rewards_amount = 10000 * EIGHTEEN_DECIMALS
    mock_ripe_token.approve(loot_distributor.address, rewards_amount, sender=governance.address)
    loot_distributor.addDepositRewards(mock_ripe_token.address, rewards_amount, sender=governance.address)
    
    # Build deposit points for user1 (smaller deposit)
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 500 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    
    # Build deposit points for user2 (larger deposit)
    loot_distributor.updateDepositPointsWithNewValue(wallet2.address, 1500 * EIGHTEEN_DECIMALS, sender=wallet2.address)
    
    # Travel blocks to accumulate points
    boa.env.time_travel(blocks=1000)
    
    # Update points
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    loot_distributor.updateDepositPoints(wallet2.address, sender=switchboard_alpha.address)
    
    # Get the owners of the wallets
    user_wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet2_config = UserWalletConfig.at(wallet2.walletConfig())
    
    # User1 claims RIPE rewards (using the actual owner)
    user1_rewards = loot_distributor.claimDepositRewards(user_wallet.address, sender=user_wallet_config.owner())

    # User2 claims RIPE rewards (using the actual owner)
    user2_rewards = loot_distributor.claimDepositRewards(wallet2.address, sender=wallet2_config.owner())

    # Verify proportional distribution
    # User1 had 25% of total value (500 / 2000)
    # User2 had 75% of total value (1500 / 2000)
    assert user1_rewards == 2500 * EIGHTEEN_DECIMALS  # 25% of 10000
    assert user2_rewards == 7500 * EIGHTEEN_DECIMALS  # 75% of 10000

    # With 80% stake ratio: calculate staked and direct amounts
    user1_staked = user1_rewards * 80_00 // 100_00  # 2000 RIPE
    user1_direct = user1_rewards * 20_00 // 100_00   # 500 RIPE
    user2_staked = user2_rewards * 80_00 // 100_00  # 6000 RIPE
    user2_direct = user2_rewards * 20_00 // 100_00   # 1500 RIPE

    # Verify 80% of total RIPE (8000 RIPE) went to mock_ripe for staking
    assert mock_ripe_token.balanceOf(mock_ripe.address) == user1_staked + user2_staked

    # Verify 20% sent directly to user wallets
    assert mock_ripe_token.balanceOf(user_wallet.address) == user1_direct
    assert mock_ripe_token.balanceOf(wallet2.address) == user2_direct


def test_loot_adjusted_event(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, switchboard_alpha, setAssetConfig, createAmbassadorRevShare):
    """ Test LootAdjusted event emission """
    
    # Set up ambassador config with swap fee share
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,      # 30%
        _rewardsRatio=25_00,   # 25%
        _yieldRatio=20_00,     # 20%
    )
    
    setAssetConfig(
        alpha_token,
        _ambassadorRevShare=ambassadorRevShare,
    )
    
    # First, add some loot for the ambassador
    fee_amount = 100 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor, fee_amount, sender=user_wallet.address)
    
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    # Get initial claimable amount
    initial_claimable = loot_distributor.claimableLoot(ambassador_wallet, alpha_token)
    assert initial_claimable > 0
    
    # Adjust loot down (only switchboard can do this)
    new_claimable = initial_claimable // 2  # Reduce by half
    loot_distributor.adjustLoot(
        ambassador_wallet,
        alpha_token,
        new_claimable,
        sender=switchboard_alpha.address
    )
    
    # Check LootAdjusted event
    event = filter_logs(loot_distributor, 'LootAdjusted')[0]
    assert event.user == ambassador_wallet.address
    assert event.asset == alpha_token.address
    assert event.newClaimable == new_claimable
    
    # Verify the adjustment took effect
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == new_claimable


def test_loot_claimed_event(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, alice, setAssetConfig, createAmbassadorRevShare):
    """ Test LootClaimed event emission """
    
    # Set up ambassador config with swap fee share
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,      # 30%
        _rewardsRatio=25_00,   # 25%
        _yieldRatio=20_00,     # 20%
    )
    
    setAssetConfig(
        alpha_token,
        _ambassadorRevShare=ambassadorRevShare,
    )
    
    # Add some loot for the ambassador
    fee_amount = 100 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor, fee_amount, sender=user_wallet.address)
    
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    # Get claimable amount
    claimable = loot_distributor.claimableLoot(ambassador_wallet, alpha_token)
    assert claimable > 0
    
    # Claim the loot
    loot_distributor.claimRevShareAndBonusLoot(ambassador_wallet, sender=alice)
    
    # Check LootClaimed event
    event = filter_logs(loot_distributor, 'LootClaimed')[0]
    assert event.user == ambassador_wallet.address
    assert event.asset == alpha_token.address
    assert event.amount > 0  # Should have claimed something
    
    # Verify claim was successful
    assert loot_distributor.claimableLoot(ambassador_wallet, alpha_token) == 0


def test_ripe_lock_duration_set_event(loot_distributor, switchboard_alpha):
    """ Test RipeRewardsConfigSet event emission """

    # Set new ripe rewards config
    new_stake_ratio = 90_00  # 90%
    new_duration = 86400  # 1 day in blocks
    loot_distributor.setRipeRewardsConfig(new_stake_ratio, new_duration, sender=switchboard_alpha.address)

    # Check RipeRewardsConfigSet event
    event = filter_logs(loot_distributor, 'RipeRewardsConfigSet')[0]
    assert event.ripeStakeRatio == new_stake_ratio
    assert event.ripeLockDuration == new_duration

    # Verify the changes took effect
    assert loot_distributor.ripeStakeRatio() == new_stake_ratio
    assert loot_distributor.ripeLockDuration() == new_duration


def test_get_claimable_loot_for_asset(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, setAssetConfig, createAmbassadorRevShare):
    """ Test getClaimableLootForAsset view function """
    
    # Initially should be 0
    assert loot_distributor.getClaimableLootForAsset(ambassador_wallet, alpha_token) == 0
    
    # Set up ambassador config with swap fee share
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,      # 30%
        _rewardsRatio=25_00,   # 25%
        _yieldRatio=20_00,     # 20%
    )
    
    setAssetConfig(
        alpha_token,
        _ambassadorRevShare=ambassadorRevShare,
    )
    
    # Add some loot
    fee_amount = 100 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor, fee_amount, sender=user_wallet.address)
    
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    # Should now return the claimable amount (limited by balance)
    claimable = loot_distributor.getClaimableLootForAsset(ambassador_wallet, alpha_token)
    assert claimable > 0
    assert claimable <= alpha_token.balanceOf(loot_distributor)
    
    # Test when contract has less balance than claimable
    # Transfer most tokens out, leaving only 1 token
    current_balance = alpha_token.balanceOf(loot_distributor)
    assert current_balance > EIGHTEEN_DECIMALS  # Should have more than 1 token from the fee added above
    alpha_token.transfer(alpha_token_whale, current_balance - EIGHTEEN_DECIMALS, sender=loot_distributor.address)
    
    # Should return the limited amount (what's actually in the contract)
    limited_claimable = loot_distributor.getClaimableLootForAsset(ambassador_wallet, alpha_token)
    assert limited_claimable == EIGHTEEN_DECIMALS


def test_get_claimable_deposit_rewards(loot_distributor, user_wallet, mock_ripe_token, setUserWalletConfig, governance):
    """ Test getClaimableDepositRewards view function """
    
    # Set deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=mock_ripe_token.address)
    
    # Initially should be 0
    assert loot_distributor.getClaimableDepositRewards(user_wallet) == 0
    
    # Add deposit rewards (use governance as it's a minter)
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    mock_ripe_token.approve(loot_distributor, rewards_amount, sender=governance.address)
    loot_distributor.addDepositRewards(mock_ripe_token, rewards_amount, sender=governance.address)
    
    # Update deposit points for the user
    loot_distributor.updateDepositPointsWithNewValue(user_wallet, 1000 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    
    # Advance blocks to accumulate points
    boa.env.time_travel(blocks=100)
    
    # Should now have claimable rewards
    claimable = loot_distributor.getClaimableDepositRewards(user_wallet)
    assert claimable > 0


def test_get_swap_fee(loot_distributor, user_wallet, alpha_token, bravo_token, mission_control, setAssetConfig, createTxFees):
    """ Test getSwapFee view function """
    
    # Create tx fees with swap fee
    txFees = createTxFees(_swapFee=30)  # 0.3%
    
    # Set asset config with swap fees for bravo token (tokenOut)
    setAssetConfig(bravo_token, _txFees=txFees)
    
    # Get swap fee through loot distributor (should use bravo token's fee as tokenOut)
    fee = loot_distributor.getSwapFee(user_wallet, alpha_token, bravo_token)
    assert fee == 30
    
    # Test with explicit mission control address
    fee_explicit = loot_distributor.getSwapFee(user_wallet, alpha_token, bravo_token, mission_control.address)
    assert fee_explicit == 30
    
    # Test when swapping to alpha (which doesn't have config set)
    default_fee = loot_distributor.getSwapFee(user_wallet, bravo_token, alpha_token)
    assert default_fee >= 0  # Should return some default value


def test_get_rewards_fee(loot_distributor, user_wallet, alpha_token, mission_control, setAssetConfig, createTxFees):
    """ Test getRewardsFee view function """
    
    # Create tx fees with rewards fee
    txFees = createTxFees(_rewardsFee=50)  # 0.5%
    
    # Set asset config with rewards fee
    setAssetConfig(alpha_token, _txFees=txFees)
    
    # Get rewards fee through loot distributor
    fee = loot_distributor.getRewardsFee(user_wallet, alpha_token)
    assert fee == 50
    
    # Test with explicit mission control address
    fee_explicit = loot_distributor.getRewardsFee(user_wallet, alpha_token, mission_control.address)
    assert fee_explicit == 50
    
    # Test default fee for unset asset
    bravo_token = alpha_token  # Use same token for simplicity
    default_fee = loot_distributor.getRewardsFee(user_wallet, bravo_token)
    assert default_fee >= 0  # Should return some default value


def test_view_functions_comprehensive(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, setAssetConfig, createAmbassadorRevShare):
    """ Comprehensive test of all new view functions working together """
    
    # Set up ambassador config with rewards fee share
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,      # 30%
        _rewardsRatio=25_00,   # 25%
        _yieldRatio=20_00,     # 20%
    )
    
    setAssetConfig(
        alpha_token,
        _ambassadorRevShare=ambassadorRevShare,
    )
    
    # Add some loot
    fee_amount = 100 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor, fee_amount, sender=user_wallet.address)
    
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.REWARDS,
        sender=user_wallet.address
    )
    
    # Test all view functions
    assert loot_distributor.getClaimableLootForAsset(ambassador_wallet, alpha_token) > 0
    assert loot_distributor.getTotalClaimableAssets(ambassador_wallet) > 0
    assert loot_distributor.validateCanClaimLoot(ambassador_wallet, ambassador_wallet.address) == False  # Can't claim for self unless owner
    
    # Get latest deposit points
    points = loot_distributor.getLatestDepositPoints(1000 * EIGHTEEN_DECIMALS, 0)
    assert points >= 0
    
    # Get loot distro config
    config = loot_distributor.getLootDistroConfig(user_wallet, alpha_token, True)
    assert config.ambassador == ambassador_wallet.address
    assert config.decimals > 0



def test_update_deposit_points_on_ejection(loot_distributor, user_wallet, ledger, switchboard_alpha):
    """ Test updateDepositPointsOnEjection function """
    
    # Set initial deposit points with a specific value
    initial_value = 1000 * EIGHTEEN_DECIMALS
    loot_distributor.updateDepositPointsWithNewValue(user_wallet, initial_value, sender=user_wallet.address)
    
    # Verify initial state
    userData, _ = ledger.getUserAndGlobalPoints(user_wallet)
    assert userData.usdValue == initial_value
    initial_points = userData.depositPoints
    
    # Travel some blocks to accumulate points
    boa.env.time_travel(blocks=100)
    
    # Call updateDepositPointsOnEjection (only switchboard can call)
    loot_distributor.updateDepositPointsOnEjection(user_wallet, sender=switchboard_alpha.address)
    
    # Verify points were updated and user value set to 0
    userData, _ = ledger.getUserAndGlobalPoints(user_wallet)
    assert userData.usdValue == 0  # User value should be zeroed on ejection
    assert userData.depositPoints > initial_points  # Points should have increased from the time travel


def test_claim_all_loot_multiple_assets(loot_distributor, alpha_token, bravo_token, alpha_token_whale, bravo_token_whale, alice, setAssetConfig, createAmbassadorRevShare, hatchery, charlie):
    """ Test claimAllLoot with multiple different assets """
    
    # Create a fresh ambassador wallet for this test to avoid state from other tests
    fresh_ambassador = hatchery.createUserWallet(charlie, charlie, False, 0, sender=charlie)
    fresh_ambassador_wallet = UserWallet.at(fresh_ambassador)
    
    # Create a fresh user wallet with the new ambassador
    fresh_user = hatchery.createUserWallet(alice, fresh_ambassador_wallet, False, 1, sender=alice)
    fresh_user_wallet = UserWallet.at(fresh_user)
    
    # Set up ambassador config
    ambassadorRevShare = createAmbassadorRevShare(
        _swapRatio=30_00,      # 30%
        _rewardsRatio=25_00,   # 25%
        _yieldRatio=20_00,     # 20%
    )
    
    # Configure both tokens
    setAssetConfig(alpha_token, _ambassadorRevShare=ambassadorRevShare)
    setAssetConfig(bravo_token, _ambassadorRevShare=ambassadorRevShare)
    
    # Should start with no claimable assets
    assert loot_distributor.numClaimableAssets(fresh_ambassador_wallet) == 0
    
    # Add loot for alpha token
    fee_amount = 100 * EIGHTEEN_DECIMALS
    alpha_token.transfer(fresh_user_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor, fee_amount, sender=fresh_user_wallet.address)
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=fresh_user_wallet.address
    )
    
    # Add loot for bravo token
    bravo_token.transfer(fresh_user_wallet, fee_amount, sender=bravo_token_whale)
    bravo_token.approve(loot_distributor, fee_amount, sender=fresh_user_wallet.address)
    loot_distributor.addLootFromSwapOrRewards(
        bravo_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=fresh_user_wallet.address
    )
    
    # Should now have exactly 2 claimable assets (numClaimableAssets uses 1-based indexing, so 2 assets = 3)
    assert loot_distributor.numClaimableAssets(fresh_ambassador_wallet) == 3
    
    # Should have 30% of fees for each token (30% of 100 = 30)
    expected_per_token = 30 * EIGHTEEN_DECIMALS
    assert loot_distributor.claimableLoot(fresh_ambassador_wallet, alpha_token) == expected_per_token
    assert loot_distributor.claimableLoot(fresh_ambassador_wallet, bravo_token) == expected_per_token
    
    # Record initial balances
    initial_alpha = alpha_token.balanceOf(fresh_ambassador_wallet)
    initial_bravo = bravo_token.balanceOf(fresh_ambassador_wallet)
    
    # Claim all loot at once
    success = loot_distributor.claimAllLoot(fresh_ambassador_wallet, sender=charlie)
    assert success == True
    
    # Verify exact amounts were transferred
    assert alpha_token.balanceOf(fresh_ambassador_wallet) == initial_alpha + expected_per_token
    assert bravo_token.balanceOf(fresh_ambassador_wallet) == initial_bravo + expected_per_token
    
    # Should have no claimable loot left (numClaimableAssets might still be non-zero but claimable amounts should be 0)
    assert loot_distributor.claimableLoot(fresh_ambassador_wallet, alpha_token) == 0
    assert loot_distributor.claimableLoot(fresh_ambassador_wallet, bravo_token) == 0

###################################
# RIPE Stake Ratio Edge Case Tests
###################################


def test_ripe_stake_ratio_zero_percent(loot_distributor, user_wallet, bob, mock_ripe_token, governance, setUserWalletConfig, mock_ripe, switchboard_alpha):
    """ Test RIPE rewards with 0% stake ratio - all rewards sent directly to user """
    
    # Set ripe stake ratio to 0% (all direct, no staking)
    loot_distributor.setRipeRewardsConfig(0, 43200, sender=switchboard_alpha.address)
    assert loot_distributor.ripeStakeRatio() == 0
    
    # Configure RIPE as deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=mock_ripe_token.address)
    
    # Add RIPE rewards
    rewards_amount = 1000 * EIGHTEEN_DECIMALS
    mock_ripe_token.approve(loot_distributor.address, rewards_amount, sender=governance.address)
    loot_distributor.addDepositRewards(mock_ripe_token.address, rewards_amount, sender=governance.address)
    
    # Build deposit points
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 500 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=1000)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Claim rewards
    user_rewards = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    
    # With 0% stake ratio: ALL rewards sent directly to user wallet
    assert user_rewards > 0
    assert mock_ripe_token.balanceOf(user_wallet.address) == user_rewards
    
    # Verify NO RIPE went to mock_ripe for staking
    assert mock_ripe_token.balanceOf(mock_ripe.address) == 0


def test_ripe_stake_ratio_fifty_percent(loot_distributor, user_wallet, bob, mock_ripe_token, governance, setUserWalletConfig, mock_ripe, switchboard_alpha):
    """ Test RIPE rewards with 50% stake ratio - equal split between staking and direct """
    
    # Set ripe stake ratio to 50%
    loot_distributor.setRipeRewardsConfig(50_00, 43200, sender=switchboard_alpha.address)
    assert loot_distributor.ripeStakeRatio() == 50_00
    
    # Configure RIPE as deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=mock_ripe_token.address)
    
    # Add RIPE rewards
    rewards_amount = 2000 * EIGHTEEN_DECIMALS
    mock_ripe_token.approve(loot_distributor.address, rewards_amount, sender=governance.address)
    loot_distributor.addDepositRewards(mock_ripe_token.address, rewards_amount, sender=governance.address)
    
    # Build deposit points
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 1000 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=1000)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Claim rewards
    user_rewards = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    
    # With 50% stake ratio: split evenly
    assert user_rewards > 0
    staked_amount = user_rewards * 50_00 // 100_00
    direct_amount = user_rewards * 50_00 // 100_00
    
    assert mock_ripe_token.balanceOf(mock_ripe.address) == staked_amount
    assert mock_ripe_token.balanceOf(user_wallet.address) == direct_amount


def test_ripe_stake_ratio_hundred_percent(loot_distributor, user_wallet, bob, mock_ripe_token, governance, setUserWalletConfig, mock_ripe, switchboard_alpha):
    """ Test RIPE rewards with 100% stake ratio - all rewards staked, none direct """
    
    # Set ripe stake ratio to 100%
    loot_distributor.setRipeRewardsConfig(100_00, 43200, sender=switchboard_alpha.address)
    assert loot_distributor.ripeStakeRatio() == 100_00
    
    # Configure RIPE as deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=mock_ripe_token.address)
    
    # Add RIPE rewards
    rewards_amount = 5000 * EIGHTEEN_DECIMALS
    mock_ripe_token.approve(loot_distributor.address, rewards_amount, sender=governance.address)
    loot_distributor.addDepositRewards(mock_ripe_token.address, rewards_amount, sender=governance.address)
    
    # Build deposit points
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 750 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=1000)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    # Claim rewards
    user_rewards = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    
    # With 100% stake ratio: ALL rewards staked
    assert user_rewards > 0
    assert mock_ripe_token.balanceOf(mock_ripe.address) == user_rewards
    
    # Verify NO RIPE sent directly to user wallet
    assert mock_ripe_token.balanceOf(user_wallet.address) == 0


def test_set_ripe_rewards_config_boundaries(loot_distributor, switchboard_alpha):
    """ Test setting RIPE rewards config with boundary values """
    
    # Test valid boundary: 0% stake ratio
    loot_distributor.setRipeRewardsConfig(0, 1, sender=switchboard_alpha.address)
    assert loot_distributor.ripeStakeRatio() == 0
    assert loot_distributor.ripeLockDuration() == 1
    
    # Test valid boundary: 100% stake ratio
    loot_distributor.setRipeRewardsConfig(100_00, 86400, sender=switchboard_alpha.address)
    assert loot_distributor.ripeStakeRatio() == 100_00
    assert loot_distributor.ripeLockDuration() == 86400
    
    # Test invalid: stake ratio > 100%
    with boa.reverts("invalid stake ratio"):
        loot_distributor.setRipeRewardsConfig(100_01, 43200, sender=switchboard_alpha.address)

    # Test invalid: zero lock duration
    with boa.reverts("invalid lock duration"):
        loot_distributor.setRipeRewardsConfig(80_00, 0, sender=switchboard_alpha.address)


#######################################
# Governance Revenue Transfer Tests
#######################################


def test_governance_receives_leftover_when_no_ambassador(loot_distributor, hatchery, charlie, alpha_token, alpha_token_whale, governance):
    """ Test that governance receives ALL fees when there's no ambassador """
    
    # Create user wallet WITHOUT ambassador
    user_wallet_addr = hatchery.createUserWallet(charlie, ZERO_ADDRESS, False, 1, sender=charlie)
    user_wallet = UserWallet.at(user_wallet_addr)
    
    # Transfer tokens and approve
    fee_amount = 500 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor.address, fee_amount, sender=user_wallet.address)
    
    # Check initial governance balance
    initial_gov_balance = alpha_token.balanceOf(governance.address)
    
    # Add loot from swap (no ambassador, so 100% should go to governance)
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    # Verify governance receives ALL fees (100%)
    assert alpha_token.balanceOf(governance.address) == initial_gov_balance + fee_amount


def test_revenue_transferred_to_gov_event_swap(loot_distributor, user_wallet, ambassador_wallet, alpha_token, alpha_token_whale, setAssetConfig, createAmbassadorRevShare):
    """ Test RevenueTransferredToGov event emission for swap fees """
    
    # Set up ambassador config with 30% swap fee share
    ambassadorRevShare = createAmbassadorRevShare(_swapRatio=30_00)
    setAssetConfig(alpha_token, _ambassadorRevShare=ambassadorRevShare)
    
    # Transfer and approve
    fee_amount = 1000 * EIGHTEEN_DECIMALS
    alpha_token.transfer(user_wallet, fee_amount, sender=alpha_token_whale)
    alpha_token.approve(loot_distributor.address, fee_amount, sender=user_wallet.address)
    
    # Add loot from swap
    loot_distributor.addLootFromSwapOrRewards(
        alpha_token,
        fee_amount,
        ACTION_TYPE.SWAP,
        sender=user_wallet.address
    )
    
    # Check RevenueTransferredToGov event
    events = filter_logs(loot_distributor, 'RevenueTransferredToGov')
    assert len(events) == 1
    event = events[0]
    
    # Verify event parameters
    assert event.asset == alpha_token.address
    assert event.amount == fee_amount * 70_00 // 100_00  # 70% to governance
    assert event.action == ACTION_TYPE.SWAP


def test_revenue_transferred_to_gov_event_yield(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, governance, mock_yield_lego, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test RevenueTransferredToGov event emission for yield profit fees """
    
    # Set up ambassador config with 25% yield fee share
    ambassadorRevShare = createAmbassadorRevShare(_yieldRatio=25_00)
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
    )
    setAssetConfig(yield_vault_token, _ambassadorRevShare=ambassadorRevShare, _yieldConfig=yieldConfig)
    
    # Register vault token
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(yield_underlying_token, deposit_amount, yield_vault_token, sender=yield_underlying_token_whale)
    
    # Simulate yield profit
    performance_fee = 100 * EIGHTEEN_DECIMALS
    yield_vault_token.transfer(loot_distributor, performance_fee, sender=yield_underlying_token_whale)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        500 * EIGHTEEN_DECIMALS,
        sender=user_wallet.address
    )
    
    # Check RevenueTransferredToGov event
    events = filter_logs(loot_distributor, 'RevenueTransferredToGov')
    assert len(events) == 1
    event = events[0]
    
    # Verify event parameters
    assert event.asset == yield_vault_token.address
    assert event.amount == performance_fee * 75_00 // 100_00  # 75% to governance
    assert event.action == ACTION_TYPE.EARN_WITHDRAW


###################################
# Combined Scenario Tests
###################################


def test_ripe_rewards_with_different_stake_ratios_sequential(loot_distributor, user_wallet, bob, mock_ripe_token, governance, setUserWalletConfig, mock_ripe, switchboard_alpha):
    """ Test sequential claims with different stake ratios """
    
    # Configure RIPE as deposit rewards asset
    setUserWalletConfig(_depositRewardsAsset=mock_ripe_token.address)
    
    # First claim with 80% stake ratio (default)
    rewards_amount_1 = 1000 * EIGHTEEN_DECIMALS
    mock_ripe_token.approve(loot_distributor.address, rewards_amount_1, sender=governance.address)
    loot_distributor.addDepositRewards(mock_ripe_token.address, rewards_amount_1, sender=governance.address)
    
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 500 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=500)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    user_rewards_1 = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    staked_1 = user_rewards_1 * 80_00 // 100_00
    direct_1 = user_rewards_1 * 20_00 // 100_00
    
    # Change to 50% stake ratio
    loot_distributor.setRipeRewardsConfig(50_00, 43200, sender=switchboard_alpha.address)
    
    # Second claim with 50% stake ratio
    rewards_amount_2 = 2000 * EIGHTEEN_DECIMALS
    mock_ripe_token.approve(loot_distributor.address, rewards_amount_2, sender=governance.address)
    loot_distributor.addDepositRewards(mock_ripe_token.address, rewards_amount_2, sender=governance.address)
    
    loot_distributor.updateDepositPointsWithNewValue(user_wallet.address, 500 * EIGHTEEN_DECIMALS, sender=user_wallet.address)
    boa.env.time_travel(blocks=500)
    loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)
    
    user_rewards_2 = loot_distributor.claimDepositRewards(user_wallet.address, sender=bob)
    staked_2 = user_rewards_2 * 50_00 // 100_00
    direct_2 = user_rewards_2 * 50_00 // 100_00
    
    # Verify cumulative balances reflect both stake ratios
    assert mock_ripe_token.balanceOf(mock_ripe.address) == staked_1 + staked_2
    assert mock_ripe_token.balanceOf(user_wallet.address) == direct_1 + direct_2


def test_governance_and_ripe_staking_yield_bonus_combined(loot_distributor, user_wallet, ambassador_wallet, yield_vault_token, yield_underlying_token, yield_underlying_token_whale, mock_ripe_token, governance, mock_yield_lego, mock_ripe, switchboard_alpha, setAssetConfig, createAmbassadorRevShare, createAssetYieldConfig):
    """ Test governance revenue transfer AND RIPE staking working together """
    
    # Set ripe stake ratio to 60%
    loot_distributor.setRipeRewardsConfig(60_00, 43200, sender=switchboard_alpha.address)
    
    # Set prices for RIPE and underlying
    mock_ripe.setPrice(mock_ripe_token.address, 2 * EIGHTEEN_DECIMALS)  # $2 per RIPE
    mock_ripe.setPrice(yield_underlying_token.address, 10 * EIGHTEEN_DECIMALS)  # $10 per underlying
    
    # Transfer RIPE to loot distributor for bonuses
    mock_ripe_token.transfer(loot_distributor.address, 5000 * EIGHTEEN_DECIMALS, sender=governance.address)
    
    # Set up configs with 35% yield fee share and RIPE as alt bonus
    ambassadorRevShare = createAmbassadorRevShare(_yieldRatio=35_00)
    yieldConfig = createAssetYieldConfig(
        _isYieldAsset=True,
        _underlyingAsset=yield_underlying_token.address,
        _bonusRatio=20_00,  # 20% user bonus in RIPE
        _altBonusAsset=mock_ripe_token.address,
    )
    setAssetConfig(yield_vault_token, _ambassadorRevShare=ambassadorRevShare, _yieldConfig=yieldConfig)
    
    # Register vault token
    deposit_amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.approve(mock_yield_lego, deposit_amount, sender=yield_underlying_token_whale)
    mock_yield_lego.depositForYield(yield_underlying_token, deposit_amount, yield_vault_token, sender=yield_underlying_token_whale)
    
    # Simulate yield profit
    performance_fee = 50 * EIGHTEEN_DECIMALS
    total_yield = 100 * EIGHTEEN_DECIMALS
    yield_vault_token.transfer(loot_distributor.address, performance_fee, sender=yield_underlying_token_whale)
    
    # Check initial balances
    initial_gov_balance = yield_vault_token.balanceOf(governance.address)
    initial_ripe_staked = mock_ripe_token.balanceOf(mock_ripe.address)
    
    # Add loot from yield profit
    loot_distributor.addLootFromYieldProfit(
        yield_vault_token,
        performance_fee,
        total_yield,
        sender=user_wallet.address
    )
    
    # Verify governance receives 65% of performance fee (100% - 35% ambassador share)
    expected_gov_fee = performance_fee * 65_00 // 100_00
    assert yield_vault_token.balanceOf(governance.address) == initial_gov_balance + expected_gov_fee
    
    # User claims RIPE bonus
    # Yield profit value: 100 tokens * $10 = $1000
    # User bonus: $1000 * 20% = $200 worth of RIPE = 100 RIPE tokens (at $2 each)
    user_wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    loot_distributor.claimRevShareAndBonusLoot(user_wallet.address, sender=user_wallet_config.owner())
    
    # Verify RIPE bonus with 60% stake ratio
    expected_ripe_bonus = 100 * EIGHTEEN_DECIMALS
    staked_ripe = expected_ripe_bonus * 60_00 // 100_00  # 60 RIPE
    direct_ripe = expected_ripe_bonus * 40_00 // 100_00  # 40 RIPE
    
    assert mock_ripe_token.balanceOf(mock_ripe.address) == initial_ripe_staked + staked_ripe
    assert mock_ripe_token.balanceOf(user_wallet.address) == direct_ripe
