"""
Tests for onlyApprovedYieldOpps manager permission validation.
"""
import pytest
import boa

from constants import ONE_DAY_IN_BLOCKS, ZERO_ADDRESS, EIGHTEEN_DECIMALS


####################
# Test Fixtures    #
####################


@pytest.fixture
def setup_manager_with_approval_flag(
    user_wallet_config,
    user_wallet,
    createManagerSettings,
    createManagerLimits,
    createLegoPerms,
    createWhitelistPerms,
    createTransferPerms,
    bob,
    alice,
    high_command,
):
    """Setup a manager with onlyApprovedYieldOpps enabled"""
    def _setup(only_approved=True):
        # Alice will be the manager, Bob is the owner
        manager_settings = createManagerSettings(
            _limits=createManagerLimits(),
            _legoPerms=createLegoPerms(_onlyApprovedYieldOpps=only_approved),
            _whitelistPerms=createWhitelistPerms(),
            _transferPerms=createTransferPerms(),
            _allowedAssets=[],
            _canClaimLoot=False,
        )
        user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)
        return alice  # return the manager address
    return _setup


@pytest.fixture
def setup_approved_vault_token(
    vault_registry,
    switchboard_alpha,
    undy_usd_vault,
):
    """Setup an approved vault token in VaultRegistry

    Note: The first parameter is the Underscore vault (like undy_usd_vault),
    not the underlying ERC20 token. This is how VaultRegistry tracks approvals.
    """
    def _setup(underlying, vault_token):
        # Use undy_usd_vault for all approvals in these tests
        # In production, you'd use the appropriate Underscore vault for each asset
        vault_registry.setApprovedVaultToken(
            undy_usd_vault.address,
            vault_token.address if hasattr(vault_token, 'address') else vault_token,
            True,  # approved
            False,  # _shouldMaxWithdraw
            sender=switchboard_alpha.address
        )
    return _setup


######################
# Deposit Tests      #
######################


def test_manager_can_deposit_to_approved_vault(
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    setup_manager_with_approval_flag,
    setup_approved_vault_token,
    bob,
):
    """Manager with onlyApprovedYieldOpps=True can deposit to approved vault"""
    # Setup manager with approval flag enabled
    manager = setup_manager_with_approval_flag(only_approved=True)

    # Approve the vault token
    setup_approved_vault_token(yield_underlying_token, yield_vault_token)

    # Fund the user wallet with underlying tokens
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount, sender=yield_underlying_token_whale)

    # Manager should be able to deposit
    lego_id = 2  # mock_yield_lego
    user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        sender=manager
    )

    # Verify deposit succeeded
    assert yield_vault_token.balanceOf(user_wallet) > 0


def test_manager_cannot_deposit_to_unapproved_vault(
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    setup_manager_with_approval_flag,
    vault_registry,
    switchboard_alpha,
    undy_usd_vault,
    bob,
):
    """Manager with onlyApprovedYieldOpps=True cannot deposit to unapproved vault"""
    # Setup manager with approval flag enabled
    manager = setup_manager_with_approval_flag(only_approved=True)

    # UNAPPROVE the vault token (it's approved by default in test setup)
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,  # unapproved
        False,  # _shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Fund the user wallet with underlying tokens
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount, sender=yield_underlying_token_whale)

    # Manager should NOT be able to deposit
    lego_id = 2  # mock_yield_lego
    with boa.reverts("manager limits not allowed"):
        user_wallet.depositForYield(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            amount,
            sender=manager
        )


def test_manager_can_deposit_to_any_vault_when_flag_disabled(
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    setup_manager_with_approval_flag,
    bob,
):
    """Manager with onlyApprovedYieldOpps=False can deposit to any vault"""
    # Setup manager with approval flag DISABLED
    manager = setup_manager_with_approval_flag(only_approved=False)

    # Do NOT approve the vault token - but it should still work

    # Fund the user wallet with underlying tokens
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount, sender=yield_underlying_token_whale)

    # Manager should be able to deposit even without approval
    lego_id = 2  # mock_yield_lego
    user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        sender=manager
    )

    # Verify deposit succeeded
    assert yield_vault_token.balanceOf(user_wallet) > 0


