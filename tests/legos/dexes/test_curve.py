import pytest
import boa

from config.BluePrint import TOKENS, TEST_AMOUNTS
from constants import ZERO_ADDRESS, MAX_UINT256


POOLS = {
    "base": {
        "USDC": "0x63Eb7846642630456707C3efBb50A03c79B89D81", # usdc/usdm (stable ng)
        "WETH": "0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59", # weth/cbeth (two crypto)
        "TBTC": "0x6e53131F68a034873b6bFA15502aF094Ef0c5854", # tbtc/crvusd (tricrypto)
        "FROK": "0xa0D3911349e701A1F49C1Ba2dDA34b4ce9636569", # frok/weth (two crypto ng)
        "CRVUSD": "0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f", # crvusd/usdbc (4pool)
        "TBTC_CRVUSD": "0x6e53131F68a034873b6bFA15502aF094Ef0c5854", # tbtc/crvusd (tricrypto)
        "CRVUSD_USDBC": "0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f", # crvusd/usdbc (4pool)
    },
}


TO_TOKEN = {
    "base": {
        "USDC": TOKENS["base"]["USDM"], # usdm (stable ng)
        "WETH": TOKENS["base"]["CBETH"], # cbeth (two crypto)
        "TBTC": TOKENS["base"]["CRVUSD"], # crvusd (tricrypto)
        "FROK": TOKENS["base"]["WETH"], # weth (two crypto ng)
        "CRVUSD": TOKENS["base"]["USDBC"], # usdbc (4pool)
    },
}


TEST_ASSETS = [
    "USDC",
    "WETH",
    "TBTC",
    "FROK",
    "CRVUSD",
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
def test_curve_swap_max_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    getToToken,
    getPool,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    fromAsset.transfer(bob_user_wallet.address, TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals()), sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_curve, fromAsset, toToken, pool)


