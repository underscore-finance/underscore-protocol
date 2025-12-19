import pytest
import boa

from constants import ZERO_ADDRESS


# Tests that require full lego setup (will skip on local fork due to DEX lego dependencies)

@pytest.always
def test_lego_tools_deploy(
    lego_tools,
    lego_book,
    lego_aave_v3,
    lego_compound_v3,
    lego_euler,
    lego_fluid,
    lego_moonwell,
    lego_morpho,
    lego_uniswap_v2,
    lego_uniswap_v3,
    lego_aero_classic,
    lego_aero_slipstream,
    lego_curve,
):
    """Test that LegoTools deploys with correct lego IDs."""
    # Yield lego IDs should match LegoBook registration
    assert lego_tools.AAVE_V3_ID() == lego_book.getRegId(lego_aave_v3)
    assert lego_tools.COMPOUND_V3_ID() == lego_book.getRegId(lego_compound_v3)
    assert lego_tools.EULER_ID() == lego_book.getRegId(lego_euler)
    assert lego_tools.FLUID_ID() == lego_book.getRegId(lego_fluid)
    assert lego_tools.MOONWELL_ID() == lego_book.getRegId(lego_moonwell)
    assert lego_tools.MORPHO_ID() == lego_book.getRegId(lego_morpho)

    # DEX lego IDs should match LegoBook registration
    assert lego_tools.UNISWAP_V2_ID() == lego_book.getRegId(lego_uniswap_v2)
    assert lego_tools.UNISWAP_V3_ID() == lego_book.getRegId(lego_uniswap_v3)
    assert lego_tools.AERODROME_ID() == lego_book.getRegId(lego_aero_classic)
    assert lego_tools.AERODROME_SLIPSTREAM_ID() == lego_book.getRegId(lego_aero_slipstream)
    assert lego_tools.CURVE_ID() == lego_book.getRegId(lego_curve)


def test_lego_tools_yield_lego_getters(
    lego_tools,
    lego_aave_v3,
    lego_compound_v3,
    lego_euler,
    lego_fluid,
    lego_moonwell,
    lego_morpho,
):
    """Test yield lego address getters."""
    assert lego_tools.aaveV3() == lego_aave_v3.address
    assert lego_tools.compoundV3() == lego_compound_v3.address
    assert lego_tools.euler() == lego_euler.address
    assert lego_tools.fluid() == lego_fluid.address
    assert lego_tools.moonwell() == lego_moonwell.address
    assert lego_tools.morpho() == lego_morpho.address


def test_lego_tools_yield_lego_id_getters(
    lego_tools,
    lego_book,
    lego_aave_v3,
    lego_compound_v3,
    lego_euler,
    lego_fluid,
    lego_moonwell,
    lego_morpho,
):
    """Test yield lego ID getters."""
    assert lego_tools.aaveV3Id() == lego_book.getRegId(lego_aave_v3)
    assert lego_tools.compoundV3Id() == lego_book.getRegId(lego_compound_v3)
    assert lego_tools.eulerId() == lego_book.getRegId(lego_euler)
    assert lego_tools.fluidId() == lego_book.getRegId(lego_fluid)
    assert lego_tools.moonwellId() == lego_book.getRegId(lego_moonwell)
    assert lego_tools.morphoId() == lego_book.getRegId(lego_morpho)


def test_lego_tools_dex_lego_getters(
    lego_tools,
    lego_uniswap_v2,
    lego_uniswap_v3,
    lego_aero_classic,
    lego_aero_slipstream,
    lego_curve,
):
    """Test DEX lego address getters."""
    assert lego_tools.uniswapV2() == lego_uniswap_v2.address
    assert lego_tools.uniswapV3() == lego_uniswap_v3.address
    assert lego_tools.aerodrome() == lego_aero_classic.address
    assert lego_tools.aerodromeSlipstream() == lego_aero_slipstream.address
    assert lego_tools.curve() == lego_curve.address


