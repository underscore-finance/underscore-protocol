import boa
import pytest

from constants import ZERO_ADDRESS


# HIG-383 regression tests.
#
# A LegoBook entry can be *disabled*: AddressRegistry sets addrInfo[regId].addr
# to empty(address) but keeps that regId within numAddrs, and isValidRegId()
# stays true for it. LegoTools walks `range(1, numAddrs)` and used to call
# isDexLego()/isYieldLego() on getAddr(i) directly -- a staticcall against 0x0
# reverts, so a single disabled lego reverted *every* swap-route quote (and
# every yield lookup) for every user. LegoTools now skips empty entries; these
# tests pin that behaviour.
#
# The shared `lego_tools` fixture skips on the local fork (it wires up real DEX
# legos), so we build LegoTools directly against the local `lego_book`
# (regId 1 = ripe, 2 = mock yield, 3 = mock dex). Swap routing always resolves
# the LegoBook from undy_hq, so mutations to it happen inside boa.env.anchor()
# to keep the session-scoped fixture pristine for other tests.


MAX_UINT256 = 2**256 - 1
ROUTE_AMOUNT = 1_000 * 10**18


@pytest.fixture
def lego_tools_local(undy_hq_deploy, lego_book, mock_dex_lego, mock_yield_lego, alpha_token, weth):
    dex_id = lego_book.getRegId(mock_dex_lego)
    yield_id = lego_book.getRegId(mock_yield_lego)
    return boa.load(
        "contracts/legos/LegoTools.vy",
        undy_hq_deploy,
        alpha_token,  # ROUTER_TOKENA (usdc on local)
        weth,         # ROUTER_TOKENB
        # yield lego ids -- only need to be valid regIds; routing walks the
        # whole book regardless of which id sits in which slot
        yield_id, yield_id, yield_id, yield_id, yield_id, yield_id,
        # dex lego ids -- keep the "non-standard" uniV3 / aero-slipstream ids
        # off the mock dex so it is quoted through the standard staticcall path
        dex_id, yield_id, dex_id, yield_id, dex_id,
        name="lego_tools_local",
    )


def _route_key(route):
    return (route.legoId, route.pool, route.tokenIn, route.tokenOut, route.amountIn, route.amountOut)


def _disable_in_registry(registry, reg_id, sender):
    registry.startAddressDisableInRegistry(reg_id, sender=sender)
    boa.env.time_travel(blocks=registry.registryChangeTimeLock() + 1)
    assert registry.confirmAddressDisableInRegistry(reg_id, sender=sender)
    # the exact state that used to brick LegoTools: address wiped to zero, but
    # the regId still counts toward numAddrs so the loop keeps visiting it
    assert registry.getAddr(reg_id) == ZERO_ADDRESS
    assert registry.isValidRegId(reg_id)


def test_swap_quotes_unaffected_by_disabled_non_dex_lego(
    lego_tools_local, lego_book, mock_yield_lego, governance, alpha_token, weth
):
    """Disabling a non-dex lego must be a transparent no-op for swap routing."""
    baseline = [
        lego_tools_local.getBestSwapAmountOutSinglePool(weth, alpha_token, ROUTE_AMOUNT),
        lego_tools_local.getSwapAmountOutViaRouterPool(weth, alpha_token, ROUTE_AMOUNT),
        lego_tools_local.getBestSwapAmountInSinglePool(weth, alpha_token, ROUTE_AMOUNT),
        lego_tools_local.getSwapAmountInViaRouterPool(weth, alpha_token, ROUTE_AMOUNT),
    ]

    with boa.env.anchor():
        # pre-fix this reverted on the isDexLego() staticcall against 0x0
        _disable_in_registry(lego_book, lego_book.getRegId(mock_yield_lego), governance.address)

        after = [
            lego_tools_local.getBestSwapAmountOutSinglePool(weth, alpha_token, ROUTE_AMOUNT),
            lego_tools_local.getSwapAmountOutViaRouterPool(weth, alpha_token, ROUTE_AMOUNT),
            lego_tools_local.getBestSwapAmountInSinglePool(weth, alpha_token, ROUTE_AMOUNT),
            lego_tools_local.getSwapAmountInViaRouterPool(weth, alpha_token, ROUTE_AMOUNT),
        ]
        assert lego_tools_local.getBestSwapRoutesAmountOut(weth, alpha_token, ROUTE_AMOUNT) == []
        assert lego_tools_local.getBestSwapRoutesAmountIn(weth, alpha_token, ROUTE_AMOUNT) == []

    assert [_route_key(r) for r in after] == [_route_key(r) for r in baseline]


