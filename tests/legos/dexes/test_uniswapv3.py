import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


POOLS = {
    "base": {
        "USDC": "0xd0b53D9277642d899DF5C87A3966A349A798F224", # usdc/weth
        "WETH": "0x68B27E9066d3aAdC6078E17C8611b37868F96A1D", # weth/fai
        "WETH_USDC": "0xd0b53D9277642d899DF5C87A3966A349A798F224", # usdc/weth
        "WETH_CBBTC": "0x8c7080564B5A792A33Ef2FD473fbA6364d5495e5", # cbbtc/weth
    },
}


TO_TOKEN = {
    "base": {
        "USDC": TOKENS["base"]["WETH"],
        "WETH": "0xb33Ff54b9F7242EF1593d2C9Bcd8f9df46c77935", # FAI
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
def test_uniswapV3_swap_max_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v3,
    getToToken,
    getPool,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    fromAsset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals()), sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_uniswap_v3, fromAsset, toToken, pool)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_uniswapV3_swap_partial_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v3,
    getToToken,
    getPool,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    testAmount = TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals())
    fromAsset.transfer(bob_user_wallet.address, testAmount, sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_uniswap_v3, fromAsset, toToken, pool, testAmount // 2)


@pytest.always
def test_uniswapV3_swap_with_routes(
    getTokenAndWhale,
    bob,
    lego_uniswap_v3,
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

    # cbbtc setup
    cbbtc = boa.from_etherscan(TOKENS[fork]["CBBTC"], name="cbbtc token")
    weth_cbbtc_pool = POOLS[fork]["WETH_CBBTC"]
    cbbtc_price = lego_uniswap_v3.getPriceUnsafe(weth_cbbtc_pool, cbbtc)

    # pre balances
    pre_usdc_bal = usdc.balanceOf(bob)
    pre_cbbtc_bal = cbbtc.balanceOf(bob)

    # swap uniswap v3
    usdc.approve(lego_uniswap_v3, usdc_amount, sender=bob)
    fromSwapAmount, toAmount, usd_value = lego_uniswap_v3.swapTokens(usdc_amount, 0, [usdc, weth, cbbtc], [weth_usdc_pool, weth_cbbtc_pool], bob, sender=bob)
    assert toAmount != 0

    # post balances
    assert usdc.balanceOf(bob) == pre_usdc_bal - fromSwapAmount
    assert cbbtc.balanceOf(bob) == pre_cbbtc_bal + toAmount

    # usd values
    usdc_input_usd_value = appraiser.getUsdValue(usdc, usdc_amount)
    cbbtc_output_usd_value = cbbtc_price * toAmount // (10 ** cbbtc.decimals())
    _test(usdc_input_usd_value, cbbtc_output_usd_value, 1_00)


# add liquidity


@pytest.always
def test_uniswapV3_add_liquidity_new_position_more_token_A(
    testLegoLiquidityAdded,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v3,
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
    uniswap_nft_token_manager = boa.from_etherscan(lego_uniswap_v3.getRegistries()[1])
    nftTokenId = testLegoLiquidityAdded(lego_uniswap_v3, uniswap_nft_token_manager, 0, pool, tokenA, tokenB, amountA, amountB)
    assert nftTokenId != 0


@pytest.always
def test_uniswapV3_add_liquidity_new_position_more_token_B(
    testLegoLiquidityAdded,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v3,
    fork,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 1_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])
    uniswap_nft_token_manager = boa.from_etherscan(lego_uniswap_v3.getRegistries()[1])
    nftTokenId = testLegoLiquidityAdded(lego_uniswap_v3, uniswap_nft_token_manager, 0, pool, tokenA, tokenB, amountA, amountB)
    assert nftTokenId != 0


@pytest.always
def test_uniswapV3_add_liquidity_increase_position(
    testLegoLiquidityAdded,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v3,
    bob,
    fork,
    lego_book,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 50_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 1 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])
    uniswap_nft_token_manager = boa.from_etherscan(lego_uniswap_v3.getRegistries()[1])

    # initial mint position
    liquidityAdded, _a, _b, nftTokenId, _c = bob_user_wallet.addLiquidityConcentrated(lego_book.getRegId(lego_uniswap_v3), uniswap_nft_token_manager.address, 0, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert liquidityAdded != 0
    assert nftTokenId != 0

    # add new amounts
    new_amount_a = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, new_amount_a, sender=whaleA)
    new_amount_b = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, new_amount_b, sender=whaleB)

    # increase liquidity
    testLegoLiquidityAdded(lego_uniswap_v3, uniswap_nft_token_manager, nftTokenId, pool, tokenA, tokenB, new_amount_a, new_amount_b)


