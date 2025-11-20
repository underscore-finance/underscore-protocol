import pytest
import boa
from constants import ZERO_ADDRESS


########################
# Access Control Tests #
########################


def test_set_user_wallet_config_access(mission_control, bob, createTxFees, createAmbassadorRevShare, createAssetYieldConfig):
    """Only switchboard_alpha should be able to set user wallet config"""
    config = (
        ZERO_ADDRESS,  # walletTemplate
        ZERO_ADDRESS,  # configTemplate
        10,            # numUserWalletsAllowed
        False,         # enforceCreatorWhitelist
        100,           # minKeyActionTimeLock
        1000,          # maxKeyActionTimeLock
        ZERO_ADDRESS,  # depositRewardsAsset
        86400,         # lootClaimCoolOffPeriod
        createTxFees(30, 10, 50),  # txFees
        createAmbassadorRevShare(100, 200, 300),  # ambassadorRevShare
        createAssetYieldConfig(10000, 1000, 500, 1000, ZERO_ADDRESS),  # yieldConfig
    )
    
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setUserWalletConfig(config, sender=bob)


def test_set_manager_config_access(mission_control, bob):
    """Only switchboard_alpha should be able to set manager config"""
    config = (
        86400,  # managerPeriod
        100,    # managerActivationLength
        False,  # mustHaveUsdValueOnSwaps
        0,      # maxNumSwapsPerPeriod
        0,      # maxSlippageOnSwaps
        False,  # onlyApprovedYieldOpps
    )

    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setManagerConfig(config, sender=bob)


def test_set_payee_config_access(mission_control, bob):
    """Only switchboard_alpha should be able to set payee config"""
    config = (
        86400,  # payeePeriod
        100,    # payeeActivationLength
    )
    
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setPayeeConfig(config, sender=bob)


def test_set_cheque_config_access(mission_control, bob):
    """Only switchboard_alpha should be able to set cheque config"""
    config = (
        10,     # maxNumActiveCheques
        1000,   # instantUsdThreshold
        86400,  # periodLength
        100,    # expensiveDelayBlocks
        1000,   # defaultExpiryBlocks
    )
    
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setChequeConfig(config, sender=bob)


def test_set_agent_config_access(mission_control, bob):
    """Only switchboard_alpha should be able to set agent config"""
    config = (
        ZERO_ADDRESS,  # agentTemplate
        5,             # numAgentsAllowed
        False,         # enforceCreatorWhitelist
        ZERO_ADDRESS,  # startingAgent
        100,           # startingAgentActivationLength
    )
    
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setAgentConfig(config, sender=bob)


def test_set_starter_agent_access(mission_control, bob, alice):
    """Only switchboard_alpha should be able to set starter agent"""
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setStarterAgent(alice, sender=bob)


def test_set_asset_config_access(mission_control, bob, alice, createTxFees, createAmbassadorRevShare, createAssetYieldConfig):
    """Only switchboard_alpha should be able to set asset config"""
    config = (
        True,  # hasConfig
        createTxFees(30, 10, 50),  # txFees
        createAmbassadorRevShare(100, 200, 300),  # ambassadorRevShare
        createAssetYieldConfig(
            10000,         # maxYieldIncrease
            1000,          # performanceFee
            500,           # ambassadorBonusRatio
            1000,          # bonusRatio
            ZERO_ADDRESS,  # bonusAsset
        ),
    )
    
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setAssetConfig(alice, config, sender=bob)


def test_set_is_stablecoin_access(mission_control, bob, alice):
    """Only switchboard_alpha should be able to set stablecoin status"""
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setIsStablecoin(alice, True, sender=bob)


def test_set_can_perform_security_action_access(mission_control, bob, alice):
    """Only switchboard_alpha should be able to set security action permissions"""
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setCanPerformSecurityAction(alice, True, sender=bob)


def test_set_creator_whitelist_access(mission_control, bob, alice):
    """Only switchboard_alpha should be able to set creator whitelist"""
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setCreatorWhitelist(alice, True, sender=bob)


def test_set_locked_signer_access(mission_control, bob, alice):
    """Only switchboard_alpha should be able to set locked signer"""
    # Non-switchboard_alpha address should fail
    with boa.reverts("no perms"):
        mission_control.setLockedSigner(alice, True, sender=bob)


