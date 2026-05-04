import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs


#########################
# Global Payee Settings #
#########################


def test_set_global_payee_settings_forces_can_pay_owner_false(paymaster, user_wallet, user_wallet_config, createPayeeLimits, bob):
    """Paymaster should ignore canPayOwner input and emit the stored value"""
    start_delay = user_wallet_config.timeLock()
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS,
    )

    result = paymaster.setGlobalPayeeSettings(
        user_wallet,
        2 * ONE_DAY_IN_BLOCKS,
        start_delay,
        ONE_DAY_IN_BLOCKS,
        10,
        100,
        True,
        usd_limits,
        True,
        sender=bob,
    )

    assert result == True

    saved = user_wallet_config.globalPayeeSettings()
    assert saved.defaultPeriodLength == 2 * ONE_DAY_IN_BLOCKS
    assert saved.startDelay == start_delay
    assert saved.activationLength == ONE_DAY_IN_BLOCKS
    assert saved.maxNumTxsPerPeriod == 10
    assert saved.txCooldownBlocks == 100
    assert saved.failOnZeroPrice == True
    assert saved.canPayOwner == False
    assert saved.canPull == True

    event = filter_logs(paymaster, "GlobalPayeeSettingsModified")[-1]
    assert event.user == user_wallet.address
    assert event.canPayOwner == False
    assert event.canPull == True


#############
# Add Payee #
#############


def test_add_payee_verifies_real_user_wallet(paymaster, createPayeeLimits, alice, bob):
    """Test that addPayee verifies it's a real user wallet"""
    # Try to add payee to a non-wallet address (bob's EOA)
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # This should fail because bob is not a user wallet
    with boa.reverts("invalid user wallet"):
        paymaster.addPayee(
            bob,  # Not a real user wallet, just an EOA
            alice,  # payee
            False,  # canPull
            2 * ONE_DAY_IN_BLOCKS,  # periodLength
            10,  # maxNumTxsPerPeriod
            0,  # txCooldownBlocks
            True,  # failOnZeroPrice
            ZERO_ADDRESS,  # primaryAsset
            False,  # onlyPrimaryAsset
            createPayeeLimits(),  # unitLimits
            usd_limits,  # usdLimits
            sender=bob
        )


def test_add_payee_verifies_caller_is_owner(paymaster, user_wallet, createPayeeLimits, alice, charlie):
    """Test that only the owner can add a payee"""
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Try to add payee as non-owner (alice)
    with boa.reverts("no perms"):
        paymaster.addPayee(
            user_wallet,
            charlie,  # payee
            False,  # canPull
            2 * ONE_DAY_IN_BLOCKS,  # periodLength
            10,  # maxNumTxsPerPeriod
            0,  # txCooldownBlocks
            True,  # failOnZeroPrice
            ZERO_ADDRESS,  # primaryAsset
            False,  # onlyPrimaryAsset
            createPayeeLimits(),  # unitLimits
            usd_limits,  # usdLimits
            sender=alice  # Not the owner
        )


def test_add_payee_rejects_owner_as_payee(paymaster, user_wallet, createPayeeLimits, bob):
    """Owner must use a separate wallet if they want to receive payee payments"""
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )

    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
            user_wallet,
            bob,
            False,
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            usd_limits,
            sender=bob
        )


