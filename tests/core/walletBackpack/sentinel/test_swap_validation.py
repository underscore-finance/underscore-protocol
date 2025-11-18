"""
Tests for SwapPerms manager permission validation.

This test suite covers:
1. mustHaveUsdValue - Require USD pricing for swap assets
2. maxNumSwapsPerPeriod - Limit number of swaps per period
3. maxSlippage - Maximum allowed price slippage (loss prevention only)
"""
import pytest
import boa

from constants import ONE_DAY_IN_BLOCKS, ZERO_ADDRESS, EIGHTEEN_DECIMALS


####################
# Test Fixtures    #
####################


@pytest.fixture
def setup_manager_with_swap_perms(
    user_wallet_config,
    createManagerSettings,
    createManagerLimits,
    createLegoPerms,
    createSwapPerms,
    createWhitelistPerms,
    createTransferPerms,
    alice,
    high_command,
):
    """Setup a manager with specific swap permissions"""
    def _setup(
        must_have_usd_value=False,
        max_num_swaps_per_period=0,
        max_slippage=0
    ):
        manager_settings = createManagerSettings(
            _limits=createManagerLimits(),
            _legoPerms=createLegoPerms(),
            _swapPerms=createSwapPerms(
                _mustHaveUsdValue=must_have_usd_value,
                _maxNumSwapsPerPeriod=max_num_swaps_per_period,
                _maxSlippage=max_slippage
            ),
            _whitelistPerms=createWhitelistPerms(),
            _transferPerms=createTransferPerms(),
            _allowedAssets=[],
            _canClaimLoot=False,
        )
        user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)
        return alice
    return _setup


@pytest.fixture
def fund_wallet_with_usdc(user_wallet, usdc, usdc_whale):
    """Helper to fund wallet with USDC"""
    def _fund(amount=10000 * 10**6):  # Default 10k USDC
        usdc.transfer(user_wallet, amount, sender=usdc_whale)
        return amount
    return _fund


#########################
# mustHaveUsdValue Tests #
#########################


def test_manager_can_swap_with_usd_pricing_when_required(
    user_wallet,
    setup_manager_with_swap_perms,
    fund_wallet_with_usdc,
    usdc,
    weth,
):
    """Manager with mustHaveUsdValue=True can swap assets with USD pricing"""
    manager = setup_manager_with_swap_perms(must_have_usd_value=True)
    amount = fund_wallet_with_usdc()

    # Both USDC and WETH have USD pricing in test setup
    # This swap should succeed
    user_wallet.swapTokens(
        usdc.address,
        weth.address,
        amount,
        0,  # min out
        [],  # empty route (handled by router)
        sender=manager
    )


def test_manager_cannot_swap_without_usd_pricing_when_required(
    user_wallet,
    setup_manager_with_swap_perms,
    mock_token_no_price,
    usdc,
    usdc_whale,
):
    """Manager with mustHaveUsdValue=True cannot swap assets without USD pricing"""
    manager = setup_manager_with_swap_perms(must_have_usd_value=True)

    # Fund wallet with mock token that has no price
    amount = 1000 * EIGHTEEN_DECIMALS
    mock_token_no_price.transfer(user_wallet, amount, sender=usdc_whale)

    # This swap should fail because mock_token_no_price lacks USD pricing
    with boa.reverts("manager limits not allowed"):
        user_wallet.swapTokens(
            mock_token_no_price.address,
            usdc.address,
            amount,
            0,
            [],
            sender=manager
        )


def test_manager_can_swap_without_usd_pricing_when_not_required(
    user_wallet,
    setup_manager_with_swap_perms,
    mock_token_no_price,
    usdc,
    usdc_whale,
):
    """Manager with mustHaveUsdValue=False can swap assets without USD pricing"""
    manager = setup_manager_with_swap_perms(must_have_usd_value=False)

    # Fund wallet with mock token that has no price
    amount = 1000 * EIGHTEEN_DECIMALS
    mock_token_no_price.transfer(user_wallet, amount, sender=usdc_whale)

    # This swap should succeed even without USD pricing
    user_wallet.swapTokens(
        mock_token_no_price.address,
        usdc.address,
        amount,
        0,
        [],
        sender=manager
    )


