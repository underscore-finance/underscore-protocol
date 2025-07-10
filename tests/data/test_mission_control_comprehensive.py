import pytest
import boa
from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS, HUNDRED_PERCENT, ONE_DAY_IN_BLOCKS, ONE_MONTH_IN_BLOCKS, ONE_YEAR_IN_BLOCKS


def test_set_user_wallet_config_success(mission_control, switchboard_alpha, user_wallet_template, user_wallet_config_template, alpha_token):
    """Test setting user wallet config with valid parameters"""
    config = (
        user_wallet_template.address,
        user_wallet_config_template.address,
        alpha_token,
        10 * EIGHTEEN_DECIMALS,
        100,  # numUserWalletsAllowed
        False,  # enforceCreatorWhitelist
        10,  # minKeyActionTimeLock
        100,  # maxKeyActionTimeLock
        (100, 10, 2000),  # walletFees (swap, stableSwap, rewards)
        (5000, 5000, 5000),  # ambassadorFeeRatio
        0,  # defaultStaleBlocks
        alpha_token,  # depositRewardsAsset
    )
    
    mission_control.setUserWalletConfig(config, sender=switchboard_alpha.address)
    
    # Verify config was set
    stored_config = mission_control.userWalletConfig()
    assert stored_config[0] == user_wallet_template.address
    assert stored_config[1] == user_wallet_config_template.address
    assert stored_config[2] == alpha_token.address
    assert stored_config[3] == 10 * EIGHTEEN_DECIMALS
    assert stored_config[4] == 100
    assert stored_config[5] == False
    assert stored_config[6] == 10
    assert stored_config[7] == 100
    assert stored_config[11] == alpha_token.address
    
def test_set_user_wallet_config_unauthorized(mission_control, deploy3r, user_wallet_template, user_wallet_config_template, alpha_token):
    """Test setting user wallet config from unauthorized address"""
    config = (
        user_wallet_template.address,
        user_wallet_config_template.address,
        alpha_token,
        10 * EIGHTEEN_DECIMALS,
        100,
        False,
        10,
        100,
        (100, 10, 2000),
        (5000, 5000, 5000),
        0,
        alpha_token,
    )
    
    with boa.reverts("no perms"):
        mission_control.setUserWalletConfig(config, sender=deploy3r)
    
def test_get_user_wallet_creation_config(mission_control, switchboard_alpha, setUserWalletConfig, setManagerConfig, setPayeeConfig, alice):
    """Test getting user wallet creation config"""
    # Set configs
    setUserWalletConfig()
    setManagerConfig()
    setPayeeConfig()
    
    # Get creation config
    config = mission_control.getUserWalletCreationConfig(alice)
    
    # Verify all fields
    assert config[0] == 100  # numUserWalletsAllowed
    assert config[1] == True  # isCreatorAllowed (no whitelist)
    assert config[6] == ONE_DAY_IN_BLOCKS  # managerPeriod
    assert config[7] == ONE_MONTH_IN_BLOCKS  # managerActivationLength
    assert config[8] == ONE_DAY_IN_BLOCKS  # payeePeriod
    assert config[9] == ONE_MONTH_IN_BLOCKS  # payeeActivationLength
    assert config[12] == 10  # minKeyActionTimeLock
    assert config[13] == 100  # maxKeyActionTimeLock
    
def test_get_user_wallet_creation_config_with_whitelist(mission_control, switchboard_alpha, setUserWalletConfig, alice, bob):
    """Test getting user wallet creation config with whitelist enforcement"""
    # Set config with whitelist enforcement
    setUserWalletConfig(_enforceCreatorWhitelist=True)
    
    # Alice not whitelisted
    config = mission_control.getUserWalletCreationConfig(alice)
    assert config[1] == False  # isCreatorAllowed
    
    # Whitelist alice
    mission_control.setCreatorWhitelist(alice, True, sender=switchboard_alpha.address)
    
    # Alice now allowed
    config = mission_control.getUserWalletCreationConfig(alice)
    assert config[1] == True  # isCreatorAllowed
    
    # Bob still not allowed
    config = mission_control.getUserWalletCreationConfig(bob)
    assert config[1] == False  # isCreatorAllowed
    