# remove liquidity


@pytest.always
def test_uniswapV3_remove_liq_max(
    testLegoLiquidityRemoved,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v3,
    bob,
    fork,
    lego_book,
):
    legoId = lego_book.getRegId(lego_uniswap_v3)
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    uniswap_nft_token_manager = boa.from_etherscan(lego_uniswap_v3.getRegistries()[1])
    liquidityAdded, liqAmountA, liqAmountB, nftTokenId, usdValue = bob_user_wallet.addLiquidityConcentrated(legoId, uniswap_nft_token_manager, 0, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert nftTokenId != 0 and liquidityAdded != 0

    # test remove liquidity
    testLegoLiquidityRemoved(lego_uniswap_v3, uniswap_nft_token_manager, nftTokenId, pool, tokenA, tokenB)


@pytest.always
def test_uniswapV3_remove_liq_partial(
    testLegoLiquidityRemoved,
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v3,
    bob,
    fork,
    lego_book,
):
    legoId = lego_book.getRegId(lego_uniswap_v3)
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    uniswap_nft_token_manager = boa.from_etherscan(lego_uniswap_v3.getRegistries()[1])
    liquidityAdded, liqAmountA, liqAmountB, nftTokenId, usdValue = bob_user_wallet.addLiquidityConcentrated(legoId, uniswap_nft_token_manager, 0, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert nftTokenId != 0 and liquidityAdded != 0

    # test remove liquidity (partial)
    testLegoLiquidityRemoved(lego_uniswap_v3, uniswap_nft_token_manager, nftTokenId, pool, tokenA, tokenB, liquidityAdded // 2)


# helper / utils


@pytest.always
def test_uniswapV3_get_best_pool(
    getTokenAndWhale,
    lego_uniswap_v3,
    fork,
):
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")

    best_pool = lego_uniswap_v3.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == POOLS[fork]["WETH_USDC"]
    assert best_pool.fee == 5
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2

    tokenA, _ = getTokenAndWhale("CBBTC")
    best_pool = lego_uniswap_v3.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == POOLS[fork]["WETH_CBBTC"]
    assert best_pool.fee == 30
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2


@pytest.always
def test_uniswapV3_get_swap_amount_out(
    getTokenAndWhale,
    lego_uniswap_v3,
    fork,
    _test,
):
    pool = POOLS[fork]["WETH_USDC"]
    alt_pool = "0x6c561B446416E1A00E8E93E221854d6eA4171372"
    tokenA, _ = getTokenAndWhale("USDC")
    tokenA_amount = 2_600 * (10 ** tokenA.decimals())
    tokenB, _ = getTokenAndWhale("WETH")
    tokenB_amount = 1 * (10 ** tokenB.decimals())

    # usdc -> weth
    amount_out = lego_uniswap_v3.getSwapAmountOut(pool, tokenA, tokenB, tokenA_amount)
    _test(tokenB_amount, amount_out, 100)

    best_pool, amount_out_b = lego_uniswap_v3.getBestSwapAmountOut(tokenA, tokenB, tokenA_amount)
    assert best_pool in [pool, alt_pool]
    _test(amount_out, amount_out_b, 100)

    # weth -> usdc
    amount_out = lego_uniswap_v3.getSwapAmountOut(pool, tokenB, tokenA, tokenB_amount)
    _test(tokenA_amount, amount_out, 100)

    best_pool, amount_out_b = lego_uniswap_v3.getBestSwapAmountOut(tokenB, tokenA, tokenB_amount)
    assert best_pool in [pool, alt_pool]
    _test(amount_out, amount_out_b, 100)


@pytest.always
def test_uniswapV3_get_best_swap_amount_out(
    lego_uniswap_v3,
    fork,
):
    usdc = boa.from_etherscan(TOKENS[fork]["USDC"])
    usdc_amount = 100 * (10 ** usdc.decimals())

    virtual = boa.from_etherscan(TOKENS[fork]["VIRTUAL"])
    virtual_amount = 100 * (10 ** virtual.decimals())

    best_pool, _ = lego_uniswap_v3.getBestSwapAmountOut(usdc, virtual, usdc_amount)
    assert best_pool != ZERO_ADDRESS

    best_pool, _ = lego_uniswap_v3.getBestSwapAmountOut(virtual, usdc, virtual_amount)
    assert best_pool != ZERO_ADDRESS


@pytest.always
def test_uniswapV3_get_swap_amount_in(
    getTokenAndWhale,
    lego_uniswap_v3,
    fork,
    _test,
):
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")
    amount_in = lego_uniswap_v3.getSwapAmountIn(POOLS[fork]["WETH_USDC"], tokenB, tokenA, 2_600 * (10 ** tokenA.decimals()))
    _test(1 * (10 ** tokenB.decimals()), amount_in, 100)

    amount_in = lego_uniswap_v3.getSwapAmountIn(POOLS[fork]["WETH_USDC"], tokenA, tokenB, 1 * (10 ** tokenB.decimals()))
    _test(2_600 * (10 ** tokenA.decimals()), amount_in, 100)


@pytest.always
def test_uniswapV3_get_add_liq_amounts_in(
    getTokenAndWhale,
    lego_uniswap_v3,
    fork,
    _test,
):
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())

    # reduce amount a
    liq_amount_a, liq_amount_b, _ = lego_uniswap_v3.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 7_800 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, 3 * (10 ** tokenB.decimals()), 1_00)

    # set new amount b
    amountB = 10 * (10 ** tokenB.decimals())

    # reduce amount b
    liq_amount_a, liq_amount_b, _ = lego_uniswap_v3.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 10_000 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, int(3.84 * (10 ** tokenB.decimals())), 1_00)