def test_owner_can_swap_without_usd_pricing(
    user_wallet,
    mock_token_no_price,
    usdc,
    usdc_whale,
    bob,  # owner
):
    """Owner can always swap, even without USD pricing"""
    # Fund wallet with mock token that has no price
    amount = 1000 * EIGHTEEN_DECIMALS
    mock_token_no_price.transfer(user_wallet, amount, sender=usdc_whale)

    # Owner can swap without restrictions
    user_wallet.swapTokens(
        mock_token_no_price.address,
        usdc.address,
        amount,
        0,
        [],
        sender=bob
    )


################################
# maxNumSwapsPerPeriod Tests   #
################################


def test_manager_can_swap_within_period_limit(
    user_wallet,
    setup_manager_with_swap_perms,
    fund_wallet_with_usdc,
    usdc,
    weth,
):
    """Manager can perform swaps up to the period limit"""
    max_swaps = 3
    manager = setup_manager_with_swap_perms(max_num_swaps_per_period=max_swaps)
    fund_wallet_with_usdc(30000 * 10**6)  # Fund with enough for 3 swaps

    # Perform swaps up to the limit
    for i in range(max_swaps):
        user_wallet.swapTokens(
            usdc.address,
            weth.address,
            1000 * 10**6,  # 1k USDC per swap
            0,
            [],
            sender=manager
        )


def test_manager_cannot_exceed_swap_period_limit(
    user_wallet,
    setup_manager_with_swap_perms,
    fund_wallet_with_usdc,
    usdc,
    weth,
):
    """Manager cannot exceed maxNumSwapsPerPeriod"""
    max_swaps = 2
    manager = setup_manager_with_swap_perms(max_num_swaps_per_period=max_swaps)
    fund_wallet_with_usdc(30000 * 10**6)

    # Perform swaps up to the limit
    for i in range(max_swaps):
        user_wallet.swapTokens(
            usdc.address,
            weth.address,
            1000 * 10**6,
            0,
            [],
            sender=manager
        )

    # Next swap should fail
    with boa.reverts("manager limits not allowed"):
        user_wallet.swapTokens(
            usdc.address,
            weth.address,
            1000 * 10**6,
            0,
            [],
            sender=manager
        )


def test_swap_counter_resets_after_period(
    user_wallet,
    user_wallet_config,
    setup_manager_with_swap_perms,
    fund_wallet_with_usdc,
    createGlobalManagerSettings,
    high_command,
    usdc,
    weth,
):
    """Swap counter resets when manager period expires"""
    max_swaps = 2
    period_length = ONE_DAY_IN_BLOCKS
    manager = setup_manager_with_swap_perms(max_num_swaps_per_period=max_swaps)

    # Set a short period for testing
    global_settings = createGlobalManagerSettings(_managerPeriod=period_length)
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    fund_wallet_with_usdc(30000 * 10**6)

    # Use up the swap limit
    for i in range(max_swaps):
        user_wallet.swapTokens(usdc.address, weth.address, 1000 * 10**6, 0, [], sender=manager)

    # Fast forward past the period
    boa.env.time_travel(blocks=period_length + 1)

    # Should be able to swap again after period reset
    user_wallet.swapTokens(usdc.address, weth.address, 1000 * 10**6, 0, [], sender=manager)