def test_add_payee_saves_settings_in_wallet_config(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, alpha_token):
    """Test that addPayee correctly saves all payee settings in user wallet config"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create specific limits to verify they're saved correctly
    unit_limits = createPayeeLimits(
        _perTxCap=100,
        _perPeriodCap=1000,
        _lifetimeCap=10000
    )
    usd_limits = createPayeeLimits(
        _perTxCap=2000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=20000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=200000 * EIGHTEEN_DECIMALS
    )

    # Add payee with specific settings
    result = paymaster.addPayee(
        user_wallet,
        alice,  # payee
        True,  # canPull
        3 * ONE_DAY_IN_BLOCKS,  # periodLength
        15,  # maxNumTxsPerPeriod
        500,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        True,  # onlyPrimaryAsset
        unit_limits,  # unitLimits
        usd_limits,  # usdLimits
        sender=bob  # Owner
    )
    
    assert result == True
    
    # Verify the payee was added by checking the index
    assert user_wallet_config.indexOfPayee(alice) != 0

    # Get the payee config bundle to verify all settings
    payee_settings = user_wallet_config.payeeSettings(alice)

    # Verify basic settings
    assert payee_settings.canPull == True
    assert payee_settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert payee_settings.maxNumTxsPerPeriod == 15
    assert payee_settings.txCooldownBlocks == 500
    assert payee_settings.failOnZeroPrice == True
    assert payee_settings.primaryAsset == alpha_token.address
    assert payee_settings.onlyPrimaryAsset == True
    
    # Verify unit limits
    assert payee_settings.unitLimits.perTxCap == 100
    assert payee_settings.unitLimits.perPeriodCap == 1000
    assert payee_settings.unitLimits.lifetimeCap == 10000
    
    # Verify USD limits
    assert payee_settings.usdLimits.perTxCap == 2000 * EIGHTEEN_DECIMALS
    assert payee_settings.usdLimits.perPeriodCap == 20000 * EIGHTEEN_DECIMALS
    assert payee_settings.usdLimits.lifetimeCap == 200000 * EIGHTEEN_DECIMALS
    
    # Also verify the direct public mappings
    # Check that alice is stored at the correct index
    payee_index = user_wallet_config.indexOfPayee(alice)
    assert payee_index > 0  # Should have a non-zero index
    
    # Verify the payee address can be retrieved by index
    assert user_wallet_config.payees(payee_index) == alice
    
    # Verify the number of payees increased
    assert user_wallet_config.numPayees() == 2
    
    # Check the payeeSettings mapping directly
    direct_settings = user_wallet_config.payeeSettings(alice)
    assert direct_settings.canPull == True
    assert direct_settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert direct_settings.maxNumTxsPerPeriod == 15


def test_add_payee_emits_event_with_correct_data(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, alpha_token):
    """Test that addPayee emits PayeeAdded event with all correct data"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create specific limits
    unit_limits = createPayeeLimits(
        _perTxCap=50,
        _perPeriodCap=500,
        _lifetimeCap=5000
    )
    usd_limits = createPayeeLimits(
        _perTxCap=1500 * EIGHTEEN_DECIMALS,
        _perPeriodCap=15000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=150000 * EIGHTEEN_DECIMALS
    )
    
    # Add payee
    paymaster.addPayee(
        user_wallet,
        alice,  # payee
        True,  # canPull
        4 * ONE_DAY_IN_BLOCKS,  # periodLength
        20,  # maxNumTxsPerPeriod
        1000,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        False,  # onlyPrimaryAsset
        unit_limits,  # unitLimits
        usd_limits,  # usdLimits
        100,  # startDelay
        5000,  # activationLength
        sender=bob  # Owner
    )
    
    # Get the event
    event = filter_logs(paymaster, "PayeeAdded")[0]
    
    # Verify indexed fields
    assert event.user == user_wallet.address
    assert event.payee == alice
    
    # Verify start and expiry blocks
    # The actual block numbers depend on when the payee was added
    # Just verify the difference equals our parameters
    assert event.expiryBlock - event.startBlock == 5000  # activationLength
    
    # Verify all settings
    assert event.canPull == True
    assert event.periodLength == 4 * ONE_DAY_IN_BLOCKS
    assert event.maxNumTxsPerPeriod == 20
    assert event.txCooldownBlocks == 1000
    assert event.failOnZeroPrice == True
    assert event.primaryAsset == alpha_token.address
    assert event.onlyPrimaryAsset == False
    
    # Verify unit limits
    assert event.unitPerTxCap == 50
    assert event.unitPerPeriodCap == 500
    assert event.unitLifetimeCap == 5000
    
    # Verify USD limits
    assert event.usdPerTxCap == 1500 * EIGHTEEN_DECIMALS
    assert event.usdPerPeriodCap == 15000 * EIGHTEEN_DECIMALS
    assert event.usdLifetimeCap == 150000 * EIGHTEEN_DECIMALS


def test_add_payee_reverts_on_invalid_settings(paymaster, user_wallet, createPayeeLimits, alice, bob):
    """Test that addPayee reverts with 'invalid payee settings' when validation fails"""
    # Create invalid limits where perTxCap > perPeriodCap
    invalid_usd_limits = createPayeeLimits(
        _perTxCap=10000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,  # Less than perTxCap - invalid!
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # This should fail validation and revert with "invalid payee settings"
    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
            user_wallet,
            alice,  # payee
            False,  # canPull
            2 * ONE_DAY_IN_BLOCKS,  # periodLength
            10,  # maxNumTxsPerPeriod
            0,  # txCooldownBlocks
            True,  # failOnZeroPrice
            ZERO_ADDRESS,  # primaryAsset
            False,  # onlyPrimaryAsset
            createPayeeLimits(),  # unitLimits
            invalid_usd_limits,  # usdLimits with invalid settings
            sender=bob  # Owner
        )
    