def test_get_deposit_rewards_asset(mission_control, setUserWalletConfig, alpha_token, bravo_token):
    """Test getting deposit rewards asset"""
    # Set with alpha token
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address)
    assert mission_control.getDepositRewardsAsset() == alpha_token.address
    
    # Update to beta token
    setUserWalletConfig(_depositRewardsAsset=bravo_token.address)
    assert mission_control.getDepositRewardsAsset() == bravo_token.address


def test_set_manager_config_success(mission_control, switchboard_alpha, agent_eoa):
    """Test setting manager config with valid parameters"""
    config = (
        agent_eoa,
        ONE_YEAR_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_MONTH_IN_BLOCKS,
    )
    
    mission_control.setManagerConfig(config, sender=switchboard_alpha.address)
    
    # Verify config was set
    stored_config = mission_control.managerConfig()
    assert stored_config[0] == agent_eoa
    assert stored_config[1] == ONE_YEAR_IN_BLOCKS
    assert stored_config[2] == ONE_DAY_IN_BLOCKS
    assert stored_config[3] == ONE_MONTH_IN_BLOCKS
    
def test_set_manager_config_unauthorized(mission_control, deploy3r, agent_eoa):
    """Test setting manager config from unauthorized address"""
    config = (
        agent_eoa,
        ONE_YEAR_IN_BLOCKS,
        ONE_DAY_IN_BLOCKS,
        ONE_MONTH_IN_BLOCKS,
    )
    
    with boa.reverts("no perms"):
        mission_control.setManagerConfig(config, sender=deploy3r)


def test_set_payee_config_success(mission_control, switchboard_alpha):
    """Test setting payee config with valid parameters"""
    config = (
        ONE_DAY_IN_BLOCKS,
        ONE_MONTH_IN_BLOCKS,
    )
    
    mission_control.setPayeeConfig(config, sender=switchboard_alpha.address)
    
    # Verify config was set
    stored_config = mission_control.payeeConfig()
    assert stored_config[0] == ONE_DAY_IN_BLOCKS
    assert stored_config[1] == ONE_MONTH_IN_BLOCKS
    
def test_set_payee_config_unauthorized(mission_control, deploy3r):
    """Test setting payee config from unauthorized address"""
    config = (
        ONE_DAY_IN_BLOCKS,
        ONE_MONTH_IN_BLOCKS,
    )
    
    with boa.reverts("no perms"):
        mission_control.setPayeeConfig(config, sender=deploy3r)


def test_set_agent_config_success(mission_control, switchboard_alpha, agent_template):
    """Test setting agent config with valid parameters"""
    config = (
        agent_template.address,
        50,  # numAgentsAllowed
        False,  # enforceCreatorWhitelist
    )
    
    mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    
    # Verify config was set
    stored_config = mission_control.agentConfig()
    assert stored_config[0] == agent_template.address
    assert stored_config[1] == 50
    assert stored_config[2] == False
    
def test_set_agent_config_unauthorized(mission_control, deploy3r, agent_template):
    """Test setting agent config from unauthorized address"""
    config = (
        agent_template.address,
        50,
        False,
    )
    
    with boa.reverts("no perms"):
        mission_control.setAgentConfig(config, sender=deploy3r)
    
def test_get_agent_creation_config(mission_control, setAgentConfig, setUserWalletConfig, alice):
    """Test getting agent creation config"""
    # Set configs
    setAgentConfig(_numAgentsAllowed=50, _enforceCreatorWhitelist=False)
    setUserWalletConfig(_minTimeLock=20, _maxTimeLock=200)
    
    # Get creation config
    config = mission_control.getAgentCreationConfig(alice)
    
    # Verify all fields
    assert config[1] == 50  # numAgentsAllowed
    assert config[2] == True  # isCreatorAllowed (no whitelist)
    assert config[3] == 20  # minTimeLock
    assert config[4] == 200  # maxTimeLock
    
