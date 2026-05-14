import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS
from constants import EIGHTEEN_DECIMALS


POOLS = {
    "base": {
        "USDC": "0xcEFC8B799a8EE5D9b312aeca73262645D664AaF7", # msUSD/usdc (sAMM)
        "WETH": "0xDE4FB30cCC2f1210FcE2c8aD66410C586C8D1f9A", # msETH/weth (sAMM)
        "AERO": "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d", # USDC/aero (vAMM)
        "CBBTC": "0xb909F567c5c2Bb1A4271349708CC4637D7318b4A", # VIRTUAL/cbbtc (vAMM)
        "DOLA": "0xf213F2D02837012dC0236cC105061e121bB03e37", # USDC/dola
        "BOLD": "0x2De3fE21d32319a1550264dA37846737885Ad7A1", # USDC/bold
        "WETH_USDC": "0xcDAC0d6c6C59727a65F871236188350531885C43", # weth/usdc
    },
}


TO_TOKEN = {
    "base": {
        "USDC": "0x526728DBc96689597F85ae4cd716d4f7fCcBAE9d", # msUSD (sAMM)
        "WETH": "0x7Ba6F01772924a82D9626c126347A28299E98c98", # msETH (sAMM)
        "AERO": TOKENS["base"]["USDC"], # USDC (vAMM)
        "CBBTC": TOKENS["base"]["VIRTUAL"], # VIRTUAL (vAMM)
    },
}


TEST_ASSETS = [
    "USDC",
    "WETH",
    "AERO",
    "CBBTC",
]


@pytest.fixture(scope="module")
def getToToken(fork):
    def getToToken(_token_str):
        if fork == "local":
            pytest.skip("asset not relevant on this fork")
        return boa.from_etherscan(TO_TOKEN[fork][_token_str], name=_token_str + "_token")
    yield getToToken


@pytest.fixture(scope="module")
def getPool(fork):
    def getPool(_token_str):
        if fork == "local":
            pytest.skip("asset not relevant on this fork")
        return POOLS[fork][_token_str]
    yield getPool


@pytest.fixture(scope="module", autouse=True)
def setup_assets(setUserWalletConfig, createTxFees):
    setUserWalletConfig(_txFees=createTxFees())
   

