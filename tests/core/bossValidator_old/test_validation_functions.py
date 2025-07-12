"""
Test validation functions in BossValidator
"""
import pytest
import boa
from eth_utils import to_checksum_address

from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ONE_YEAR_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setup_wallet(setUserWalletConfig, setManagerConfig, hatchery, bob):
    """Setup user wallet with config"""
    setUserWalletConfig()
    setManagerConfig()
    
    wallet_addr = hatchery.createUserWallet(sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


@pytest.fixture(scope="module")
def setup_contracts(setup_wallet, boss_validator, alice, bob):
    """Setup contracts and basic configuration"""
    user_wallet = setup_wallet
    wallet_config_addr = user_wallet.walletConfig()
    wallet_config = UserWalletConfig.at(wallet_config_addr)
    owner = bob
    
    return {
        'wallet': user_wallet,
        'wallet_config': wallet_config,
        'boss_validator': boss_validator,
        'owner': owner,
        'manager': alice
    }


# Test manager period validation


def test_validate_manager_period(setup_contracts, createGlobalManagerSettings):
    """Test manager period validation through validateGlobalManagerSettings"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    # Get min/max from contract
    min_period = boss.MIN_MANAGER_PERIOD()
    max_period = boss.MAX_MANAGER_PERIOD()
    
    wallet_config = ctx['wallet_config']
    
    # Valid period
    settings = createGlobalManagerSettings(_managerPeriod=ONE_DAY_IN_BLOCKS)
    assert boss.validateGlobalManagerSettings(settings, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    # At boundaries
    settings_min = createGlobalManagerSettings(_managerPeriod=min_period)
    assert boss.validateGlobalManagerSettings(settings_min, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    settings_max = createGlobalManagerSettings(_managerPeriod=max_period)
    assert boss.validateGlobalManagerSettings(settings_max, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    # Invalid: too short
    settings_short = createGlobalManagerSettings(_managerPeriod=min_period - 1)
    assert not boss.validateGlobalManagerSettings(settings_short, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    # Invalid: too long
    settings_long = createGlobalManagerSettings(_managerPeriod=max_period + 1)
    assert not boss.validateGlobalManagerSettings(settings_long, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    # Invalid: zero
    settings_zero = createGlobalManagerSettings(_managerPeriod=0)
    assert not boss.validateGlobalManagerSettings(settings_zero, False, 0, ZERO_ADDRESS, wallet_config.address)


def test_validate_start_delay(setup_contracts, createGlobalManagerSettings):
    """Test start delay validation through validateGlobalManagerSettings"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    max_start_delay = boss.MAX_START_DELAY()
    
    wallet_config = ctx['wallet_config']
    
    # Valid delays
    settings_no_delay = createGlobalManagerSettings(_startDelay=0)
    assert boss.validateGlobalManagerSettings(settings_no_delay, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    settings_day_delay = createGlobalManagerSettings(_startDelay=ONE_DAY_IN_BLOCKS)
    assert boss.validateGlobalManagerSettings(settings_day_delay, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    settings_max_delay = createGlobalManagerSettings(_startDelay=max_start_delay)
    assert boss.validateGlobalManagerSettings(settings_max_delay, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    # Invalid: exceeds max
    settings_exceed = createGlobalManagerSettings(_startDelay=max_start_delay + 1)
    assert not boss.validateGlobalManagerSettings(settings_exceed, False, 0, ZERO_ADDRESS, wallet_config.address)


def test_validate_activation_length(setup_contracts, createGlobalManagerSettings):
    """Test activation length validation through validateGlobalManagerSettings"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    min_length = boss.MIN_ACTIVATION_LENGTH()
    max_length = boss.MAX_ACTIVATION_LENGTH()
    
    wallet_config = ctx['wallet_config']
    
    # Valid lengths
    settings_year = createGlobalManagerSettings(_activationLength=ONE_YEAR_IN_BLOCKS)
    assert boss.validateGlobalManagerSettings(settings_year, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    settings_min = createGlobalManagerSettings(_activationLength=min_length)
    assert boss.validateGlobalManagerSettings(settings_min, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    settings_max = createGlobalManagerSettings(_activationLength=max_length)
    assert boss.validateGlobalManagerSettings(settings_max, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    # Invalid: too short
    settings_short = createGlobalManagerSettings(_activationLength=min_length - 1)
    assert not boss.validateGlobalManagerSettings(settings_short, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    # Invalid: too long  
    settings_long = createGlobalManagerSettings(_activationLength=max_length + 1)
    assert not boss.validateGlobalManagerSettings(settings_long, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    # Invalid: zero
    settings_zero = createGlobalManagerSettings(_activationLength=0)
    assert not boss.validateGlobalManagerSettings(settings_zero, False, 0, ZERO_ADDRESS, wallet_config.address)


# Test lego permissions validation


def test_validate_lego_perms_basic(setup_contracts, createLegoPerms, createManagerSettings, lego_book):
    """Test basic lego permissions validation through validateSpecificManagerSettings"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # All permissions enabled, no restrictions
    perms = createLegoPerms()
    settings = createManagerSettings(_legoPerms=perms)
    assert boss.validateSpecificManagerSettings(
        settings,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Empty allowed legos list (means all allowed)
    perms_empty = createLegoPerms(_allowedLegos=[])
    settings_empty = createManagerSettings(_legoPerms=perms_empty)
    assert boss.validateSpecificManagerSettings(
        settings_empty,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # With specific lego restrictions - only lego ID 1 exists
    perms_restricted = createLegoPerms(_allowedLegos=[1])
    settings_restricted = createManagerSettings(_legoPerms=perms_restricted)
    assert boss.validateSpecificManagerSettings(
        settings_restricted,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


def test_validate_lego_perms_invalid_ids(setup_contracts, createLegoPerms, createManagerSettings, lego_book):
    """Test lego permissions with invalid lego IDs"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Lego ID 999 doesn't exist in lego book (only ID 1 exists)
    perms_invalid = createLegoPerms(_allowedLegos=[1, 999])
    settings_invalid = createManagerSettings(_legoPerms=perms_invalid)
    assert not boss.validateSpecificManagerSettings(
        settings_invalid,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Duplicate lego IDs
    perms_duplicate = createLegoPerms(_allowedLegos=[1, 1])
    settings_duplicate = createManagerSettings(_legoPerms=perms_duplicate)
    assert not boss.validateSpecificManagerSettings(
        settings_duplicate,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


def test_validate_lego_perms_eject_mode(setup_contracts, createLegoPerms, createManagerSettings):
    """Test lego permissions validation in eject mode"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # In eject mode, cannot have allowed legos list - it must be empty
    perms = createLegoPerms(_allowedLegos=[])  # Must be empty in eject mode
    settings = createManagerSettings(_legoPerms=perms)
    assert boss.validateSpecificManagerSettings(
        settings,
        ONE_DAY_IN_BLOCKS,
        True,  # eject mode
        ZERO_ADDRESS,  # lego book address ignored
        wallet_config.address
    )
    
    # With allowed legos in eject mode should fail
    perms_with_legos = createLegoPerms(_allowedLegos=[1])
    settings_with_legos = createManagerSettings(_legoPerms=perms_with_legos)
    assert not boss.validateSpecificManagerSettings(
        settings_with_legos,
        ONE_DAY_IN_BLOCKS,
        True,  # eject mode
        ZERO_ADDRESS,
        wallet_config.address
    )


def test_validate_lego_perms_limits(setup_contracts, createLegoPerms, createManagerSettings, lego_book):
    """Test lego permissions with max allowed legos"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Test with single lego (ID 1 exists)
    perms_single = createLegoPerms(_allowedLegos=[1])
    settings_single = createManagerSettings(_legoPerms=perms_single)
    assert boss.validateSpecificManagerSettings(
        settings_single,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Test empty allowed legos (means all legos allowed)
    perms_empty = createLegoPerms(_allowedLegos=[])
    settings_empty = createManagerSettings(_legoPerms=perms_empty)
    assert boss.validateSpecificManagerSettings(
        settings_empty,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Test that validation fails with too many legos
    # Create a list with exactly 25 legos (the maximum)
    max_legos = list(range(1, 26))  # [1, 2, ..., 25]
    perms_max = createLegoPerms(_allowedLegos=max_legos)
    settings_max = createManagerSettings(_legoPerms=perms_max)
    
    # This should fail because only lego ID 1 exists in the test setup
    assert not boss.validateSpecificManagerSettings(
        settings_max,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


# Test transfer permissions validation


def test_validate_transfer_perms_basic(setup_contracts, createTransferPerms, createManagerSettings, lego_book):
    """Test basic transfer permissions validation"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # All permissions enabled, no restrictions
    perms = createTransferPerms()
    settings = createManagerSettings(_transferPerms=perms)
    assert boss.validateSpecificManagerSettings(
        settings,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # With specific payee restrictions - using empty list which is valid
    perms_restricted = createTransferPerms(_allowedPayees=[])
    settings_restricted = createManagerSettings(_transferPerms=perms_restricted)
    assert boss.validateSpecificManagerSettings(
        settings_restricted,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


def test_validate_transfer_perms_registered_payees(setup_contracts, createTransferPerms,
                                                  createPayeeSettings, createManagerSettings,
                                                  paymaster, alice, lego_book):
    """Test transfer permissions with registered payees"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Register a payee
    payee_settings = createPayeeSettings()
    wallet_config.addPayee(alice, payee_settings, sender=paymaster.address)
    
    # Allowed payees must be registered
    perms_valid = createTransferPerms(_allowedPayees=[alice])
    settings_valid = createManagerSettings(_transferPerms=perms_valid)
    assert boss.validateSpecificManagerSettings(
        settings_valid,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Unregistered payee should fail
    unregistered = to_checksum_address("0x" + "9" * 40)
    perms_invalid = createTransferPerms(_allowedPayees=[unregistered])
    settings_invalid = createManagerSettings(_transferPerms=perms_invalid)
    assert not boss.validateSpecificManagerSettings(
        settings_invalid,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


def test_validate_transfer_perms_limits(setup_contracts, createTransferPerms, 
                                       createPayeeSettings, createManagerSettings,
                                       paymaster, lego_book):
    """Test transfer permissions with max allowed payees"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Register max allowed payees (40)
    payees = []
    for i in range(40):
        payee = to_checksum_address(f"0x{str(i+1).zfill(40)}")
        payee_settings = createPayeeSettings()
        wallet_config.addPayee(payee, payee_settings, sender=paymaster.address)
        payees.append(payee)
    
    # Max allowed payees
    perms_max = createTransferPerms(_allowedPayees=payees)
    settings_max = createManagerSettings(_transferPerms=perms_max)
    assert boss.validateSpecificManagerSettings(
        settings_max,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Test validation with unregistered payee (which should fail)
    # Add an unregistered payee to the existing list
    unregistered_payee = to_checksum_address("0x" + "f" * 40)
    perms_with_unregistered = createTransferPerms(_allowedPayees=payees[:39] + [unregistered_payee])
    settings_with_unregistered = createManagerSettings(_transferPerms=perms_with_unregistered)
    
    # This should fail because the unregistered payee is not registered
    assert not boss.validateSpecificManagerSettings(
        settings_with_unregistered,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


# Test allowed assets validation


def test_validate_allowed_assets_basic(setup_contracts, createManagerSettings, alpha_token, lego_book):
    """Test basic allowed assets validation"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Empty list (all assets allowed)
    settings_empty = createManagerSettings(_allowedAssets=[])
    assert boss.validateSpecificManagerSettings(
        settings_empty,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # With specific assets
    settings_single = createManagerSettings(_allowedAssets=[alpha_token.address])
    assert boss.validateSpecificManagerSettings(
        settings_single,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Multiple assets
    asset1 = to_checksum_address("0x" + "1" * 40)
    asset2 = to_checksum_address("0x" + "2" * 40)
    settings_multiple = createManagerSettings(_allowedAssets=[asset1, asset2])
    assert boss.validateSpecificManagerSettings(
        settings_multiple,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


def test_validate_allowed_assets_invalid(setup_contracts, createManagerSettings, lego_book):
    """Test allowed assets validation with invalid inputs"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Zero address not allowed
    settings_zero = createManagerSettings(_allowedAssets=[ZERO_ADDRESS])
    assert not boss.validateSpecificManagerSettings(
        settings_zero,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Duplicate assets not allowed
    asset1 = to_checksum_address("0x" + "1" * 40)
    settings_duplicate = createManagerSettings(_allowedAssets=[asset1, asset1])
    assert not boss.validateSpecificManagerSettings(
        settings_duplicate,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Mixed valid and invalid
    asset2 = to_checksum_address("0x" + "2" * 40)
    settings_mixed = createManagerSettings(_allowedAssets=[asset1, ZERO_ADDRESS, asset2])
    assert not boss.validateSpecificManagerSettings(
        settings_mixed,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


def test_validate_allowed_assets_limits(setup_contracts, createManagerSettings, lego_book):
    """Test allowed assets with max limit"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Max allowed is 40 assets (from MAX_CONFIG_ASSETS in contract)
    assets = []
    for i in range(40):
        assets.append(to_checksum_address(f"0x{str(i+1).zfill(40)}"))
    
    # Max assets allowed
    settings_max = createManagerSettings(_allowedAssets=assets)
    assert boss.validateSpecificManagerSettings(
        settings_max,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )
    
    # Test validation with duplicate assets (which should fail)
    # Create a list with a duplicate asset
    assets_with_duplicate = assets[:39] + [assets[0]]  # Add duplicate of first asset
    settings_with_duplicate = createManagerSettings(_allowedAssets=assets_with_duplicate)
    
    # This should fail because of duplicate assets
    assert not boss.validateSpecificManagerSettings(
        settings_with_duplicate,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


# Test manager settings validation


def test_validate_specific_manager_settings(setup_contracts, createManagerSettings,
                                          createManagerLimits, lego_book):
    """Test validateSpecificManagerSettings function"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Valid settings
    settings = createManagerSettings()
    assert boss.validateSpecificManagerSettings(
        settings,
        ONE_DAY_IN_BLOCKS,
        False,  # not in eject mode
        lego_book.address,
        wallet_config.address
    )
    
    # Test with invalid limits (per-tx > per-period)
    invalid_limits = createManagerLimits(
        _maxUsdValuePerTx=1000 * EIGHTEEN_DECIMALS,
        _maxUsdValuePerPeriod=100 * EIGHTEEN_DECIMALS
    )
    invalid_settings = createManagerSettings(_limits=invalid_limits)
    assert not boss.validateSpecificManagerSettings(
        invalid_settings,
        ONE_DAY_IN_BLOCKS,
        False,
        lego_book.address,
        wallet_config.address
    )


def test_validate_global_manager_settings(setup_contracts, createGlobalManagerSettings):
    """Test validateGlobalManagerSettings function"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    wallet_config = ctx['wallet_config']
    
    # Valid settings
    settings = createGlobalManagerSettings()
    assert boss.validateGlobalManagerSettings(settings, False, 0, ZERO_ADDRESS, wallet_config.address)
    
    # Invalid: manager period too short
    invalid_settings = createGlobalManagerSettings(
        _managerPeriod=100  # Too short
    )
    assert not boss.validateGlobalManagerSettings(invalid_settings, False, 0, ZERO_ADDRESS, wallet_config.address)


# Test create functions


def test_create_default_global_settings(setup_contracts):
    """Test createDefaultGlobalManagerSettings function"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    settings = boss.createDefaultGlobalManagerSettings(
        ONE_DAY_IN_BLOCKS,  # managerPeriod
        ONE_DAY_IN_BLOCKS,  # minTimeLock
        30 * ONE_DAY_IN_BLOCKS  # defaultActivationLength
    )
    
    # Check the provided values are set correctly
    assert settings[0] == ONE_DAY_IN_BLOCKS  # managerPeriod
    assert settings[1] == ONE_DAY_IN_BLOCKS  # startDelay (set to minTimeLock)
    assert settings[2] == 30 * ONE_DAY_IN_BLOCKS  # activationLength
    assert settings[3] == True  # canOwnerManage (default)
    
    # All limits should be 0 (unlimited)
    limits = settings[4]
    assert limits[0] == 0  # maxUsdValuePerTx
    assert limits[1] == 0  # maxUsdValuePerPeriod
    assert limits[2] == 0  # maxUsdValueLifetime
    
    # All permissions should be enabled
    lego_perms = settings[5]
    assert lego_perms[0] == True  # canManageYield
    assert lego_perms[1] == True  # canBuyAndSell
    assert lego_perms[2] == True  # canManageDebt
    assert lego_perms[3] == True  # canManageLiq
    assert lego_perms[4] == True  # canClaimRewards


def test_create_starter_agent_settings(setup_contracts):
    """Test createStarterAgentSettings function"""
    ctx = setup_contracts
    boss = ctx['boss_validator']
    
    activation_length = ONE_YEAR_IN_BLOCKS
    settings = boss.createStarterAgentSettings(activation_length)
    
    # Check settings
    current_block = boa.env.evm.patch.block_number
    assert settings[0] == current_block  # startBlock
    assert settings[1] == current_block + activation_length  # expiryBlock
    
    # All permissions should be enabled
    lego_perms = settings[3]
    assert lego_perms[0] == True  # canManageYield
    assert lego_perms[1] == True  # canBuyAndSell
    
    # No asset restrictions
    assert len(settings[6]) == 0  # allowedAssets