@pytest.always
def test_uniswapV3_get_remove_liq_amounts_out(
    getTokenAndWhale,
    bob_user_wallet,
    lego_uniswap_v3,
    bob,
    fork,
    lego_book,
    _test,
):
    legoId = lego_book.getRegId(lego_uniswap_v3)
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 7_800 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    nft_token_manager = boa.from_etherscan(lego_uniswap_v3.getRegistries()[1])
    liquidityAdded, liqAmountA, liqAmountB, nftTokenId, usdValue = bob_user_wallet.addLiquidityConcentrated(legoId, nft_token_manager, 0, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert nftTokenId != 0 and liquidityAdded != 0

    # test
    amountAOut, amountBOut = lego_uniswap_v3.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    _test(amountAOut, 7_800 * (10 ** tokenA.decimals()), 1_00)
    _test(amountBOut, 3 * (10 ** tokenB.decimals()), 1_00)

    # re-arrange amounts
    first_amount, second_amount = lego_uniswap_v3.getRemoveLiqAmountsOut(pool, tokenB, tokenA, liquidityAdded)
    _test(first_amount, 3 * (10 ** tokenB.decimals()), 1_00)
    _test(second_amount, 7_800 * (10 ** tokenA.decimals()), 1_00)


@pytest.always
def test_uniswapV3_get_price(
    getTokenAndWhale,
    lego_uniswap_v3,
    appraiser,
    _test,
    fork,
):
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    tokenA, _ = getTokenAndWhale("USDC")
    assert appraiser.getNormalAssetPrice(tokenA) != 0

    tokenB, _ = getTokenAndWhale("WETH")
    exp_weth_price = appraiser.getNormalAssetPrice(tokenB)
    assert exp_weth_price != 0

    price = lego_uniswap_v3.getPriceUnsafe(pool, tokenA)
    assert int(0.98 * EIGHTEEN_DECIMALS) <= price <= int(1.02 * EIGHTEEN_DECIMALS)

    price = lego_uniswap_v3.getPriceUnsafe(pool, tokenB)
    _test(exp_weth_price, price, 1_00)