def test_get_agent_creation_config_with_whitelist(mission_control, switchboard_alpha, setAgentConfig, alice, bob):
    """Test getting agent creation config with whitelist enforcement"""
    # Set config with whitelist enforcement
    setAgentConfig(_enforceCreatorWhitelist=True)
    
    # Alice not whitelisted
    config = mission_control.getAgentCreationConfig(alice)
    assert config[2] == False  # isCreatorAllowed
    
    # Whitelist alice
    mission_control.setCreatorWhitelist(alice, True, sender=switchboard_alpha.address)
    
    # Alice now allowed
    config = mission_control.getAgentCreationConfig(alice)
    assert config[2] == True  # isCreatorAllowed
    
    # Bob still not allowed
    config = mission_control.getAgentCreationConfig(bob)
    assert config[2] == False  # isCreatorAllowed


def test_set_asset_config_success(mission_control, switchboard_alpha, alpha_token):
    """Test setting asset config with valid parameters"""
    fees = (100, 25, 2000)  # swap, stableSwap, rewards
    yieldConfig = (
        False,  # isRebasing
        alpha_token,  # underlyingAsset
        500,  # maxYieldIncrease
        2000,  # yieldProfitFee
        5000,  # ambassadorBonusRatio
    )
    config = (
        1,  # legoId
        False,  # isStablecoin
        18,  # decimals
        100,  # staleBlocks
        fees,
        False,  # isYieldAsset
        yieldConfig,
    )
    
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    # Verify config was set
    stored_config = mission_control.assetConfig(alpha_token.address)
    assert stored_config[0] == 1  # legoId
    assert stored_config[1] == False  # isStablecoin
    assert stored_config[2] == 18  # decimals
    assert stored_config[3] == 100  # staleBlocks
    assert stored_config[5] == False  # isYieldAsset
    
def test_set_asset_config_unauthorized(mission_control, deploy3r, alpha_token):
    """Test setting asset config from unauthorized address"""
    fees = (100, 25, 2000)
    yieldConfig = (False, alpha_token.address, 500, 2000, 5000)
    config = (1, False, 18, 100, fees, False, yieldConfig)
    
    with boa.reverts("no perms"):
        mission_control.setAssetConfig(alpha_token.address, config, sender=deploy3r)
    
def test_set_asset_config_stablecoin(mission_control, switchboard_alpha, alpha_token):
    """Test setting asset config for stablecoin"""
    fees = (100, 25, 2000)
    yieldConfig = (False, ZERO_ADDRESS, 0, 0, 0)
    config = (
        1,  # legoId
        True,  # isStablecoin
        6,  # decimals (USDC-like)
        50,  # staleBlocks
        fees,
        False,  # isYieldAsset
        yieldConfig,
    )
    
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    # Verify stablecoin flag
    stored_config = mission_control.assetConfig(alpha_token.address)
    assert stored_config[1] == True  # isStablecoin
    assert stored_config[2] == 6  # decimals
    
def test_set_asset_config_yield_asset(mission_control, switchboard_alpha, alpha_token, bravo_token):
    """Test setting asset config for yield asset"""
    fees = (100, 25, 2000)
    yieldConfig = (
        True,  # isRebasing
        bravo_token.address,  # underlyingAsset
        1000,  # maxYieldIncrease (10%)
        1500,  # yieldProfitFee (15%)
        3000,  # ambassadorBonusRatio (30%)
    )
    config = (
        2,  # legoId
        False,  # isStablecoin
        18,  # decimals
        200,  # staleBlocks
        fees,
        True,  # isYieldAsset
        yieldConfig,
    )
    
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    # Verify yield asset config
    stored_config = mission_control.assetConfig(alpha_token.address)
    assert stored_config[5] == True  # isYieldAsset
    assert stored_config[6][0] == True  # isRebasing
    assert stored_config[6][1] == bravo_token.address  # underlyingAsset
    assert stored_config[6][2] == 1000  # maxYieldIncrease
    assert stored_config[6][3] == 1500  # yieldProfitFee
    assert stored_config[6][4] == 3000  # ambassadorBonusRatio


