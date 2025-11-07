"""
Test MockSwapLego - A simple mock DEX for testing GREEN <-> USDC swaps
"""
import pytest

from constants import EIGHTEEN_DECIMALS

# Decimal constants
SIX_DECIMALS = 10 ** 6

# Price constants (in USD, 18 decimals - as required by MockSwapLego)
ONE_DOLLAR = 1 * EIGHTEEN_DECIMALS      # $1.00
FIFTY_CENTS = 5 * 10**17                 # $0.50
TWO_DOLLARS = 2 * EIGHTEEN_DECIMALS     # $2.00
POINT_ZERO_ONE = 1 * 10**16              # $0.01
ONE_THOUSAND = 1000 * EIGHTEEN_DECIMALS  # $1000.00


@pytest.fixture(scope="module")
def setup_tokens(mock_swap_lego, mock_green_token, mock_usdc, governance, alice):
    """Setup: Give Alice some tokens to test with"""
    # Mint 1000 GREEN and 1000 USDC to Alice
    mock_green_token.mint(alice, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    mock_usdc.mint(alice, 1000 * SIX_DECIMALS, sender=governance.address)

    # Set initial prices: $1 each
    mock_swap_lego.setPrice(mock_green_token.address, ONE_DOLLAR, sender=governance.address)
    mock_swap_lego.setPrice(mock_usdc.address, ONE_DOLLAR, sender=governance.address)

    return {
        "green": mock_green_token,
        "usdc": mock_usdc,
        "lego": mock_swap_lego,
    }


def test_swap_green_to_usdc_equal_prices(setup_tokens, alice):
    """Test swapping GREEN to USDC when both are $1"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Approve and swap 100 GREEN for USDC
    swap_amount = 100 * EIGHTEEN_DECIMALS
    green.approve(lego.address, swap_amount, sender=alice)

    usdc_before = usdc.balanceOf(alice)
    green_before = green.balanceOf(alice)

    # Swap: 100 GREEN -> USDC
    token_path = [green.address, usdc.address]
    pool_path = []
    amount_in, amount_out, usd_value = lego.swapTokens(
        swap_amount,
        0,  # no min amount out for this test
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # With equal prices: 100 GREEN * $1 / $1 = 100 USDC
    assert amount_in == swap_amount
    assert amount_out == 100 * SIX_DECIMALS
    assert usd_value == 100 * EIGHTEEN_DECIMALS  # $100 in USD
    assert green.balanceOf(alice) == green_before - swap_amount
    assert usdc.balanceOf(alice) == usdc_before + 100 * SIX_DECIMALS


def test_swap_usdc_to_green_equal_prices(setup_tokens, alice):
    """Test swapping USDC to GREEN when both are $1"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Approve and swap 50 USDC for GREEN
    swap_amount = 50 * SIX_DECIMALS
    usdc.approve(lego.address, swap_amount, sender=alice)

    usdc_before = usdc.balanceOf(alice)
    green_before = green.balanceOf(alice)

    # Swap: 50 USDC -> GREEN
    token_path = [usdc.address, green.address]
    pool_path = []
    amount_in, amount_out, usd_value = lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # With equal prices: 50 USDC * $1 / $1 = 50 GREEN
    assert amount_in == swap_amount
    assert amount_out == 50 * EIGHTEEN_DECIMALS
    assert usd_value == 50 * EIGHTEEN_DECIMALS  # $50 in USD
    assert usdc.balanceOf(alice) == usdc_before - swap_amount
    assert green.balanceOf(alice) == green_before + 50 * EIGHTEEN_DECIMALS


def test_swap_with_price_difference(setup_tokens, alice, governance):
    """Test swapping when GREEN is $0.50 and USDC is $1"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Change GREEN price to $0.50
    lego.setPrice(green.address, FIFTY_CENTS, sender=governance.address)

    # Approve and swap 100 GREEN for USDC
    swap_amount = 100 * EIGHTEEN_DECIMALS
    green.approve(lego.address, swap_amount, sender=alice)

    usdc_before = usdc.balanceOf(alice)

    # Swap: 100 GREEN -> USDC
    token_path = [green.address, usdc.address]
    pool_path = []
    amount_in, amount_out, usd_value = lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # With price difference: 100 GREEN * $0.50 / $1 = 50 USDC
    assert amount_out == 50 * SIX_DECIMALS
    assert usd_value == 50 * EIGHTEEN_DECIMALS  # $50 in USD (100 GREEN * $0.50)
    assert usdc.balanceOf(alice) == usdc_before + 50 * SIX_DECIMALS


def test_swap_with_higher_green_price(setup_tokens, alice, governance):
    """Test swapping when GREEN is $2 and USDC is $1"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Change GREEN price to $2
    lego.setPrice(green.address, TWO_DOLLARS, sender=governance.address)

    # Approve and swap 100 GREEN for USDC
    swap_amount = 100 * EIGHTEEN_DECIMALS
    green.approve(lego.address, swap_amount, sender=alice)

    usdc_before = usdc.balanceOf(alice)

    # Swap: 100 GREEN -> USDC
    token_path = [green.address, usdc.address]
    pool_path = []
    amount_in, amount_out, usd_value = lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # With price difference: 100 GREEN * $2 / $1 = 200 USDC
    assert amount_out == 200 * SIX_DECIMALS
    assert usd_value == 200 * EIGHTEEN_DECIMALS  # $200 in USD (100 GREEN * $2.00)
    assert usdc.balanceOf(alice) == usdc_before + 200 * SIX_DECIMALS


def test_swap_fails_without_price(mock_swap_lego, mock_green_token, mock_usdc, alice, governance):
    """Test that swap fails if price is not set"""
    # Create fresh tokens without prices set
    from contracts.mock import MockErc20
    token_a = MockErc20.deploy(governance, "Token A", "TKA", 18, 1_000_000_000)
    token_b = MockErc20.deploy(governance, "Token B", "TKB", 18, 1_000_000_000)

    # Give minting permissions
    token_a.setMinter(mock_swap_lego.address, True, sender=governance.address)
    token_b.setMinter(mock_swap_lego.address, True, sender=governance.address)

    # Mint some tokens to alice
    token_a.mint(alice, 100 * EIGHTEEN_DECIMALS, sender=governance.address)
    token_a.approve(mock_swap_lego.address, 100 * EIGHTEEN_DECIMALS, sender=alice)

    # Try to swap without setting prices - should fail
    token_path = [token_a.address, token_b.address]
    pool_path = []

    with pytest.raises(Exception, match="price not set"):
        mock_swap_lego.swapTokens(
            100 * EIGHTEEN_DECIMALS,
            0,
            token_path,
            pool_path,
            alice,
            sender=alice
        )


def test_get_price(setup_tokens, governance):
    """Test getting prices"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Get current prices
    green_price = lego.getPrice(green.address, 18)
    usdc_price = lego.getPrice(usdc.address, 6)

    # Should match what we set in setup
    assert green_price == ONE_DOLLAR
    assert usdc_price == ONE_DOLLAR

    # Change GREEN price
    lego.setPrice(green.address, FIFTY_CENTS, sender=governance.address)
    assert lego.getPrice(green.address, 18) == FIFTY_CENTS


def test_slippage_protection(setup_tokens, alice):
    """Test that slippage protection works (minAmountOut)"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    swap_amount = 100 * EIGHTEEN_DECIMALS
    green.approve(lego.address, swap_amount, sender=alice)

    # With equal prices, we expect 100 USDC out
    # But require 101 USDC minimum - should fail
    token_path = [green.address, usdc.address]
    pool_path = []

    with pytest.raises(Exception, match="slippage"):
        lego.swapTokens(
            swap_amount,
            101 * SIX_DECIMALS,  # min amount out too high
            token_path,
            pool_path,
            alice,
            sender=alice
        )


#################################
# Additional Comprehensive Tests #
#################################


def test_swap_insufficient_balance(setup_tokens, alice):
    """Test swapping more than user has - should swap available balance"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Alice has 1000 GREEN, try to swap 2000
    swap_amount = 2000 * EIGHTEEN_DECIMALS
    green.approve(lego.address, swap_amount, sender=alice)

    green_before = green.balanceOf(alice)

    token_path = [green.address, usdc.address]
    pool_path = []
    amount_in, amount_out, usd_value = lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # Should only swap what's available (1000 GREEN minus previous tests)
    assert amount_in == green_before
    assert green.balanceOf(alice) == 0


def test_swap_insufficient_approval(setup_tokens, alice):
    """Test swapping without sufficient approval"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Approve only 50 GREEN
    green.approve(lego.address, 50 * EIGHTEEN_DECIMALS, sender=alice)

    token_path = [green.address, usdc.address]
    pool_path = []

    # Try to swap 100 GREEN - should fail
    with pytest.raises(Exception):
        lego.swapTokens(
            100 * EIGHTEEN_DECIMALS,
            0,
            token_path,
            pool_path,
            alice,
            sender=alice
        )


def test_swap_zero_amount(setup_tokens, alice):
    """Test swapping zero amount should fail"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    token_path = [green.address, usdc.address]
    pool_path = []

    with pytest.raises(Exception, match="nothing to transfer"):
        lego.swapTokens(
            0,
            0,
            token_path,
            pool_path,
            alice,
            sender=alice
        )


def test_swap_invalid_token_path_empty(setup_tokens, alice):
    """Test swapping with empty token path"""
    lego = setup_tokens["lego"]

    token_path = []
    pool_path = []

    with pytest.raises(Exception, match="invalid token path"):
        lego.swapTokens(
            100 * EIGHTEEN_DECIMALS,
            0,
            token_path,
            pool_path,
            alice,
            sender=alice
        )


def test_swap_invalid_token_path_single(setup_tokens, alice):
    """Test swapping with single token in path"""
    green = setup_tokens["green"]
    lego = setup_tokens["lego"]

    token_path = [green.address]
    pool_path = []

    with pytest.raises(Exception, match="invalid token path"):
        lego.swapTokens(
            100 * EIGHTEEN_DECIMALS,
            0,
            token_path,
            pool_path,
            alice,
            sender=alice
        )


def test_swap_reverse_price_scenario(setup_tokens, alice, governance):
    """Test swapping when USDC is more expensive than GREEN"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Set USDC to $2, GREEN to $1
    lego.setPrice(usdc.address, TWO_DOLLARS, sender=governance.address)
    lego.setPrice(green.address, ONE_DOLLAR, sender=governance.address)

    # Swap 100 USDC for GREEN
    swap_amount = 100 * SIX_DECIMALS
    usdc.approve(lego.address, swap_amount, sender=alice)

    token_path = [usdc.address, green.address]
    pool_path = []
    amount_in, amount_out, usd_value = lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # 100 USDC * $2 / $1 = 200 GREEN
    assert amount_out == 200 * EIGHTEEN_DECIMALS
    assert usd_value == 200 * EIGHTEEN_DECIMALS  # $200 in USD


def test_swap_very_low_prices(setup_tokens, alice, governance):
    """Test swapping with very low prices ($0.01 each)"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Set both to $0.01
    lego.setPrice(green.address, POINT_ZERO_ONE, sender=governance.address)
    lego.setPrice(usdc.address, POINT_ZERO_ONE, sender=governance.address)

    swap_amount = 100 * EIGHTEEN_DECIMALS
    green.approve(lego.address, swap_amount, sender=alice)

    token_path = [green.address, usdc.address]
    pool_path = []
    amount_in, amount_out, usd_value = lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # With equal prices, should get 100 USDC
    assert amount_out == 100 * SIX_DECIMALS
    assert usd_value == 1 * EIGHTEEN_DECIMALS  # $1 in USD (100 * $0.01)


def test_swap_very_high_prices(setup_tokens, alice, governance):
    """Test swapping with very high prices ($1000 each)"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Set both to $1000
    lego.setPrice(green.address, ONE_THOUSAND, sender=governance.address)
    lego.setPrice(usdc.address, ONE_THOUSAND, sender=governance.address)

    swap_amount = 10 * EIGHTEEN_DECIMALS  # Swap 10 GREEN
    green.approve(lego.address, swap_amount, sender=alice)

    token_path = [green.address, usdc.address]
    pool_path = []
    amount_in, amount_out, usd_value = lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # With equal prices, should get 10 USDC
    assert amount_out == 10 * SIX_DECIMALS
    assert usd_value == 10_000 * EIGHTEEN_DECIMALS  # $10,000 in USD


def test_swap_same_decimals_18_to_18(mock_swap_lego, governance, alice):
    """Test swapping between two 18-decimal tokens"""
    from contracts.mock import MockErc20

    # Create two 18-decimal tokens
    token_a = MockErc20.deploy(governance, "Token A", "TKA", 18, 1_000_000_000)
    token_b = MockErc20.deploy(governance, "Token B", "TKB", 18, 1_000_000_000)

    # Give minting permissions
    token_a.setMinter(mock_swap_lego.address, True, sender=governance.address)
    token_b.setMinter(mock_swap_lego.address, True, sender=governance.address)

    # Mint and set prices
    token_a.mint(alice, 1000 * EIGHTEEN_DECIMALS, sender=governance.address)
    mock_swap_lego.setPrice(token_a.address, ONE_DOLLAR, sender=governance.address)
    mock_swap_lego.setPrice(token_b.address, ONE_DOLLAR, sender=governance.address)

    # Swap
    swap_amount = 100 * EIGHTEEN_DECIMALS
    token_a.approve(mock_swap_lego.address, swap_amount, sender=alice)

    token_path = [token_a.address, token_b.address]
    pool_path = []
    amount_in, amount_out, usd_value = mock_swap_lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # Should get exact same amount with same decimals and prices
    assert amount_out == 100 * EIGHTEEN_DECIMALS
    assert usd_value == 100 * EIGHTEEN_DECIMALS


def test_swap_same_decimals_6_to_6(mock_swap_lego, governance, alice):
    """Test swapping between two 6-decimal tokens"""
    from contracts.mock import MockErc20

    # Create two 6-decimal tokens
    token_a = MockErc20.deploy(governance, "Token A", "TKA", 6, 1_000_000_000)
    token_b = MockErc20.deploy(governance, "Token B", "TKB", 6, 1_000_000_000)

    # Give minting permissions
    token_a.setMinter(mock_swap_lego.address, True, sender=governance.address)
    token_b.setMinter(mock_swap_lego.address, True, sender=governance.address)

    # Mint and set prices
    token_a.mint(alice, 1000 * SIX_DECIMALS, sender=governance.address)
    mock_swap_lego.setPrice(token_a.address, ONE_DOLLAR, sender=governance.address)
    mock_swap_lego.setPrice(token_b.address, ONE_DOLLAR, sender=governance.address)

    # Swap
    swap_amount = 100 * SIX_DECIMALS
    token_a.approve(mock_swap_lego.address, swap_amount, sender=alice)

    token_path = [token_a.address, token_b.address]
    pool_path = []
    amount_in, amount_out, usd_value = mock_swap_lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # Should get exact same amount with same decimals and prices
    assert amount_out == 100 * SIX_DECIMALS
    assert usd_value == 100 * EIGHTEEN_DECIMALS


def test_swap_8_decimals_to_6_decimals(mock_swap_lego, governance, alice):
    """Test swapping from 8-decimal token (BTC-like) to 6-decimal token (USDC-like)"""
    from contracts.mock import MockErc20

    EIGHT_DECIMALS = 10 ** 8

    # Create tokens
    token_btc = MockErc20.deploy(governance, "Mock BTC", "MBTC", 8, 1_000_000_000)
    token_usdc = MockErc20.deploy(governance, "Mock USDC", "MUSDC", 6, 1_000_000_000)

    # Give minting permissions
    token_btc.setMinter(mock_swap_lego.address, True, sender=governance.address)
    token_usdc.setMinter(mock_swap_lego.address, True, sender=governance.address)

    # Mint BTC and set prices: BTC = $50,000, USDC = $1
    token_btc.mint(alice, 10 * EIGHT_DECIMALS, sender=governance.address)
    mock_swap_lego.setPrice(token_btc.address, 50_000 * EIGHTEEN_DECIMALS, sender=governance.address)
    mock_swap_lego.setPrice(token_usdc.address, ONE_DOLLAR, sender=governance.address)

    # Swap 1 BTC for USDC
    swap_amount = 1 * EIGHT_DECIMALS
    token_btc.approve(mock_swap_lego.address, swap_amount, sender=alice)

    token_path = [token_btc.address, token_usdc.address]
    pool_path = []
    amount_in, amount_out, usd_value = mock_swap_lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # 1 BTC * $50,000 / $1 = 50,000 USDC
    assert amount_out == 50_000 * SIX_DECIMALS
    assert usd_value == 50_000 * EIGHTEEN_DECIMALS


def test_balance_verification_tokens_burned_and_minted(setup_tokens, alice, governance):
    """Test that tokens are properly burned from contract and minted to recipient"""
    green = setup_tokens["green"]
    usdc = setup_tokens["usdc"]
    lego = setup_tokens["lego"]

    # Reset prices to $1
    lego.setPrice(green.address, ONE_DOLLAR, sender=governance.address)
    lego.setPrice(usdc.address, ONE_DOLLAR, sender=governance.address)

    swap_amount = 10 * EIGHTEEN_DECIMALS
    green.approve(lego.address, swap_amount, sender=alice)

    # Check contract balances before
    lego_green_before = green.balanceOf(lego.address)
    lego_usdc_before = usdc.balanceOf(lego.address)

    token_path = [green.address, usdc.address]
    pool_path = []
    lego.swapTokens(
        swap_amount,
        0,
        token_path,
        pool_path,
        alice,
        sender=alice
    )

    # Contract should not hold any tokens (they're burned/minted)
    assert green.balanceOf(lego.address) == lego_green_before  # No change (burned immediately)
    assert usdc.balanceOf(lego.address) == lego_usdc_before    # No change (minted to recipient)