def test_swaps_count_toward_both_general_and_swap_limits(
    user_wallet,
    setup_manager_with_swap_perms,
    createManagerSettings,
    createManagerLimits,
    createLegoPerms,
    createSwapPerms,
    createWhitelistPerms,
    createTransferPerms,
    user_wallet_config,
    high_command,
    fund_wallet_with_usdc,
    usdc,
    weth,
    alice,
):
    """Swaps should increment both numTxsInPeriod and numSwapsInPeriod"""
    # Set both general tx limit and swap limit
    manager_settings = createManagerSettings(
        _limits=createManagerLimits(_maxNumTxsPerPeriod=5),  # General limit
        _legoPerms=createLegoPerms(),
        _swapPerms=createSwapPerms(_maxNumSwapsPerPeriod=3),  # Swap limit
        _whitelistPerms=createWhitelistPerms(),
        _transferPerms=createTransferPerms(),
        _allowedAssets=[],
        _canClaimLoot=False,
    )
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    fund_wallet_with_usdc(30000 * 10**6)

    # Perform 3 swaps (should hit swap limit first)
    for i in range(3):
        user_wallet.swapTokens(usdc.address, weth.address, 1000 * 10**6, 0, [], sender=alice)

    # 4th swap should fail due to swap limit (not general limit of 5)
    with boa.reverts("manager limits not allowed"):
        user_wallet.swapTokens(usdc.address, weth.address, 1000 * 10**6, 0, [], sender=alice)


##########################
# maxSlippage Tests      #
##########################


def test_manager_can_swap_within_slippage_limit(
    user_wallet,
    setup_manager_with_swap_perms,
    fund_wallet_with_usdc,
    usdc,
    weth,
):
    """Manager can swap if slippage is within limit"""
    # 5% max slippage = 500 basis points
    manager = setup_manager_with_swap_perms(max_slippage=500)
    amount = fund_wallet_with_usdc()

    # Assume swap has minimal slippage (< 5%)
    # This should succeed
    user_wallet.swapTokens(
        usdc.address,
        weth.address,
        amount,
        0,
        [],
        sender=manager
    )


def test_manager_cannot_swap_exceeding_slippage_limit(
    user_wallet,
    setup_manager_with_swap_perms,
    fund_wallet_with_usdc,
    mock_bad_swap_router,  # Mock router that causes high slippage
    usdc,
    weth,
):
    """Manager cannot swap if slippage exceeds limit"""
    # 1% max slippage = 100 basis points
    manager = setup_manager_with_swap_perms(max_slippage=100)
    amount = fund_wallet_with_usdc()

    # Mock router simulates a swap with 10% loss
    # This should fail due to slippage
    with boa.reverts("manager limits not allowed"):
        user_wallet.swapTokens(
            usdc.address,
            weth.address,
            amount,
            0,
            [],
            sender=manager
        )


def test_favorable_swaps_allowed_regardless_of_slippage(
    user_wallet,
    setup_manager_with_swap_perms,
    fund_wallet_with_usdc,
    mock_favorable_swap_router,  # Mock router that gives bonus
    usdc,
    weth,
):
    """Swaps with favorable rates (gains) should always be allowed"""
    # Even with strict 0.1% slippage limit
    manager = setup_manager_with_swap_perms(max_slippage=10)
    amount = fund_wallet_with_usdc()

    # Mock router gives 10% bonus (favorable)
    # This should succeed because we only prevent losses, not gains
    user_wallet.swapTokens(
        usdc.address,
        weth.address,
        amount,
        0,
        [],
        sender=manager
    )


def test_zero_slippage_limit_means_unlimited(
    user_wallet,
    setup_manager_with_swap_perms,
    fund_wallet_with_usdc,
    usdc,
    weth,
):
    """maxSlippage=0 means no limit on slippage"""
    manager = setup_manager_with_swap_perms(max_slippage=0)
    amount = fund_wallet_with_usdc()

    # Any slippage should be allowed
    user_wallet.swapTokens(
        usdc.address,
        weth.address,
        amount,
        0,
        [],
        sender=manager
    )


################################
# Global Settings Tests        #
################################