def test_lego_tools_dex_lego_id_getters(
    lego_tools,
    lego_book,
    lego_uniswap_v2,
    lego_uniswap_v3,
    lego_aero_classic,
    lego_aero_slipstream,
    lego_curve,
):
    """Test DEX lego ID getters."""
    assert lego_tools.uniswapV2Id() == lego_book.getRegId(lego_uniswap_v2)
    assert lego_tools.uniswapV3Id() == lego_book.getRegId(lego_uniswap_v3)
    assert lego_tools.aerodromeId() == lego_book.getRegId(lego_aero_classic)
    assert lego_tools.aerodromeSlipstreamId() == lego_book.getRegId(lego_aero_slipstream)
    assert lego_tools.curveId() == lego_book.getRegId(lego_curve)


def test_lego_tools_router_tokens(
    lego_tools,
    alpha_token,
    weth,
    fork,
):
    """Test router tokens are set correctly."""
    from config.BluePrint import TOKENS

    expected_usdc = alpha_token if fork == "local" else TOKENS[fork]["USDC"]

    assert lego_tools.ROUTER_TOKENA() == expected_usdc.address
    assert lego_tools.ROUTER_TOKENB() == weth.address


def test_lego_tools_get_underlying_asset_empty_returns_zero(
    lego_tools,
):
    """Test getUnderlyingAsset returns zero address for empty input."""
    result = lego_tools.getUnderlyingAsset(ZERO_ADDRESS)
    assert result == ZERO_ADDRESS


def test_lego_tools_is_vault_token_empty_returns_false(
    lego_tools,
):
    """Test isVaultToken returns False for empty input."""
    result = lego_tools.isVaultToken(ZERO_ADDRESS)
    assert result == False


def test_lego_tools_get_vault_token_amount_zero_amount_returns_zero(
    lego_tools,
    alpha_token,
):
    """Test getVaultTokenAmount returns 0 for zero amount input."""
    # Some random address as vault token (won't actually be used due to 0 amount)
    result = lego_tools.getVaultTokenAmount(alpha_token.address, 0, alpha_token.address)
    assert result == 0


def test_lego_tools_get_underlying_for_user_empty_returns_zero(
    lego_tools,
    bob,
    alpha_token,
):
    """Test getUnderlyingForUser returns 0 for empty user."""
    result = lego_tools.getUnderlyingForUser(ZERO_ADDRESS, alpha_token.address)
    assert result == 0

    result = lego_tools.getUnderlyingForUser(bob, ZERO_ADDRESS)
    assert result == 0


def test_lego_tools_get_vault_tokens_for_user_empty_returns_empty(
    lego_tools,
    bob,
    alpha_token,
):
    """Test getVaultTokensForUser returns empty list for empty inputs."""
    result = lego_tools.getVaultTokensForUser(ZERO_ADDRESS, alpha_token.address)
    assert len(result) == 0

    result = lego_tools.getVaultTokensForUser(bob, ZERO_ADDRESS)
    assert len(result) == 0


def test_lego_tools_get_lego_info_from_vault_token_empty_returns_zeros(
    lego_tools,
):
    """Test getLegoInfoFromVaultToken returns zeros for empty input."""
    lego_id, lego_addr, lego_desc = lego_tools.getLegoInfoFromVaultToken(ZERO_ADDRESS)
    assert lego_id == 0
    assert lego_addr == ZERO_ADDRESS
    assert lego_desc == ""


def test_lego_tools_is_not_paused(
    lego_tools,
):
    """Test lego_tools is not paused by default."""
    assert not lego_tools.isPaused()


def test_lego_tools_can_be_paused(
    lego_tools,
    switchboard_alpha,
):
    """Test lego_tools can be paused by switchboard."""
    # Not paused initially
    assert not lego_tools.isPaused()

    # Pause
    lego_tools.pause(sender=switchboard_alpha.address)
    assert lego_tools.isPaused()

    # Unpause
    lego_tools.unpause(sender=switchboard_alpha.address)
    assert not lego_tools.isPaused()


def test_lego_tools_pause_requires_switchboard(
    lego_tools,
    bob,
):
    """Test only switchboard can pause/unpause."""
    with boa.reverts():
        lego_tools.pause(sender=bob)
