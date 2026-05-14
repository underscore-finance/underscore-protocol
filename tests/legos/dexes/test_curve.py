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
def setup_assets(setUserWalletConfig, createTxFees):
    setUserWalletConfig(_txFees=createTxFees())


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
    bob_user_wallet,
    lego_curve,
    lego_book,
    fork,
    appraiser,
    _test,
):
    # Multi-hop TBTC -> CRVUSD -> USDC routed through the user wallet.
    tbtc, tbtc_whale = getTokenAndWhale("TBTC")
    tbtc_amount = int(0.1 * (10 ** tbtc.decimals()))
    tbtc.transfer(bob_user_wallet.address, tbtc_amount, sender=tbtc_whale)

    crvusd = TOKENS[fork]["CRVUSD"]
    tbtc_crvusd = POOLS[fork]["TBTC_CRVUSD"]
    usdc = boa.from_etherscan(TOKENS[fork]["USDC"], name="usdc token")
    usdc_4pool = POOLS[fork]["CRVUSD_USDBC"]

    pre_tbtc_bal = tbtc.balanceOf(bob_user_wallet)
    pre_usdc_bal = usdc.balanceOf(bob_user_wallet)

    lego_id = lego_book.getRegId(lego_curve)
    instruction = (
        lego_id,
        tbtc_amount,
        0,
        [tbtc, crvusd, usdc],
        [tbtc_crvusd, usdc_4pool],
    )
    tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, usd_value = bob_user_wallet.swapTokens([instruction], sender=bob)
    assert lastTokenOutAmount != 0

    assert tbtc.balanceOf(bob_user_wallet) == pre_tbtc_bal - origAmountIn
    assert usdc.balanceOf(bob_user_wallet) == pre_usdc_bal + lastTokenOutAmount

    tbtc_input_usd_value = appraiser.getUsdValue(TOKENS[fork]["CBBTC"], tbtc_amount // (10 ** 10)) # using cbbtc price for tbtc
    usdc_output_usd_value = appraiser.getUsdValue(TOKENS[fork]["USDC"], lastTokenOutAmount)
    _test(tbtc_input_usd_value, usdc_output_usd_value, 5_00) # 5%


# add liquidity


@pytest.always
def test_curve_add_liquidity_stable_ng(
    testLegoLiquidityAddedBasic,
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
):
    # setup — at this fork block, USDM "whale" is the Curve pool itself, which holds ~893 USDM.
    # Use small amounts so the pool retains enough to fund both this test and other USDM tests.
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 100 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("USDM")
    amountB = 100 * (10 ** tokenB.decimals())
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
    # setup — adds only USDC (no USDM needed)
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
    # setup — small amounts so the pool (acting as USDM whale at this fork block) retains liquidity.
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 100 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("USDM")
    amountB = 100 * (10 ** tokenB.decimals())
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
    # setup — small amounts so the pool (acting as USDM whale at this fork block) retains liquidity.
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 100 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("USDM")
    amountB = 100 * (10 ** tokenB.decimals())
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
    # Verify the lego picks the registered deepest pool AND correctly normalizes its fee.
    # Curve lego normalization: pool.fee() // 1_000_000 (see Curve.vy:1053).
    tokenA, _ = getTokenAndWhale("CBETH")
    tokenB, _ = getTokenAndWhale("WETH")

    best_pool = lego_curve.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == "0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59"
    pool_contract = boa.from_etherscan(best_pool.pool, name="best_pool_two_crypto")
    assert best_pool.fee == pool_contract.fee() // 1_000_000
    assert best_pool.fee != 0
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 2

    # tricrypto
    tokenA, _ = getTokenAndWhale("CRVUSD")
    best_pool = lego_curve.getDeepestLiqPool(tokenA, tokenB)
    assert best_pool.pool == "0x6e53131F68a034873b6bFA15502aF094Ef0c5854"
    pool_contract = boa.from_etherscan(best_pool.pool, name="best_pool_tricrypto")
    assert best_pool.fee == pool_contract.fee() // 1_000_000
    assert best_pool.fee != 0
    assert best_pool.liquidity != 0
    assert best_pool.numCoins == 3


@pytest.always
def test_curve_get_swap_amount_out(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    # Round-trip A -> B -> A on tricrypto pool, price-agnostic.
    tokenA, _ = getTokenAndWhale("CRVUSD")
    tokenB, _ = getTokenAndWhale("WETH")
    pool = "0x6e53131F68a034873b6bFA15502aF094Ef0c5854"

    amount_in_a = 2_600 * (10 ** tokenA.decimals())
    amount_b = lego_curve.getSwapAmountOut(pool, tokenA, tokenB, amount_in_a)
    assert amount_b != 0
    amount_a_back = lego_curve.getSwapAmountOut(pool, tokenB, tokenA, amount_b)
    _test(amount_in_a, amount_a_back, 2_00)  # tricrypto has higher swap impact

    amount_in_b = 1 * (10 ** tokenB.decimals())
    amount_a = lego_curve.getSwapAmountOut(pool, tokenB, tokenA, amount_in_b)
    assert amount_a != 0
    amount_b_back = lego_curve.getSwapAmountOut(pool, tokenA, tokenB, amount_a)
    _test(amount_in_b, amount_b_back, 2_00)


@pytest.always
def test_curve_get_swap_amount_out_diff_decimals(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    # Cross-decimal stable pair (CRVUSD 18d <-> USDC 6d). Stables stay ~1:1.
    tokenA, _ = getTokenAndWhale("CRVUSD")
    tokenB, _ = getTokenAndWhale("USDC")
    pool = "0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f"

    amount_out = lego_curve.getSwapAmountOut(pool, tokenA, tokenB, 1_000 * (10 ** tokenA.decimals()))
    _test(1_000 * (10 ** tokenB.decimals()), amount_out, 1_00)

    amount_out = lego_curve.getSwapAmountOut(pool, tokenB, tokenA, 1_000 * (10 ** tokenB.decimals()))
    _test(1_000 * (10 ** tokenA.decimals()), amount_out, 1_00)


@pytest.always
def test_curve_get_swap_amount_in(
    getTokenAndWhale,
    lego_curve,
    _test,
):
    # Inverse consistency on tricrypto pool.
    tokenA, _ = getTokenAndWhale("CRVUSD")
    tokenB, _ = getTokenAndWhale("WETH")
    pool = "0x6e53131F68a034873b6bFA15502aF094Ef0c5854"

    target_out_a = 2_600 * (10 ** tokenA.decimals())
    needed_in_b = lego_curve.getSwapAmountIn(pool, tokenB, tokenA, target_out_a)
    assert needed_in_b != 0
    realized_out_a = lego_curve.getSwapAmountOut(pool, tokenB, tokenA, needed_in_b)
    _test(target_out_a, realized_out_a, 1_00)

    target_out_b = 1 * (10 ** tokenB.decimals())
    needed_in_a = lego_curve.getSwapAmountIn(pool, tokenA, tokenB, target_out_b)
    assert needed_in_a != 0
    realized_out_b = lego_curve.getSwapAmountOut(pool, tokenA, tokenB, needed_in_a)
    _test(target_out_b, realized_out_b, 1_00)


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


def _check_curve_add_liq(lego_curve, pool, tokenA, tokenB, amountA, amountB):
    """Structural check: lego returns non-zero deposits within input bounds and a non-zero LP.

    Curve has multiple pool types (stable_ng, two_crypto, tricrypto, meta) that use different
    formulas to size deposits. We can't easily compute the expected ratio without duplicating
    the pool's internal logic, so we settle for structural invariants.
    """
    liq_a, liq_b, lp_amount = lego_curve.getAddLiqAmountsIn(pool, tokenA, tokenB, amountA, amountB)
    assert liq_a != 0
    assert liq_b != 0
    assert liq_a <= amountA
    assert liq_b <= amountB
    assert lp_amount != 0
    # At least one side must use its full input (binding constraint)
    assert liq_a == amountA or liq_b == amountB


@pytest.always
def test_curve_get_add_liq_amounts_in_stable_ng(
    getTokenAndWhale,
    lego_curve,
):
    pool = boa.from_etherscan("0x63Eb7846642630456707C3efBb50A03c79B89D81")
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("USDM")
    _check_curve_add_liq(lego_curve, pool, tokenA, tokenB, 20_000 * (10 ** tokenA.decimals()), 100 * (10 ** tokenB.decimals()))
    _check_curve_add_liq(lego_curve, pool, tokenA, tokenB, 100 * (10 ** tokenA.decimals()), 30_000 * (10 ** tokenB.decimals()))


@pytest.always
def test_curve_get_add_liq_amounts_in_crypto_ng(
    getTokenAndWhale,
    lego_curve,
):
    pool = boa.from_etherscan("0xa0D3911349e701A1F49C1Ba2dDA34b4ce9636569")
    tokenA, _ = getTokenAndWhale("WETH")
    tokenB, _ = getTokenAndWhale("FROK")
    _check_curve_add_liq(lego_curve, pool, tokenA, tokenB, 1 * (10 ** tokenA.decimals()), 70_000 * (10 ** tokenB.decimals()))


@pytest.always
def test_curve_get_add_liq_amounts_in_two_crypto(
    getTokenAndWhale,
    lego_curve,
):
    pool = boa.from_etherscan("0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59")
    tokenA, _ = getTokenAndWhale("WETH")
    tokenB, _ = getTokenAndWhale("CBETH")
    _check_curve_add_liq(lego_curve, pool, tokenA, tokenB, 2 * (10 ** tokenA.decimals()), 2 * (10 ** tokenB.decimals()))


@pytest.always
def test_curve_get_add_liq_amounts_in_tricrypto(
    getTokenAndWhale,
    lego_curve,
):
    pool = boa.from_etherscan("0x6e53131F68a034873b6bFA15502aF094Ef0c5854")
    tokenA, _ = getTokenAndWhale("TBTC")
    tokenB, _ = getTokenAndWhale("CRVUSD")
    _check_curve_add_liq(lego_curve, pool, tokenA, tokenB, int(0.1 * (10 ** tokenA.decimals())), 10_000 * (10 ** tokenB.decimals()))


@pytest.always
def test_curve_get_add_liq_amounts_in_meta_pool(
    getTokenAndWhale,
    lego_curve,
):
    pool = boa.from_etherscan("0xf6C5F01C7F3148891ad0e19DF78743D31E390D1f")
    tokenA, _ = getTokenAndWhale("USDC")
    tokenB, _ = getTokenAndWhale("CRVUSD")
    _check_curve_add_liq(lego_curve, pool, tokenA, tokenB, 10_000 * (10 ** tokenA.decimals()), 10_000 * (10 ** tokenB.decimals()))


def _curve_pool_reserves_and_supply(lego_curve, pool, tokenA, tokenB):
    """Return (lp_total_supply, reserve_a, reserve_b) for a Curve pool.

    For NG pools (stable_ng, crypto_ng, tricrypto), the pool IS the LP token.
    For older two_crypto / meta pools, the LP token is separate; the Curve meta registry maps it.
    """
    coin_0 = pool.coins(0)
    coin_1 = pool.coins(1)
    bal_0 = pool.balances(0)
    bal_1 = pool.balances(1)

    if coin_0.lower() == tokenA.address.lower():
        reserve_a, reserve_b = bal_0, bal_1
    else:
        assert coin_1.lower() == tokenA.address.lower(), "tokenA not in pool"
        reserve_a, reserve_b = bal_1, bal_0

    # Try the pool itself first (NG pools), fall back to meta registry lookup.
    try:
        total_supply = pool.totalSupply()
    except AttributeError:
        meta_registry = boa.from_etherscan(lego_curve.CURVE_META_REGISTRY(), name="curve_meta_registry")
        lp_token_addr = meta_registry.get_lp_token(pool.address)
        lp_token = boa.from_etherscan(lp_token_addr, name="curve_lp_token")
        total_supply = lp_token.totalSupply()

    return total_supply, reserve_a, reserve_b


def _check_curve_remove_liq(lego_curve, pool, tokenA, tokenB, liquidityAdded, liqAmountA, liqAmountB, _test, can_dual=True):
    """Verify the lego's getRemoveLiqAmountsOut returns proportional amounts vs. pool state.

    For pools that support dual-coin removal, the math is:
        amount[i] = liquidityAdded * reserves[i] / totalLpSupply

    For pools that only support one-coin removal (tricrypto, 4pool), the lego returns
    MAX_UINT256 sentinels for the dual-coin path. We verify those sentinels and that the
    one-coin paths return non-zero only on the requested side.
    """
    if can_dual:
        total_supply, reserve_a, reserve_b = _curve_pool_reserves_and_supply(lego_curve, pool, tokenA, tokenB)
        expected_a = liquidityAdded * reserve_a // total_supply
        expected_b = liquidityAdded * reserve_b // total_supply

        liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
        _test(expected_a, liq_amount_a, 50)  # 0.5% buffer for rounding in proportional math
        _test(expected_b, liq_amount_b, 50)
    else:
        liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, tokenB, liquidityAdded)
        assert liq_amount_a == MAX_UINT256
        assert liq_amount_b == MAX_UINT256

    # One-coin removal: amount math depends on each pool's bonding curve, but we can verify
    # the lego only fills the requested coin and that the result is non-trivial.
    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, tokenA, ZERO_ADDRESS, liquidityAdded)
    assert liq_amount_a != 0
    assert liq_amount_b == 0

    liq_amount_a, liq_amount_b = lego_curve.getRemoveLiqAmountsOut(pool, ZERO_ADDRESS, tokenB, liquidityAdded)
    assert liq_amount_a == 0
    assert liq_amount_b != 0


@pytest.always
def test_curve_get_remove_liq_amounts_out_stable_ng(
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
    _test,
):
    pool = boa.from_etherscan("0x63Eb7846642630456707C3efBb50A03c79B89D81")
    tokenA, whaleA = getTokenAndWhale("USDC")
    amountA = 100 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("USDM")
    amountB = 100 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    liquidityAdded, liqAmountA, liqAmountB, usdValue = setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)
    _check_curve_remove_liq(lego_curve, pool, tokenA, tokenB, liquidityAdded, liqAmountA, liqAmountB, _test, can_dual=True)