def test_get_profit_calc_config(mission_control, setAssetConfig, createAssetYieldConfig, alpha_token, bravo_token):
    """Test getting profit calculation config"""
    # Set up yield asset
    setAssetConfig(
        alpha_token,
        _legoId=2,
        _staleBlocks=200,
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _isRebasing=True,
            _underlyingAsset=bravo_token,
            _maxYieldIncrease=1000,
            _performanceFee=1500
        )
    )
    
    config = mission_control.getProfitCalcConfig(alpha_token.address)
    
    assert config[0] == 2  # legoId
    assert config[1] == ZERO_ADDRESS  # legoAddr (always empty)
    assert config[2] == 18  # decimals
    assert config[3] == 200  # staleBlocks
    assert config[4] == True  # isYieldAsset
    assert config[5] == True  # isRebasing
    assert config[6] == bravo_token.address  # underlyingAsset
    assert config[7] == 1000  # maxYieldIncrease
    assert config[8] == 1500  # yieldProfitFee
    
def test_get_profit_calc_config_default_stale_blocks(mission_control, setAssetConfig, setUserWalletConfig, switchboard_alpha, alpha_token):
    """Test profit calc config uses default stale blocks when asset decimals is 0"""
    # Set default stale blocks in user wallet config
    setUserWalletConfig(_staleBlocks=500)
    
    # Set asset with 0 decimals (which triggers default)
    fees = (100, 25, 2000)
    yieldConfig = (False, ZERO_ADDRESS, 0, 0, 0)
    config = (1, False, 0, 100, fees, False, yieldConfig)  # decimals = 0
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    profit_config = mission_control.getProfitCalcConfig(alpha_token.address)
    assert profit_config[3] == 500  # Should use default stale blocks
    
def test_get_asset_usd_value_config(mission_control, setAssetConfig, createAssetYieldConfig, alpha_token, bravo_token):
    """Test getting asset USD value config"""
    # Set up asset
    setAssetConfig(
        alpha_token,
        _legoId=3,
        _staleBlocks=150,
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=bravo_token
        )
    )
    
    config = mission_control.getAssetUsdValueConfig(alpha_token.address)
    
    assert config[0] == 3  # legoId
    assert config[1] == ZERO_ADDRESS  # legoAddr (always empty)
    assert config[2] == 18  # decimals
    assert config[3] == 150  # staleBlocks
    assert config[4] == True  # isYieldAsset
    assert config[5] == bravo_token.address  # underlyingAsset
    
def test_get_asset_usd_value_config_default_stale_blocks(mission_control, setAssetConfig, setUserWalletConfig, switchboard_alpha, alpha_token):
    """Test asset USD value config uses default stale blocks when asset decimals is 0"""
    # Set default stale blocks
    setUserWalletConfig(_staleBlocks=300)
    
    # Set asset with 0 decimals
    fees = (100, 25, 2000)
    yieldConfig = (False, ZERO_ADDRESS, 0, 0, 0)
    config = (1, False, 0, 100, fees, False, yieldConfig)  # decimals = 0
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    value_config = mission_control.getAssetUsdValueConfig(alpha_token.address)
    assert value_config[3] == 300  # Should use default stale blocks


def test_get_swap_fee_regular(mission_control, setUserWalletConfig, alice, alpha_token, bravo_token):
    """Test getting regular swap fee"""
    # Set global swap fee
    setUserWalletConfig(_swapFee=150)  # 1.5%
    
    fee = mission_control.getSwapFee(alice, alpha_token.address, bravo_token.address)
    assert fee == 150
    
def test_get_swap_fee_stable_to_stable(mission_control, setUserWalletConfig, setAssetConfig, alice, alpha_token, bravo_token):
    """Test getting swap fee for stable-to-stable swap"""
    # Set fees
    setUserWalletConfig(_swapFee=150, _stableSwapFee=10)  # 0.1% for stable
    
    # Mark both as stablecoins
    setAssetConfig(alpha_token, _isStablecoin=True)
    setAssetConfig(bravo_token, _isStablecoin=True)
    
    fee = mission_control.getSwapFee(alice, alpha_token.address, bravo_token.address)
    assert fee == 10  # Should use stable swap fee
    