def test_paused_state_blocks_changes(mission_control, switchboard_alpha, createTxFees, createAmbassadorRevShare, createAssetYieldConfig):
    """All setter functions should fail when protocol is paused"""
    # Pause the protocol
    mission_control.pause(True, sender=switchboard_alpha.address)

    # All these should fail when paused
    with boa.reverts("not activated"):
        mission_control.setUserWalletConfig((
            ZERO_ADDRESS, ZERO_ADDRESS, 100, False, 1000, 10000, ZERO_ADDRESS, 86400,
            createTxFees(), createAmbassadorRevShare(), createAssetYieldConfig()
        ), sender=switchboard_alpha.address)
    
    with boa.reverts("not activated"):
        mission_control.setManagerConfig((86400, 100, False, 0, 0, False), sender=switchboard_alpha.address)
    
    with boa.reverts("not activated"):
        mission_control.setPayeeConfig((86400, 100), sender=switchboard_alpha.address)
    
    with boa.reverts("not activated"):
        mission_control.setChequeConfig((10, 1000, 86400, 100, 1000), sender=switchboard_alpha.address)
    
    with boa.reverts("not activated"):
        mission_control.setAgentConfig((ZERO_ADDRESS, 5, False, ZERO_ADDRESS, 100), sender=switchboard_alpha.address)


###########################
# State Persistence Tests #
###########################


def test_user_wallet_config_persistence(mission_control, switchboard_alpha, alice, createTxFees, createAmbassadorRevShare, createAssetYieldConfig):
    """User wallet config should persist after being set"""
    wallet_template = alice
    config_template = alice
    deposit_rewards_asset = alice
    alt_bonus_asset = alice

    config = (
        wallet_template,
        config_template,
        10,            # numUserWalletsAllowed
        True,          # enforceCreatorWhitelist
        200,           # minKeyActionTimeLock
        2000,          # maxKeyActionTimeLock
        deposit_rewards_asset,
        172800,        # lootClaimCoolOffPeriod
        createTxFees(30, 10, 50),
        createAmbassadorRevShare(100, 200, 300),
        createAssetYieldConfig(15000, 1500, 600, 1200, alt_bonus_asset),
    )

    # Set config
    mission_control.setUserWalletConfig(config, sender=switchboard_alpha.address)

    # Verify each field persists
    saved_config = mission_control.userWalletConfig()
    assert saved_config.walletTemplate == wallet_template
    assert saved_config.configTemplate == config_template
    assert saved_config.numUserWalletsAllowed == 10
    assert saved_config.enforceCreatorWhitelist == True
    assert saved_config.minKeyActionTimeLock == 200
    assert saved_config.maxKeyActionTimeLock == 2000
    assert saved_config.depositRewardsAsset == deposit_rewards_asset
    assert saved_config.lootClaimCoolOffPeriod == 172800
    assert saved_config.txFees.swapFee == 30
    assert saved_config.txFees.stableSwapFee == 10
    assert saved_config.txFees.rewardsFee == 50
    assert saved_config.ambassadorRevShare.swapRatio == 100
    assert saved_config.ambassadorRevShare.rewardsRatio == 200
    assert saved_config.ambassadorRevShare.yieldRatio == 300
    assert saved_config.yieldConfig.maxYieldIncrease == 15000
    assert saved_config.yieldConfig.performanceFee == 1500
    assert saved_config.yieldConfig.ambassadorBonusRatio == 600
    assert saved_config.yieldConfig.bonusRatio == 1200
    assert saved_config.yieldConfig.bonusAsset == alt_bonus_asset


def test_agent_config_persistence(mission_control, switchboard_alpha, alice):
    """Agent config should persist after being set"""
    agent_template = alice
    starting_agent = alice
    
    config = (
        agent_template,
        5,              # numAgentsAllowed
        True,           # enforceCreatorWhitelist
        starting_agent,
        200,            # startingAgentActivationLength
    )
    
    # Set config
    mission_control.setAgentConfig(config, sender=switchboard_alpha.address)
    
    # Verify each field persists
    saved_config = mission_control.agentConfig()
    assert saved_config.agentTemplate == agent_template
    assert saved_config.numAgentsAllowed == 5
    assert saved_config.enforceCreatorWhitelist == True
    assert saved_config.startingAgent == starting_agent
    assert saved_config.startingAgentActivationLength == 200
    
    # Test setStarterAgent separately
    mission_control.setStarterAgent(ZERO_ADDRESS, sender=switchboard_alpha.address)
    assert mission_control.agentConfig().startingAgent == ZERO_ADDRESS


def test_manager_config_persistence(mission_control, switchboard_alpha):
    """Manager config should persist after being set"""
    config = (
        172800,  # managerPeriod
        200,     # managerActivationLength
        True,    # mustHaveUsdValueOnSwaps
        10,      # maxNumSwapsPerPeriod
        500,     # maxSlippageOnSwaps
        True,    # onlyApprovedYieldOpps
    )

    # Set config
    mission_control.setManagerConfig(config, sender=switchboard_alpha.address)

    # Verify fields persist
    saved_config = mission_control.managerConfig()
    assert saved_config.managerPeriod == 172800
    assert saved_config.managerActivationLength == 200
    assert saved_config.mustHaveUsdValueOnSwaps == True
    assert saved_config.maxNumSwapsPerPeriod == 10
    assert saved_config.maxSlippageOnSwaps == 500
    assert saved_config.onlyApprovedYieldOpps == True