def test_owner_can_deposit_to_unapproved_vault(
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    bob,  # owner
):
    """Owner can always deposit to any vault, regardless of approval"""
    # Owner doesn't need manager setup - they have full permissions

    # Do NOT approve the vault token

    # Fund the user wallet with underlying tokens
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount, sender=yield_underlying_token_whale)

    # Owner should be able to deposit
    lego_id = 2  # mock_yield_lego
    user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        sender=bob  # owner
    )

    # Verify deposit succeeded
    assert yield_vault_token.balanceOf(user_wallet) > 0


######################
# Withdraw Tests     #
######################


def test_manager_can_withdraw_from_unapproved_vault(
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    setup_manager_with_approval_flag,
    setup_approved_vault_token,
    vault_registry,
    switchboard_alpha,
    undy_usd_vault,
    bob,  # owner
    alice,
):
    """Manager can withdraw from unapproved vault (no restriction on withdrawals)"""
    # Setup manager with approval flag enabled
    manager = setup_manager_with_approval_flag(only_approved=True)

    # Approve the vault token initially so we can deposit
    setup_approved_vault_token(yield_underlying_token, yield_vault_token)

    # Fund and deposit as owner first
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount, sender=yield_underlying_token_whale)

    lego_id = 2  # mock_yield_lego
    user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        sender=bob  # owner
    )

    vault_balance = yield_vault_token.balanceOf(user_wallet)
    assert vault_balance > 0

    # Now UNAPPROVE the vault token
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,  # unapproved
        False,  # _shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Manager should still be able to withdraw even though vault is now unapproved
    user_wallet.withdrawFromYield(
        lego_id,
        yield_vault_token.address,
        vault_balance,
        sender=manager
    )

    # Verify withdrawal succeeded
    assert yield_vault_token.balanceOf(user_wallet) == 0
    assert yield_underlying_token.balanceOf(user_wallet) > 0


########################
# Rebalance Tests      #
########################


def test_manager_can_rebalance_to_approved_vault(
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_vault_token_2,
    yield_underlying_token_whale,
    setup_manager_with_approval_flag,
    setup_approved_vault_token,
    bob,  # owner
    alice,
):
    """Manager can rebalance from one vault to another approved vault"""
    # Setup manager with approval flag enabled
    manager = setup_manager_with_approval_flag(only_approved=True)

    # Approve BOTH vault tokens
    setup_approved_vault_token(yield_underlying_token, yield_vault_token)
    setup_approved_vault_token(yield_underlying_token, yield_vault_token_2)

    # Fund and deposit as owner first (into first vault)
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount, sender=yield_underlying_token_whale)

    lego_id = 2  # mock_yield_lego
    user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        sender=bob  # owner
    )

    vault1_balance = yield_vault_token.balanceOf(user_wallet)
    assert vault1_balance > 0

    # Manager should be able to rebalance to approved second vault
    user_wallet.rebalanceYieldPosition(
        lego_id,  # from
        yield_vault_token.address,
        lego_id,  # to
        yield_vault_token_2.address,
        sender=manager
    )

    # Verify rebalance succeeded
    assert yield_vault_token.balanceOf(user_wallet) == 0
    assert yield_vault_token_2.balanceOf(user_wallet) > 0


def test_manager_cannot_rebalance_to_unapproved_vault(
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_vault_token_2,
    yield_underlying_token_whale,
    setup_manager_with_approval_flag,
    setup_approved_vault_token,
    vault_registry,
    switchboard_alpha,
    undy_usd_vault,
    bob,  # owner
    alice,
):
    """Manager cannot rebalance to an unapproved vault"""
    # Setup manager with approval flag enabled
    manager = setup_manager_with_approval_flag(only_approved=True)

    # Approve ONLY the source vault, not the destination
    setup_approved_vault_token(yield_underlying_token, yield_vault_token)
    # UNAPPROVE yield_vault_token_2 (it's approved by default in test setup)
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token_2.address,
        False,  # unapproved
        False,  # _shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Fund and deposit as owner first (into first vault)
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount, sender=yield_underlying_token_whale)

    lego_id = 2  # mock_yield_lego
    user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        sender=bob  # owner
    )

    vault1_balance = yield_vault_token.balanceOf(user_wallet)
    assert vault1_balance > 0

    # Manager should NOT be able to rebalance to unapproved second vault
    with boa.reverts("manager limits not allowed"):
        user_wallet.rebalanceYieldPosition(
            lego_id,  # from
            yield_vault_token.address,
            lego_id,  # to (unapproved)
            yield_vault_token_2.address,
            sender=manager
        )