def test_get_swap_fee_asset_specific(mission_control, setUserWalletConfig, setAssetConfig, alice, alpha_token, bravo_token):
    """Test asset-specific swap fee takes precedence"""
    # Set global swap fee
    setUserWalletConfig(_swapFee=150)
    
    # Set asset-specific fee for output token
    setAssetConfig(bravo_token, _swapFee=250)  # 2.5%
    
    fee = mission_control.getSwapFee(alice, alpha_token.address, bravo_token.address)
    assert fee == 250  # Should use asset-specific fee
    
def test_get_swap_fee_zero_decimals(mission_control, setUserWalletConfig, switchboard_alpha, alice, alpha_token, bravo_token):
    """Test swap fee falls back to global when asset has 0 decimals"""
    # Set global swap fee
    setUserWalletConfig(_swapFee=150)
    
    # Set asset with 0 decimals (which means use global)
    fees = (300, 25, 2000)  # This swap fee should be ignored
    yieldConfig = (False, ZERO_ADDRESS, 0, 0, 0)
    config = (1, False, 0, 100, fees, False, yieldConfig)  # decimals = 0
    mission_control.setAssetConfig(bravo_token.address, config, sender=switchboard_alpha.address)
    
    fee = mission_control.getSwapFee(alice, alpha_token.address, bravo_token.address)
    assert fee == 150  # Should use global fee
    
def test_get_rewards_fee_global(mission_control, setUserWalletConfig, alice, alpha_token):
    """Test getting global rewards fee"""
    # Set global rewards fee
    setUserWalletConfig(_rewardsFee=2500)  # 25%
    
    fee = mission_control.getRewardsFee(alice, alpha_token.address)
    assert fee == 2500
    
def test_get_rewards_fee_asset_specific(mission_control, setUserWalletConfig, setAssetConfig, alice, alpha_token):
    """Test asset-specific rewards fee takes precedence"""
    # Set global rewards fee
    setUserWalletConfig(_rewardsFee=2500)
    
    # Set asset-specific fee
    setAssetConfig(alpha_token, _rewardsFee=1000)  # 10%
    
    fee = mission_control.getRewardsFee(alice, alpha_token.address)
    assert fee == 1000  # Should use asset-specific fee
    
def test_get_rewards_fee_zero_decimals(mission_control, setUserWalletConfig, switchboard_alpha, alice, alpha_token):
    """Test rewards fee falls back to global when asset has 0 decimals"""
    # Set global rewards fee
    setUserWalletConfig(_rewardsFee=2500)
    
    # Set asset with 0 decimals
    fees = (100, 25, 1000)  # This rewards fee should be ignored
    yieldConfig = (False, ZERO_ADDRESS, 0, 0, 0)
    config = (1, False, 0, 100, fees, False, yieldConfig)  # decimals = 0
    mission_control.setAssetConfig(alpha_token.address, config, sender=switchboard_alpha.address)
    
    fee = mission_control.getRewardsFee(alice, alpha_token.address)
    assert fee == 2500  # Should use global fee


def test_get_ambassador_config_non_yield(mission_control, setUserWalletConfig, createAmbassadorRevShare, alice, alpha_token):
    """Test getting ambassador config for non-yield profit"""
    # Set ambassador fee ratios
    setUserWalletConfig(
        _ambassadorRevShare=createAmbassadorRevShare(
            _swapRatio=4000,  # 40%
            _rewardsRatio=3000,  # 30%
            _yieldRatio=5000  # 50%
        )
    )
    
    config = mission_control.getAmbassadorConfig(alice, alpha_token.address, False)
    
    assert config[0] == alice  # ambassador
    assert config[1][0] == 4000  # swap fee ratio
    assert config[1][1] == 3000  # rewards fee ratio
    assert config[1][2] == 5000  # yield profit fee ratio
    assert config[2] == 0  # ambassadorBonusRatio (0 for non-yield)
    assert config[3] == ZERO_ADDRESS  # underlyingAsset (empty for non-yield)
    assert config[4] == 0  # decimals (0 for non-yield)
    
