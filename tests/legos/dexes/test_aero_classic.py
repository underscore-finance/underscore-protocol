import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS, INTEGRATION_ADDYS
from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS, MAX_UINT256


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
def setup_assets(setUserWalletConfig):
    setUserWalletConfig(_swapFee=0)
   

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
    lego_book,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    fromAsset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals()), sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_book.getRegId(lego_aero_classic), fromAsset, toToken, pool)


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
    testLegoSwap(lego_book.getRegId(lego_aero_classic), fromAsset, toToken, pool, testAmount // 2)


@pytest.always
def test_aerodrom_classic_swap_with_routes(
    getTokenAndWhale,
    bob,
    lego_aero_classic,
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
    weth_usdc_pool = "0xcDAC0d6c6C59727a65F871236188350531885C43"

    # virtual setup
    virtual = boa.from_etherscan(TOKENS[fork]["VIRTUAL"], name="virtual token")
    weth_virtual_pool = "0x21594b992F68495dD28d605834b58889d0a727c7"
    virtual_price = lego_aero_classic.getPriceUnsafe(weth_virtual_pool, virtual)

    # pre balances
    pre_usdc_bal = usdc.balanceOf(bob)
    pre_virtual_bal = virtual.balanceOf(bob)

    # swap aerodrome classic
    usdc.approve(lego_aero_classic, usdc_amount, sender=bob)
    fromSwapAmount, toAmount, usd_value = lego_aero_classic.swapTokens(usdc_amount, 0, [usdc, weth, virtual], [weth_usdc_pool, weth_virtual_pool], bob, sender=bob)
    assert toAmount != 0

    # post balances
    assert usdc.balanceOf(bob) == pre_usdc_bal - fromSwapAmount
    assert virtual.balanceOf(bob) == pre_virtual_bal + toAmount

    # usd values
    usdc_input_usd_value = appraiser.getUsdValue(usdc, usdc_amount)
    virtual_output_usd_value = virtual_price * toAmount // (10 ** virtual.decimals())
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
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool, tokenA, tokenB, amountA, amountB, sender=bob)

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
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool, tokenA, tokenB, amountA, amountB, sender=bob)

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
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool, tokenA, tokenB, amountA, amountB, sender=bob)

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
    lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(legoId, pool, tokenA, tokenB, amountA, amountB, sender=bob)

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
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")
    amount_out = lego_aero_classic.getSwapAmountOut(POOLS[fork]["WETH_USDC"], tokenA, tokenB, 2_600 * (10 ** tokenA.decimals()))
    _test(1 * (10 ** tokenB.decimals()), amount_out, 100)

    amount_out = lego_aero_classic.getSwapAmountOut(POOLS[fork]["WETH_USDC"], tokenB, tokenA, 1 * (10 ** tokenB.decimals()))
    _test(2_600 * (10 ** tokenA.decimals()), amount_out, 100)


@pytest.always
def test_aerodrome_classic_get_swap_amount_in(
    getTokenAndWhale,
    lego_aero_classic,
    _test,
    fork,
):
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("WETH")
    amount_in = lego_aero_classic.getSwapAmountIn(POOLS[fork]["WETH_USDC"], tokenB, tokenA, 2_600 * (10 ** tokenA.decimals()))
    _test(1 * (10 ** tokenB.decimals()), amount_in, 100)

    amount_in = lego_aero_classic.getSwapAmountIn(POOLS[fork]["WETH_USDC"], tokenA, tokenB, 1 * (10 ** tokenB.decimals()))
    _test(2_600 * (10 ** tokenA.decimals()), amount_in, 100)


@pytest.always
def test_aerodrome_classic_get_add_liq_amounts_in(
    getTokenAndWhale,
    lego_aero_classic,
    _test,
    fork,
):
    pool = boa.from_etherscan(POOLS[fork]["WETH_USDC"])
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenB, whaleB = getTokenAndWhale("WETH")
    amountB = 3 * (10 ** tokenB.decimals())

    # reduce amount a
    liq_amount_a, liq_amount_b, _ = lego_aero_classic.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 7_800 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, 3 * (10 ** tokenB.decimals()), 1_00)

    # set new amount b
    amountB = 10 * (10 ** tokenB.decimals())

    # reduce amount b
    liq_amount_a, liq_amount_b, _ = lego_aero_classic.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 10_000 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, int(3.84 * (10 ** tokenB.decimals())), 1_00)


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
    legoId = lego_book.getRegId(lego_aero_classic)
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
    amountAOut, amountBOut = lego_aero_classic.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    _test(amountAOut, 7_800 * (10 ** tokenA.decimals()), 1_00)
    _test(amountBOut, 3 * (10 ** tokenB.decimals()), 1_00)

    # re-arrange amounts
    first_amount, second_amount = lego_aero_classic.getRemoveLiqAmountsOut(pool, tokenB, tokenA, liquidityAdded)
    _test(first_amount, 3 * (10 ** tokenB.decimals()), 1_00)
    _test(second_amount, 7_800 * (10 ** tokenA.decimals()), 1_00)


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
    assert appraiser.getNormalAssetPrice(tokenA) != 0

    tokenB, _ = getTokenAndWhale("WETH")
    exp_weth_price = appraiser.getNormalAssetPrice(tokenB)
    assert exp_weth_price != 0

    price = lego_aero_classic.getPriceUnsafe(pool, tokenA)
    assert int(0.98 * EIGHTEEN_DECIMALS) <= price <= int(1.02 * EIGHTEEN_DECIMALS)

    price = lego_aero_classic.getPriceUnsafe(pool, tokenB)
    _test(exp_weth_price, price, 1_00)