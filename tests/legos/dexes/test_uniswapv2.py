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
    lego_uniswap_v2,
    fork,
    appraiser,
    _test,
):
    # usdc setup
    usdc, usdc_whale = getTokenAndWhale("USDC")
    usdc_amount = 10_000 * (10 ** usdc.decimals())
    usdc.transfer(bob, usdc_amount, sender=usdc_whale)

    # weth setup
    weth = TOKENS[fork]["WETH"]
    weth_usdc_pool = POOLS[fork]["WETH_USDC"]

    # virtual setup
    virtual = boa.from_etherscan(TOKENS[fork]["VIRTUAL"], name="virtual token")
    weth_virtual_pool = POOLS[fork]["WETH_VIRTUAL"]
    virtual_price = lego_uniswap_v2.getPriceUnsafe(weth_virtual_pool, virtual)

    # pre balances
    pre_usdc_bal = usdc.balanceOf(bob)
    pre_virtual_bal = virtual.balanceOf(bob)

    # swap uniswap v2
    usdc.approve(lego_uniswap_v2, usdc_amount, sender=bob)
    fromSwapAmount, toAmount, usd_value = lego_uniswap_v2.swapTokens(usdc_amount, 0, [usdc, weth, virtual], [weth_usdc_pool, weth_virtual_pool], bob, sender=bob)
    assert toAmount != 0

    # post balances
    assert usdc.balanceOf(bob) == pre_usdc_bal - fromSwapAmount
    assert virtual.balanceOf(bob) == pre_virtual_bal + toAmount

    # usd values
    usdc_input_usd_value = appraiser.getUsdValue(usdc, usdc_amount)
    virtual_output_usd_value = virtual_price * toAmount // (10 ** virtual.decimals())
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
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)

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
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)

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
    pool = POOLS[fork]["WETH_USDC"]
    tokenA, _ = getTokenAndWhale("USDC")
    tokenA_amount = 2_600 * (10 ** tokenA.decimals())
    tokenB, _ = getTokenAndWhale("WETH")
    tokenB_amount = 1 * (10 ** tokenB.decimals())

    # usdc -> weth
    amount_out = lego_uniswap_v2.getSwapAmountOut(pool, tokenA, tokenB, tokenA_amount)
    _test(tokenB_amount, amount_out, 100)

    best_pool, amount_out_b = lego_uniswap_v2.getBestSwapAmountOut(tokenA, tokenB, tokenA_amount)
    assert best_pool == pool
    assert amount_out == amount_out_b

    # weth -> usdc
    amount_out = lego_uniswap_v2.getSwapAmountOut(pool, tokenB, tokenA, tokenB_amount)
    _test(tokenA_amount, amount_out, 100)

    best_pool, amount_out_b = lego_uniswap_v2.getBestSwapAmountOut(tokenB, tokenA, tokenB_amount)
    assert best_pool == pool
    assert amount_out == amount_out_b


@pytest.always
def test_uniswapV2_get_swap_amount_in(
    getTokenAndWhale,
    lego_uniswap_v2,
    _test,
    fork,
):
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")
    amount_in = lego_uniswap_v2.getSwapAmountIn(POOLS[fork]["WETH_USDC"], tokenB, tokenA, 2_600 * (10 ** tokenA.decimals()))
    _test(1 * (10 ** tokenB.decimals()), amount_in, 100)

    amount_in = lego_uniswap_v2.getSwapAmountIn(POOLS[fork]["WETH_USDC"], tokenA, tokenB, 1 * (10 ** tokenB.decimals()))
    _test(2_600 * (10 ** tokenA.decimals()), amount_in, 100)


@pytest.always
def test_uniswapV2_get_add_liq_amounts_in(
    getTokenAndWhale,
    lego_uniswap_v2,
    _test,
    fork,
):
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())

    # reduce amount a
    liq_amount_a, liq_amount_b, _ = lego_uniswap_v2.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 7_800 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, 3 * (10 ** tokenB.decimals()), 1_00)

    # set new amount b
    amountB = 10 * (10 ** tokenB.decimals())

    # reduce amount b
    liq_amount_a, liq_amount_b, _ = lego_uniswap_v2.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 10_000 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, int(3.84 * (10 ** tokenB.decimals())), 1_00)


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
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 7_800 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    liquidityAdded, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert liquidityAdded != 0

    # test
    amountAOut, amountBOut = lego_uniswap_v2.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    _test(amountAOut, 7_800 * (10 ** tokenA.decimals()), 1_00)
    _test(amountBOut, 3 * (10 ** tokenB.decimals()), 1_00)

    # re-arrange amounts
    first_amount, second_amount = lego_uniswap_v2.getRemoveLiqAmountsOut(pool, tokenB, tokenA, liquidityAdded)
    _test(first_amount, 3 * (10 ** tokenB.decimals()), 1_00)
    _test(second_amount, 7_800 * (10 ** tokenA.decimals()), 1_00)


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