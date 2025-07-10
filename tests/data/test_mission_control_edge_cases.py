import pytest
import boa
from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS, HUNDRED_PERCENT, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ONE_YEAR_IN_BLOCKS


def test_zero_address_handling(mission_control, setUserWalletConfig, setAssetConfig, alice):
    """Test handling of zero addresses in various configs"""
    # Set config with zero addresses where allowed
    setUserWalletConfig(
        _walletTemplate=ZERO_ADDRESS,  # Should fail in actual deployment
        _configTemplate=ZERO_ADDRESS,  # Should fail in actual deployment
        _trialAsset=ZERO_ADDRESS,  # Valid - no trial funds
        _depositRewardsAsset=ZERO_ADDRESS,  # Valid - no deposit rewards
    )
    
    config = mission_control.userWalletConfig()
    assert config[0] == ZERO_ADDRESS
    assert config[1] == ZERO_ADDRESS
    assert config[2] == ZERO_ADDRESS
    assert config[11] == ZERO_ADDRESS


def test_maximum_values(mission_control, switchboard_alpha, alpha_token):
    """Test setting maximum allowed values"""
    # Set config with maximum values
    max_uint256 = 2**256 - 1
    max_fees = (HUNDRED_PERCENT, HUNDRED_PERCENT, HUNDRED_PERCENT)
    max_ambassador = (HUNDRED_PERCENT, HUNDRED_PERCENT, HUNDRED_PERCENT)
    
    config = (
        alpha_token.address,  # walletTemplate
        alpha_token.address,  # configTemplate
        alpha_token.address,  # trialAsset
        max_uint256,  # trialAmount - maximum
        max_uint256,  # numUserWalletsAllowed - maximum
        True,  # enforceCreatorWhitelist
        max_uint256,  # minKeyActionTimeLock - maximum (problematic in practice)
        max_uint256,  # maxKeyActionTimeLock - maximum
        max_fees,  # walletFees - 100% each
        max_ambassador,  # ambassadorFeeRatio - 100% each
        max_uint256,  # defaultStaleBlocks - maximum
        alpha_token.address,  # depositRewardsAsset
    )
    
    # This should succeed even with extreme values
    mission_control.setUserWalletConfig(config, sender=switchboard_alpha.address)
    
    stored = mission_control.userWalletConfig()
    assert stored[3] == max_uint256  # trialAmount
    assert stored[4] == max_uint256  # numUserWalletsAllowed


def test_zero_fees(mission_control, setUserWalletConfig, setAssetConfig, alice, alpha_token, bravo_token):
    """Test zero fee configurations"""
    # Set all fees to zero
    setUserWalletConfig(
        _swapFee=0,
        _stableSwapFee=0,
        _rewardsFee=0,
        _ambassadorFeesSwap=0,
        _ambassadorFeesRewards=0,
        _ambassadorFeesYieldProfit=0,
    )
    
    # Verify zero fees
    assert mission_control.getSwapFee(alice, alpha_token.address, bravo_token.address) == 0
    assert mission_control.getRewardsFee(alice, alpha_token.address) == 0
    
    config = mission_control.getAmbassadorConfig(alice, alpha_token.address, False)
    assert config[1][0] == 0  # swap
    assert config[1][1] == 0  # rewards
    assert config[1][2] == 0  # yield profit


def test_conflicting_configurations(mission_control, setUserWalletConfig, setAssetConfig, alice, alpha_token):
    """Test potentially conflicting configurations"""
    # Set min > max for timelock (logically invalid but contract allows)
    setUserWalletConfig(
        _minTimeLock=1000,
        _maxTimeLock=100,  # Less than min
    )
    
    config = mission_control.getUserWalletCreationConfig(alice)
    assert config[12] == 1000  # min
    assert config[13] == 100   # max (less than min)


def test_asset_config_edge_cases(mission_control, switchboard_alpha, alpha_token, bravo_token):
    """Test edge cases in asset configuration"""
    # Asset that is both stablecoin and yield asset
    fees = (100, 25, 2000)
    yieldConfig = (
        True,  # isRebasing
        bravo_token.address,  # underlyingAsset
        0,  # maxYieldIncrease - 0% allowed increase
        HUNDRED_PERCENT,  # yieldProfitFee - 100% fee
        0,  # ambassadorBonusRatio - 0% bonus
    )
    config = (
        0,  # legoId - 0 is valid
        True,  # isStablecoin
        0,  # decimals - 0 decimals (triggers defaults)
        0,  # staleBlocks - 0 blocks
        fees,
        True,  # isYieldAsset
        yieldConfig,
    )
    
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    stored = mission_control.assetConfig(alpha_token.address)
    assert stored[0] == 0  # legoId can be 0
    assert stored[1] == True  # stablecoin
    assert stored[2] == 0  # 0 decimals
    assert stored[5] == True  # yield asset
    assert stored[6][2] == 0  # 0% max yield increase
    assert stored[6][3] == HUNDRED_PERCENT  # 100% fee


