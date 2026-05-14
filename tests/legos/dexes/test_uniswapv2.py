import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS
from constants import EIGHTEEN_DECIMALS


POOLS = {
    "base": {
        "USDC": "0x88A43bbDF9D098eEC7bCEda4e2494615dfD9bB9C", # usdc/weth
        "WETH": "0xE31c372a7Af875b3B5E0F3713B17ef51556da667", # weth/virtual
        "WETH_USDC": "0x88A43bbDF9D098eEC7bCEda4e2494615dfD9bB9C", # usdc/weth
        "WETH_VIRTUAL": "0xE31c372a7Af875b3B5E0F3713B17ef51556da667", # weth/virtual
    },
}


TO_TOKEN = {
    "base": {
        "USDC": TOKENS["base"]["WETH"], # WETH
        "WETH":  TOKENS["base"]["VIRTUAL"], # VIRTUAL
    },
}


TEST_ASSETS = [
    "USDC",
    "WETH",
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
def test_uniswapV2_swap_max_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v2,
    getToToken,
    getPool,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    fromAsset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals()), sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_uniswap_v2, fromAsset, toToken, pool)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_uniswapV2_swap_partial_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v2,
    getToToken,
    getPool,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    testAmount = TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals())
    fromAsset.transfer(bob_user_wallet.address, testAmount, sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_uniswap_v2, fromAsset, toToken, pool, testAmount // 2)


@pytest.always
def test_uniswapV2_swap_with_multiple_routes(
    getTokenAndWhale,
    bob,
    bob_user_wallet,
    lego_uniswap_v2,
    lego_book,
    fork,
    appraiser,
    _test,
):
    # Multi-hop USDC -> WETH -> VIRTUAL routed through the user wallet.
    usdc, usdc_whale = getTokenAndWhale("USDC")
    usdc_amount = 10_000 * (10 ** usdc.decimals())
    usdc.transfer(bob_user_wallet.address, usdc_amount, sender=usdc_whale)

    weth = TOKENS[fork]["WETH"]
    weth_usdc_pool = POOLS[fork]["WETH_USDC"]
    virtual = boa.from_etherscan(TOKENS[fork]["VIRTUAL"], name="virtual token")
    weth_virtual_pool = POOLS[fork]["WETH_VIRTUAL"]
    virtual_price = lego_uniswap_v2.getPriceUnsafe(weth_virtual_pool, virtual)

    pre_usdc_bal = usdc.balanceOf(bob_user_wallet)
    pre_virtual_bal = virtual.balanceOf(bob_user_wallet)

    lego_id = lego_book.getRegId(lego_uniswap_v2)
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
    _test(usdc_input_usd_value, virtual_output_usd_value, 5_00) # 5%


# add liquidity


@pytest.always
def test_uniswapV2_add_liquidity_more_token_A(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v2,
    fork,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 50_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 1 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])
    testLegoLiquidityAddedBasic(lego_uniswap_v2, pool, tokenA, tokenB, amountA, amountB)


@pytest.always
def test_uniswapV2_add_liquidity_more_token_B(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v2,
    fork,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 1_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 10 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])
    testLegoLiquidityAddedBasic(lego_uniswap_v2, pool, tokenA, tokenB, amountA, amountB)


# remove liquidity


@pytest.always
def test_uniswapV2_remove_liq_max(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v2,
    bob,
    fork,
    lego_book
):
    legoId = lego_book.getRegId(lego_uniswap_v2)
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool.address, tokenA.address, tokenB.address, amountA, amountB, 0, 0, 0, b"", sender=bob)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_uniswap_v2, pool, tokenA, tokenB)


@pytest.always
def test_uniswapV2_remove_liq_partial(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v2,
    bob,
    fork,
    lego_book,
):
    legoId = lego_book.getRegId(lego_uniswap_v2)
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool.address, tokenA.address, tokenB.address, amountA, amountB, 0, 0, 0, b"", sender=bob)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_uniswap_v2, pool, tokenA, tokenB, lpAmountReceived // 2)


# helper / utils


@pytest.always
def test_uniswapV2_get_best_pool(
    getTokenAndWhale,
    lego_uniswap_v2,
    fork,
):
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")

    best_pool = lego_uniswap_v2.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == POOLS[fork]["WETH_USDC"]
    assert best_pool.fee == 30
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2

    # virtual
    best_pool = lego_uniswap_v2.getDeepestLiqPool("0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b", tokenB)
    assert best_pool.pool == POOLS[fork]["WETH_VIRTUAL"]
    assert best_pool.fee == 30
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2


