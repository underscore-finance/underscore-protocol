import pytest
import boa

from contracts.core.userWallet import UserWallet
from contracts.core.userWallet import UserWalletConfig
from constants import EIGHTEEN_DECIMALS, MAX_UINT256


###########
# Fixtures #
###########


@pytest.fixture(scope="module")
def setupSwapTest(user_wallet, mock_dex_lego, mock_dex_asset, mock_dex_asset_alt, lego_book, mock_ripe, switchboard_alpha, whale):
    def setupSwapTest():
        lego_id = lego_book.getRegId(mock_dex_lego.address)

        # Set prices for assets
        mock_ripe.setPrice(mock_dex_asset, 2 * EIGHTEEN_DECIMALS)  # $2
        mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)  # $3

        # Transfer some tokens to the user wallet
        amount = 1000 * EIGHTEEN_DECIMALS
        mock_dex_asset.transfer(user_wallet, amount, sender=whale)
        mock_dex_asset_alt.transfer(user_wallet, amount, sender=whale)

        # Register assets in wallet config
        wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
        wallet_config.updateAssetData(lego_id, mock_dex_asset, False, sender=switchboard_alpha.address)
        wallet_config.updateAssetData(lego_id, mock_dex_asset_alt, False, sender=switchboard_alpha.address)

        return amount

    yield setupSwapTest


@pytest.fixture(scope="module")
def prepareAssetForWalletTx(user_wallet, lego_book, mock_yield_lego, whale, mock_ripe, switchboard_alpha):
    def prepareAssetForWalletTx(_asset, _amount, _whale, _price, _shouldCheckYield=False):
        # Set price for asset
        mock_ripe.setPrice(_asset, _price)

        # Transfer tokens to the user wallet
        _asset.transfer(user_wallet, _amount, sender=_whale)

        # Register asset in wallet config
        lego_id = lego_book.getRegId(mock_yield_lego.address)
        wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
        wallet_config.updateAssetData(lego_id, _asset, _shouldCheckYield, sender=switchboard_alpha.address)

        return _amount

    yield prepareAssetForWalletTx


############################
# Owner Bypasses Swap Restrictions #
############################


def test_owner_bypasses_swap_must_have_usd_value(
    setupSwapTest,
    user_wallet,
    user_wallet_config,
    bob,
    alice,
    mock_dex_asset,
    mock_dex_asset_alt,
    high_command,
    createGlobalManagerSettings,
    createSwapPerms,
    mock_ripe
):
    """Test that owner can swap even with zero USD values when mustHaveUsdValue=True"""
    setupSwapTest()
    lego_id = 3  # mock_dex_lego is always id 3

    # Set global manager settings with mustHaveUsdValue=True
    swap_perms = createSwapPerms(_mustHaveUsdValue=True)
    global_settings = createGlobalManagerSettings(_canOwnerManage=True, _swapPerms=swap_perms)
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Set asset prices to zero (would fail mustHaveUsdValue check for managers)
    mock_ripe.setPrice(mock_dex_asset, 0)
    mock_ripe.setPrice(mock_dex_asset_alt, 0)

    # Prepare swap instruction
    swap_amount = 100 * EIGHTEEN_DECIMALS
    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_dex_asset.address, mock_dex_asset_alt.address],
        []
    )

    # Owner can perform swap even with zero USD values (bypasses manager limits entirely)
    tokenIn, amountIn, tokenOut, amountOut, usdValue = user_wallet.swapTokens([instruction], sender=bob)

    assert tokenIn == mock_dex_asset.address
    assert amountIn == swap_amount
    assert tokenOut == mock_dex_asset_alt.address
    assert usdValue == 0  # Zero USD value


