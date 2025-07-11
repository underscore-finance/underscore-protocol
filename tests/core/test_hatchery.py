import pytest
import boa

from contracts.core.userWallet import UserWallet, UserWalletConfig
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs


######################
# Create User Wallet #
######################


def test_create_user_wallet_with_trial_funds(hatchery, alice, alpha_token, alpha_token_whale, setUserWalletConfig):
    """Test that trial funds get sent to the wallet when configured"""

    # Setup: Configure trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Transfer trial funds to hatchery
    alpha_token.transfer(hatchery, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds enabled (default)
    initial_hatchery_balance = alpha_token.balanceOf(hatchery.address)
    wallet_address = hatchery.createUserWallet(sender=alice)
    
    # Verify trial funds were transferred
    wallet = UserWallet.at(wallet_address)
    assert alpha_token.balanceOf(wallet.address) == trial_amount
    assert alpha_token.balanceOf(hatchery.address) == initial_hatchery_balance - trial_amount

    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    assert wallet_config.trialFundsAsset() == alpha_token.address
    assert wallet_config.trialFundsAmount() == trial_amount


def test_create_user_wallet_without_trial_funds(hatchery, alice, alpha_token, alpha_token_whale, setUserWalletConfig):
    """Test wallet creation without trial funds when disabled"""

    # Setup: Configure trial funds but disable them in creation
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Transfer trial funds to hatchery
    alpha_token.transfer(hatchery.address, trial_amount * 10, sender=alpha_token_whale)
    
    # Create wallet with trial funds disabled
    initial_hatchery_balance = alpha_token.balanceOf(hatchery.address)
    wallet_address = hatchery.createUserWallet(
        alice,
        ZERO_ADDRESS,
        False,
        sender=alice
    )
    
    # Verify no trial funds were transferred
    wallet = UserWallet.at(wallet_address)
    assert alpha_token.balanceOf(wallet.address) == 0
    assert alpha_token.balanceOf(hatchery.address) == initial_hatchery_balance
    
    # Verify wallet config still has trial funds data
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_create_user_wallet_with_ambassador(hatchery, alice, bob, ledger):
    """Test that ambassador is properly set when provided"""

    # First create an ambassador wallet
    ambassador_wallet_addr = hatchery.createUserWallet(sender=alice)
    
    # Create a user wallet with ambassador
    user_wallet_addr = hatchery.createUserWallet(
        bob,
        ambassador_wallet_addr,
        sender=bob
    )
    
    # Verify ambassador relationship in ledger
    assert ledger.ambassadors(user_wallet_addr) == ambassador_wallet_addr
    
    # Verify ambassador is a valid user wallet
    assert ledger.isUserWallet(ambassador_wallet_addr) == True


def test_create_user_wallet_ledger_registration(hatchery, alice, ledger):
    """Test that user wallet gets registered with Ledger after creation"""

    initial_count = ledger.numUserWallets()

    # Create wallet
    wallet_address = hatchery.createUserWallet(sender=alice)
    
    # Verify wallet is registered in ledger
    assert ledger.isUserWallet(wallet_address) == True
    assert ledger.userWallets(initial_count) == wallet_address
    assert ledger.indexOfUserWallet(wallet_address) == initial_count

    # Verify wallet count increased
    assert ledger.numUserWallets() == initial_count + 1


def test_user_wallet_config_data(hatchery, alice, setUserWalletConfig):
    """Test that data stored in user wallet and config reflect expected values"""

    # Setup specific configuration
    setUserWalletConfig(
        _minTimeLock=10,
        _maxTimeLock=100,
    )
    
    # Create wallet with specific group ID
    group_id = 42
    wallet_address = hatchery.createUserWallet(
        alice,
        ZERO_ADDRESS,
        False,
        group_id,
        sender=alice
    )
    
    # Get wallet and config
    wallet = UserWallet.at(wallet_address)
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    
    # Verify config data
    assert wallet_config.wallet() == wallet_address
    assert wallet_config.groupId() == group_id
    assert wallet_config.owner() == alice

    assert wallet_config.MIN_TIMELOCK() == 10
    assert wallet_config.MAX_TIMELOCK() == 100


def test_create_user_wallet_permissions(hatchery, alice, bob, charlie, setUserWalletConfig, mission_control, switchboard_alpha):
    """Test permissions around who can create wallets"""

    # By default, anyone can create wallets
    wallet1 = hatchery.createUserWallet(sender=alice)
    assert UserWalletConfig.at(UserWallet.at(wallet1).walletConfig()).owner() == alice
    
    # Create wallet for someone else
    wallet2 = hatchery.createUserWallet(bob, sender=alice)
    assert UserWalletConfig.at(UserWallet.at(wallet2).walletConfig()).owner() == bob
    
    # Restrict wallet creation by enabling whitelist
    setUserWalletConfig(
        _enforceCreatorWhitelist=True
    )
    # Add charlie to whitelist
    mission_control.setCreatorWhitelist(charlie, True, sender=switchboard_alpha.address)
    
    # Non-allowed creator should fail
    with boa.reverts("creator not allowed"):
        hatchery.createUserWallet(sender=bob)
    
    # Allowed creator should succeed
    wallet3 = hatchery.createUserWallet(sender=charlie)
    assert UserWalletConfig.at(UserWallet.at(wallet3).walletConfig()).owner() == charlie


def test_create_user_wallet_limits(hatchery, alice, setUserWalletConfig):
    """Test limits on how many wallets can be created"""
    # Set max wallets limit
    max_wallets = 5
    setUserWalletConfig(
        _numUserWalletsAllowed=max_wallets
    )
    
    # Create wallets up to the limit
    created_wallets = []
    for i in range(max_wallets - 1):
        wallet = hatchery.createUserWallet(sender=alice)
        created_wallets.append(wallet)
    
    # Verify all wallets were created
    assert len(created_wallets) == max_wallets - 1
    
    # Try to create one more - should fail
    with boa.reverts("max user wallets reached"):
        hatchery.createUserWallet(sender=alice)


def test_create_user_wallet_invalid_ambassador(hatchery, alice, bob, ledger):
    """Test that invalid ambassador addresses are rejected"""

    # Try to use a non-wallet address as ambassador
    user_wallet_addr = hatchery.createUserWallet(
        alice,
        bob,  # bob is an EOA, not a wallet
        sender=alice
    )

    # will fail gracefully
    assert ledger.ambassadors(user_wallet_addr) == ZERO_ADDRESS


def test_create_user_wallet_events(hatchery, alice, charlie, bob, alpha_token, alpha_token_whale, setUserWalletConfig, ambassador_wallet, setAgentConfig):
    """Test that correct events are emitted during wallet creation"""

    # Setup trial funds
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    alpha_token.transfer(hatchery.address, trial_amount * 10, sender=alpha_token_whale)
    setAgentConfig(
        _startingAgent=charlie
    )

    # Create user wallet and capture events
    wallet_addr = hatchery.createUserWallet(
        alice,
        ambassador_wallet,
        True,
        5,
        sender=bob
    )
    
    # Check for UserWalletCreated event
    event = filter_logs(hatchery, "UserWalletCreated")[0]
    assert event.mainAddr == wallet_addr
    assert event.configAddr == UserWallet.at(wallet_addr).walletConfig()
    assert event.owner == alice
    assert event.agent == charlie
    assert event.ambassador == ambassador_wallet.address
    assert event.creator == bob
    assert event.trialFundsAsset == alpha_token.address
    assert event.trialFundsAmount == trial_amount
    assert event.groupId == 5
    

def test_create_user_wallet_paused(hatchery, alice, switchboard_alpha):
    """Test that wallet creation fails when contract is paused"""

    # Pause the contract
    hatchery.pause(True, sender=switchboard_alpha.address)
    
    # Try to create wallet - should fail
    with boa.reverts("contract paused"):
        hatchery.createUserWallet(sender=alice)
    
    # Unpause and verify it works again
    hatchery.pause(False, sender=switchboard_alpha.address)

    wallet = hatchery.createUserWallet(sender=alice)
    assert UserWalletConfig.at(UserWallet.at(wallet).walletConfig()).owner() == alice


def test_create_user_wallet_invalid_owner(hatchery, alice):
    """Test that wallet creation fails when owner is ZERO_ADDRESS"""
    
    # Try to create wallet with ZERO_ADDRESS as owner - should fail
    with boa.reverts("invalid setup"):
        hatchery.createUserWallet(
            ZERO_ADDRESS,  # Invalid owner
            ZERO_ADDRESS,
            True,
            1,
            sender=alice
        )


def test_create_user_wallet_starting_agent_same_as_owner(hatchery, alice, setAgentConfig):
    """Test that wallet creation fails when starting agent is the same as owner"""
    
    # Set starting agent to be alice
    setAgentConfig(
        _startingAgent=alice
    )
    
    # Try to create wallet where owner and starting agent are the same - should fail
    with boa.reverts("starting agent cannot be the owner"):
        hatchery.createUserWallet(
            alice,  # Owner is alice
            ZERO_ADDRESS,
            True,
            1,
            sender=alice  # Starting agent will be alice based on config
        )


def test_create_user_wallet_insufficient_trial_funds(hatchery, alice, alpha_token, setUserWalletConfig, alpha_token_whale):
    """Test wallet creation when hatchery has insufficient trial funds"""
    
    # Setup trial funds config
    trial_amount = 10 * EIGHTEEN_DECIMALS
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=trial_amount
    )
    
    # Don't fund hatchery or fund with less than required
    # Hatchery balance is 0 or less than trial_amount

    # remove funds from hatchery
    if alpha_token.balanceOf(hatchery.address) != 0:
        alpha_token.transfer(alpha_token_whale, alpha_token.balanceOf(hatchery.address), sender=hatchery.address)

    # Create wallet - should succeed but without trial funds
    wallet_address = hatchery.createUserWallet(sender=alice)
    
    # Verify wallet was created
    wallet = UserWallet.at(wallet_address)
    assert wallet != ZERO_ADDRESS
    
    # Verify no trial funds were sent
    assert alpha_token.balanceOf(wallet.address) == 0
    
    # Verify wallet config shows no trial funds
    wallet_config = UserWalletConfig.at(wallet.walletConfig())
    assert wallet_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet_config.trialFundsAmount() == 0


def test_create_user_wallet_trial_funds_partial_config(hatchery, alice, alpha_token, setUserWalletConfig):
    """Test wallet creation with incomplete trial funds configuration"""
    
    # Test 1: Asset set but amount is 0
    setUserWalletConfig(
        _trialAsset=alpha_token.address,
        _trialAmount=0
    )
    
    wallet1 = hatchery.createUserWallet(sender=alice)
    wallet1_config = UserWalletConfig.at(UserWallet.at(wallet1).walletConfig())
    
    # Should create wallet without trial funds
    assert alpha_token.balanceOf(wallet1) == 0
    assert wallet1_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet1_config.trialFundsAmount() == 0
    
    # Test 2: Amount set but asset is ZERO_ADDRESS
    setUserWalletConfig(
        _trialAsset=ZERO_ADDRESS,
        _trialAmount=10 * EIGHTEEN_DECIMALS
    )
    
    wallet2 = hatchery.createUserWallet(sender=alice)
    wallet2_config = UserWalletConfig.at(UserWallet.at(wallet2).walletConfig())
    
    # Should create wallet without trial funds
    assert wallet2_config.trialFundsAsset() == ZERO_ADDRESS
    assert wallet2_config.trialFundsAmount() == 0