@pytest.always
def test_uniswapV2_get_swap_amount_out(
    getTokenAndWhale,
    lego_uniswap_v2,
    _test,
    fork,
):
    # Round-trip A -> B -> A should preserve amount within ~2x AMM fee.
    pool = POOLS[fork]["WETH_USDC"]
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")

    amount_in_a = 2_600 * (10 ** tokenA.decimals())
    amount_b = lego_uniswap_v2.getSwapAmountOut(pool, tokenA, tokenB, amount_in_a)
    assert amount_b != 0
    amount_a_back = lego_uniswap_v2.getSwapAmountOut(pool, tokenB, tokenA, amount_b)
    _test(amount_in_a, amount_a_back, 1_00)

    # getBestSwapAmountOut should agree with the explicit pool call
    best_pool, amount_out_b = lego_uniswap_v2.getBestSwapAmountOut(tokenA, tokenB, amount_in_a)
    assert best_pool == pool
    assert amount_out_b == amount_b

    amount_in_b = 1 * (10 ** tokenB.decimals())
    amount_a = lego_uniswap_v2.getSwapAmountOut(pool, tokenB, tokenA, amount_in_b)
    assert amount_a != 0
    amount_b_back = lego_uniswap_v2.getSwapAmountOut(pool, tokenA, tokenB, amount_a)
    _test(amount_in_b, amount_b_back, 1_00)

    best_pool, amount_out_a = lego_uniswap_v2.getBestSwapAmountOut(tokenB, tokenA, amount_in_b)
    assert best_pool == pool
    assert amount_out_a == amount_a


@pytest.always
def test_uniswapV2_get_swap_amount_in(
    getTokenAndWhale,
    lego_uniswap_v2,
    _test,
    fork,
):
    # Inverse consistency check.
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")
    pool = POOLS[fork]["WETH_USDC"]

    target_out_a = 2_600 * (10 ** tokenA.decimals())
    needed_in_b = lego_uniswap_v2.getSwapAmountIn(pool, tokenB, tokenA, target_out_a)
    assert needed_in_b != 0
    realized_out_a = lego_uniswap_v2.getSwapAmountOut(pool, tokenB, tokenA, needed_in_b)
    _test(target_out_a, realized_out_a, 50)

    target_out_b = 1 * (10 ** tokenB.decimals())
    needed_in_a = lego_uniswap_v2.getSwapAmountIn(pool, tokenA, tokenB, target_out_b)
    assert needed_in_a != 0
    realized_out_b = lego_uniswap_v2.getSwapAmountOut(pool, tokenA, tokenB, needed_in_a)
    _test(target_out_b, realized_out_b, 50)


@pytest.always
def test_uniswapV2_get_add_liq_amounts_in(
    getTokenAndWhale,
    lego_uniswap_v2,
    _test,
    fork,
):
    pool_addr = POOLS[fork]["WETH_USDC"]
    pool = boa.from_etherscan(pool_addr)
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")

    a_per_b_unit = lego_uniswap_v2.getSwapAmountOut(pool_addr, tokenB, tokenA, 10 ** tokenB.decimals())
    amountB = 3 * (10 ** tokenB.decimals())
    needed_a_for_b = amountB * a_per_b_unit // (10 ** tokenB.decimals())

    # case: B binding
    amountA_excess = needed_a_for_b * 2
    liq_a, liq_b, _ = lego_uniswap_v2.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA_excess, amountB)
    assert liq_b == amountB
    _test(needed_a_for_b, liq_a, 1_00)

    # case: A binding
    amountA_short = needed_a_for_b // 2
    expected_b_for_a = amountA_short * (10 ** tokenB.decimals()) // a_per_b_unit
    liq_a, liq_b, _ = lego_uniswap_v2.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA_short, amountB)
    assert liq_a == amountA_short
    _test(expected_b_for_a, liq_b, 1_00)


@pytest.always
def test_uniswapV2_get_remove_liq_amounts_out(
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v2,
    bob,
    lego_book,
    _test,
    fork,
):
    legoId = lego_book.getRegId(lego_uniswap_v2)
    pool_addr = POOLS[fork]["WETH_USDC"]
    pool = boa.from_etherscan(pool_addr)
    tokenA, whaleA = getTokenAndWhale("USDC")
    tokenB, whaleB = getTokenAndWhale("WETH")

    amountB = 3 * (10 ** tokenB.decimals())
    a_per_b_unit = lego_uniswap_v2.getSwapAmountOut(pool_addr, tokenB, tokenA, 10 ** tokenB.decimals())
    amountA = amountB * a_per_b_unit // (10 ** tokenB.decimals())
    amountA = amountA * 105 // 100

    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    liquidityAdded, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(
        legoId, pool.address, tokenA.address, tokenB.address, amountA, amountB, 0, 0, 0, b"", sender=bob,
    )
    assert liquidityAdded != 0
    assert liqAmountA != 0 and liqAmountB != 0

    amountAOut, amountBOut = lego_uniswap_v2.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    _test(liqAmountA, amountAOut, 50)
    _test(liqAmountB, amountBOut, 50)

    # re-arrange amounts: swapping token order should swap the returned amounts
    first_amount, second_amount = lego_uniswap_v2.getRemoveLiqAmountsOut(pool, tokenB, tokenA, liquidityAdded)
    _test(liqAmountB, first_amount, 50)
    _test(liqAmountA, second_amount, 50)


@pytest.always
def test_uniswapV2_get_price(
    getTokenAndWhale,
    lego_uniswap_v2,
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

    price = lego_uniswap_v2.getPriceUnsafe(pool, tokenA)
    assert int(0.98 * EIGHTEEN_DECIMALS) <= price <= int(1.02 * EIGHTEEN_DECIMALS)

    price = lego_uniswap_v2.getPriceUnsafe(pool, tokenB)
    _test(exp_weth_price, price, 1_00)