################
# Update Payee #
################


def test_update_payee_requires_registered_payee(paymaster, user_wallet, createPayeeLimits, alice, bob):
    """Test that updatePayee requires the payee to be already registered"""
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Try to update a non-existent payee
    with boa.reverts("invalid payee settings"):
        paymaster.updatePayee(
            user_wallet,
            alice,  # Not a registered payee yet
            False,  # canPull
            2 * ONE_DAY_IN_BLOCKS,  # periodLength
            10,  # maxNumTxsPerPeriod
            0,  # txCooldownBlocks
            True,  # failOnZeroPrice
            ZERO_ADDRESS,  # primaryAsset
            False,  # onlyPrimaryAsset
            createPayeeLimits(),  # unitLimits
            usd_limits,  # usdLimits
            sender=bob  # Owner
        )


def test_update_payee_verifies_caller_is_owner(paymaster, user_wallet, createPayeeLimits, alice, bob, charlie):
    """Test that only the owner can update a payee"""
    # First add alice as a payee
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    # Try to update as non-owner (charlie)
    with boa.reverts("no perms"):
        paymaster.updatePayee(
            user_wallet,
            alice,
            True,  # canPull (changing)
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            usd_limits,
            sender=charlie  # Not the owner
        )


def test_update_payee_saves_new_settings(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, alpha_token, bravo_token):
    """Test that updatePayee correctly saves all new payee settings"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add alice as a payee with initial settings
    initial_unit_limits = createPayeeLimits(
        _perTxCap=50,
        _perPeriodCap=500,
        _lifetimeCap=5000
    )
    initial_usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )

    paymaster.addPayee(
        user_wallet,
        alice,
        False,  # canPull
        2 * ONE_DAY_IN_BLOCKS,  # periodLength
        5,  # maxNumTxsPerPeriod
        0,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        False,  # onlyPrimaryAsset
        initial_unit_limits,
        initial_usd_limits,
        sender=bob
    )
    
    # Get the original start/expiry blocks
    original_settings = user_wallet_config.payeeSettings(alice)
    original_start = original_settings.startBlock
    original_expiry = original_settings.expiryBlock
    
    # Now update with new settings
    new_unit_limits = createPayeeLimits(
        _perTxCap=100,
        _perPeriodCap=1000,
        _lifetimeCap=10000
    )
    new_usd_limits = createPayeeLimits(
        _perTxCap=2000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=20000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=200000 * EIGHTEEN_DECIMALS
    )

    result = paymaster.updatePayee(
        user_wallet,
        alice,
        True,  # canPull (changed)
        3 * ONE_DAY_IN_BLOCKS,  # periodLength (changed)
        15,  # maxNumTxsPerPeriod (changed)
        500,  # txCooldownBlocks (changed)
        True,  # failOnZeroPrice (changed)
        bravo_token,  # primaryAsset (changed)
        True,  # onlyPrimaryAsset (changed)
        new_unit_limits,  # unitLimits (changed)
        new_usd_limits,  # usdLimits (changed)
        sender=bob
    )
    
    assert result == True
    
    # Get updated settings
    updated_settings = user_wallet_config.payeeSettings(alice)
    
    # Verify start/expiry blocks are preserved
    assert updated_settings.startBlock == original_start
    assert updated_settings.expiryBlock == original_expiry
    
    # Verify all new settings were saved
    assert updated_settings.canPull == True
    assert updated_settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert updated_settings.maxNumTxsPerPeriod == 15
    assert updated_settings.txCooldownBlocks == 500
    assert updated_settings.failOnZeroPrice == True
    assert updated_settings.primaryAsset == bravo_token.address
    assert updated_settings.onlyPrimaryAsset == True
    
    # Verify unit limits
    assert updated_settings.unitLimits.perTxCap == 100
    assert updated_settings.unitLimits.perPeriodCap == 1000
    assert updated_settings.unitLimits.lifetimeCap == 10000
    
    # Verify USD limits
    assert updated_settings.usdLimits.perTxCap == 2000 * EIGHTEEN_DECIMALS
    assert updated_settings.usdLimits.perPeriodCap == 20000 * EIGHTEEN_DECIMALS
    assert updated_settings.usdLimits.lifetimeCap == 200000 * EIGHTEEN_DECIMALS


def test_update_payee_emits_event_with_correct_data(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, alpha_token):
    """Test that updatePayee emits PayeeUpdated event with all correct data"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        5,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Update the payee with new settings
    unit_limits = createPayeeLimits(
        _perTxCap=75,
        _perPeriodCap=750,
        _lifetimeCap=7500
    )
    usd_limits = createPayeeLimits(
        _perTxCap=1750 * EIGHTEEN_DECIMALS,
        _perPeriodCap=17500 * EIGHTEEN_DECIMALS,
        _lifetimeCap=175000 * EIGHTEEN_DECIMALS
    )

    paymaster.updatePayee(
        user_wallet,
        alice,
        True,  # canPull
        4 * ONE_DAY_IN_BLOCKS,  # periodLength
        25,  # maxNumTxsPerPeriod
        1500,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        True,  # onlyPrimaryAsset
        unit_limits,
        usd_limits,
        sender=bob
    )
    
    # Get the event
    event = filter_logs(paymaster, "PayeeUpdated")[0]
    
    # Verify indexed fields
    assert event.user == user_wallet.address
    assert event.payee == alice
    
    # Verify all settings
    assert event.canPull == True
    assert event.periodLength == 4 * ONE_DAY_IN_BLOCKS
    assert event.maxNumTxsPerPeriod == 25
    assert event.txCooldownBlocks == 1500
    assert event.failOnZeroPrice == True
    assert event.primaryAsset == alpha_token.address
    assert event.onlyPrimaryAsset == True
    
    # Verify unit limits
    assert event.unitPerTxCap == 75
    assert event.unitPerPeriodCap == 750
    assert event.unitLifetimeCap == 7500
    
    # Verify USD limits
    assert event.usdPerTxCap == 1750 * EIGHTEEN_DECIMALS
    assert event.usdPerPeriodCap == 17500 * EIGHTEEN_DECIMALS
    assert event.usdLifetimeCap == 175000 * EIGHTEEN_DECIMALS


