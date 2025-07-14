import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS
from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS


POOLS = {
    "base": {
        "USDC": "0x7501bc8Bb51616F79bfA524E464fb7B41f0B10fB", # msUSD (CL50)
        "WETH": "0x5d4e504EB4c526995E0cC7A6E327FDa75D8B52b5", # EURC (CL100)
        "AERO": "0x82321f3BEB69f503380D6B233857d5C43562e2D0", # weth (CL200)
        "CBBTC": "0x138aceE5573fA09e7F215965ff60898cc33c6330", # tbtc (CL1)
        "EURC": "0xE846373C1a92B167b4E9cd5d8E4d6B1Db9E90EC7", # usdc (CL50)
        "WETH_USDC": "0xb2cc224c1c9feE385f8ad6a55b4d94E92359DC59", # usdc/weth
        "WETH_CBBTC": "0x70aCDF2Ad0bf2402C957154f944c19Ef4e1cbAE1", # weth/cbbtc
    },
}


TO_TOKEN = {
    "base": {
        "USDC": "0x526728DBc96689597F85ae4cd716d4f7fCcBAE9d", # msUSD (CL50)
        "WETH": TOKENS["base"]["EURC"], # EURC (CL100)
        "AERO": TOKENS["base"]["WETH"], # weth (CL200)
        "CBBTC": TOKENS["base"]["TBTC"], # tbtc (CL1)
        "EURC": TOKENS["base"]["USDC"], # usdc (CL50)
    },
}


