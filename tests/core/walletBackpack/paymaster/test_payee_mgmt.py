import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ONE_DAY_IN_BLOCKS, ZERO_ADDRESS
from conf_utils import filter_logs


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


##################
# Pending Payees #
##################


# add pending payee


def test_add_pending_payee_by_manager_with_permission(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that a manager with permission can add a pending payee"""
    # Set global permissions to allow adding pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Add alice as manager with permission to add pending payees
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Create payee limits
    usd_limits = createPayeeLimits(
        _perTxCap=1000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=10000 * EIGHTEEN_DECIMALS,
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Alice (manager) adds charlie as pending payee
    result = paymaster.addPendingPayee(
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
        sender=alice  # Manager
    )
    
    assert result == True
    
    # Verify pending payee was created
    pending = user_wallet_config.pendingPayees(charlie)
    assert pending.initiatedBlock > 0
    assert pending.confirmBlock > pending.initiatedBlock


def test_add_pending_payee_without_permission_fails(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that a manager without permission cannot add a pending payee"""
    # Set global permissions to allow adding pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Add alice as manager WITHOUT permission to add pending payees
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=False)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Try to add pending payee
    with boa.reverts("no permission to add pending payee"):
        paymaster.addPendingPayee(
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
            sender=alice
        )


def test_add_pending_payee_global_restriction_overrides(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that global permissions can restrict manager from adding pending payees"""
    # Set global permissions to DENY adding pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=False)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # Add alice as manager with permission to add pending payees
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Should fail due to global restriction
    with boa.reverts("no permission to add pending payee"):
        paymaster.addPendingPayee(
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
            sender=alice
        )


def test_owner_cannot_add_pending_payee(paymaster, user_wallet, createPayeeLimits, alice, bob):
    """Test that owner cannot add pending payee (they use addPayee instead)"""
    # Owner tries to add pending payee
    with boa.reverts("no permission to add pending payee"):
        paymaster.addPendingPayee(
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
            sender=bob  # Owner
        )


def test_non_manager_cannot_add_pending_payee(paymaster, user_wallet, createPayeeLimits, alice, charlie):
    """Test that non-manager cannot add pending payee"""
    # Charlie (not a manager) tries to add pending payee
    with boa.reverts("no permission to add pending payee"):
        paymaster.addPendingPayee(
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
            sender=charlie  # Not a manager
        )


def test_add_pending_payee_saves_all_settings(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command, alpha_token):
    """Test that addPendingPayee correctly saves all payee settings"""
    # Set global payee settings to allow canPull
    global_payee_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_payee_settings, sender=paymaster.address)
    
    # Setup manager
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Create specific limits
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

    # Add pending payee
    paymaster.addPendingPayee(
        user_wallet,
        charlie,
        True,  # canPull
        3 * ONE_DAY_IN_BLOCKS,  # periodLength
        15,  # maxNumTxsPerPeriod
        500,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        True,  # onlyPrimaryAsset
        unit_limits,
        usd_limits,
        100,  # startDelay
        5000,  # activationLength
        sender=alice
    )
    
    # Get pending payee data
    pending = user_wallet_config.pendingPayees(charlie)
    
    # Verify all settings were saved
    assert pending.settings.canPull == True
    assert pending.settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert pending.settings.maxNumTxsPerPeriod == 15
    assert pending.settings.txCooldownBlocks == 500
    assert pending.settings.failOnZeroPrice == True
    assert pending.settings.primaryAsset == alpha_token.address
    assert pending.settings.onlyPrimaryAsset == True
    assert pending.currentOwner == bob  # Current owner
    
    # Verify limits
    assert pending.settings.unitLimits.perTxCap == 100
    assert pending.settings.unitLimits.perPeriodCap == 1000
    assert pending.settings.unitLimits.lifetimeCap == 10000
    assert pending.settings.usdLimits.perTxCap == 2000 * EIGHTEEN_DECIMALS
    assert pending.settings.usdLimits.perPeriodCap == 20000 * EIGHTEEN_DECIMALS
    assert pending.settings.usdLimits.lifetimeCap == 200000 * EIGHTEEN_DECIMALS
    
    # Verify timing
    assert pending.initiatedBlock > 0
    assert pending.confirmBlock > pending.initiatedBlock


def test_add_pending_payee_emits_event(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that addPendingPayee emits PayeePending event with correct data"""
    # Setup manager
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Add pending payee
    paymaster.addPendingPayee(
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
        createPayeeLimits(_perTxCap=1500 * EIGHTEEN_DECIMALS),
        sender=alice
    )
    
    # Get the event
    event = filter_logs(paymaster, "PayeePending")[0]
    
    # Verify event data
    assert event.user == user_wallet.address
    assert event.payee == charlie
    assert event.addedBy == alice
    assert event.confirmBlock > 0


def test_add_pending_payee_cannot_add_existing_payee(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that cannot add pending payee if already a registered payee"""
    # First add charlie as a regular payee
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
    
    # Setup manager
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Try to add pending payee for existing payee
    with boa.reverts("invalid payee settings"):
        paymaster.addPendingPayee(
            user_wallet,
            charlie,  # Already a payee
            False,
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
            sender=alice
        )


def test_add_pending_payee_cannot_add_duplicate_pending(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, charlie, high_command):
    """Test that cannot add duplicate pending payee"""
    # Setup manager
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Add pending payee first time
    paymaster.addPendingPayee(
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
        sender=alice
    )
    
    # Try to add same pending payee again
    with boa.reverts("no permission to add pending payee"):
        paymaster.addPendingPayee(
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
            sender=alice
        )


def test_add_pending_payee_reverts_on_invalid_settings(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, charlie, high_command):
    """Test that addPendingPayee reverts with 'invalid payee settings' when validation fails"""
    # Setup manager
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Create invalid limits (perTxCap > perPeriodCap)
    invalid_usd_limits = createPayeeLimits(
        _perTxCap=10000 * EIGHTEEN_DECIMALS,
        _perPeriodCap=1000 * EIGHTEEN_DECIMALS,  # Less than perTxCap - invalid!
        _lifetimeCap=100000 * EIGHTEEN_DECIMALS
    )
    
    # Should fail validation
    with boa.reverts("invalid payee settings"):
        paymaster.addPendingPayee(
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
            invalid_usd_limits,
            sender=alice
        )


# confirm pending payee


def test_confirm_pending_payee_by_owner(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that owner can confirm a pending payee after timelock"""
    # Setup manager and add pending payee
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Add pending payee
    paymaster.addPendingPayee(
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
        sender=alice
    )
    
    # Get the pending payee to check confirmBlock
    pending = user_wallet_config.pendingPayees(charlie)
    blocks_to_wait = pending.confirmBlock - boa.env.evm.patch.block_number
    
    # Time travel to after timelock
    boa.env.time_travel(blocks=blocks_to_wait)
    
    # Confirm as owner
    result = paymaster.confirmPendingPayee(user_wallet, charlie, sender=bob)
    assert result == True
    
    # Verify charlie is now a registered payee
    assert user_wallet_config.indexOfPayee(charlie) != 0
    
    # Verify pending payee is cleared
    pending_after = user_wallet_config.pendingPayees(charlie)
    assert pending_after.initiatedBlock == 0


def test_confirm_pending_payee_before_timelock_fails(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that confirming before timelock fails"""
    # Setup manager and add pending payee
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Add pending payee
    paymaster.addPendingPayee(
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
        sender=alice
    )
    
    # Try to confirm immediately (before timelock)
    with boa.reverts("time delay not reached"):
        paymaster.confirmPendingPayee(user_wallet, charlie, sender=bob)


def test_confirm_pending_payee_non_owner_fails(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that non-owner cannot confirm pending payee"""
    # Setup manager and add pending payee
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Add pending payee
    paymaster.addPendingPayee(
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
        sender=alice
    )
    
    # Get timelock and wait
    pending = user_wallet_config.pendingPayees(charlie)
    blocks_to_wait = pending.confirmBlock - boa.env.evm.patch.block_number
    boa.env.time_travel(blocks=blocks_to_wait)
    
    # Try to confirm as alice (not owner)
    with boa.reverts("no perms"):
        paymaster.confirmPendingPayee(user_wallet, charlie, sender=alice)


def test_confirm_pending_payee_no_pending_fails(paymaster, user_wallet, charlie, bob):
    """Test that confirming non-existent pending payee fails"""
    # Try to confirm when there's no pending payee
    with boa.reverts("no pending payee"):
        paymaster.confirmPendingPayee(user_wallet, charlie, sender=bob)


def test_confirm_pending_payee_preserves_settings(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command, alpha_token):
    """Test that confirmed payee has all the settings from pending payee"""
    # Set global payee settings to allow canPull
    global_payee_settings = createGlobalPayeeSettings(_canPull=True)
    user_wallet_config.setGlobalPayeeSettings(global_payee_settings, sender=paymaster.address)
    
    # Setup manager
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Create specific limits
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

    # Add pending payee with specific settings
    paymaster.addPendingPayee(
        user_wallet,
        charlie,
        True,  # canPull
        3 * ONE_DAY_IN_BLOCKS,  # periodLength
        15,  # maxNumTxsPerPeriod
        500,  # txCooldownBlocks
        True,  # failOnZeroPrice
        alpha_token,  # primaryAsset
        True,  # onlyPrimaryAsset
        unit_limits,
        usd_limits,
        100,  # startDelay
        5000,  # activationLength
        sender=alice
    )
    
    # Get timelock and wait
    pending = user_wallet_config.pendingPayees(charlie)
    blocks_to_wait = pending.confirmBlock - boa.env.evm.patch.block_number
    boa.env.time_travel(blocks=blocks_to_wait)
    
    # Confirm
    paymaster.confirmPendingPayee(user_wallet, charlie, sender=bob)
    
    # Get the confirmed payee settings
    payee_settings = user_wallet_config.payeeSettings(charlie)
    
    # Verify all settings match what was in pending
    assert payee_settings.canPull == True
    assert payee_settings.periodLength == 3 * ONE_DAY_IN_BLOCKS
    assert payee_settings.maxNumTxsPerPeriod == 15
    assert payee_settings.txCooldownBlocks == 500
    assert payee_settings.failOnZeroPrice == True
    assert payee_settings.primaryAsset == alpha_token.address
    assert payee_settings.onlyPrimaryAsset == True
    
    # Verify limits
    assert payee_settings.unitLimits.perTxCap == 100
    assert payee_settings.unitLimits.perPeriodCap == 1000
    assert payee_settings.unitLimits.lifetimeCap == 10000
    assert payee_settings.usdLimits.perTxCap == 2000 * EIGHTEEN_DECIMALS
    assert payee_settings.usdLimits.perPeriodCap == 20000 * EIGHTEEN_DECIMALS
    assert payee_settings.usdLimits.lifetimeCap == 200000 * EIGHTEEN_DECIMALS


def test_confirm_pending_payee_emits_event(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that confirmPendingPayee emits PayeePendingConfirmed event"""
    # Setup manager and add pending payee
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Add pending payee
    paymaster.addPendingPayee(
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
        sender=alice
    )
    
    # Get pending info for verification
    pending = user_wallet_config.pendingPayees(charlie)
    initiated_block = pending.initiatedBlock
    confirm_block = pending.confirmBlock
    
    # Wait for timelock
    blocks_to_wait = confirm_block - boa.env.evm.patch.block_number
    boa.env.time_travel(blocks=blocks_to_wait)
    
    # Confirm
    paymaster.confirmPendingPayee(user_wallet, charlie, sender=bob)
    
    # Get the event
    event = filter_logs(paymaster, "PayeePendingConfirmed")[0]
    
    # Verify event data
    assert event.user == user_wallet.address
    assert event.payee == charlie
    assert event.initiatedBlock == initiated_block
    assert event.confirmBlock == confirm_block
    assert event.confirmedBy == bob


def test_confirm_pending_payee_owner_changed_fails(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that confirmation fails if owner changed after pending payee was added"""
    # Setup manager and add pending payee
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Add pending payee
    paymaster.addPendingPayee(
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
        sender=alice
    )
    
    # Get timelock for pending payee
    pending = user_wallet_config.pendingPayees(charlie)
    
    # Transfer ownership to a new owner
    user_wallet_config.changeOwnership(alice, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.ownershipTimeLock())
    user_wallet_config.confirmOwnershipChange(sender=alice)
    
    # Wait for timelock
    blocks_to_wait = pending.confirmBlock - boa.env.evm.patch.block_number
    if blocks_to_wait > 0:
        boa.env.time_travel(blocks=blocks_to_wait)
    
    # Try to confirm as alice (should fail because owner changed after pending was created)
    with boa.reverts("must be same owner"):
        paymaster.confirmPendingPayee(user_wallet, charlie, sender=alice)


def test_confirm_pending_payee_invalid_wallet_fails(paymaster, alice, bob):
    """Test that confirming on invalid wallet fails"""
    # Try to confirm on bob's address (not a user wallet)
    with boa.reverts("invalid user wallet"):
        paymaster.confirmPendingPayee(bob, alice, sender=bob)


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


def test_pending_payee_canpull_validation(paymaster, user_wallet, user_wallet_config, createPayeeLimits, createGlobalPayeeSettings, createGlobalManagerSettings, createTransferPerms, createManagerSettings, alice, bob, charlie, high_command):
    """Test that pending payees also respect global canPull setting"""
    # Set global payee settings with canPull=False
    global_payee_settings = createGlobalPayeeSettings(_canPull=False)
    user_wallet_config.setGlobalPayeeSettings(global_payee_settings, sender=paymaster.address)
    
    # Setup manager with permission to add pending payees
    global_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_global_manager_settings = createGlobalManagerSettings(_transferPerms=global_transfer_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    manager_transfer_perms = createTransferPerms(_canAddPendingPayee=True)
    new_manager_settings = createManagerSettings(_transferPerms=manager_transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # Try to add pending payee with canPull=True (should fail)
    with boa.reverts("invalid payee settings"):
        paymaster.addPendingPayee(
            user_wallet,
            charlie,
            True,  # canPull=True not allowed
            2 * ONE_DAY_IN_BLOCKS,
            10,
            0,
            True,
            ZERO_ADDRESS,
            False,
            createPayeeLimits(),
            createPayeeLimits(_perTxCap=1000 * EIGHTEEN_DECIMALS),
            sender=alice
        )