def test_rapid_config_updates(mission_control, switchboard_alpha, alpha_token, bravo_token, charlie_token):
    """Test rapid configuration updates"""
    # Rapidly update configurations
    for i in range(10):
        fees = (i * 10, i * 5, i * 20)
        yieldConfig = (i % 2 == 0, alpha_token.address, i * 100, i * 200, i * 300)
        config = (
            i,  # legoId
            i % 2 == 1,  # alternating stablecoin
            18,  # decimals
            i * 10,  # staleBlocks
            fees,
            i % 3 == 0,  # every third is yield
            yieldConfig,
        )
        
        # Rotate through assets
        assets = [alpha_token, bravo_token, charlie_token]
        asset = assets[i % 3]
        
        mission_control.setAssetConfig(asset.address, config, sender=switchboard_alpha.address)
        
        # Verify immediately
        stored = mission_control.assetConfig(asset.address)
        assert stored[0] == i  # legoId matches


def test_multiple_whitelists_and_permissions(mission_control, switchboard_alpha, alice, bob, charlie, deploy3r, agent_eoa):
    """Test managing multiple whitelisted addresses and permissions with specific patterns"""
    # Set specific permissions for each address
    # alice: creator whitelist + security action + locked signer
    mission_control.setCreatorWhitelist(alice, True, sender=switchboard_alpha.address)
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)
    mission_control.setLockedSigner(alice, True, sender=switchboard_alpha.address)
    
    # bob: none
    # (no calls needed - default is False)
    
    # charlie: creator whitelist only
    mission_control.setCreatorWhitelist(charlie, True, sender=switchboard_alpha.address)
    
    # deploy3r: security action only
    mission_control.setCanPerformSecurityAction(deploy3r, True, sender=switchboard_alpha.address)
    
    # agent_eoa: creator whitelist + locked signer
    mission_control.setCreatorWhitelist(agent_eoa, True, sender=switchboard_alpha.address)
    mission_control.setLockedSigner(agent_eoa, True, sender=switchboard_alpha.address)
    
    # Verify specific permissions for each address
    # alice: all permissions
    assert mission_control.creatorWhitelist(alice) == True
    assert mission_control.canPerformSecurityAction(alice) == True
    assert mission_control.isLockedSigner(alice) == True
    
    # bob: no permissions
    assert mission_control.creatorWhitelist(bob) == False
    assert mission_control.canPerformSecurityAction(bob) == False
    assert mission_control.isLockedSigner(bob) == False
    
    # charlie: creator whitelist only
    assert mission_control.creatorWhitelist(charlie) == True
    assert mission_control.canPerformSecurityAction(charlie) == False
    assert mission_control.isLockedSigner(charlie) == False
    
    # deploy3r: security action only
    assert mission_control.creatorWhitelist(deploy3r) == False
    assert mission_control.canPerformSecurityAction(deploy3r) == True
    assert mission_control.isLockedSigner(deploy3r) == False
    
    # agent_eoa: creator whitelist + locked signer
    assert mission_control.creatorWhitelist(agent_eoa) == True
    assert mission_control.canPerformSecurityAction(agent_eoa) == False
    assert mission_control.isLockedSigner(agent_eoa) == True


def test_fee_calculation_edge_cases(mission_control, switchboard_alpha, setUserWalletConfig, setAssetConfig, alice, alpha_token, bravo_token):
    """Test edge cases in fee calculations"""
    # Test with one asset having custom fee, one without
    setUserWalletConfig(_swapFee=100, _stableSwapFee=10)
    
    # Bravo has custom fee
    setAssetConfig(bravo_token, _swapFee=200)
    
    # Alpha has 0 decimals (should use global)
    fees = (300, 25, 400)  # Should be ignored
    yieldConfig = (False, ZERO_ADDRESS, 0, 0, 0)
    config = (1, False, 0, 100, fees, False, yieldConfig)
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    # Swap from alpha (0 decimals) to beta (custom fee)
    fee = mission_control.getSwapFee(alice, alpha_token.address, bravo_token.address)
    assert fee == 200  # Beta's custom fee
    
    # Swap from beta to alpha
    fee = mission_control.getSwapFee(alice, bravo_token.address, alpha_token.address)
    assert fee == 100  # Global fee (alpha has 0 decimals)