#########
# Tests #
#########


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_aerodrome_classic_swap_max_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    getToToken,
    getPool,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    fromAsset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals()), sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_aero_classic, fromAsset, toToken, pool)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_aerodrome_classic_swap_partial_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    getToToken,
    getPool,
    lego_book,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    testAmount = TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals())
    fromAsset.transfer(bob_user_wallet.address, testAmount, sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_aero_classic, fromAsset, toToken, pool, testAmount // 2)


@pytest.always
def test_aerodrom_classic_swap_with_routes(
    getTokenAndWhale,
    bob,
    bob_user_wallet,
    lego_aero_classic,
    lego_book,
    fork,
    appraiser,
    _test,
):
    # Multi-hop USDC -> WETH -> VIRTUAL routed through the user wallet (DEX legos require
    # an approved caller per _isAllowedToPerformAction).
    usdc, usdc_whale = getTokenAndWhale("USDC")
    usdc_amount = 10_000 * (10 ** usdc.decimals())
    usdc.transfer(bob_user_wallet.address, usdc_amount, sender=usdc_whale)

    weth = TOKENS[fork]["WETH"]
    weth_usdc_pool = "0xcDAC0d6c6C59727a65F871236188350531885C43"
    virtual = boa.from_etherscan(TOKENS[fork]["VIRTUAL"], name="virtual token")
    weth_virtual_pool = "0x21594b992F68495dD28d605834b58889d0a727c7"
    virtual_price = lego_aero_classic.getPriceUnsafe(weth_virtual_pool, virtual)

    pre_usdc_bal = usdc.balanceOf(bob_user_wallet)
    pre_virtual_bal = virtual.balanceOf(bob_user_wallet)

    lego_id = lego_book.getRegId(lego_aero_classic)
    instruction = (
        lego_id,
        usdc_amount,
        0,
        [usdc, weth, virtual],
        [weth_usdc_pool, weth_virtual_pool],
    )
    tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, usd_value = bob_user_wallet.swapTokens([instruction], sender=bob)
    assert lastTokenOutAmount != 0

    assert usdc.balanceOf(bob_user_wallet) == pre_usdc_bal - origAmountIn
    assert virtual.balanceOf(bob_user_wallet) == pre_virtual_bal + lastTokenOutAmount

    usdc_input_usd_value = appraiser.getUsdValue(usdc, usdc_amount)
    virtual_output_usd_value = virtual_price * lastTokenOutAmount // (10 ** virtual.decimals())
    _test(usdc_input_usd_value, virtual_output_usd_value, 2_00) # 2%


# add liquidity


@pytest.always
def test_aerodrome_classic_add_liquidity_more_token_A_volatile(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    fork,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("AERO")
    amountB = 1_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan(POOLS[fork]["AERO"])
    testLegoLiquidityAddedBasic(lego_aero_classic, pool, tokenA, tokenB, amountA, amountB)


@pytest.always
def test_aerodrome_classic_add_liquidity_more_token_B_volatile(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    fork,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 1_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("AERO")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan(POOLS[fork]["AERO"])
    testLegoLiquidityAddedBasic(lego_aero_classic, pool, tokenA, tokenB, amountA, amountB)



@pytest.always
def test_aerodrome_classic_add_liquidity_more_token_A_stable(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    fork,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("DOLA")
    amountB = 1_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan(POOLS[fork]["DOLA"])
    testLegoLiquidityAddedBasic(lego_aero_classic, pool, tokenA, tokenB, amountA, amountB)


@pytest.always
def test_aerodrome_classic_add_liquidity_more_token_B_stable(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    fork,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 1_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("DOLA")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan(POOLS[fork]["DOLA"])
    testLegoLiquidityAddedBasic(lego_aero_classic, pool, tokenA, tokenB, amountA, amountB)


# remove liquidity


@pytest.always
def test_aerodrome_classic_remove_liq_max_volatile(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    bob,
    lego_book,
    fork,
):
    legoId = lego_book.getRegId(lego_aero_classic)
    pool = boa.from_etherscan(POOLS[fork]["AERO"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("AERO")
    amountB = 11_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool, tokenA, tokenB, amountA, amountB, 0, 0, 0, b"", sender=bob)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_aero_classic, pool, tokenA, tokenB)


@pytest.always
def test_aerodrome_classic_remove_liq_partial_volatile(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    bob,
    lego_book,
    fork,
):
    legoId = lego_book.getRegId(lego_aero_classic)
    pool = boa.from_etherscan(POOLS[fork]["AERO"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("AERO")
    amountB = 11_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool, tokenA, tokenB, amountA, amountB, 0, 0, 0, b"", sender=bob)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_aero_classic, pool, tokenA, tokenB, lpAmountReceived // 2)


@pytest.always
def test_aerodrome_classic_remove_liq_max_stable(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    bob,
    lego_book,
    fork,
):
    legoId = lego_book.getRegId(lego_aero_classic)
    pool = boa.from_etherscan(POOLS[fork]["DOLA"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 1_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("DOLA")
    amountB = 1_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool, tokenA, tokenB, amountA, amountB, 0, 0, 0, b"", sender=bob)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_aero_classic, pool, tokenA, tokenB)


@pytest.always
def test_aerodrome_classic_remove_liq_partial_stable(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    bob,
    lego_book,
    fork,
):
    legoId = lego_book.getRegId(lego_aero_classic)
    pool = boa.from_etherscan(POOLS[fork]["DOLA"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("DOLA")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool, tokenA, tokenB, amountA, amountB, 0, 0, 0, b"", sender=bob)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_aero_classic, pool, tokenA, tokenB, lpAmountReceived // 2)


# helper / utils


@pytest.always
def test_aerodrome_classic_get_best_pool(
    getTokenAndWhale,
    lego_aero_classic,
    fork,
):
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")

    best_pool = lego_aero_classic.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == POOLS[fork]["WETH_USDC"]
    assert best_pool.fee == 30
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2

    # aero
    tokenB, _ = getTokenAndWhale("AERO")
    best_pool = lego_aero_classic.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == POOLS[fork]["AERO"]
    assert best_pool.fee == 30
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2


@pytest.always
def test_aerodrome_classic_get_swap_amount_out(
    getTokenAndWhale,
    lego_aero_classic,
    _test,
    fork,
):
    # Price-agnostic round-trip: A -> B -> A should preserve amount within ~2x AMM fee.
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")
    pool = POOLS[fork]["WETH_USDC"]

    amount_in_a = 2_600 * (10 ** tokenA.decimals())
    amount_b = lego_aero_classic.getSwapAmountOut(pool, tokenA, tokenB, amount_in_a)
    assert amount_b != 0
    amount_a_back = lego_aero_classic.getSwapAmountOut(pool, tokenB, tokenA, amount_b)
    _test(amount_in_a, amount_a_back, 1_00)  # ~2x 0.3% fee + slippage; 1% buffer

    amount_in_b = 1 * (10 ** tokenB.decimals())
    amount_a = lego_aero_classic.getSwapAmountOut(pool, tokenB, tokenA, amount_in_b)
    assert amount_a != 0
    amount_b_back = lego_aero_classic.getSwapAmountOut(pool, tokenA, tokenB, amount_a)
    _test(amount_in_b, amount_b_back, 1_00)


@pytest.always
def test_aerodrome_classic_get_swap_amount_in(
    getTokenAndWhale,
    lego_aero_classic,
    _test,
    fork,
):
    # Inverse consistency: getSwapAmountIn(target_out) -> result; getSwapAmountOut(result) should ≈ target_out
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")
    pool = POOLS[fork]["WETH_USDC"]

    target_out_a = 2_600 * (10 ** tokenA.decimals())
    needed_in_b = lego_aero_classic.getSwapAmountIn(pool, tokenB, tokenA, target_out_a)
    assert needed_in_b != 0
    realized_out_a = lego_aero_classic.getSwapAmountOut(pool, tokenB, tokenA, needed_in_b)
    _test(target_out_a, realized_out_a, 50)

    target_out_b = 1 * (10 ** tokenB.decimals())
    needed_in_a = lego_aero_classic.getSwapAmountIn(pool, tokenA, tokenB, target_out_b)
    assert needed_in_a != 0
    realized_out_b = lego_aero_classic.getSwapAmountOut(pool, tokenA, tokenB, needed_in_a)
    _test(target_out_b, realized_out_b, 50)


@pytest.always
def test_aerodrome_classic_get_add_liq_amounts_in(
    getTokenAndWhale,
    lego_aero_classic,
    _test,
    fork,
):
    # Price-agnostic: cap should preserve the current pool ratio. Compute the
    # pool's market rate via getSwapAmountOut and size inputs to bind each side.
    pool_addr = POOLS[fork]["WETH_USDC"]
    pool = boa.from_etherscan(pool_addr)
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")

    # market rate: 1 unit of B in units of A (e.g. WETH price in USDC)
    a_per_b_unit = lego_aero_classic.getSwapAmountOut(pool_addr, tokenB, tokenA, 10 ** tokenB.decimals())
    amountB = 3 * (10 ** tokenB.decimals())
    needed_a_for_b = amountB * a_per_b_unit // (10 ** tokenB.decimals())

    # case: amountB is the binding constraint (provide ~2x as much A as needed)
    amountA_excess = needed_a_for_b * 2
    liq_a, liq_b, _ = lego_aero_classic.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA_excess, amountB)
    assert liq_b == amountB
    _test(needed_a_for_b, liq_a, 1_00)

    # case: amountA is the binding constraint (provide ~half as much A as needed)
    amountA_short = needed_a_for_b // 2
    expected_b_for_a = amountA_short * (10 ** tokenB.decimals()) // a_per_b_unit
    liq_a, liq_b, _ = lego_aero_classic.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA_short, amountB)
    assert liq_a == amountA_short
    _test(expected_b_for_a, liq_b, 1_00)


@pytest.always
def test_aerodrome_classic_get_remove_liq_amounts_out(
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_classic,
    bob,
    _test,
    lego_book,
    fork,
):
    # Add then remove should round-trip the contributed amounts (less fees/rounding).
    legoId = lego_book.getRegId(lego_aero_classic)
    pool_addr = POOLS[fork]["WETH_USDC"]
    pool = boa.from_etherscan(pool_addr)

    tokenA, whaleA = getTokenAndWhale("USDC")
    tokenB, whaleB = getTokenAndWhale("WETH")

    # Size A based on market rate so neither side is leftover.
    amountB = 3 * (10 ** tokenB.decimals())
    a_per_b_unit = lego_aero_classic.getSwapAmountOut(pool_addr, tokenB, tokenA, 10 ** tokenB.decimals())
    amountA = amountB * a_per_b_unit // (10 ** tokenB.decimals())
    # give a small buffer to avoid binding on A
    amountA = amountA * 105 // 100

    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity (lego will cap to the binding side)
    liquidityAdded, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(
        legoId, pool.address, tokenA.address, tokenB.address, amountA, amountB, 0, 0, 0, b"", sender=bob,
    )
    assert liquidityAdded != 0
    assert liqAmountA != 0 and liqAmountB != 0

    # removeOut should return approximately what was added (within rounding)
    amountAOut, amountBOut = lego_aero_classic.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    _test(liqAmountA, amountAOut, 50)
    _test(liqAmountB, amountBOut, 50)

    # swapped order should swap the returned amounts
    first_amount, second_amount = lego_aero_classic.getRemoveLiqAmountsOut(pool, tokenB, tokenA, liquidityAdded)
    _test(liqAmountB, first_amount, 50)
    _test(liqAmountA, second_amount, 50)


@pytest.always
def test_aerodrome_classic_get_price(
    getTokenAndWhale,
    lego_aero_classic,
    appraiser,
    _test,
    fork,
):
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    tokenA, _ = getTokenAndWhale("USDC")
    assert appraiser.getRipePrice(tokenA) != 0

    tokenB, _ = getTokenAndWhale("WETH")
    exp_weth_price = appraiser.getRipePrice(tokenB)
    assert exp_weth_price != 0

    price = lego_aero_classic.getPriceUnsafe(pool, tokenA)
    assert int(0.98 * EIGHTEEN_DECIMALS) <= price <= int(1.02 * EIGHTEEN_DECIMALS)

    price = lego_aero_classic.getPriceUnsafe(pool, tokenB)
    _test(exp_weth_price, price, 1_00)