def test_payee_config_persistence(mission_control, switchboard_alpha):
    """Payee config should persist after being set"""
    config = (
        172800,  # payeePeriod
        200,     # payeeActivationLength
    )
    
    # Set config
    mission_control.setPayeeConfig(config, sender=switchboard_alpha.address)
    
    # Verify fields persist
    saved_config = mission_control.payeeConfig()
    assert saved_config.payeePeriod == 172800
    assert saved_config.payeeActivationLength == 200


def test_cheque_config_persistence(mission_control, switchboard_alpha):
    """Cheque config should persist after being set"""
    config = (
        20,      # maxNumActiveCheques
        2000,    # instantUsdThreshold
        172800,  # periodLength
        200,     # expensiveDelayBlocks
        2000,    # defaultExpiryBlocks
    )
    
    # Set config
    mission_control.setChequeConfig(config, sender=switchboard_alpha.address)
    
    # Verify fields persist
    saved_config = mission_control.chequeConfig()
    assert saved_config.maxNumActiveCheques == 20
    assert saved_config.instantUsdThreshold == 2000
    assert saved_config.periodLength == 172800
    assert saved_config.expensiveDelayBlocks == 200
    assert saved_config.defaultExpiryBlocks == 2000


def test_asset_config_persistence(mission_control, switchboard_alpha, alice, createTxFees, createAmbassadorRevShare, createAssetYieldConfig):
    """Asset config should persist after being set"""
    asset = alice
    underlying_asset = alice
    alt_bonus_asset = alice
    
    config = (
        True,   # hasConfig
        createTxFees(40, 20, 60),
        createAmbassadorRevShare(150, 250, 350),
        createAssetYieldConfig(
            20000,           # maxYieldIncrease
            2000,            # performanceFee
            700,             # ambassadorBonusRatio
            1400,            # bonusRatio
            alt_bonus_asset,
        ),
    )

    # Set config
    mission_control.setAssetConfig(asset, config, sender=switchboard_alpha.address)

    # Verify fields persist
    saved_config = mission_control.assetConfig(asset)
    assert saved_config.hasConfig == True
    assert saved_config.txFees.swapFee == 40
    assert saved_config.txFees.stableSwapFee == 20
    assert saved_config.txFees.rewardsFee == 60
    assert saved_config.ambassadorRevShare.swapRatio == 150
    assert saved_config.ambassadorRevShare.rewardsRatio == 250
    assert saved_config.ambassadorRevShare.yieldRatio == 350
    # isYieldAsset, isRebasing, and underlyingAsset are now derived from Ledger
    assert saved_config.yieldConfig.maxYieldIncrease == 20000
    assert saved_config.yieldConfig.performanceFee == 2000
    assert saved_config.yieldConfig.ambassadorBonusRatio == 700
    assert saved_config.yieldConfig.bonusRatio == 1400
    assert saved_config.yieldConfig.bonusAsset == alt_bonus_asset


def test_stablecoin_status_persistence(mission_control, switchboard_alpha, alice):
    """Stablecoin status should persist after being set"""
    asset = alice
    
    # Initially should be false
    assert not mission_control.isStablecoin(asset)
    
    # Set to true
    mission_control.setIsStablecoin(asset, True, sender=switchboard_alpha.address)
    assert mission_control.isStablecoin(asset)
    
    # Set back to false
    mission_control.setIsStablecoin(asset, False, sender=switchboard_alpha.address)
    assert not mission_control.isStablecoin(asset)


def test_security_settings_persistence(mission_control, switchboard_alpha, alice, bob):
    """Security settings should persist after being set"""
    # Test canPerformSecurityAction
    assert not mission_control.canPerformSecurityAction(alice)
    mission_control.setCanPerformSecurityAction(alice, True, sender=switchboard_alpha.address)
    assert mission_control.canPerformSecurityAction(alice)
    
    # Test creatorWhitelist
    assert not mission_control.creatorWhitelist(bob)
    mission_control.setCreatorWhitelist(bob, True, sender=switchboard_alpha.address)
    assert mission_control.creatorWhitelist(bob)
    
    # Test isLockedSigner
    assert not mission_control.isLockedSigner(alice)
    mission_control.setLockedSigner(alice, True, sender=switchboard_alpha.address)
    assert mission_control.isLockedSigner(alice)