def test_get_ambassador_config_yield_profit(mission_control, setUserWalletConfig, setAssetConfig, createAssetYieldConfig, createAmbassadorRevShare, alice, alpha_token, bravo_token):
    """Test getting ambassador config for yield profit"""
    # Set ambassador fee ratios
    setUserWalletConfig(
        _ambassadorRevShare=createAmbassadorRevShare(
            _swapRatio=4000,
            _rewardsRatio=3000,
            _yieldRatio=5000
        )
    )
    
    # Set up yield asset
    setAssetConfig(
        alpha_token,
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _underlyingAsset=bravo_token,
            _ambassadorBonusRatio=2000  # 20% bonus
        )
    )
    
    config = mission_control.getAmbassadorConfig(alice, alpha_token.address, True)
    
    assert config[0] == alice
    assert config[1][0] == 4000
    assert config[1][1] == 3000
    assert config[1][2] == 5000
    assert config[2] == 2000  # ambassadorBonusRatio from asset config
    assert config[3] == bravo_token.address  # underlyingAsset from asset config
    assert config[4] == 18  # decimals from asset config


def test_set_can_perform_security_action(mission_control, switchboard_alpha, alice, bob):
    """Test setting security action permissions"""
    # Initially false
    assert mission_control.canPerformSecurityAction(alice) == False
    
    # Grant permission
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)
    assert mission_control.canPerformSecurityAction(alice) == True
    
    # Revoke permission
    mission_control.setCanPerformSecurityAction(alice, False, sender=switchboard_alpha.address)
    assert mission_control.canPerformSecurityAction(alice) == False
    
    # Bob unaffected
    assert mission_control.canPerformSecurityAction(bob) == False
    
def test_set_can_perform_security_action_unauthorized(mission_control, deploy3r, alice):
    """Test unauthorized security action permission change"""
    with boa.reverts("no perms"):
        mission_control.setCanPerformSecurityAction(alice, True, sender=deploy3r)
    
def test_set_creator_whitelist(mission_control, switchboard_alpha, alice, bob):
    """Test managing creator whitelist"""
    # Initially false
    assert mission_control.creatorWhitelist(alice) == False
    
    # Add to whitelist
    mission_control.setCreatorWhitelist(alice, True, sender=switchboard_alpha.address)
    assert mission_control.creatorWhitelist(alice) == True
    
    # Remove from whitelist
    mission_control.setCreatorWhitelist(alice, False, sender=switchboard_alpha.address)
    assert mission_control.creatorWhitelist(alice) == False
    
    # Bob unaffected
    assert mission_control.creatorWhitelist(bob) == False
    
def test_set_creator_whitelist_unauthorized(mission_control, deploy3r, alice):
    """Test unauthorized creator whitelist change"""
    with boa.reverts("no perms"):
        mission_control.setCreatorWhitelist(alice, True, sender=deploy3r)
    
def test_set_locked_signer(mission_control, switchboard_alpha, alice, bob):
    """Test locking/unlocking signers"""
    # Initially false
    assert mission_control.isLockedSigner(alice) == False
    
    # Lock signer
    mission_control.setLockedSigner(alice, True, sender=switchboard_alpha.address)
    assert mission_control.isLockedSigner(alice) == True
    
    # Unlock signer
    mission_control.setLockedSigner(alice, False, sender=switchboard_alpha.address)
    assert mission_control.isLockedSigner(alice) == False
    
    # Bob unaffected
    assert mission_control.isLockedSigner(bob) == False
    
def test_set_locked_signer_unauthorized(mission_control, deploy3r, alice):
    """Test unauthorized signer lock change"""
    with boa.reverts("no perms"):
        mission_control.setLockedSigner(alice, True, sender=deploy3r)