@pytest.mark.parametrize("token_str", TEST_ASSETS)
@pytest.always
def test_curve_swap_partial_with_pool(
    token_str,
    testLegoSwap,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    getToToken,
    getPool,
):
    # setup
    fromAsset, whale = getTokenAndWhale(token_str)
    testAmount = TEST_AMOUNTS[token_str] * (10 ** fromAsset.decimals())
    fromAsset.transfer(bob_user_wallet.address, testAmount, sender=whale)
    toToken = getToToken(token_str)

    pool = getPool(token_str)
    testLegoSwap(lego_curve, fromAsset, toToken, pool, testAmount // 2)


@pytest.always
def test_curve_swap_with_routes(
    getTokenAndWhale,
    bob,
    lego_curve,
    fork,
    appraiser,
    _test,
):
    # tbtc setup
    tbtc, tbtc_whale = getTokenAndWhale("TBTC")
    tbtc_amount = int(0.1 * (10 ** tbtc.decimals()))
    tbtc.transfer(bob, tbtc_amount, sender=tbtc_whale)

    # crvusd setup
    crvusd = TOKENS[fork]["CRVUSD"]
    tbtc_crvusd = POOLS[fork]["TBTC_CRVUSD"]

    # usdc
    usdc = boa.from_etherscan(TOKENS[fork]["USDC"], name="usdc token")
    usdc_4pool = POOLS[fork]["CRVUSD_USDBC"]

    # pre balances
    pre_tbtc_bal = tbtc.balanceOf(bob)
    pre_usdc_bal = usdc.balanceOf(bob)

    # swap curve
    tbtc.approve(lego_curve, tbtc_amount, sender=bob)
    fromSwapAmount, toAmount, usd_value = lego_curve.swapTokens(tbtc_amount, 0, [tbtc, crvusd, usdc], [tbtc_crvusd, usdc_4pool], bob, sender=bob)
    assert toAmount != 0

    # post balances
    assert tbtc.balanceOf(bob) == pre_tbtc_bal - fromSwapAmount
    assert usdc.balanceOf(bob) == pre_usdc_bal + toAmount

    # usd values
    tbtc_input_usd_value = appraiser.getUsdValue(TOKENS[fork]["CBBTC"], tbtc_amount // (10 ** 10)) # using cbbtc price for tbtc
    usdc_output_usd_value = appraiser.getUsdValue(TOKENS[fork]["USDC"], toAmount)
    _test(tbtc_input_usd_value, usdc_output_usd_value, 5_00) # 5%


# add liquidity


@pytest.always
def test_curve_add_liquidity_stable_ng(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 1_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("USDM")
    amountB = 1_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0x63Eb7846642630456707C3efBb50A03c79B89D81")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_add_liquidity_stable_ng_one_coin(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, _ = getTokenAndWhale("USDM")
    pool = boa.from_etherscan("0x63Eb7846642630456707C3efBb50A03c79B89D81")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB, amountA, 0)


@pytest.always
def test_curve_add_liquidity_two_crypto(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 2 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CBETH")
    amountB = 2 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_add_liquidity_two_crypto_one_coin(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 2 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, _ = getTokenAndWhale("CBETH")
    pool = boa.from_etherscan("0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB, amountA, 0)


@pytest.always
def test_curve_add_liquidity_tricrypto(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("TBTC")
    amountA = int(0.1 * (10 ** tokenA.decimals()))
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0x6e53131F68a034873b6bFA15502aF094Ef0c5854")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_add_liquidity_tricrypto_one_coin(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("TBTC")
    amountA = int(0.1 * (10 ** tokenA.decimals()))
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, _ = getTokenAndWhale("CRVUSD")
    pool = boa.from_etherscan("0x6e53131F68a034873b6bFA15502aF094Ef0c5854")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB, amountA, 0)


@pytest.always
def test_curve_add_liquidity_two_crypto_ng(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 1 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("FROK")
    amountB = 70_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0xa0D3911349e701A1F49C1Ba2dDA34b4ce9636569")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_add_liquidity_two_crypto_ng_one_coin(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 1 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, _ = getTokenAndWhale("FROK")
    pool = boa.from_etherscan("0xa0D3911349e701A1F49C1Ba2dDA34b4ce9636569")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB, amountA, 0)


@pytest.always
def test_curve_add_liquidity_4pool(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_add_liquidity_4pool_one_coin(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, _ = getTokenAndWhale("CRVUSD")
    pool = boa.from_etherscan("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f")
    testLegoLiquidityAddedBasic(lego_curve, pool, tokenA, tokenB, amountA, 0)


# remove liquidity


@pytest.always
def test_curve_remove_liquidity_stable_ng(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("USDM")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0x63Eb7846642630456707C3efBb50A03c79B89D81")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_remove_liquidity_stable_ng_one_coin(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("USDM")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0x63Eb7846642630456707C3efBb50A03c79B89D81")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, ZERO_ADDRESS)


@pytest.always
def test_curve_remove_liquidity_two_crypto(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 2 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CBETH")
    amountB = 2 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_remove_liquidity_two_crypto_one_coin(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 2 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CBETH")
    amountB = 2 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, ZERO_ADDRESS)


@pytest.always
def test_curve_remove_liquidity_tricrypto(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("TBTC")
    amountA = int(0.1 * (10 ** tokenA.decimals()))
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0x6e53131F68a034873b6bFA15502aF094Ef0c5854")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_remove_liquidity_tricrypto_one_coin(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("TBTC")
    amountA = int(0.1 * (10 ** tokenA.decimals()))
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0x6e53131F68a034873b6bFA15502aF094Ef0c5854")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, ZERO_ADDRESS)


@pytest.always
def test_curve_remove_liquidity_two_crypto_ng(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 1 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("FROK")
    amountB = 70_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0xa0D3911349e701A1F49C1Ba2dDA34b4ce9636569")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_remove_liquidity_two_crypto_ng_one_coin(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 1 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("FROK")
    amountB = 70_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0xa0D3911349e701A1F49C1Ba2dDA34b4ce9636569")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, ZERO_ADDRESS)


@pytest.always
def test_curve_remove_liquidity_4pool(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, tokenB)


@pytest.always
def test_curve_remove_liquidity_4pool_one_coin(
    testLegoLiquidityRemovedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
):
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    pool = boa.from_etherscan("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f")

    # add liquidity
    setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # test remove liquidity
    testLegoLiquidityRemovedBasic(lego_curve, pool, tokenA, ZERO_ADDRESS)


# helper / utils


@pytest.always
def test_curve_get_best_pool(
    getTokenAndWhale,
    lego_curve,
):
    tokenA, _ = getTokenAndWhale("CBETH")
    tokenB, _ = getTokenAndWhale("WETH")

    best_pool = lego_curve.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == "0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59"
    assert best_pool.fee == 3
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2

    # tricrypto
    tokenA, _ = getTokenAndWhale("CRVUSD")
    best_pool = lego_curve.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == "0x6e53131F68a034873b6bFA15502aF094Ef0c5854"
    assert best_pool.fee == 59
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 3


@pytest.always
def test_curve_get_swap_amount_out(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    tokenA, _ = getTokenAndWhale("CRVUSD")
    tokenB, _ = getTokenAndWhale("WETH")
    amount_out = lego_curve.getSwapAmountOut("0x6e53131F68a034873b6bFA15502aF094Ef0c5854", tokenA, tokenB, 2_600 * (10 ** tokenA.decimals()))
    _test(int(0.97 * (10 ** tokenB.decimals())), amount_out, 100)

    amount_out = lego_curve.getSwapAmountOut("0x6e53131F68a034873b6bFA15502aF094Ef0c5854", tokenB, tokenA, 1 * (10 ** tokenB.decimals()))
    _test(2_600 * (10 ** tokenA.decimals()), amount_out, 100)


@pytest.always
def test_curve_get_swap_amount_out_diff_decimals(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    tokenA, _ = getTokenAndWhale("CRVUSD")
    tokenB, _ = getTokenAndWhale("USDC")
    amount_out = lego_curve.getSwapAmountOut("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f", tokenA, tokenB, 1_000 * (10 ** tokenA.decimals()))
    _test(1_000 * (10 ** tokenB.decimals()), amount_out, 100)

    amount_out = lego_curve.getSwapAmountOut("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f", tokenB, tokenA, 1_000 * (10 ** tokenB.decimals()))
    _test(1_000 * (10 ** tokenA.decimals()), amount_out, 100)


@pytest.always
def test_curve_get_swap_amount_in(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    tokenA, _ = getTokenAndWhale("CRVUSD")
    tokenB, _ = getTokenAndWhale("WETH")
    amount_in = lego_curve.getSwapAmountIn("0x6e53131F68a034873b6bFA15502aF094Ef0c5854", tokenB, tokenA, 2_600 * (10 ** tokenA.decimals()))
    _test(int(0.99 * (10 ** tokenB.decimals())), amount_in, 100)

    amount_in = lego_curve.getSwapAmountIn("0x6e53131F68a034873b6bFA15502aF094Ef0c5854", tokenA, tokenB, 1 * (10 ** tokenB.decimals()))
    _test(2_630 * (10 ** tokenA.decimals()), amount_in, 100)


@pytest.always
def test_curve_get_swap_amount_in_diff_decimals(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    tokenA, _ = getTokenAndWhale("CRVUSD")
    tokenB, _ = getTokenAndWhale("USDC")

    # crvusd in, usdc out
    amount_in = lego_curve.getSwapAmountIn("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f", tokenA, tokenB, 1_000 * (10 ** tokenB.decimals()))
    _test(1_000 * (10 ** tokenA.decimals()), amount_in, 100)

    # usdc in, crvusd out
    amount_in = lego_curve.getSwapAmountIn("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f", tokenB, tokenA, 1_000 * (10 ** tokenA.decimals()))
    _test(1_000 * (10 ** tokenB.decimals()), amount_in, 100)


@pytest.always
def test_curve_get_add_liq_amounts_in_stable_ng(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    pool = boa.from_etherscan("0x63Eb7846642630456707C3efBb50A03c79B89D81")
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 20_000 * (10 ** tokenA.decimals())
    tokenB, whaleB = getTokenAndWhale("USDM")
    amountB = 10_000 * (10 ** tokenB.decimals())

    # reduce amount a
    liq_amount_a, liq_amount_b, lp_amount = lego_curve.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 2474 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, 10_000 * (10 ** tokenB.decimals()), 1_00)
    assert lp_amount != 0

    # set new amount b
    amountB = 30_000 * (10 ** tokenB.decimals())

    # reduce amount b
    liq_amount_a, liq_amount_b, lp_amount = lego_curve.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 7420 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, 30_000 * (10 ** tokenB.decimals()), 1_00)
    assert lp_amount != 0


@pytest.always
def test_curve_get_add_liq_amounts_in_crypto_ng(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    pool = boa.from_etherscan("0xa0D3911349e701A1F49C1Ba2dDA34b4ce9636569")
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 1 * (10 ** tokenA.decimals())
    tokenB, whaleB = getTokenAndWhale("FROK")
    amountB = 70_000 * (10 ** tokenB.decimals())

    # reduce amount a
    liq_amount_a, liq_amount_b, lp_amount = lego_curve.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 1 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, 67_630 * (10 ** tokenB.decimals()), 1_00)
    assert lp_amount != 0


@pytest.always
def test_curve_get_add_liq_amounts_in_two_crypto(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    pool = boa.from_etherscan("0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59")
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 2 * (10 ** tokenA.decimals())
    tokenB, whaleB = getTokenAndWhale("CBETH")
    amountB = 2 * (10 ** tokenB.decimals())

    # reduce amount a
    liq_amount_a, liq_amount_b, lp_amount = lego_curve.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 2 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, int(1.91 * (10 ** tokenB.decimals())), 1_00)
    assert lp_amount != 0


@pytest.always
def test_curve_get_add_liq_amounts_in_tricrypto(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    pool = boa.from_etherscan("0x6e53131F68a034873b6bFA15502aF094Ef0c5854")
    tokenA, whaleA = getTokenAndWhale("TBTC")
    amountA = int(0.1 * (10 ** tokenA.decimals()))
    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())

    # reduce amount a
    liq_amount_a, liq_amount_b, lp_amount = lego_curve.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, int(0.091 * (10 ** tokenA.decimals())), 1_00)
    _test(liq_amount_b, 10_000 * (10 ** tokenB.decimals()), 1_00)
    assert lp_amount != 0


@pytest.always
def test_curve_get_add_liq_amounts_in_meta_pool(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    pool = boa.from_etherscan("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f")
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())

    # reduce amount a
    liq_amount_a, liq_amount_b, lp_amount = lego_curve.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    _test(liq_amount_a, 3_760 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, amountB, 1_00)
    assert lp_amount != 0


@pytest.always
def test_curve_get_remove_liq_amounts_out_stable_ng(
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
    _test,
):
    pool = boa.from_etherscan("0x63Eb7846642630456707C3efBb50A03c79B89D81")
    
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("USDM")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    liquidityAdded, liqAmountA, liqAmountB, usdValue = setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # calc remove liquidity
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    _test(liq_amount_a, 5017 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, 15_000 * (10 ** tokenB.decimals()), 1_00)

    # one coin
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, ZERO_ADDRESS, liquidityAdded)
    _test(liq_amount_a, 19_998 * (10 ** tokenA.decimals()), 1_00)
    assert liq_amount_b == 0

    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, ZERO_ADDRESS, tokenB, liquidityAdded)
    assert liq_amount_a == 0
    _test(liq_amount_b, 19_999 * (10 ** tokenB.decimals()), 1_00)


@pytest.always
def test_curve_get_remove_liq_amounts_out_two_crypto(
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
    _test,
):
    pool = boa.from_etherscan("0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59")
    
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 2 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CBETH")
    amountB = 2 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    liquidityAdded, liqAmountA, liqAmountB, usdValue = setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # calc remove liquidity
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    _test(liq_amount_a, int(2.04 * (10 ** tokenA.decimals())), 1_00)
    _test(liq_amount_b, int(1.96 * (10 ** tokenB.decimals())), 1_00)

    # one coin
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, ZERO_ADDRESS, liquidityAdded)
    _test(liq_amount_a, int(4.20 * (10 ** tokenA.decimals())), 1_00)
    assert liq_amount_b == 0

    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, ZERO_ADDRESS, tokenB, liquidityAdded)
    assert liq_amount_a == 0
    _test(liq_amount_b, int(3.81 * (10 ** tokenB.decimals())), 1_00)


@pytest.always
def test_curve_get_remove_liq_amounts_out_tricrypto(
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
    _test,
):
    pool = boa.from_etherscan("0x6e53131F68a034873b6bFA15502aF094Ef0c5854")
    
    # setup
    tokenA, whaleA = getTokenAndWhale("TBTC")
    amountA = int(0.1 * (10 ** tokenA.decimals()))
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    liquidityAdded, liqAmountA, liqAmountB, usdValue = setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # calc remove liquidity
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    assert liq_amount_a == MAX_UINT256
    assert liq_amount_b == MAX_UINT256

    # one coin
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, ZERO_ADDRESS, liquidityAdded)
    _test(liq_amount_a, int(0.187 * (10 ** tokenA.decimals())), 1_00)
    assert liq_amount_b == 0

    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, ZERO_ADDRESS, tokenB, liquidityAdded)
    assert liq_amount_a == 0
    _test(liq_amount_b, 20_580 * (10 ** tokenB.decimals()), 1_00)


@pytest.always
def test_curve_get_remove_liq_amounts_out_crypto_ng(
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
    _test,
):
    pool = boa.from_etherscan("0xa0D3911349e701A1F49C1Ba2dDA34b4ce9636569")
    
    # setup
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 1 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("FROK")
    amountB = 70_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    liquidityAdded, liqAmountA, liqAmountB, usdValue = setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # calc remove liquidity
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    _test(liq_amount_a, 1 * (10 ** tokenA.decimals()), 1_00)
    _test(liq_amount_b, 69_695 * (10 ** tokenB.decimals()), 1_00)

    # one coin
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, ZERO_ADDRESS, liquidityAdded)
    _test(liq_amount_a, int(1.48 * (10 ** tokenA.decimals())), 1_00)
    assert liq_amount_b == 0

    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, ZERO_ADDRESS, tokenB, liquidityAdded)
    assert liq_amount_a == 0
    _test(liq_amount_b, 103_001 * (10 ** tokenB.decimals()), 1_00)


@pytest.always
def test_curve_get_remove_liq_amounts_out_4pool(
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
    _test,
):
    pool = boa.from_etherscan("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f")
    
    # setup
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 10_000 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    # add liquidity
    liquidityAdded, liqAmountA, liqAmountB, usdValue = setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)

    # calc remove liquidity
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
    assert liq_amount_a == MAX_UINT256
    assert liq_amount_b == MAX_UINT256

    # one coin
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, ZERO_ADDRESS, liquidityAdded)
    _test(liq_amount_a, 19_955 * (10 ** tokenA.decimals()), 1_00)
    assert liq_amount_b == 0

    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, ZERO_ADDRESS, tokenB, liquidityAdded)
    assert liq_amount_a == 0
    _test(liq_amount_b, 20_037 * (10 ** tokenB.decimals()), 1_00)