#########################
# Helper Function Tests #
#########################


def test_get_user_wallet_creation_config(mission_control, switchboard_alpha, alice, bob, createTxFees, createAmbassadorRevShare, createAssetYieldConfig):
    """getUserWalletCreationConfig should return correct aggregated data"""
    # Set configs
    wallet_template = alice
    config_template = bob
    starting_agent = bob
    
    mission_control.setUserWalletConfig((
        wallet_template, config_template, 10, False, 200, 2000, ZERO_ADDRESS, 172800,
        createTxFees(), createAmbassadorRevShare(), createAssetYieldConfig()
    ), sender=switchboard_alpha.address)
    
    mission_control.setAgentConfig((
        alice, 5, False, starting_agent, 300
    ), sender=switchboard_alpha.address)

    mission_control.setManagerConfig((172800, 200, False, 0, 0, False), sender=switchboard_alpha.address)
    mission_control.setPayeeConfig((172800, 200), sender=switchboard_alpha.address)
    mission_control.setChequeConfig((20, 2000, 172800, 200, 2000), sender=switchboard_alpha.address)
    
    # Get creation config
    creation_config = mission_control.getUserWalletCreationConfig(alice)
    
    # Verify all fields
    assert creation_config.numUserWalletsAllowed == 10
    assert creation_config.isCreatorAllowed == True  # whitelist not enforced
    assert creation_config.walletTemplate == wallet_template
    assert creation_config.configTemplate == config_template
    assert creation_config.startingAgent == starting_agent
    assert creation_config.startingAgentActivationLength == 300
    assert creation_config.managerPeriod == 172800
    assert creation_config.managerActivationLength == 200
    assert creation_config.payeePeriod == 172800
    assert creation_config.payeeActivationLength == 200
    assert creation_config.chequeMaxNumActiveCheques == 20
    assert creation_config.chequeInstantUsdThreshold == 2000
    assert creation_config.chequePeriodLength == 172800
    assert creation_config.chequeExpensiveDelayBlocks == 200
    assert creation_config.chequeDefaultExpiryBlocks == 2000
    # trialAsset and trialAmount have been removed from the struct
    assert creation_config.minKeyActionTimeLock == 200
    assert creation_config.maxKeyActionTimeLock == 2000


def test_get_user_wallet_creation_config_whitelist_enforced(mission_control, switchboard_alpha, alice, createTxFees, createAmbassadorRevShare, createAssetYieldConfig):
    """When whitelist is enforced, only whitelisted creators should be allowed"""
    # Enable whitelist enforcement
    mission_control.setUserWalletConfig((
        ZERO_ADDRESS, ZERO_ADDRESS, 10, True, 100, 1000, ZERO_ADDRESS, 86400,
        createTxFees(), createAmbassadorRevShare(), createAssetYieldConfig()
    ), sender=switchboard_alpha.address)
    
    # Non-whitelisted creator should not be allowed
    creation_config = mission_control.getUserWalletCreationConfig(alice)
    assert creation_config.isCreatorAllowed == False
    
    # Whitelist the creator
    mission_control.setCreatorWhitelist(alice, True, sender=switchboard_alpha.address)
    
    # Now they should be allowed
    creation_config = mission_control.getUserWalletCreationConfig(alice)
    assert creation_config.isCreatorAllowed == True


def test_get_swap_fee_logic(mission_control, switchboard_alpha, alice, bob, charlie, createTxFees, createAmbassadorRevShare, createAssetYieldConfig):
    """Test swap fee calculation logic"""
    # Set user wallet config
    mission_control.setUserWalletConfig((
        ZERO_ADDRESS, ZERO_ADDRESS, 10, False, 100, 1000, ZERO_ADDRESS, 86400,
        createTxFees(30, 10, 50), createAmbassadorRevShare(), createAssetYieldConfig()
    ), sender=switchboard_alpha.address)
    
    # Test default swap fee (no asset configs)
    assert mission_control.getSwapFee(alice, bob) == 30
    
    # Set stablecoin status for testing stable swap
    mission_control.setIsStablecoin(alice, True, sender=switchboard_alpha.address)
    mission_control.setIsStablecoin(bob, True, sender=switchboard_alpha.address)
    
    # Test stable swap fee
    assert mission_control.getSwapFee(alice, bob) == 10
    
    # Set asset config for tokenOut
    mission_control.setAssetConfig(charlie, (
        True, createTxFees(100, 50, 200), createAmbassadorRevShare(), createAssetYieldConfig()
    ), sender=switchboard_alpha.address)
    
    # Asset swap fee should take precedence
    assert mission_control.getSwapFee(alice, charlie) == 100