def test_update_payee_reverts_on_invalid_settings(paymaster, user_wallet, createPayeeLimits, alice, bob):
    """Test that updatePayee reverts with 'invalid payee settings' when validation fails"""
    # First add alice as a valid payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Try to update with invalid limits (perTxCap > perPeriodCap)
    invalid_usd_limits = createPayeeLimits(
        _perTxCap=10000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,  # Less than perTxCap - invalid!
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    with boa.reverts("invalid payee settings"):
        paymaster.updatePayee(
            user_wallet,
            alice,
            False,
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            invalid_usd_limits,
            sender=bob
        )


def test_update_payee_preserves_start_expiry_blocks(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that updatePayee preserves original start and expiry blocks"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Add payee with specific start delay and activation length
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        100,  # startDelay
        5000,  # activationLength
        sender=bob
    )

    # Get original blocks
    original_settings = user_wallet_config.payeeSettings(alice)
    original_start = original_settings.startBlock
    original_expiry = original_settings.expiryBlock

    # Time travel forward
    boa.env.time_travel(blocks=1000)

    # Update the payee
    paymaster.updatePayee(
        user_wallet,
        alice,
        True,  # Change some settings
        3 * ONE_DAY_IN_BLOCKS,
        20,
        100,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=2000 * EIGHTEEN_DECIMALS),
        sender=bob
    )

    # Verify blocks are preserved
    updated_settings = user_wallet_config.payeeSettings(alice)
    assert updated_settings.startBlock == original_start
    assert updated_settings.expiryBlock == original_expiry


################
# Remove Payee #
################


def test_remove_payee_by_owner(paymaster, user_wallet, user_wallet_config, createPayeeLimits, alice, bob):
    """Test that the owner can remove a payee"""
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Verify alice is a payee
    assert user_wallet_config.indexOfPayee(alice) != 0
    
    # Remove alice as the owner
    result = paymaster.removePayee(user_wallet, alice, sender=bob)
    assert result == True
    
    # Verify alice is no longer a payee
    assert user_wallet_config.indexOfPayee(alice) == 0


def test_remove_payee_by_payee_self(paymaster, user_wallet, user_wallet_config, createPayeeLimits, alice, bob):
    """Test that a payee can remove themselves"""
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Verify alice is a payee
    assert user_wallet_config.indexOfPayee(alice) != 0
    
    # Alice removes herself
    result = paymaster.removePayee(user_wallet, alice, sender=alice)
    assert result == True
    
    # Verify alice is no longer a payee
    assert user_wallet_config.indexOfPayee(alice) == 0