TEST_ASSETS = [
    "USDC",
    "WETH",
    "AERO",
    "CBBTC",
    "EURC",
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
def test_aero_slipstream_swap_max_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_slipstream,
    getToToken,
    getPool,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    fromAsset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals()), sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_aero_slipstream, fromAsset, toToken, pool)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_aero_slipstream_swap_partial_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_slipstream,
    getToToken,
    getPool,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    testAmount = TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals())
    fromAsset.transfer(bob_user_wallet.address, testAmount, sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_aero_slipstream, fromAsset, toToken, pool, testAmount // 2)


@pytest.always
def test_aero_slipstream_swap_with_routes(
    getTokenAndWhale,
    bob,
    lego_aero_slipstream,
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
    cbbtc = boa.from_etherscan(TOKENS[fork]["CBBTC"], name="cbbtc token")
    weth_cbbtc_pool = POOLS[fork]["WETH_CBBTC"]
    cbbtc_price = lego_aero_slipstream.getPriceUnsafe(weth_cbbtc_pool, cbbtc)

    # pre balances
    pre_usdc_bal = usdc.balanceOf(bob)
    pre_cbbtc_bal = cbbtc.balanceOf(bob)

    # swap uniswap v3
    usdc.approve(lego_aero_slipstream, usdc_amount, sender=bob)
    fromSwapAmount, toAmount, usd_value = lego_aero_slipstream.swapTokens(usdc_amount, 0, [usdc, weth, cbbtc], [weth_usdc_pool, weth_cbbtc_pool], bob, sender=bob)
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
def test_aero_slipstream_add_liquidity_new_position_more_token_A(
    testLegoLiquidityAdded,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_slipstream,
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
    nft_token_manager = boa.from_etherscan(lego_aero_slipstream.getRegistries()[1])
    nftTokenId = testLegoLiquidityAdded(lego_aero_slipstream, nft_token_manager, 0, pool, tokenA, tokenB, amountA, amountB)
    assert nftTokenId != 0


@pytest.always
def test_aero_slipstream_add_liquidity_new_position_more_token_B(
    testLegoLiquidityAdded,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_slipstream,
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
    nft_token_manager = boa.from_etherscan(lego_aero_slipstream.getRegistries()[1])
    nftTokenId = testLegoLiquidityAdded(lego_aero_slipstream, nft_token_manager, 0, pool, tokenA, tokenB, amountA, amountB)
    assert nftTokenId != 0


@pytest.always
def test_aero_slipstream_add_liquidity_increase_position(
    testLegoLiquidityAdded,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_slipstream,
    lego_book,
    bob,
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
    nft_token_manager = boa.from_etherscan(lego_aero_slipstream.getRegistries()[1])

    # initial mint position
    liquidityAdded, _a, _b, nftTokenId, _c = bob_user_wallet.addLiquidityConcentrated(lego_book.getRegId(lego_aero_slipstream), nft_token_manager.address, 0, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert liquidityAdded != 0
    assert nftTokenId != 0

    # add new amounts
    new_amount_a = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, new_amount_a, sender=whaleA)
    new_amount_b = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, new_amount_b, sender=whaleB)

    # increase liquidity
    testLegoLiquidityAdded(lego_aero_slipstream, nft_token_manager, nftTokenId, pool, tokenA, tokenB, new_amount_a, new_amount_b)


# remove liquidity


@pytest.always
def test_aero_slipstream_remove_liq_max_basic(
    testLegoLiquidityRemoved,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_slipstream,
    bob,
    fork,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_aero_slipstream)
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    nft_token_manager = boa.from_etherscan(lego_aero_slipstream.getRegistries()[1])
    liquidityAdded, liqAmountA, liqAmountB, nftTokenId, usdValue = bob_user_wallet.addLiquidityConcentrated(lego_id, nft_token_manager.address, 0, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert nftTokenId != 0 and liquidityAdded != 0

    # test remove liquidity
    testLegoLiquidityRemoved(lego_aero_slipstream, nft_token_manager, nftTokenId, pool, tokenA, tokenB)


@pytest.always
def test_aero_slipstream_remove_liq_partial(
    testLegoLiquidityRemoved,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_slipstream,
    bob,
    fork,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_aero_slipstream)
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    nft_token_manager = boa.from_etherscan(lego_aero_slipstream.getRegistries()[1])
    liquidityAdded, liqAmountA, liqAmountB, nftTokenId, usdValue = bob_user_wallet.addLiquidityConcentrated(lego_id, nft_token_manager.address, 0, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert nftTokenId != 0 and liquidityAdded != 0

    # test remove liquidity (partial)
    testLegoLiquidityRemoved(lego_aero_slipstream, nft_token_manager, nftTokenId, pool, tokenA, tokenB, liquidityAdded // 2)


@pytest.always
def test_aero_slipstream_remove_liq_max_stable(
    testLegoLiquidityRemoved,
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_slipstream,
    bob,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_aero_slipstream)
    pool = boa.from_etherscan("0x47cA96Ea59C13F72745928887f84C9F52C3D7348")

    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 1 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CBETH")
    amountB = 1 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    nft_token_manager = boa.from_etherscan(lego_aero_slipstream.getRegistries()[1])
    liquidityAdded, liqAmountA, liqAmountB, nftTokenId, usdValue = bob_user_wallet.addLiquidityConcentrated(lego_id, nft_token_manager.address, 0, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert nftTokenId != 0 and liquidityAdded != 0

    # test remove liquidity
    testLegoLiquidityRemoved(lego_aero_slipstream, nft_token_manager, nftTokenId, pool, tokenA, tokenB)


# helper / utils


@pytest.always
def test_aero_slipstream_get_best_pool(
    getTokenAndWhale,
    lego_aero_slipstream,
    fork,
):
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")

    best_pool = lego_aero_slipstream.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == POOLS[fork]["WETH_USDC"]
    assert best_pool.fee == 4
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2

    tokenA, _ = getTokenAndWhale("CBBTC")
    best_pool = lego_aero_slipstream.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == POOLS[fork]["WETH_CBBTC"]
    assert best_pool.fee == 4
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2


@pytest.always
def test_aero_slipstream_get_swap_amount_out(
    getTokenAndWhale,
    lego_aero_slipstream,
    fork,
    _test,
):
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")
    amount_out = lego_aero_slipstream.getSwapAmountOut(POOLS[fork]["WETH_USDC"], tokenA, tokenB, 2_600 * (10 ** tokenA.decimals()))
    _test(1 * (10 ** tokenB.decimals()), amount_out, 100)

    amount_out = lego_aero_slipstream.getSwapAmountOut(POOLS[fork]["WETH_USDC"], tokenB, tokenA, 1 * (10 ** tokenB.decimals()))
    _test(2_600 * (10 ** tokenA.decimals()), amount_out, 100)


@pytest.always
def test_aero_slipstream_get_best_swap_amount_out(
    lego_aero_slipstream,
    fork,
):
    weth = boa.from_etherscan(TOKENS[fork]["WETH"])
    weth_amount = 5 * (10 ** weth.decimals())

    virtual = boa.from_etherscan(TOKENS[fork]["VIRTUAL"])
    virtual_amount = 100 * (10 ** virtual.decimals())

    best_pool, _ = lego_aero_slipstream.getBestSwapAmountOut(weth, virtual, weth_amount)
    assert best_pool != ZERO_ADDRESS

    best_pool, _ = lego_aero_slipstream.getBestSwapAmountOut(virtual, weth, virtual_amount)
    assert best_pool != ZERO_ADDRESS


@pytest.always
def test_aero_slipstream_get_swap_amount_in(
    getTokenAndWhale,
    lego_aero_slipstream,
    fork,
    _test,
):
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")
    amount_in = lego_aero_slipstream.getSwapAmountIn(POOLS[fork]["WETH_USDC"], tokenB, tokenA, 2_600 * (10 ** tokenA.decimals()))
    _test(1 * (10 ** tokenB.decimals()), amount_in, 100)

    amount_in = lego_aero_slipstream.getSwapAmountIn(POOLS[fork]["WETH_USDC"], tokenA, tokenB, 1 * (10 ** tokenB.decimals()))
    _test(2_600 * (10 ** tokenA.decimals()), amount_in, 100)


@pytest.always
def test_aero_slipstream_get_add_liq_amounts_in(
    getTokenAndWhale,
    lego_aero_slipstream,
    fork,
    _test,
):
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())

    # reduce amount a
    liq_amount_a, liq_amount_b, _ = lego_aero_slipstream.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 7_800 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, 3 * (10 ** tokenB.decimals()), 1_00)

    # set new amount b
    amountB = 10 * (10 ** tokenB.decimals())

    # reduce amount b
    liq_amount_a, liq_amount_b, _ = lego_aero_slipstream.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 10_000 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, int(3.84 * (10 ** tokenB.decimals())), 1_00)


@pytest.always
def test_aero_slipstream_get_remove_liq_amounts_out(
    getTokenAndWhale,
    bob_user_wallet,
    lego_aero_slipstream,
    bob,
    fork,
    _test,
    lego_book,
):
    lego_id = lego_book.getRegId(lego_aero_slipstream)
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])

    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 7_800 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    nft_token_manager = boa.from_etherscan(lego_aero_slipstream.getRegistries()[1])
    liquidityAdded, liqAmountA, liqAmountB, nftTokenId, usdValue = bob_user_wallet.addLiquidityConcentrated(lego_id, nft_token_manager.address, 0, pool.address, tokenA.address, tokenB.address, amountA, amountB, sender=bob)
    assert nftTokenId != 0 and liquidityAdded != 0

    # test
    amountAOut, amountBOut = lego_aero_slipstream.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    _test(amountAOut, 7_800 * (10 ** tokenA.decimals()), 1_00)
    _test(amountBOut, 3 * (10 ** tokenB.decimals()), 1_00)

    # re-arrange amounts
    first_amount, second_amount = lego_aero_slipstream.getRemoveLiqAmountsOut(pool, tokenB, tokenA, liquidityAdded)
    _test(first_amount, 3 * (10 ** tokenB.decimals()), 1_00)
    _test(second_amount, 7_800 * (10 ** tokenA.decimals()), 1_00)


@pytest.always
def test_aero_slipstream_get_price(
    getTokenAndWhale,
    lego_aero_slipstream,
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

    price = lego_aero_slipstream.getPriceUnsafe(pool, tokenA)
    assert int(0.98 * EIGHTEEN_DECIMALS) <= price <= int(1.02 * EIGHTEEN_DECIMALS)

    price = lego_aero_slipstream.getPriceUnsafe(pool, tokenB)
    _test(exp_weth_price, price, 1_00)