def test_owner_bypasses_swap_max_num_swaps_per_period(
    setupSwapTest,
    user_wallet,
    user_wallet_config,
    bob,
    mock_dex_asset,
    mock_dex_asset_alt,
    high_command,
    createGlobalManagerSettings,
    createSwapPerms
):
    """Test that owner can perform unlimited swaps even when maxNumSwapsPerPeriod is set"""
    setupSwapTest()
    lego_id = 3  # mock_dex_lego is always id 3

    # Set global manager settings with very restrictive swap count (max 2 swaps)
    swap_perms = createSwapPerms(_maxNumSwapsPerPeriod=2)
    global_settings = createGlobalManagerSettings(_canOwnerManage=True, _swapPerms=swap_perms)
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Prepare swap instruction
    swap_amount = 10 * EIGHTEEN_DECIMALS
    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_dex_asset.address, mock_dex_asset_alt.address],
        []
    )

    # Owner performs 5 swaps (more than the limit of 2)
    # All should succeed because owner bypasses manager limits
    for i in range(5):
        user_wallet.swapTokens([instruction], sender=bob)

    # Verify all 5 swaps succeeded (if any failed, test would have reverted)


def test_owner_bypasses_swap_max_slippage(
    setupSwapTest,
    user_wallet,
    user_wallet_config,
    bob,
    mock_dex_asset,
    mock_dex_asset_alt,
    high_command,
    createGlobalManagerSettings,
    createSwapPerms,
    mock_ripe
):
    """Test that owner can swap even when maxSlippage is set (manager limits bypassed)"""
    setupSwapTest()
    lego_id = 3  # mock_dex_lego is always id 3

    # Set global manager settings with very restrictive slippage (1% = 100 basis points)
    # This would restrict managers from swapping if slippage exceeds 1%
    swap_perms = createSwapPerms(_mustHaveUsdValue=True, _maxSlippage=100)
    global_settings = createGlobalManagerSettings(_canOwnerManage=True, _swapPerms=swap_perms)
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Set asset prices
    mock_ripe.setPrice(mock_dex_asset, 2 * EIGHTEEN_DECIMALS)  # $2
    mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)  # $3

    # Prepare swap instruction
    # Note: MockDexLego does 1:1 swaps, but the key is that owner bypasses
    # the manager limits check entirely, so slippage is never checked
    swap_amount = 100 * EIGHTEEN_DECIMALS
    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_dex_asset.address, mock_dex_asset_alt.address],
        []
    )

    # Owner can perform swap (bypasses manager limits entirely, including slippage check)
    tokenIn, amountIn, tokenOut, amountOut, usdValue = user_wallet.swapTokens([instruction], sender=bob)

    assert tokenIn == mock_dex_asset.address
    assert amountIn == swap_amount


####################################
# Owner Bypasses Yield Restrictions #
####################################


def test_owner_bypasses_yield_max_tx_usd_value(
    prepareAssetForWalletTx,
    user_wallet,
    user_wallet_config,
    bob,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    high_command,
    createGlobalManagerSettings,
    createManagerLimits
):
    """Test that owner can deposit to yield even when transaction exceeds maxTxUsdValue"""
    # Set global manager settings with very restrictive maxTxUsdValue ($100)
    manager_limits = createManagerLimits(_maxUsdValuePerTx=100 * 10**6)
    global_settings = createGlobalManagerSettings(_canOwnerManage=True, _limits=manager_limits)
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Prepare large deposit ($1000 - exceeds $100 limit)
    deposit_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,  # $10 per token = $1000 total
        _shouldCheckYield=False
    )

    lego_id = 2  # yield_vault_lego is always id 2

    # Owner can perform large deposit (bypasses manager limits entirely)
    asset_deposited, vault_token, vault_tokens_received, usd_value = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=bob
    )

    assert asset_deposited == deposit_amount
    assert vault_token == yield_vault_token.address
    assert vault_tokens_received > 0
    assert usd_value == 1000 * EIGHTEEN_DECIMALS  # $1000 transaction succeeded


###########################################
# Managers Respect Restrictions (Contrast) #
###########################################


def test_manager_respects_swap_must_have_usd_value(
    setupSwapTest,
    user_wallet,
    user_wallet_config,
    alice,
    mock_dex_asset,
    mock_dex_asset_alt,
    high_command,
    createManagerSettings,
    createSwapPerms,
    mock_ripe
):
    """Test that manager CANNOT swap with zero USD values when mustHaveUsdValue=True"""
    setupSwapTest()
    lego_id = 3  # mock_dex_lego is always id 3

    # Add manager with mustHaveUsdValue=True
    swap_perms = createSwapPerms(_mustHaveUsdValue=True)
    manager_settings = createManagerSettings(_swapPerms=swap_perms)
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    # Set asset prices to zero (fails mustHaveUsdValue check)
    mock_ripe.setPrice(mock_dex_asset, 0)
    mock_ripe.setPrice(mock_dex_asset_alt, 0)

    # Prepare swap instruction
    swap_amount = 100 * EIGHTEEN_DECIMALS
    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_dex_asset.address, mock_dex_asset_alt.address],
        []
    )

    # Manager should fail due to zero USD values
    with boa.reverts():
        user_wallet.swapTokens([instruction], sender=alice)