def test_swap_quotes_survive_disabled_dex_lego(
    lego_tools_local, lego_book, mock_dex_lego, governance, alpha_token, weth
):
    """Disabling the dex lego itself must be skipped, not reverted on."""
    with boa.env.anchor():
        _disable_in_registry(lego_book, lego_book.getRegId(mock_dex_lego), governance.address)

        # none of these may revert now that the only dex lego is disabled
        out_single = lego_tools_local.getBestSwapAmountOutSinglePool(weth, alpha_token, ROUTE_AMOUNT)
        out_router = lego_tools_local.getSwapAmountOutViaRouterPool(weth, alpha_token, ROUTE_AMOUNT)
        in_single = lego_tools_local.getBestSwapAmountInSinglePool(weth, alpha_token, ROUTE_AMOUNT)
        in_router = lego_tools_local.getSwapAmountInViaRouterPool(weth, alpha_token, ROUTE_AMOUNT)
        routes_out = lego_tools_local.getBestSwapRoutesAmountOut(weth, alpha_token, ROUTE_AMOUNT)
        routes_in = lego_tools_local.getBestSwapRoutesAmountIn(weth, alpha_token, ROUTE_AMOUNT)

    # no dex lego left -> no route found, but the loop completed cleanly
    for route in (out_single, out_router):
        assert route.legoId == 0
        assert route.pool == ZERO_ADDRESS
        assert route.amountOut == 0
    for route in (in_single, in_router):
        assert route.legoId == 0
        assert route.pool == ZERO_ADDRESS
        assert route.amountIn == MAX_UINT256
    assert routes_out == []
    assert routes_in == []


def test_yield_lookups_survive_disabled_lego(
    undy_hq_deploy, lego_book, lego_tools_local, mock_yield_lego, governance, weth
):
    """Pattern-A yield loops must skip a disabled lego instead of reverting.

    Built against a fresh, fully-controlled LegoBook passed via the `_legoBook`
    arg (unlike swap routing, the yield lookups accept an explicit book), so the
    result does not depend on which legos other tests registered this session.
    """
    # a second, independent yield lego so a *yield* lego can be disabled while
    # another enabled yield lego remains for the loop to reach past it
    mock_yield_2 = boa.load("contracts/mock/MockYieldLego.vy", undy_hq_deploy, name="mock_yield_2")

    fresh_book = boa.load(
        "contracts/registries/LegoBook.vy",
        undy_hq_deploy,
        ZERO_ADDRESS,  # gov defers to undy_hq -> its governor after setup is `governance`
        lego_book.minRegistryTimeLock(),
        lego_book.maxRegistryTimeLock(),
        name="fresh_lego_book",
    )
    gov = governance.address
    # registry is in setup mode (timelock 0) -> confirms are instant
    assert fresh_book.startAddNewAddressToRegistry(mock_yield_lego, "yield 1", sender=gov)
    assert fresh_book.confirmNewAddressToRegistry(mock_yield_lego, sender=gov) == 1
    assert fresh_book.startAddNewAddressToRegistry(mock_yield_2, "yield 2", sender=gov)
    assert fresh_book.confirmNewAddressToRegistry(mock_yield_2, sender=gov) == 2

    # disable the first yield lego (regId 1)
    assert fresh_book.startAddressDisableInRegistry(1, sender=gov)
    assert fresh_book.confirmAddressDisableInRegistry(1, sender=gov)
    assert fresh_book.getAddr(1) == ZERO_ADDRESS
    assert fresh_book.isValidRegId(1)  # still counted -> loop still visits it

    # pre-fix this reverted at regId 1 (isYieldLego() staticcall against 0x0);
    # it now walks past the disabled entry to the live yield lego at regId 2
    assert lego_tools_local.getUnderlyingAsset(weth, fresh_book) == ZERO_ADDRESS