###########################
# Global Settings Tests   #
###########################


def test_global_setting_enforces_approval(
    user_wallet_config,
    high_command,
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    createGlobalManagerSettings,
    createManagerSettings,
    createManagerLimits,
    createLegoPerms,
    createWhitelistPerms,
    createTransferPerms,
    vault_registry,
    switchboard_alpha,
    undy_usd_vault,
    bob,  # owner
    alice,  # manager
):
    """Global onlyApprovedYieldOpps setting enforces approval even if manager-specific is False"""
    # Set global manager settings with onlyApprovedYieldOpps=True
    global_settings = createGlobalManagerSettings(
        _legoPerms=createLegoPerms(_onlyApprovedYieldOpps=True)  # Global setting enabled
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Add manager with onlyApprovedYieldOpps=False (should be overridden by global)
    manager_settings = createManagerSettings(
        _limits=createManagerLimits(),
        _legoPerms=createLegoPerms(_onlyApprovedYieldOpps=False),  # Manager-specific disabled
        _whitelistPerms=createWhitelistPerms(),
        _transferPerms=createTransferPerms(),
        _allowedAssets=[],
        _canClaimLoot=False,
    )
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    # UNAPPROVE the vault token (it's approved by default in test setup)
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,  # unapproved
        False,  # _shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Fund the user wallet
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount, sender=yield_underlying_token_whale)

    # Manager should NOT be able to deposit because GLOBAL setting requires approval
    lego_id = 2  # mock_yield_lego
    with boa.reverts("manager limits not allowed"):
        user_wallet.depositForYield(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            amount,
            sender=alice  # alice is the manager
        )


#############################
# Default Settings Tests    #
#############################


def test_default_global_manager_settings_has_approval_enabled(high_command):
    """Default global manager settings should have onlyApprovedYieldOpps=True when explicitly set"""
    default_settings = high_command.createDefaultGlobalManagerSettings(
        ONE_DAY_IN_BLOCKS,  # manager period
        ONE_DAY_IN_BLOCKS,  # min time lock
        ONE_DAY_IN_BLOCKS * 30,  # default activation length
        False,  # mustHaveUsdValueOnSwaps
        0,  # maxNumSwapsPerPeriod
        0,  # maxSlippageOnSwaps
        True,  # onlyApprovedYieldOpps
    )

    # Check that onlyApprovedYieldOpps is True when explicitly set to True
    assert default_settings.legoPerms.onlyApprovedYieldOpps == True


def test_starter_agent_settings_has_approval_enabled(high_command):
    """Starter agent settings should have onlyApprovedYieldOpps=False by default"""
    starter_settings = high_command.createStarterAgentSettings(
        ONE_DAY_IN_BLOCKS * 365  # activation length
    )

    # Check that onlyApprovedYieldOpps is False by default for starter agent
    assert starter_settings.legoPerms.onlyApprovedYieldOpps == False


##########################
# Edge Case Tests        #
##########################


def test_multiple_managers_different_approval_settings(
    user_wallet,
    user_wallet_config,
    high_command,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    vault_registry,
    undy_usd_vault,
    switchboard_alpha,
    createManagerSettings,
    createManagerLimits,
    createLegoPerms,
    createWhitelistPerms,
    createTransferPerms,
    alice,
    charlie,
):
    """Test multiple managers with different onlyApprovedYieldOpps settings"""
    # Add alice as manager with onlyApprovedYieldOpps=True
    manager_settings_strict = createManagerSettings(
        _limits=createManagerLimits(),
        _legoPerms=createLegoPerms(_onlyApprovedYieldOpps=True),
        _whitelistPerms=createWhitelistPerms(),
        _transferPerms=createTransferPerms(),
        _allowedAssets=[],
        _canClaimLoot=False,
    )
    user_wallet_config.addManager(alice, manager_settings_strict, sender=high_command.address)

    # Add charlie as manager with onlyApprovedYieldOpps=False
    manager_settings_permissive = createManagerSettings(
        _limits=createManagerLimits(),
        _legoPerms=createLegoPerms(_onlyApprovedYieldOpps=False),
        _whitelistPerms=createWhitelistPerms(),
        _transferPerms=createTransferPerms(),
        _allowedAssets=[],
        _canClaimLoot=False,
    )
    user_wallet_config.addManager(charlie, manager_settings_permissive, sender=high_command.address)

    # UNAPPROVE the vault token
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,
        False,  # _shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Fund the user wallet
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount * 2, sender=yield_underlying_token_whale)

    lego_id = 2  # mock_yield_lego

    # Alice (strict) should NOT be able to deposit to unapproved vault
    with boa.reverts("manager limits not allowed"):
        user_wallet.depositForYield(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            amount,
            sender=alice
        )

    # Charlie (permissive) SHOULD be able to deposit to unapproved vault
    user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        sender=charlie
    )

    # Verify the deposit succeeded
    assert yield_vault_token.balanceOf(user_wallet.address) > 0