def test_batch_asset_config_pattern(mission_control, switchboard_alpha, alpha_token, bravo_token, charlie_token):
    """Test pattern for batch setting asset configs"""
    assets = [alpha_token, bravo_token, charlie_token]
    
    # Configure multiple assets with similar settings
    base_fees = (100, 25, 2000)
    base_yield = (False, ZERO_ADDRESS, 0, 0, 0)
    
    for i, asset in enumerate(assets):
        config = (
            i + 1,  # legoId
            False,  # not stablecoin
            18,  # decimals
            100,  # staleBlocks
            base_fees,
            False,  # not yield asset
            base_yield,
        )
        mission_control.setAssetConfig(asset.address, config, sender=switchboard_alpha.address)
    
    # Verify all were set
    for i, asset in enumerate(assets):
        stored = mission_control.assetConfig(asset.address)
        assert stored[0] == i + 1


def test_config_reuse_pattern(mission_control, setUserWalletConfig, setManagerConfig, setPayeeConfig, alice, bob, charlie):
    """Test configuration reuse patterns"""
    # Set base configs once
    setUserWalletConfig()
    setManagerConfig()
    setPayeeConfig()
    
    # Get configs for multiple users - should reuse same base config
    configs = []
    users = [alice, bob, charlie]
    
    for user in users:
        config = mission_control.getUserWalletCreationConfig(user)
        configs.append(config)
    
    # All should have same base values
    for config in configs:
        assert config[0] == 100  # numUserWalletsAllowed
        assert config[6] == ONE_DAY_IN_BLOCKS  # managerPeriod
        assert config[7] == ONE_MONTH_IN_BLOCKS  # managerActivationLength


def test_get_ambassador_config_variations(mission_control, setUserWalletConfig, setAssetConfig, createAssetYieldConfig, alice, alpha_token, bravo_token):
    """Test ambassador config with various parameter combinations"""
    # Set base config
    setUserWalletConfig(
        _ambassadorFeesSwap=4500,
        _ambassadorFeesRewards=3500,
        _ambassadorFeesYieldProfit=5500,
    )
    
    # Non-yield asset
    setAssetConfig(alpha_token, _yieldConfig=createAssetYieldConfig(_isYieldAsset=False))
    config = mission_control.getAmbassadorConfig(alice, alpha_token.address, False)
    assert config[2] == 0  # No bonus for non-yield when called with False
    
    config = mission_control.getAmbassadorConfig(alice, alpha_token.address, True)
    assert config[2] == 5000  # Returns default ambassadorBonusRatio even for non-yield asset when called with True
    
    # Yield asset
    setAssetConfig(
        bravo_token,
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=alpha_token,
            _ambassadorBonusRatio=2500
        )
    )
    
    config = mission_control.getAmbassadorConfig(alice, bravo_token.address, False)
    assert config[2] == 0  # No bonus when called with False
    
    config = mission_control.getAmbassadorConfig(alice, bravo_token.address, True)
    assert config[2] == 2500  # Bonus when called with True
    assert config[3] == alpha_token.address  # Underlying asset
    assert config[4] == 18  # Decimals


def test_stale_blocks_fallback_logic(mission_control, switchboard_alpha, setUserWalletConfig, alpha_token):
    """Test stale blocks fallback to default"""
    # Set default stale blocks
    setUserWalletConfig(_staleBlocks=777)
    
    # Asset with specific stale blocks (decimals > 0)
    fees = (100, 25, 2000)
    yieldConfig = (False, ZERO_ADDRESS, 0, 0, 0)
    config = (1, False, 18, 555, fees, False, yieldConfig)  # 555 stale blocks
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    # Should use asset's stale blocks
    profit_config = mission_control.getProfitCalcConfig(alpha_token.address)
    assert profit_config[3] == 555
    
    usd_config = mission_control.getAssetUsdValueConfig(alpha_token.address)
    assert usd_config[3] == 555
    
    # Asset with 0 decimals (triggers default)
    config = (1, False, 0, 555, fees, False, yieldConfig)  # decimals = 0
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    # Should use default stale blocks
    profit_config = mission_control.getProfitCalcConfig(alpha_token.address)
    assert profit_config[3] == 777  # default
    
    usd_config = mission_control.getAssetUsdValueConfig(alpha_token.address)
    assert usd_config[3] == 777  # default