def test_full_wallet_creation_flow(mission_control, switchboard_alpha, setUserWalletConfig, setManagerConfig, setPayeeConfig, setAgentConfig, alice):
    """Test complete wallet creation configuration flow"""
    # Set all configs
    setUserWalletConfig(_enforceCreatorWhitelist=True)
    setManagerConfig()
    setPayeeConfig()
    setAgentConfig(_enforceCreatorWhitelist=True)
    
    # Alice not whitelisted - should not be allowed
    wallet_config = mission_control.getUserWalletCreationConfig(alice)
    agent_config = mission_control.getAgentCreationConfig(alice)
    
    assert wallet_config[1] == False  # isCreatorAllowed for wallet
    assert agent_config[2] == False  # isCreatorAllowed for agent
    
    # Whitelist alice
    mission_control.setCreatorWhitelist(alice, True, sender=switchboard_alpha.address)
    
    # Now alice should be allowed
    wallet_config = mission_control.getUserWalletCreationConfig(alice)
    agent_config = mission_control.getAgentCreationConfig(alice)
    
    assert wallet_config[1] == True
    assert agent_config[2] == True
    
def test_complex_fee_scenario(mission_control, setUserWalletConfig, setAssetConfig, alice, alpha_token, bravo_token, charlie_token):
    """Test complex fee calculation scenarios"""
    # Set global fees
    setUserWalletConfig(_swapFee=200, _stableSwapFee=10, _rewardsFee=3000)
    
    # alpha: regular token with default fees
    # bravo: stablecoin with custom fees
    setAssetConfig(bravo_token, _isStablecoin=True, _swapFee=50, _rewardsFee=1000)
    # charlie: stablecoin with default fees
    setAssetConfig(charlie_token, _isStablecoin=True)
    
    # Regular swap: should use global fee
    assert mission_control.getSwapFee(alice, alpha_token.address, alpha_token.address) == 200
    
    # Stable to stable: always uses stable swap fee regardless of custom fees
    assert mission_control.getSwapFee(alice, charlie_token.address, bravo_token.address) == 10
    
    # Stable to stable without custom: should use stable fee
    assert mission_control.getSwapFee(alice, bravo_token.address, charlie_token.address) == 10
    
    # Regular to stable with custom: should use custom
    assert mission_control.getSwapFee(alice, alpha_token.address, bravo_token.address) == 50
    
    # Rewards fees
    assert mission_control.getRewardsFee(alice, alpha_token.address) == 3000  # global
    assert mission_control.getRewardsFee(alice, bravo_token.address) == 1000  # custom
    assert mission_control.getRewardsFee(alice, charlie_token.address) == 2000  # default from fixture
    
def test_yield_asset_configuration(mission_control, setAssetConfig, createAssetYieldConfig, alice, alpha_token, bravo_token):
    """Test complete yield asset configuration"""
    # Configure a rebasing yield asset
    setAssetConfig(
        alpha_token,
        _legoId=5,
        _staleBlocks=250,
        _yieldConfig=createAssetYieldConfig(
            _isYieldAsset=True,
            _isRebasing=True,
            _underlyingAsset=bravo_token,
            _maxYieldIncrease=2000,  # 20%
            _performanceFee=1000,  # 10%
            _ambassadorBonusRatio=3000  # 30%
        )
    )
    
    # Get profit calc config
    profit_config = mission_control.getProfitCalcConfig(alpha_token.address)
    assert profit_config[4] == True  # isYieldAsset
    assert profit_config[5] == True  # isRebasing
    assert profit_config[6] == bravo_token.address
    assert profit_config[7] == 2000
    assert profit_config[8] == 1000
    
    # Get ambassador config for yield
    amb_config = mission_control.getAmbassadorConfig(alice, alpha_token.address, True)
    assert amb_config[2] == 3000  # ambassadorBonusRatio
    assert amb_config[3] == bravo_token.address
    
    # Get USD value config
    usd_config = mission_control.getAssetUsdValueConfig(alpha_token.address)
    assert usd_config[4] == True  # isYieldAsset
    assert usd_config[5] == bravo_token.address