def test_remove_payee_by_security_admin(paymaster, user_wallet, user_wallet_config, createPayeeLimits, alice, bob, charlie, mission_control, switchboard_alpha):
    """Test that security admin can remove a payee"""
    # Set charlie as security operator
    mission_control.setCanPerformSecurityAction(charlie, True, sender=switchboard_alpha.address)
    
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Verify alice is a payee
    assert user_wallet_config.indexOfPayee(alice) != 0
    
    # Remove alice as security admin (charlie)
    result = paymaster.removePayee(user_wallet, alice, sender=charlie)
    assert result == True
    
    # Verify alice is no longer a payee
    assert user_wallet_config.indexOfPayee(alice) == 0


def test_remove_payee_unauthorized(paymaster, user_wallet, createPayeeLimits, alice, bob, charlie):
    """Test that unauthorized users cannot remove a payee"""
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Try to remove alice as charlie (not owner, not payee, not security admin)
    with boa.reverts("no perms"):
        paymaster.removePayee(user_wallet, alice, sender=charlie)


def test_remove_payee_not_found(paymaster, user_wallet, alice, bob):
    """Test that removing a non-existent payee fails"""
    # Try to remove alice who is not a payee
    with boa.reverts("payee not found"):
        paymaster.removePayee(user_wallet, alice, sender=bob)


def test_remove_payee_invalid_wallet(paymaster, alice, bob):
    """Test that removing from invalid wallet fails"""
    # Try to remove from bob's address (not a user wallet)
    with boa.reverts("invalid user wallet"):
        paymaster.removePayee(bob, alice, sender=bob)


def test_remove_payee_emits_event(paymaster, user_wallet, createPayeeLimits, alice, bob):
    """Test that removePayee emits PayeeRemoved event with correct data"""
    # First add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Remove alice
    paymaster.removePayee(user_wallet, alice, sender=bob)
    
    # Get the event
    event = filter_logs(paymaster, "PayeeRemoved")[0]
    
    # Verify event data
    assert event.user == user_wallet.address
    assert event.payee == alice
    assert event.removedBy == bob


def test_remove_payee_clears_all_data(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob, charlie):
    """Test that removing a payee clears all their data"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Add alice as a payee with specific settings
    paymaster.addPayee(
        user_wallet,
        alice,
        True,
        3 * ONE_DAY_IN_BLOCKS,
        15,
        500,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(_perTxCap=100),
        createPayeeLimits(_perTxCap=2000 * EIGHTEEN_DECIMALS),
        sender=bob
    )
    
    # Also add charlie to verify numPayees changes correctly
    paymaster.addPayee(
        user_wallet,
        charlie,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )

    # Record initial state
    initial_num_payees = user_wallet_config.numPayees()
    alice_index = user_wallet_config.indexOfPayee(alice)
    
    # Remove alice
    paymaster.removePayee(user_wallet, alice, sender=bob)
    
    # Verify alice's data is cleared
    assert user_wallet_config.indexOfPayee(alice) == 0
    
    # Verify the payee count decreased
    assert user_wallet_config.numPayees() == initial_num_payees - 1
    
    # Verify alice's index is no longer mapped to alice
    assert user_wallet_config.payees(alice_index) != alice
    
    # Verify alice's settings are cleared (default values)
    settings = user_wallet_config.payeeSettings(alice)
    assert settings.startBlock == 0
    assert settings.expiryBlock == 0
    assert settings.canPull == False
    assert settings.periodLength == 0


def test_remove_payee_allows_re_adding(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that a removed payee can be added again"""
    # Set global payee settings to allow canPull
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Add alice as a payee
    paymaster.addPayee(
        user_wallet,
        alice,
        False,
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
        sender=bob
    )

    # Remove alice
    paymaster.removePayee(user_wallet, alice, sender=bob)

    # Verify alice is removed
    assert user_wallet_config.indexOfPayee(alice) == 0

    # Add alice again with different settings
    result = paymaster.addPayee(
        user_wallet,
        alice,
        True,  # Different settings
        3 * ONE_DAY_IN_BLOCKS,
        20,
        100,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        createPayeeLimits(_perTxCap=2000 * EIGHTEEN_DECIMALS),
        sender=bob
    )

    assert result == True
    
    # Verify alice is added again
    assert user_wallet_config.indexOfPayee(alice) != 0
    
    # Verify new settings
    settings = user_wallet_config.payeeSettings(alice)
    assert settings.canPull == True
    assert settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert settings.maxNumTxsPerPeriod == 20


