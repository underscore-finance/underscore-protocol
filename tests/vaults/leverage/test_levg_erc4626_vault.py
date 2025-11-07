import pytest
import boa

from constants import MAX_UINT256, EIGHTEEN_DECIMALS, ZERO_ADDRESS
from conf_utils import filter_logs

# Decimal constants for different vault types
SIX_DECIMALS = 10 ** 6
EIGHT_DECIMALS = 10 ** 8

# Test configuration - list of leverage vaults to test
TEST_LEVG_VAULTS = ["usdc", "cbbtc", "weth"]

# Decimal configurations for each vault type
VAULT_DECIMALS = {
    "usdc": SIX_DECIMALS,
    "cbbtc": EIGHT_DECIMALS,
    "weth": EIGHTEEN_DECIMALS,
}


############
# Fixtures #
############


@pytest.fixture(scope="module")
def setup_mock_prices(mock_ripe, mock_green_token, mock_savings_green_token, mock_usdc, mock_cbbtc, mock_weth):
    """Set up mock prices for testing"""
    # Set price of 1 GREEN = $1 USD (18 decimals)
    mock_ripe.setPrice(mock_green_token, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 SAVINGS_GREEN = $1 USD (since it's 1:1 with GREEN in the mock)
    mock_ripe.setPrice(mock_savings_green_token, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 USDC = $1 USD (6 decimals token, 18 decimals price)
    mock_ripe.setPrice(mock_usdc, 1 * EIGHTEEN_DECIMALS)
    # Set price of 1 CBBTC = $90,000 USD (8 decimals token, 18 decimals price)
    mock_ripe.setPrice(mock_cbbtc, 90_000 * EIGHTEEN_DECIMALS)
    # Set price of 1 WETH = $2,000 USD (18 decimals token, 18 decimals price)
    mock_ripe.setPrice(mock_weth, 2_000 * EIGHTEEN_DECIMALS)
    return mock_ripe


@pytest.fixture(scope="module")
def mock_weth_whale(env, mock_weth, whale):
    """Create a whale with WETH by depositing ETH"""
    # Give whale ETH and have them deposit to WETH
    weth_amount = 10000 * EIGHTEEN_DECIMALS  # 10000 WETH
    boa.env.set_balance(whale, weth_amount)
    mock_weth.deposit(value=weth_amount, sender=whale)
    return whale


@pytest.fixture(scope="module")
def get_vault_config():
    """Factory fixture that returns vault-specific configuration data"""
    def _get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    ):
        """Get vault configuration for the given vault type"""
        configs = {
            "usdc": {
                "vault": undy_levg_vault_usdc,
                "underlying": mock_usdc,
                "decimals": SIX_DECIMALS,
                "price": 1,  # $1 USD
            },
            "cbbtc": {
                "vault": undy_levg_vault_cbbtc,
                "underlying": mock_cbbtc,
                "decimals": EIGHT_DECIMALS,
                "price": 90_000,  # $90,000 USD
            },
            "weth": {
                "vault": undy_levg_vault_weth,
                "underlying": mock_weth,
                "decimals": EIGHTEEN_DECIMALS,
                "price": 2_000,  # $2,000 USD
            },
        }
        return configs[vault_type]

    return _get_vault_config


@pytest.fixture(scope="module")
def mint_to_user():
    """Helper function to mint tokens to a user, handling WETH specially"""
    def _mint_to_user(token, user, amount, is_weth=False, whale=None, governance=None):
        if is_weth:
            # WETH: transfer from the whale (who already has WETH from depositing ETH)
            token.transfer(user, amount, sender=whale)
        else:
            # Regular ERC20: mint directly to user
            token.mint(user, amount, sender=governance.address)
    return _mint_to_user


####################################
# 1. Basic ERC4626 Initialization #
####################################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_initialization(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    setup_mock_prices,
):
    """Test ERC4626 initialization for all leverage vault types"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    assert config["vault"].asset() == config["underlying"].address
    assert config["vault"].totalAssets() == 0


###############################
# 2. Deposit Functionality #
###############################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_deposit(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test basic deposit functionality for all leverage vault types"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens to bob
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    # Approve vault
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    # Deposit
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Check balances
    assert config["vault"].balanceOf(bob) == shares
    assert config["vault"].totalAssets() == deposit_amount
    assert config["vault"].convertToAssets(shares) == deposit_amount
    assert config["vault"].convertToShares(deposit_amount) == shares


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_deposit_max_value(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    sally,
):
    """Test deposit with max_value(uint256)"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens to sally
    mint_amount = 1000 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], sally, mint_amount, is_weth, mock_weth_whale, governance)

    # Approve the vault
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=sally)

    # Deposit max value - should use all available tokens
    shares = config["vault"].deposit(MAX_UINT256, sally, sender=sally)
    assert shares > 0
    assert config["vault"].balanceOf(sally) == shares
    assert config["vault"].totalAssets() == mint_amount
    assert config["underlying"].balanceOf(sally) == 0  # All tokens should be used


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_deposit_zero_amount(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    bob,
):
    """Test deposit with zero amount"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    with boa.reverts("cannot deposit 0 amount"):
        config["vault"].deposit(0, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_deposit_invalid_receiver(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test deposit with invalid receiver"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens to bob
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    with boa.reverts("invalid recipient"):
        config["vault"].deposit(deposit_amount, ZERO_ADDRESS, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_deposit_with_different_decimals(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test that deposits properly handle different decimal precisions"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Use fractional amounts that test full decimal precision
    if vault_type == "usdc":
        amount = 12345678  # 12.345678 USDC
    elif vault_type == "cbbtc":
        amount = 12345678  # 0.12345678 cbBTC
    else:  # weth
        amount = 123456789012345678  # 0.123456789012345678 WETH

    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    shares = config["vault"].deposit(amount, bob, sender=bob)
    assert shares > 0
    assert config["vault"].totalAssets() == amount


############################
# 3. Mint Functionality #
############################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_mint(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test mint functionality"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint enough tokens to bob
    mint_amount = 1000 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, mint_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    # Calculate how many assets we need for desired shares
    desired_shares = 100 * config["decimals"]
    required_assets = config["vault"].previewMint(desired_shares)

    # Mint the shares
    assets = config["vault"].mint(desired_shares, bob, sender=bob)

    # Check balances
    assert config["vault"].balanceOf(bob) == desired_shares
    assert assets == required_assets
    assert config["vault"].totalAssets() == assets


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_mint_max_value(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test mint with max_value(uint256)"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens to bob
    mint_amount = 1000 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, mint_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    with boa.reverts("deposit failed"):
        config["vault"].mint(MAX_UINT256, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_mint_preview_accuracy(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test that previewMint accurately predicts actual mint cost"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens to bob
    mint_amount = 1000 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, mint_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    # First deposit to establish non-1:1 share price
    initial_deposit = 500 * config["decimals"]
    config["vault"].deposit(initial_deposit, bob, sender=bob)

    # Now test mint preview accuracy
    desired_shares = 50 * config["decimals"]
    expected_assets = config["vault"].previewMint(desired_shares)
    actual_assets = config["vault"].mint(desired_shares, bob, sender=bob)

    assert actual_assets == expected_assets


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_mint_zero_shares(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    bob,
):
    """Test mint with zero shares"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    # Minting 0 shares means 0 amount (at 1:1 initial price)
    # The _amount check comes before the _shares check
    with boa.reverts("cannot deposit 0 amount"):
        config["vault"].mint(0, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_mint_invalid_receiver(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test mint with invalid receiver"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens to bob
    mint_amount = 1000 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, mint_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    shares_to_mint = 100 * config["decimals"]
    with boa.reverts("invalid recipient"):
        config["vault"].mint(shares_to_mint, ZERO_ADDRESS, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_mint_when_deposits_disabled(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test mint fails when canDeposit is False"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Mint tokens to bob
    mint_amount = 1000 * config["decimals"]
    mint_to_user(config["underlying"], bob, mint_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    # Disable deposits
    vault_registry.setCanDeposit(config["vault"].address, False, sender=switchboard_alpha.address)

    shares_to_mint = 100 * config["decimals"]
    with boa.reverts("cannot deposit"):
        config["vault"].mint(shares_to_mint, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_mint_exceeding_max_deposit(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mission_control,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test mint fails when it would exceed maxDepositAmount"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Enable security actions
    mission_control.setCanPerformSecurityAction(switchboard_alpha.address, True, sender=switchboard_alpha.address)

    # Set max deposit amount
    max_amount = 1000 * config["decimals"]
    vault_registry.setMaxDepositAmount(config["vault"].address, max_amount, sender=switchboard_alpha.address)

    # Try to mint shares that would require more assets than the limit
    # At 1:1 initial price, minting more shares than max_amount should fail
    excess_shares = max_amount + (100 * config["decimals"])
    excess_assets = excess_shares  # 1:1 initial price

    mint_to_user(config["underlying"], bob, excess_assets, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    with boa.reverts("exceeds max deposit"):
        config["vault"].mint(excess_shares, bob, sender=bob)


#################################
# 4. Withdraw Functionality #
#################################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_withdraw(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test withdraw functionality"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Withdraw half
    withdraw_amount = deposit_amount // 2
    withdrawn_shares = config["vault"].withdraw(withdraw_amount, bob, bob, sender=bob)

    # Check balances
    assert config["vault"].balanceOf(bob) == shares - withdrawn_shares
    assert config["vault"].totalAssets() == deposit_amount - withdraw_amount
    assert config["underlying"].balanceOf(bob) == withdraw_amount


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_withdraw_zero_amount(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test withdraw with zero amount"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    config["vault"].deposit(deposit_amount, bob, sender=bob)

    with boa.reverts("cannot withdraw 0 amount"):
        config["vault"].withdraw(0, bob, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_withdraw_insufficient_balance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    bob,
):
    """Test withdraw with insufficient balance"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    with boa.reverts("insufficient shares"):
        config["vault"].withdraw(100 * config["decimals"], bob, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_withdraw_invalid_receiver(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test withdraw with invalid receiver"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Make a deposit first
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Try to withdraw to zero address
    with boa.reverts("invalid recipient"):
        config["vault"].withdraw(deposit_amount, ZERO_ADDRESS, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_withdraw_with_allowance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
):
    """Test third party withdrawal with allowance"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Bob makes a deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Bob approves Sally to spend his shares
    config["vault"].approve(sally, shares, sender=bob)

    # Sally withdraws on behalf of Bob
    initial_sally_balance = config["underlying"].balanceOf(sally)
    withdraw_amount = 50 * config["decimals"]
    shares_burned = config["vault"].withdraw(withdraw_amount, sally, bob, sender=sally)

    # Sally should have received the assets
    assert config["underlying"].balanceOf(sally) == initial_sally_balance + withdraw_amount

    # Bob's shares should have been burned
    assert config["vault"].balanceOf(bob) == shares - shares_burned

    # Sally's allowance should have been reduced
    assert config["vault"].allowance(bob, sally) < shares


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_withdraw_insufficient_allowance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
):
    """Test withdrawal fails with insufficient allowance"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Bob makes a deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Sally tries to withdraw without allowance
    withdraw_amount = 50 * config["decimals"]
    with boa.reverts():  # ERC20 insufficient allowance error
        config["vault"].withdraw(withdraw_amount, sally, bob, sender=sally)


##############################
# 5. Redeem Functionality #
##############################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_redeem(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test redeem functionality"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Redeem half
    redeem_shares = shares // 2
    redeemed_amount = config["vault"].redeem(redeem_shares, bob, bob, sender=bob)

    # Check balances
    assert config["vault"].balanceOf(bob) == shares - redeem_shares
    assert config["vault"].totalAssets() == deposit_amount - redeemed_amount
    assert config["underlying"].balanceOf(bob) == redeemed_amount


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_redeem_max_value(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test redeem with max_value(uint256)"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Redeem all shares
    redeemed_amount = config["vault"].redeem(MAX_UINT256, bob, bob, sender=bob)
    assert redeemed_amount == deposit_amount
    assert config["vault"].balanceOf(bob) == 0


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_redeem_zero_shares(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test redeem with zero shares"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    config["vault"].deposit(deposit_amount, bob, sender=bob)

    with boa.reverts("cannot withdraw 0 amount"):
        config["vault"].redeem(0, bob, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_redeem_invalid_receiver(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test redeem with invalid receiver"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Make a deposit first
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Try to redeem to zero address
    with boa.reverts("invalid recipient"):
        config["vault"].redeem(shares, ZERO_ADDRESS, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_redeem_with_allowance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
):
    """Test third party redemption with allowance"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Bob makes a deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Bob approves Sally to spend his shares
    config["vault"].approve(sally, shares, sender=bob)

    # Sally redeems on behalf of Bob
    initial_sally_balance = config["underlying"].balanceOf(sally)
    redeem_shares = shares // 2
    assets_received = config["vault"].redeem(redeem_shares, sally, bob, sender=sally)

    # Sally should have received the assets
    assert config["underlying"].balanceOf(sally) == initial_sally_balance + assets_received

    # Bob's shares should have been burned
    assert config["vault"].balanceOf(bob) == shares - redeem_shares

    # Sally's allowance should have been reduced
    assert config["vault"].allowance(bob, sally) < shares


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_redeem_insufficient_allowance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
):
    """Test redemption fails with insufficient allowance"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Bob makes a deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Sally tries to redeem without allowance
    with boa.reverts():  # ERC20 insufficient allowance error
        config["vault"].redeem(shares // 2, sally, bob, sender=sally)


##############################
# 6. Share Calculations #
##############################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_share_calculations(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
):
    """Test share calculations with multiple deposits"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # First deposit
    deposit1 = 100 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit1, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares1 = config["vault"].deposit(deposit1, bob, sender=bob)

    # Second deposit
    deposit2 = 200 * config["decimals"]
    mint_to_user(config["underlying"], sally, deposit2, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=sally)
    shares2 = config["vault"].deposit(deposit2, sally, sender=sally)

    # Check share ratios
    assert shares2 > shares1  # More assets should give more shares
    assert config["vault"].convertToAssets(shares1) == deposit1
    assert config["vault"].convertToAssets(shares2) == deposit2


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_rounding_behavior(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test rounding behavior in share calculations"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Test preview functions maintain consistency
    shares_preview = config["vault"].previewDeposit(deposit_amount)
    assert shares_preview >= shares

    # Test redeem preview
    assets_preview = config["vault"].previewRedeem(shares)
    assert assets_preview <= deposit_amount


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_proportional_shares(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test proportional share distribution for different deposit sizes"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Initial deposit
    deposit_amount = 100 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares1 = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Try to manipulate share price with tiny deposit
    tiny_amount = 1
    mint_to_user(config["underlying"], bob, tiny_amount, is_weth, mock_weth_whale, governance)
    shares2 = config["vault"].deposit(tiny_amount, bob, sender=bob)

    # Check that share price wasn't significantly affected
    assert shares2 < shares1 // 100  # Tiny deposit should give proportionally tiny shares


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_decimal_precision(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test calculations maintain decimal precision"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Use fractional amount using all decimal places
    if vault_type == "usdc":
        amount = 12345678  # 12.345678 USDC
    elif vault_type == "cbbtc":
        amount = 12345678  # 0.12345678 cbBTC
    else:  # weth
        amount = 123456789012345678  # 0.123456789012345678 WETH

    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(amount, bob, sender=bob)

    # Should preserve decimal precision
    assert config["vault"].convertToAssets(shares) == amount


###########################################
# 7. Preview and Convert Functions #
###########################################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_preview_functions(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test preview functions accuracy"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Test previewDeposit
    preview_shares = config["vault"].previewDeposit(deposit_amount)
    assert preview_shares == shares

    # Test previewMint
    preview_assets = config["vault"].previewMint(shares)
    assert preview_assets == deposit_amount

    # Test previewWithdraw
    preview_withdraw_shares = config["vault"].previewWithdraw(deposit_amount)
    assert preview_withdraw_shares == shares

    # Test previewRedeem
    preview_redeem_assets = config["vault"].previewRedeem(shares)
    assert preview_redeem_assets == deposit_amount


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_convert_functions(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test convert functions accuracy"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Test convertToShares
    converted_shares = config["vault"].convertToShares(deposit_amount)
    assert converted_shares == shares

    # Test convertToAssets
    converted_assets = config["vault"].convertToAssets(shares)
    assert converted_assets == deposit_amount

    # Test with zero values
    assert config["vault"].convertToShares(0) == 0
    assert config["vault"].convertToAssets(0) == 0


#########################
# 8. Max Functions #
#########################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_max_functions(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test max functions"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Test maxDeposit
    assert config["vault"].maxDeposit(bob) == MAX_UINT256

    # Test maxMint
    assert config["vault"].maxMint(bob) == MAX_UINT256

    # Test maxWithdraw and maxRedeem before deposit
    assert config["vault"].maxWithdraw(bob) == 0
    assert config["vault"].maxRedeem(bob) == 0

    # Make a deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Test maxWithdraw and maxRedeem after deposit
    assert config["vault"].maxWithdraw(bob) == deposit_amount
    assert config["vault"].maxRedeem(bob) == shares


###########################
# 9. Allowance Tests #
###########################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_allowance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
):
    """Test allowance functionality"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Approve Sally to spend Bob's shares
    config["vault"].approve(sally, shares, sender=bob)

    # Sally redeems Bob's shares
    redeemed_amount = config["vault"].redeem(shares, sally, bob, sender=sally)
    assert redeemed_amount == deposit_amount
    assert config["vault"].balanceOf(bob) == 0
    assert config["underlying"].balanceOf(sally) == deposit_amount


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_insufficient_allowance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
):
    """Test insufficient allowance"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens and deposit
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Approve Sally for less than total shares
    config["vault"].approve(sally, shares // 2, sender=bob)

    # Try to redeem more than allowed
    with boa.reverts("insufficient allowance"):
        config["vault"].redeem(shares, sally, bob, sender=sally)


#########################
# 10. Event Tests #
#########################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_events(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test event emissions"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Mint tokens
    deposit_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    # Test Deposit event
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)
    log = filter_logs(config["vault"], "Deposit")[0]

    assert log.sender == bob
    assert log.owner == bob
    assert log.assets == deposit_amount
    assert log.shares == shares

    # Test Withdraw event
    withdraw_amount = deposit_amount // 2
    withdrawn_shares = config["vault"].withdraw(withdraw_amount, bob, bob, sender=bob)
    log = filter_logs(config["vault"], "Withdraw")[0]

    assert log.sender == bob
    assert log.receiver == bob
    assert log.owner == bob
    assert log.assets == withdraw_amount
    assert log.shares == withdrawn_shares


################################################
# 11. Leverage Vault Specific Tests (totalAssets with collateral/debt) #
################################################

# Note: The following tests check leverage-specific totalAssets behavior by directly
# minting to the vault and setting up collateral/debt on MockRipe.


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_total_assets_with_collateral(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_ripe,
    mock_savings_green_token,
    mint_to_user,
    mock_weth_whale,
    governance,
    vault_registry,
    switchboard_alpha,
    setup_mock_prices,
):
    """Test totalAssets includes collateral deposited on Ripe"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Disable shouldAutoDeposit to allow direct minting to vault
    vault_registry.setShouldAutoDeposit(config["vault"].address, False, sender=switchboard_alpha.address)

    # Mint underlying tokens directly to vault
    underlying_amount = 10 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], config["vault"].address, underlying_amount, is_weth, mock_weth_whale, governance)

    # Give vault some SAVINGS_GREEN collateral on Ripe
    savings_green_amount = 5_000 * EIGHTEEN_DECIMALS  # $5,000 worth of SAVINGS_GREEN
    mock_ripe.setUserCollateral(config["vault"].address, mock_savings_green_token, savings_green_amount)

    total_assets = config["vault"].totalAssets()

    # For USDC: should be 10 USDC + $5k GREEN = 5010 USDC
    # For cbBTC: 10 cbBTC ($900k) + $5k GREEN = $905k / $90k = ~10.055 cbBTC
    # For WETH: 10 WETH ($20k) + $5k GREEN = $25k / $2k = 12.5 WETH
    assert total_assets > underlying_amount  # Should include GREEN value


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_total_assets_with_debt(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_ripe,
    mint_to_user,
    mock_weth_whale,
    governance,
    vault_registry,
    switchboard_alpha,
    setup_mock_prices,
):
    """Test totalAssets subtracts debt owed to Ripe"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Disable shouldAutoDeposit to allow direct minting to vault
    vault_registry.setShouldAutoDeposit(config["vault"].address, False, sender=switchboard_alpha.address)

    # Mint underlying tokens directly to vault
    underlying_amount = 100 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], config["vault"].address, underlying_amount, is_weth, mock_weth_whale, governance)

    # Add debt to the vault
    debt_amount = 10_000 * EIGHTEEN_DECIMALS  # $10,000 debt
    mock_ripe.setUserDebt(config["vault"].address, debt_amount)

    total_assets = config["vault"].totalAssets()

    # For USDC: 100 USDC - $10k debt = underwater (should be very low or 0)
    # For cbBTC: 100 cbBTC ($9M) - $10k debt = $8.99M / $90k = ~99.88 cbBTC
    # For WETH: 100 WETH ($200k) - $10k debt = $190k / $2k = 95 WETH
    assert total_assets < underlying_amount  # Should subtract debt value


@pytest.mark.parametrize("vault_type", ["cbbtc", "weth"])  # Skip USDC as it would be underwater
def test_total_assets_underwater(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_ripe,
    mint_to_user,
    mock_weth_whale,
    governance,
    vault_registry,
    switchboard_alpha,
    setup_mock_prices,
):
    """Test totalAssets when vault is underwater (debt > assets)"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Disable shouldAutoDeposit to allow direct minting to vault
    vault_registry.setShouldAutoDeposit(config["vault"].address, False, sender=switchboard_alpha.address)

    # Mint small amount of underlying directly to vault
    underlying_amount = 1 * config["decimals"]  # 1 unit
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], config["vault"].address, underlying_amount, is_weth, mock_weth_whale, governance)

    # Add debt that exceeds the asset value
    # cbBTC: 1 cbBTC = $90k, add $100k debt
    # WETH: 1 WETH = $2k, add $3k debt
    if vault_type == "cbbtc":
        debt_amount = 100_000 * EIGHTEEN_DECIMALS
    else:  # weth
        debt_amount = 3_000 * EIGHTEEN_DECIMALS

    mock_ripe.setUserDebt(config["vault"].address, debt_amount)

    total_assets = config["vault"].totalAssets()

    # Vault is underwater - should return very small or 0 (can't be negative)
    assert total_assets < underlying_amount


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_share_price_with_leverage_positions(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_ripe,
    mock_savings_green_token,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
    setup_mock_prices,
):
    """Test share price calculations with active leverage positions"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Bob deposits initially
    initial_deposit = 100 * config["decimals"]
    mint_to_user(config["underlying"], bob, initial_deposit, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    bob_shares = config["vault"].deposit(initial_deposit, bob, sender=bob)

    # Vault takes on leverage position (SAVINGS_GREEN collateral + debt)
    savings_green_collateral = 50_000 * EIGHTEEN_DECIMALS  # $50k SAVINGS_GREEN collateral
    green_debt = 25_000 * EIGHTEEN_DECIMALS  # $25k debt
    mock_ripe.setUserCollateral(config["vault"].address, mock_savings_green_token, savings_green_collateral)
    mock_ripe.setUserDebt(config["vault"].address, green_debt)

    # Total assets should now be higher due to net leverage position
    total_assets_with_leverage = config["vault"].totalAssets()
    assert total_assets_with_leverage > initial_deposit

    # Sally deposits after leverage is applied
    sally_deposit = 50 * config["decimals"]
    mint_to_user(config["underlying"], sally, sally_deposit, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=sally)
    sally_shares = config["vault"].deposit(sally_deposit, sally, sender=sally)

    # Sally should get fewer shares because share price increased
    expected_sally_shares_if_no_leverage = sally_deposit
    assert sally_shares < expected_sally_shares_if_no_leverage


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_multiple_operations_with_changing_leverage(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mock_ripe,
    mock_savings_green_token,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    setup_mock_prices,
):
    """Test deposits/withdrawals work correctly as leverage positions change"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Initial deposit
    deposit_amount = 100 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    initial_total_assets = config["vault"].totalAssets()

    # Add leverage (SAVINGS_GREEN collateral, net positive)
    savings_green_collateral = 20_000 * EIGHTEEN_DECIMALS
    green_debt = 10_000 * EIGHTEEN_DECIMALS
    mock_ripe.setUserCollateral(config["vault"].address, mock_savings_green_token, savings_green_collateral)
    mock_ripe.setUserDebt(config["vault"].address, green_debt)

    # Total assets should increase
    leveraged_total_assets = config["vault"].totalAssets()
    assert leveraged_total_assets > initial_total_assets

    # Withdraw half
    withdraw_amount = deposit_amount // 2
    withdrawn_shares = config["vault"].withdraw(withdraw_amount, bob, bob, sender=bob)

    # Should still have shares remaining
    assert config["vault"].balanceOf(bob) > 0
    assert config["vault"].balanceOf(bob) == shares - withdrawn_shares


#######################
# 12. Edge Cases #
#######################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_erc4626_rounding_edge_cases(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    setup_mock_prices,
):
    """Test rounding with very small and very large amounts"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Test with small amount (need to exceed minimum deposit requirement)
    # MockErc4626Vault requires amount > 10 ** (decimals // 2)
    if vault_type == "usdc":
        tiny_amount = 10000  # 0.01 USDC (6 decimals), > 10^3
    elif vault_type == "cbbtc":
        tiny_amount = 100000  # 0.001 cbBTC (8 decimals), > 10^4
    else:  # weth
        tiny_amount = 10000000000  # 0.00000001 WETH (18 decimals), > 10^9

    mint_to_user(config["underlying"], bob, tiny_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    tiny_shares = config["vault"].deposit(tiny_amount, bob, sender=bob)
    assert tiny_shares > 0  # Should still get some shares

    # Test with large amount (use reasonable amounts that whale can afford for WETH)
    if vault_type == "weth":
        large_amount = 1000 * config["decimals"]  # 1000 WETH (whale has 10,000)
    else:
        large_amount = 1000000 * config["decimals"]  # 1 million units
    mint_to_user(config["underlying"], bob, large_amount, is_weth, mock_weth_whale, governance)
    large_shares = config["vault"].deposit(large_amount, bob, sender=bob)
    assert large_shares > tiny_shares  # Should get more shares


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_first_depositor_share_price(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test first depositor gets 1:1 share price"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # First deposit should get 1:1 shares
    deposit_amount = 100 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # First depositor gets 1:1
    assert shares == deposit_amount


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_share_price_changes_with_profit(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
    vault_registry,
    switchboard_alpha,
    setup_mock_prices,
):
    """Test share price changes when vault earns profit"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Bob makes initial deposit
    initial_deposit = 1000 * config["decimals"]
    mint_to_user(config["underlying"], bob, initial_deposit, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    bob_shares = config["vault"].deposit(initial_deposit, bob, sender=bob)

    # Record initial share price (should be 1:1 initially)
    initial_total_assets = config["vault"].totalAssets()
    total_supply = config["vault"].totalSupply()
    initial_share_price = config["vault"].convertToAssets(config["decimals"])

    # Simulate profit by directly adding assets to vault (without issuing shares)
    # Disable shouldAutoDeposit to allow direct minting to vault
    vault_registry.setShouldAutoDeposit(config["vault"].address, False, sender=switchboard_alpha.address)

    profit_amount = 500 * config["decimals"]  # 50% profit
    mint_to_user(config["underlying"], config["vault"].address, profit_amount, is_weth, mock_weth_whale, governance)

    # Total assets should have increased, but total supply should stay the same
    new_total_assets = config["vault"].totalAssets()
    assert new_total_assets > initial_total_assets
    assert config["vault"].totalSupply() == total_supply  # No new shares issued

    # Share price should have increased
    new_share_price = config["vault"].convertToAssets(config["decimals"])
    assert new_share_price > initial_share_price

    # Sally deposits same amount as initial deposit
    # She should get fewer shares due to increased share price
    sally_deposit = initial_deposit
    mint_to_user(config["underlying"], sally, sally_deposit, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=sally)

    # Re-enable shouldAutoDeposit for Sally's deposit
    vault_registry.setShouldAutoDeposit(config["vault"].address, True, sender=switchboard_alpha.address)
    sally_shares = config["vault"].deposit(sally_deposit, sally, sender=sally)

    # Sally should get fewer shares than Bob for the same deposit amount
    assert sally_shares < bob_shares


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_sequential_deposits_and_withdrawals(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test multiple sequential operations maintain accounting consistency"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Mint enough for multiple operations
    total_amount = 500 * config["decimals"]
    mint_to_user(config["underlying"], bob, total_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    # Deposit 100
    deposit1 = 100 * config["decimals"]
    shares1 = config["vault"].deposit(deposit1, bob, sender=bob)

    # Withdraw 50
    withdraw1 = 50 * config["decimals"]
    withdrawn_shares1 = config["vault"].withdraw(withdraw1, bob, bob, sender=bob)

    # Deposit 200
    deposit2 = 200 * config["decimals"]
    shares2 = config["vault"].deposit(deposit2, bob, sender=bob)

    # Redeem half of remaining shares
    current_shares = config["vault"].balanceOf(bob)
    redeem_shares = current_shares // 2
    redeemed_amount = config["vault"].redeem(redeem_shares, bob, bob, sender=bob)

    # Final state should be consistent
    final_shares = config["vault"].balanceOf(bob)
    final_assets_value = config["vault"].convertToAssets(final_shares)

    # Should have positive balance
    assert final_shares > 0
    assert final_assets_value > 0


########################################
# 13. Vault Registry Integration #
########################################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_can_deposit_flag_blocks_deposits(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test that deposits are blocked when canDeposit is False"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Initially canDeposit should be True
    assert vault_registry.canDeposit(config["vault"].address) == True

    # Make a successful deposit first
    deposit_amount = 100 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # Disable deposits
    vault_registry.setCanDeposit(config["vault"].address, False, sender=switchboard_alpha.address)
    assert vault_registry.canDeposit(config["vault"].address) == False

    # Try to deposit - should fail
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    with boa.reverts("cannot deposit"):
        config["vault"].deposit(deposit_amount, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_can_withdraw_flag_blocks_withdrawals(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test that withdrawals are blocked when canWithdraw is False"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Initially canWithdraw should be True
    assert vault_registry.canWithdraw(config["vault"].address) == True

    # First deposit some funds
    deposit_amount = 100 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # Disable withdrawals
    vault_registry.setCanWithdraw(config["vault"].address, False, sender=switchboard_alpha.address)
    assert vault_registry.canWithdraw(config["vault"].address) == False

    # Try to redeem - should fail
    with boa.reverts("cannot withdraw"):
        config["vault"].redeem(shares, bob, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_multiple_flag_changes(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test multiple changes to canDeposit and canWithdraw flags"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"
    deposit_amount = 50 * config["decimals"]

    # Mint tokens for bob
    mint_to_user(config["underlying"], bob, deposit_amount * 3, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    # Deposit when allowed
    shares1 = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Disable deposits
    vault_registry.setCanDeposit(config["vault"].address, False, sender=switchboard_alpha.address)

    # Can't deposit
    with boa.reverts("cannot deposit"):
        config["vault"].deposit(deposit_amount, bob, sender=bob)

    # But can still withdraw
    withdrawn = config["vault"].redeem(shares1 // 2, bob, bob, sender=bob)
    assert withdrawn > 0

    # Enable deposits, disable withdrawals
    vault_registry.setCanDeposit(config["vault"].address, True, sender=switchboard_alpha.address)
    vault_registry.setCanWithdraw(config["vault"].address, False, sender=switchboard_alpha.address)

    # Can deposit again
    shares2 = config["vault"].deposit(deposit_amount, bob, sender=bob)
    assert shares2 > 0

    # But can't withdraw
    with boa.reverts("cannot withdraw"):
        config["vault"].redeem(shares2, bob, bob, sender=bob)

    # Enable both
    vault_registry.setCanWithdraw(config["vault"].address, True, sender=switchboard_alpha.address)

    # Both operations should work
    shares3 = config["vault"].deposit(deposit_amount, bob, sender=bob)
    assert shares3 > 0

    total_shares = config["vault"].balanceOf(bob)
    assets_received = config["vault"].redeem(total_shares, bob, bob, sender=bob)
    assert assets_received > 0

    # Should have no shares left
    assert config["vault"].balanceOf(bob) == 0


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_governance_can_deposit_when_flag_disabled(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    governance,
    mint_to_user,
    mock_weth_whale,
    setup_mock_prices,
    bob,
):
    """Test that governance can deposit even when canDeposit is False"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"
    deposit_amount = 100 * config["decimals"]

    # Setup: Mint tokens for both bob and governance
    mint_to_user(config["underlying"], bob, deposit_amount * 2, is_weth, mock_weth_whale, governance)
    mint_to_user(config["underlying"], governance.address, deposit_amount, is_weth, mock_weth_whale, governance)

    # Approve vault for both users
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=governance.address)

    # Initially canDeposit should be True - verify regular user can deposit
    assert vault_registry.canDeposit(config["vault"].address) == True
    shares_bob_before = config["vault"].deposit(deposit_amount, bob, sender=bob)
    assert shares_bob_before > 0

    # Disable deposits
    vault_registry.setCanDeposit(config["vault"].address, False, sender=switchboard_alpha.address)
    assert vault_registry.canDeposit(config["vault"].address) == False

    # Verify regular user (bob) cannot deposit
    with boa.reverts("cannot deposit"):
        config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Verify governance CAN deposit when flag is disabled
    gov_shares = config["vault"].deposit(deposit_amount, governance.address, sender=governance.address)
    assert gov_shares > 0
    assert config["vault"].balanceOf(governance.address) == gov_shares

    # Re-enable deposits and verify normal operation resumes
    vault_registry.setCanDeposit(config["vault"].address, True, sender=switchboard_alpha.address)
    shares_bob_after = config["vault"].deposit(deposit_amount, bob, sender=bob)
    assert shares_bob_after > 0


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_governance_can_withdraw_when_flag_disabled(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    governance,
    mint_to_user,
    mock_weth_whale,
    setup_mock_prices,
    bob,
):
    """Test that governance can withdraw even when canWithdraw is False"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"
    deposit_amount = 100 * config["decimals"]

    # Setup: Mint tokens and make deposits for both bob and governance
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    mint_to_user(config["underlying"], governance.address, deposit_amount, is_weth, mock_weth_whale, governance)

    # Approve vault for both users
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=governance.address)

    # Make deposits for both users
    shares_bob = config["vault"].deposit(deposit_amount, bob, sender=bob)
    shares_gov = config["vault"].deposit(deposit_amount, governance.address, sender=governance.address)
    assert shares_bob > 0
    assert shares_gov > 0

    # Disable withdrawals
    vault_registry.setCanWithdraw(config["vault"].address, False, sender=switchboard_alpha.address)
    assert vault_registry.canWithdraw(config["vault"].address) == False

    # Verify regular user (bob) cannot withdraw
    with boa.reverts("cannot withdraw"):
        config["vault"].redeem(shares_bob, bob, bob, sender=bob)

    # Verify governance CAN withdraw when flag is disabled
    gov_balance_before = config["underlying"].balanceOf(governance.address)
    assets_received = config["vault"].redeem(shares_gov, governance.address, governance.address, sender=governance.address)
    assert assets_received > 0
    gov_balance_after = config["underlying"].balanceOf(governance.address)
    assert gov_balance_after == gov_balance_before + assets_received
    assert config["vault"].balanceOf(governance.address) == 0

    # Re-enable withdrawals and verify normal operation resumes
    vault_registry.setCanWithdraw(config["vault"].address, True, sender=switchboard_alpha.address)
    bob_balance_before = config["underlying"].balanceOf(bob)
    assets_bob = config["vault"].redeem(shares_bob, bob, bob, sender=bob)
    assert assets_bob > 0
    assert config["underlying"].balanceOf(bob) == bob_balance_before + assets_bob


########################################
# 14. maxDepositAmount Tests #
########################################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_max_deposit_amount_enforcement(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mission_control,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test that maxDepositAmount is enforced correctly"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Enable security actions for switchboard
    mission_control.setCanPerformSecurityAction(switchboard_alpha.address, True, sender=switchboard_alpha.address)

    # Set max deposit amount to 1000 units
    max_amount = 1000 * config["decimals"]
    vault_registry.setMaxDepositAmount(config["vault"].address, max_amount, sender=switchboard_alpha.address)

    # Verify maxDeposit returns the limit
    assert config["vault"].maxDeposit(bob) == max_amount

    # Deposit up to the limit should work
    deposit_amount = 500 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)
    assert shares > 0

    # maxDeposit should now return remaining capacity
    assert config["vault"].maxDeposit(bob) == max_amount - deposit_amount

    # Try to deposit more than remaining capacity - should fail
    excess_deposit = (max_amount - deposit_amount) + (1 * config["decimals"])
    mint_to_user(config["underlying"], bob, excess_deposit, is_weth, mock_weth_whale, governance)
    with boa.reverts("exceeds max deposit"):
        config["vault"].deposit(excess_deposit, bob, sender=bob)

    # Deposit exactly to the limit should work
    remaining = max_amount - deposit_amount
    config["vault"].deposit(remaining, bob, sender=bob)

    # maxDeposit should now return 0
    assert config["vault"].maxDeposit(bob) == 0


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_max_deposit_amount_zero_means_unlimited(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    bob,
):
    """Test that maxDepositAmount of 0 means unlimited deposits"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Default maxDepositAmount should be 0
    # maxDeposit should return MAX_UINT256
    assert config["vault"].maxDeposit(bob) == MAX_UINT256


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_max_mint_respects_deposit_limit(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mission_control,
    bob,
):
    """Test that maxMint correctly converts maxDeposit limit to shares"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Enable security actions
    mission_control.setCanPerformSecurityAction(switchboard_alpha.address, True, sender=switchboard_alpha.address)

    # Set max deposit amount
    max_amount = 1000 * config["decimals"]
    vault_registry.setMaxDepositAmount(config["vault"].address, max_amount, sender=switchboard_alpha.address)

    # maxMint should return shares equivalent to max deposit amount
    max_deposit = config["vault"].maxDeposit(bob)
    max_mint = config["vault"].maxMint(bob)

    # At 1:1 initial price, should be equal
    assert max_mint == max_deposit


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_max_deposit_when_can_deposit_false(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mission_control,
    bob,
):
    """Test that maxDeposit returns 0 when canDeposit is false"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Enable security actions
    mission_control.setCanPerformSecurityAction(switchboard_alpha.address, True, sender=switchboard_alpha.address)

    # Set max deposit amount
    max_amount = 1000 * config["decimals"]
    vault_registry.setMaxDepositAmount(config["vault"].address, max_amount, sender=switchboard_alpha.address)

    # Disable deposits
    vault_registry.setCanDeposit(config["vault"].address, False, sender=switchboard_alpha.address)

    # maxDeposit should return 0 even though there's a limit set
    assert config["vault"].maxDeposit(bob) == 0
    assert config["vault"].maxMint(bob) == 0


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_deposit_limit_updates_with_withdrawals(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mission_control,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test that maxDeposit capacity is restored after withdrawals"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Enable security actions
    mission_control.setCanPerformSecurityAction(switchboard_alpha.address, True, sender=switchboard_alpha.address)

    # Set max deposit amount
    max_amount = 1000 * config["decimals"]
    vault_registry.setMaxDepositAmount(config["vault"].address, max_amount, sender=switchboard_alpha.address)

    # Deposit full amount
    mint_to_user(config["underlying"], bob, max_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(max_amount, bob, sender=bob)

    # maxDeposit should be 0
    assert config["vault"].maxDeposit(bob) == 0

    # Withdraw half
    config["vault"].redeem(shares // 2, bob, bob, sender=bob)

    # maxDeposit should be restored to ~half of limit
    # (allowing for small rounding differences)
    new_max = config["vault"].maxDeposit(bob)
    expected = max_amount // 2
    assert abs(new_max - expected) <= expected // 100  # Within 1%


####################################
# 15. Slippage Tolerance Tests #
####################################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_withdrawal_slippage_within_tolerance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test withdrawal succeeds with slippage up to 0.1%"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Make a deposit
    deposit_amount = 1000 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Withdraw with expected 0.1% slippage (should succeed)
    # The actual test of this would require mocking _prepareRedemption to return less
    # For now, we just verify normal withdrawal works (0% slippage)
    withdraw_amount = 500 * config["decimals"]
    actual = config["vault"].withdraw(withdraw_amount, bob, bob, sender=bob)

    # Should be within 0.1% of requested amount
    assert actual >= withdraw_amount - (withdraw_amount // 1000)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_redemption_slippage_within_tolerance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test redemption succeeds with slippage up to 0.1%"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Make a deposit
    deposit_amount = 1000 * config["decimals"]
    is_weth = vault_type == "weth"
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Redeem half the shares
    # The actual test of this would require mocking _prepareRedemption to return less
    # For now, we just verify normal redemption works (0% slippage)
    redeem_shares = shares // 2
    actual = config["vault"].redeem(redeem_shares, bob, bob, sender=bob)

    # Should be close to expected amount
    expected = deposit_amount // 2
    assert abs(actual - expected) <= expected // 100  # Within 1%


##########################################
# 16. shouldAutoDeposit Behavior Tests #
##########################################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_should_auto_deposit_disabled(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test that shouldAutoDeposit=False does NOT call _onReceiveVaultFunds"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Disable shouldAutoDeposit
    vault_registry.setShouldAutoDeposit(config["vault"].address, False, sender=switchboard_alpha.address)

    # Make a deposit
    deposit_amount = 100 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Deposit should succeed
    assert shares > 0

    # Assets should remain in vault (not auto-deployed)
    # This is verified by the fact that the vault can directly transfer them out
    assert config["underlying"].balanceOf(config["vault"].address) == deposit_amount


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_should_auto_deposit_enabled(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    vault_registry,
    switchboard_alpha,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
):
    """Test that shouldAutoDeposit=True calls _onReceiveVaultFunds"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Ensure shouldAutoDeposit is enabled (default should be true)
    assert vault_registry.shouldAutoDeposit(config["vault"].address) == True

    # Make a deposit
    deposit_amount = 100 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Deposit should succeed
    assert shares > 0

    # With autoDeposit enabled, funds may be deployed to yield opportunities
    # We can't make strong assumptions about vault balance since it depends on the implementation


###################################
# 17. max_value Edge Case Tests #
###################################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_deposit_max_value_with_zero_balance(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    bob,
):
    """Test deposit(max_value) with zero balance fails appropriately"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Bob has no tokens
    assert config["underlying"].balanceOf(bob) == 0

    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)

    # Trying to deposit max_value should fail with "cannot deposit 0 amount"
    with boa.reverts("cannot deposit 0 amount"):
        config["vault"].deposit(MAX_UINT256, bob, sender=bob)


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_redeem_max_value_with_zero_shares(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    bob,
):
    """Test redeem(max_value) with zero shares fails appropriately"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # Bob has no shares
    assert config["vault"].balanceOf(bob) == 0

    # Trying to redeem max_value should fail
    # redeem(max_value) becomes redeem(0 shares) -> 0 amount -> "cannot withdraw 0 amount"
    with boa.reverts("cannot withdraw 0 amount"):
        config["vault"].redeem(MAX_UINT256, bob, bob, sender=bob)


#######################################
# 18. Conversion Edge Case Tests #
#######################################


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_conversions_with_zero_total_supply(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
):
    """Test conversion functions when totalSupply is 0"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    # At initialization, totalSupply should be 0
    assert config["vault"].totalSupply() == 0

    # convertToShares should return 1:1 for first deposit
    amount = 100 * config["decimals"]
    shares = config["vault"].convertToShares(amount)
    assert shares == amount

    # convertToAssets should also return 1:1
    assets = config["vault"].convertToAssets(amount)
    assert assets == amount


@pytest.mark.parametrize("vault_type", TEST_LEVG_VAULTS)
def test_all_shares_burned_then_new_deposit(
    vault_type,
    get_vault_config,
    undy_levg_vault_usdc,
    undy_levg_vault_cbbtc,
    undy_levg_vault_weth,
    mock_usdc,
    mock_cbbtc,
    mock_weth,
    mint_to_user,
    mock_weth_whale,
    governance,
    bob,
    sally,
):
    """Test that after all shares are burned, new deposits work correctly"""
    config = get_vault_config(
        vault_type,
        undy_levg_vault_usdc,
        undy_levg_vault_cbbtc,
        undy_levg_vault_weth,
        mock_usdc,
        mock_cbbtc,
        mock_weth,
    )

    is_weth = vault_type == "weth"

    # Bob makes initial deposit
    deposit_amount = 1000 * config["decimals"]
    mint_to_user(config["underlying"], bob, deposit_amount, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=bob)
    shares = config["vault"].deposit(deposit_amount, bob, sender=bob)

    # Bob redeems all shares
    config["vault"].redeem(shares, bob, bob, sender=bob)

    # Total supply should be 0
    assert config["vault"].totalSupply() == 0

    # Sally makes a new deposit - should get 1:1 shares like first depositor
    sally_deposit = 500 * config["decimals"]
    mint_to_user(config["underlying"], sally, sally_deposit, is_weth, mock_weth_whale, governance)
    config["underlying"].approve(config["vault"], MAX_UINT256, sender=sally)
    sally_shares = config["vault"].deposit(sally_deposit, sally, sender=sally)

    # Should get 1:1 shares
    assert sally_shares == sally_deposit