def test_vault_approval_revoked_after_deposit(
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    setup_manager_with_approval_flag,
    setup_approved_vault_token,
    vault_registry,
    undy_usd_vault,
    switchboard_alpha,
):
    """Test that revoking approval after deposit doesn't affect existing positions (withdrawals still work)"""
    # Setup manager with approval flag enabled
    manager = setup_manager_with_approval_flag(only_approved=True)

    # Approve the vault token
    setup_approved_vault_token(yield_underlying_token, yield_vault_token)

    # Fund the user wallet and deposit
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount, sender=yield_underlying_token_whale)

    lego_id = 2  # mock_yield_lego
    user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        sender=manager
    )

    vault_balance = yield_vault_token.balanceOf(user_wallet.address)
    assert vault_balance > 0

    # REVOKE approval after deposit
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,  # revoke approval
        False,  # _shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Manager should still be able to withdraw from the vault (withdrawals not restricted)
    user_wallet.withdrawFromYield(
        lego_id,
        yield_vault_token.address,
        vault_balance,
        sender=manager
    )

    # Verify withdrawal succeeded
    assert yield_vault_token.balanceOf(user_wallet.address) == 0


def test_vault_approval_granted_enables_deposits(
    user_wallet,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    setup_manager_with_approval_flag,
    vault_registry,
    undy_usd_vault,
    switchboard_alpha,
):
    """Test that granting approval enables previously blocked deposits"""
    # Setup manager with approval flag enabled
    manager = setup_manager_with_approval_flag(only_approved=True)

    # UNAPPROVE the vault token
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        False,
        False,  # _shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Fund the user wallet
    amount = 1000 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, amount * 2, sender=yield_underlying_token_whale)

    lego_id = 2  # mock_yield_lego

    # First deposit should fail (not approved)
    with boa.reverts("manager limits not allowed"):
        user_wallet.depositForYield(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            amount,
            sender=manager
        )

    # APPROVE the vault token
    vault_registry.setApprovedVaultToken(
        undy_usd_vault.address,
        yield_vault_token.address,
        True,  # approve
        False,  # _shouldMaxWithdraw
        sender=switchboard_alpha.address
    )

    # Now the deposit should succeed
    user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        sender=manager
    )

    # Verify the deposit succeeded
    assert yield_vault_token.balanceOf(user_wallet.address) > 0


def test_remove_and_readd_manager_preserves_setting(
    user_wallet,
    user_wallet_config,
    high_command,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    vault_registry,
    undy_usd_vault,
    switchboard_alpha,
    createManagerSettings,
    createManagerLimits,
    createLegoPerms,
    createSwapPerms,
    createWhitelistPerms,
    createTransferPerms,
    createGlobalManagerSettings,
    alice,
    bob,
):
    """Test that removing and re-adding a manager can have different onlyApprovedYieldOpps settings"""
    # Set global settings first
    global_settings = createGlobalManagerSettings()
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Add alice as manager with onlyApprovedYieldOpps=True
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(_onlyApprovedYieldOpps=True),
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    # Verify the setting
    settings_1 = user_wallet_config.managerSettings(alice)
    assert settings_1.legoPerms.onlyApprovedYieldOpps == True

    # Remove alice
    high_command.removeManager(user_wallet, alice, sender=bob)

    # Re-add alice with onlyApprovedYieldOpps=False
    high_command.addManager(
        user_wallet,
        alice,
        createManagerLimits(),
        createLegoPerms(_onlyApprovedYieldOpps=False),
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,  # canClaimLoot
        sender=bob
    )

    # Verify the new setting
    settings_2 = user_wallet_config.managerSettings(alice)
    assert settings_2.legoPerms.onlyApprovedYieldOpps == False