@pytest.always
def test_curve_get_remove_liq_amounts_out_two_crypto(
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
    _test,
):
    pool = boa.from_etherscan("0x11C1fBd4b3De66bC0565779b35171a6CF3E71f59")
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 2 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CBETH")
    amountB = 2 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    liquidityAdded, liqAmountA, liqAmountB, usdValue = setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)
    _check_curve_remove_liq(lego_curve, pool, tokenA, tokenB, liquidityAdded, liqAmountA, liqAmountB, _test, can_dual=True)


@pytest.always
def test_curve_get_remove_liq_amounts_out_tricrypto(
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
    _test,
):
    pool = boa.from_etherscan("0x6e53131F68a034873b6bFA15502aF094Ef0c5854")
    tokenA, whaleA = getTokenAndWhale("TBTC")
    amountA = int(0.1 * (10 ** tokenA.decimals()))
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("CRVUSD")
    amountB = 10_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    liquidityAdded, liqAmountA, liqAmountB, usdValue = setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)
    _check_curve_remove_liq(lego_curve, pool, tokenA, tokenB, liquidityAdded, liqAmountA, liqAmountB, _test, can_dual=False)


@pytest.always
def test_curve_get_remove_liq_amounts_out_crypto_ng(
    getTokenAndWhale,
    bob_user_wallet,
    lego_curve,
    setupRemoveLiq,
    _test,
):
    pool = boa.from_etherscan("0xa0D3911349e701A1F49C1Ba2dDA34b4ce9636569")
    tokenA, whaleA = getTokenAndWhale("WETH")
    amountA = 1 * (10 ** tokenA.decimals())
    tokenA.transfer(bob_user_wallet.address, amountA, sender=whaleA)

    tokenB, whaleB = getTokenAndWhale("FROK")
    amountB = 70_000 * (10 ** tokenB.decimals())
    tokenB.transfer(bob_user_wallet.address, amountB, sender=whaleB)

    liquidityAdded, liqAmountA, liqAmountB, usdValue = setupRemoveLiq(lego_curve, pool, tokenA, tokenB, amountA, amountB)
    _check_curve_remove_liq(lego_curve, pool, tokenA, tokenB, liquidityAdded, liqAmountA, liqAmountB, _test, can_dual=True)


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