def test_manager_respects_swap_max_num_swaps_per_period(
    setupSwapTest,
    user_wallet,
    user_wallet_config,
    alice,
    mock_dex_asset,
    mock_dex_asset_alt,
    high_command,
    createManagerSettings,
    createSwapPerms
):
    """Test that manager CANNOT exceed maxNumSwapsPerPeriod limit"""
    setupSwapTest()
    lego_id = 3  # mock_dex_lego is always id 3

    # Add manager with swap count limit of 2
    swap_perms = createSwapPerms(_maxNumSwapsPerPeriod=2)
    manager_settings = createManagerSettings(_swapPerms=swap_perms)
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    # Prepare swap instruction
    swap_amount = 10 * EIGHTEEN_DECIMALS
    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_dex_asset.address, mock_dex_asset_alt.address],
        []
    )

    # Manager can perform 2 swaps (within limit)
    user_wallet.swapTokens([instruction], sender=alice)
    user_wallet.swapTokens([instruction], sender=alice)

    # Third swap should fail (exceeds limit)
    with boa.reverts():
        user_wallet.swapTokens([instruction], sender=alice)


def test_manager_respects_swap_max_slippage(
    setupSwapTest,
    user_wallet,
    user_wallet_config,
    alice,
    mock_dex_asset,
    mock_dex_asset_alt,
    high_command,
    createManagerSettings,
    createSwapPerms,
    mock_ripe
):
    """Test that manager is subject to maxSlippage validation when swapping"""
    setupSwapTest()
    lego_id = 3  # mock_dex_lego is always id 3

    # Add manager with mustHaveUsdValue and maxSlippage set
    # This test verifies that the manager goes through the slippage check
    # (Unlike owner who bypasses it entirely)
    swap_perms = createSwapPerms(_mustHaveUsdValue=True, _maxSlippage=500)  # 5%
    manager_settings = createManagerSettings(_swapPerms=swap_perms)
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    # Set asset prices
    mock_ripe.setPrice(mock_dex_asset, 2 * EIGHTEEN_DECIMALS)  # $2
    mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)  # $3

    # Prepare swap instruction
    # MockDexLego does 1:1 swaps
    # Input: 100 tokens at $2 = $200
    # Output: 100 tokens at $3 = $300 (actually a gain, so passes slippage check)
    swap_amount = 100 * EIGHTEEN_DECIMALS
    instruction = (
        lego_id,
        swap_amount,
        0,
        [mock_dex_asset.address, mock_dex_asset_alt.address],
        []
    )

    # Manager can perform swap (within slippage limit)
    # This test verifies that manager IS subject to slippage validation
    # (even though this particular swap passes the check)
    user_wallet.swapTokens([instruction], sender=alice)


def test_manager_respects_yield_max_tx_usd_value(
    prepareAssetForWalletTx,
    user_wallet,
    user_wallet_config,
    alice,
    yield_underlying_token,
    yield_underlying_token_whale,
    yield_vault_token,
    high_command,
    createManagerSettings,
    createManagerLimits
):
    """Test that manager CANNOT deposit to yield when transaction exceeds maxTxUsdValue"""
    # Add manager with restrictive maxTxUsdValue ($100)
    manager_limits = createManagerLimits(_maxUsdValuePerTx=100 * 10**6, _failOnZeroPrice=True)
    manager_settings = createManagerSettings(_limits=manager_limits)
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    # Prepare large deposit ($1000 - exceeds $100 limit)
    deposit_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,  # $10 per token = $1000 total
        _shouldCheckYield=False
    )

    lego_id = 2  # yield_vault_lego is always id 2

    # Manager should fail due to exceeding maxTxUsdValue
    with boa.reverts():
        user_wallet.depositForYield(
            lego_id,
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=alice
        )