def test_global_swap_perms_enforced_when_stricter(
    user_wallet_config,
    high_command,
    user_wallet,
    createGlobalManagerSettings,
    createManagerSettings,
    createManagerLimits,
    createLegoPerms,
    createSwapPerms,
    createWhitelistPerms,
    createTransferPerms,
    fund_wallet_with_usdc,
    usdc,
    weth,
    alice,
):
    """Global swap settings should be enforced when more restrictive"""
    # Set global settings with strict swap limit
    global_settings = createGlobalManagerSettings(
        _swapPerms=createSwapPerms(_maxNumSwapsPerPeriod=2)
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Add manager with more permissive setting (10 swaps)
    manager_settings = createManagerSettings(
        _limits=createManagerLimits(),
        _legoPerms=createLegoPerms(),
        _swapPerms=createSwapPerms(_maxNumSwapsPerPeriod=10),
        _whitelistPerms=createWhitelistPerms(),
        _transferPerms=createTransferPerms(),
        _allowedAssets=[],
        _canClaimLoot=False,
    )
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    fund_wallet_with_usdc(30000 * 10**6)

    # Can only do 2 swaps (global limit) not 10 (manager limit)
    for i in range(2):
        user_wallet.swapTokens(usdc.address, weth.address, 1000 * 10**6, 0, [], sender=alice)

    # 3rd swap should fail due to global limit
    with boa.reverts("manager limits not allowed"):
        user_wallet.swapTokens(usdc.address, weth.address, 1000 * 10**6, 0, [], sender=alice)


def test_global_must_have_usd_value_enforced(
    user_wallet_config,
    high_command,
    user_wallet,
    createGlobalManagerSettings,
    createManagerSettings,
    createManagerLimits,
    createLegoPerms,
    createSwapPerms,
    createWhitelistPerms,
    createTransferPerms,
    mock_token_no_price,
    usdc,
    usdc_whale,
    alice,
):
    """Global mustHaveUsdValue setting should be enforced"""
    # Set global settings requiring USD value
    global_settings = createGlobalManagerSettings(
        _swapPerms=createSwapPerms(_mustHaveUsdValue=True)
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    # Add manager with permissive setting (doesn't require USD)
    manager_settings = createManagerSettings(
        _limits=createManagerLimits(),
        _legoPerms=createLegoPerms(),
        _swapPerms=createSwapPerms(_mustHaveUsdValue=False),
        _whitelistPerms=createWhitelistPerms(),
        _transferPerms=createTransferPerms(),
        _allowedAssets=[],
        _canClaimLoot=False,
    )
    user_wallet_config.addManager(alice, manager_settings, sender=high_command.address)

    # Fund with token that has no price
    amount = 1000 * EIGHTEEN_DECIMALS
    mock_token_no_price.transfer(user_wallet, amount, sender=usdc_whale)

    # Should fail due to global mustHaveUsdValue requirement
    with boa.reverts("manager limits not allowed"):
        user_wallet.swapTokens(
            mock_token_no_price.address,
            usdc.address,
            amount,
            0,
            [],
            sender=alice
        )


##########################
# Owner Bypass Tests     #
##########################


def test_owner_bypasses_all_swap_restrictions(
    user_wallet_config,
    high_command,
    user_wallet,
    createGlobalManagerSettings,
    createSwapPerms,
    fund_wallet_with_usdc,
    usdc,
    weth,
    bob,  # owner
):
    """Owner should bypass all swap restrictions"""
    # Set very restrictive global settings
    global_settings = createGlobalManagerSettings(
        _swapPerms=createSwapPerms(
            _mustHaveUsdValue=True,
            _maxNumSwapsPerPeriod=1,
            _maxSlippage=10  # 0.1% max slippage
        )
    )
    user_wallet_config.setGlobalManagerSettings(global_settings, sender=high_command.address)

    fund_wallet_with_usdc(30000 * 10**6)

    # Owner can do unlimited swaps
    for i in range(5):
        user_wallet.swapTokens(usdc.address, weth.address, 1000 * 10**6, 0, [], sender=bob)