#############################
# canPull Validation Tests  #
#############################


def test_payee_cannot_have_canpull_when_global_is_false(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that payee cannot have canPull=True when global canPull=False"""
    # Set global payee settings with canPull=False (default)
    global_settings = createGlobalPayeeSettings(_canPull=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create valid limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Try to add payee with canPull=True (should fail)
    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
            user_wallet,
            alice,
            True,  # canPull - not allowed when global is False
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            usd_limits,
            sender=bob
        )


def test_payee_can_have_canpull_false_when_global_is_false(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that payee can have canPull=False when global canPull=False"""
    # Set global payee settings with canPull=False
    global_settings = createGlobalPayeeSettings(_canPull=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create valid limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Add payee with canPull=False (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        False,  # canPull=False is always allowed
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == False


def test_payee_can_have_canpull_true_when_global_is_true(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that payee can have canPull=True when global canPull=True"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create valid limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Add payee with canPull=True (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        True,  # canPull=True allowed when global is True
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == True


def test_payee_can_have_canpull_false_when_global_is_true(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that payee can have canPull=False even when global canPull=True"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create valid limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Add payee with canPull=False (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        False,  # canPull=False is always allowed
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == False


def test_pull_payee_must_have_limits(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that pull payees (canPull=True) must have at least one type of limit"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Try to add pull payee with no limits (all zeros)
    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
            user_wallet,
            alice,
            True,  # canPull=True
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),  # All zero limits
            createPayeeLimits(),  # All zero limits
            sender=bob
        )


def test_pull_payee_with_unit_limits_only(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that pull payees can have only unit limits"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create unit limits only
    unit_limits = createPayeeLimits(
        _perTxCap=100,
        _perPeriodCap=1000,
        _lifetimeCap=10000
    )
    
    # Add pull payee with unit limits only (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        True,  # canPull=True
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        unit_limits,  # Has unit limits
        createPayeeLimits(),  # No USD limits
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == True


def test_pull_payee_with_usd_limits_only(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that pull payees can have only USD limits"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Create USD limits only
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Add pull payee with USD limits only (should succeed)
    result = paymaster.addPayee(
        user_wallet,
        alice,
        True,  # canPull=True
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),  # No unit limits
        usd_limits,  # Has USD limits
        sender=bob
    )
    
    assert result == True
    assert user_wallet_config.payeeSettings(alice).canPull == True


def test_update_payee_cannot_enable_canpull_when_global_is_false(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that updating a payee cannot set canPull=True when global canPull=False"""
    # Set global payee settings with canPull=False
    global_settings = createGlobalPayeeSettings(_canPull=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # First add alice as a payee with canPull=False
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    paymaster.addPayee(
        user_wallet,
        alice,
        False,  # canPull=False
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(),
        usd_limits,
        sender=bob
    )
    
    # Try to update to canPull=True (should fail)
    with boa.reverts("invalid payee settings"):
        paymaster.updatePayee(
            user_wallet,
            alice,
            True,  # Try to enable canPull
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            usd_limits,
            sender=bob
        )


def test_changing_global_canpull_does_not_affect_existing_payees(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, alice, bob):
    """Test that changing global canPull setting doesn't affect existing payees"""
    # Set global payee settings with canPull=True
    global_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Add payee with canPull=True
    usd_limits = createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS)
    paymaster.addPayee(
        user_wallet,
        alice,
        True,  # canPull=True
        2 * ONE_DAY_IN_BLOCKS,
        10,
        0,
        True,
        ZERO_ADDRESS,
        False,
        createPayeeLimits(_perTxCap=100),  # Has limits
        usd_limits,
        sender=bob
    )
    
    # Verify payee has canPull=True
    assert user_wallet_config.payeeSettings(alice).canPull == True
    
    # Now change global settings to canPull=False
    global_settings = createGlobalPayeeSettings(_canPull=False)
    user_wallet_config.setGlobalPayeeSettings(global_settings, sender=paymaster.address)
    
    # Existing payee should still have canPull=True
    assert user_wallet_config.payeeSettings(alice).canPull == True

    # But we can't add new payees with canPull=True
    with boa.reverts("invalid payee settings"):
        paymaster.addPayee(
            user_wallet,
            bob,  # Different payee
            True,  # canPull=True not allowed anymore
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(_perTxCap=100),
            usd_limits,
            sender=bob
        )
