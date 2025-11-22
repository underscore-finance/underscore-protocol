import pytest
import boa

from contracts.core.userWallet import UserWallet
from constants import MAX_UINT256, ZERO_ADDRESS, MIN_INT24, MAX_INT24
from conf_utils import filter_logs
from config.BluePrint import TEST_AMOUNTS, TOKENS, WHALES


@pytest.fixture(scope="package")
def bob_user_wallet(setUserWalletConfig, setManagerConfig, hatchery, bob):
    setUserWalletConfig()
    setManagerConfig()  # Set up manager config with default agent

    wallet_addr = hatchery.createUserWallet(bob, ZERO_ADDRESS, 1, sender=bob)
    assert wallet_addr != ZERO_ADDRESS
    return UserWallet.at(wallet_addr)


@pytest.fixture(scope="package")
def setupWithdrawal(getTokenAndWhale, bob_user_wallet, bob):
    def setupWithdrawal(_legoId, _token_str, _vaultToken):
        asset, whale = getTokenAndWhale(_token_str)
        asset.transfer(bob_user_wallet.address, TEST_AMOUNTS[_token_str] * (10 ** asset.decimals()), sender=whale)
        _a, _b, vault_tokens_received, _c = bob_user_wallet.depositForYield(_legoId, asset, _vaultToken, MAX_UINT256, sender=bob)
        return asset, vault_tokens_received

    yield setupWithdrawal


@pytest.fixture(scope="package")
def testLegoDeposit(bob_user_wallet, bob, lego_book, _test):
    def testLegoDeposit(
        _lego,
        _asset,
        _vaultToken,
        _amount = MAX_UINT256,
    ):
        lego_id = lego_book.getRegId(_lego)

        # pre balances
        pre_user_asset_bal = _asset.balanceOf(bob_user_wallet)
        pre_user_vault_bal = _vaultToken.balanceOf(bob_user_wallet)

        lego_addr = lego_book.getAddr(lego_id)
        pre_lego_asset_bal = _asset.balanceOf(lego_addr)
        pre_lego_vault_bal = _vaultToken.balanceOf(lego_addr)

        # deposit
        deposit_amount, vault_token, vault_tokens_received, usd_value = bob_user_wallet.depositForYield(lego_id, _asset, _vaultToken, _amount, sender=bob)

        # event
        log_wallet = filter_logs(bob_user_wallet, "WalletAction")[0]
        assert log_wallet.op == 10  # yield deposit
        assert log_wallet.asset1 == _asset.address
        assert log_wallet.asset2 == vault_token
        assert log_wallet.amount1 == deposit_amount
        assert log_wallet.amount2 == vault_tokens_received
        assert log_wallet.usdValue == usd_value
        assert log_wallet.legoId == lego_id
        assert log_wallet.signer == bob

        assert _vaultToken.address == vault_token
        assert deposit_amount != 0
        assert vault_tokens_received != 0

        if _amount == MAX_UINT256:
            _test(deposit_amount, pre_user_asset_bal)
        else:
            _test(deposit_amount, _amount)

        # lego addr should not have any leftover
        assert _asset.balanceOf(lego_addr) == pre_lego_asset_bal
        assert _vaultToken.balanceOf(lego_addr) == pre_lego_vault_bal

        # vault tokens
        _test(pre_user_vault_bal + vault_tokens_received, _vaultToken.balanceOf(bob_user_wallet.address))

        # asset amounts
        _test(pre_user_asset_bal - deposit_amount, _asset.balanceOf(bob_user_wallet.address))

        # test key utility functions
        _test(vault_tokens_received, _lego.getVaultTokenAmount(_asset, deposit_amount, _vaultToken))
        _test(deposit_amount, _lego.getUnderlyingAmount(_vaultToken, vault_tokens_received))
        assert _asset.address == _lego.getUnderlyingAsset(_vaultToken)

    yield testLegoDeposit


@pytest.fixture(scope="package")
def testLegoWithdrawal(bob_user_wallet, bob, lego_book, _test):
    def testLegoWithdrawal(
        _legoId,
        _asset,
        _vaultToken,
        _amount = MAX_UINT256,
    ):
        # pre balances
        pre_user_asset_bal = _asset.balanceOf(bob_user_wallet)
        pre_user_vault_bal = _vaultToken.balanceOf(bob_user_wallet)

        lego_addr = lego_book.getAddr(_legoId)
        pre_lego_asset_bal = _asset.balanceOf(lego_addr)
        pre_lego_vault_bal = _vaultToken.balanceOf(lego_addr)

        # withdraw
        vault_token_burned, underlyingAsset, underlyingAmount, usd_value = bob_user_wallet.withdrawFromYield(_legoId, _vaultToken, _amount, sender=bob)

        # event
        log_wallet = filter_logs(bob_user_wallet, "WalletAction")[0]
        assert log_wallet.op == 11  # yield withdraw
        assert log_wallet.asset1 == _vaultToken.address
        assert log_wallet.asset2 == underlyingAsset
        assert log_wallet.amount1 == vault_token_burned
        assert log_wallet.amount2 == underlyingAmount
        assert log_wallet.usdValue == usd_value
        assert log_wallet.legoId == _legoId
        assert log_wallet.signer == bob

        assert underlyingAmount != 0
        assert vault_token_burned != 0

        if _amount == MAX_UINT256:
            _test(vault_token_burned, pre_user_vault_bal)
        else:
            _test(vault_token_burned, _amount)

        # lego addr should not have any leftover
        assert _asset.balanceOf(lego_addr) == pre_lego_asset_bal
        assert _vaultToken.balanceOf(lego_addr) == pre_lego_vault_bal

        # vault tokens
        _test(pre_user_vault_bal - vault_token_burned, _vaultToken.balanceOf(bob_user_wallet.address))

        # asset amounts
        _test(pre_user_asset_bal + underlyingAmount, _asset.balanceOf(bob_user_wallet.address))

    yield testLegoWithdrawal


@pytest.fixture(scope="package")
def testLegoViewFunctions(lego_book, fork):
    def testLegoViewFunctions(_lego, _vaultToken, _tokenStr, _shouldHaveBorrow=True):
        reg_id = lego_book.getRegId(_lego)
        print(f"\n--- {_tokenStr} View Functions ---")
        print("Lego: ", lego_book.getAddrDescription(reg_id))
        print(f"Vault Token: {_vaultToken.address}")

        # get underlying asset decimals
        token = TOKENS[fork][_tokenStr]
        underlying = boa.from_etherscan(token, name=_tokenStr)
        decimals = underlying.decimals()

        # test totalAssets - should be > 0 for active vaults
        total_assets = _lego.totalAssets(_vaultToken)
        print(f"totalAssets: {total_assets / 10 ** decimals}")
        assert total_assets > 0

        # test totalBorrows
        total_borrows = _lego.totalBorrows(_vaultToken)
        print(f"totalBorrows: {total_borrows / 10 ** decimals}")
        if _shouldHaveBorrow:
            assert total_borrows > 0
        else:
            assert total_borrows == 0

        # test getAvailLiquidity - should be >= 0
        avail_liq = _lego.getAvailLiquidity(_vaultToken)
        print(f"availLiquidity: {avail_liq / 10 ** decimals}")
        assert avail_liq > 0

        # test getUtilizationRatio - should be 0-10000 (basis points)
        util_ratio = _lego.getUtilizationRatio(_vaultToken)
        print(f"utilizationRatio: {util_ratio} ({util_ratio / 100}%)")
        assert util_ratio >= 0
        assert util_ratio <= 10000
        if _shouldHaveBorrow:
            assert util_ratio > 0
        else:
            assert util_ratio == 0

        # sanity checks on relationships
        assert total_borrows < total_assets
        assert avail_liq <= total_assets

    yield testLegoViewFunctions


@pytest.fixture(scope="package")
def testLegoSwap(bob_user_wallet, bob, lego_book, _test):
    def testLegoSwap(
        _lego,
        _tokenIn,
        _tokenOut,
        _pool,
        _amountIn = MAX_UINT256,
        _minAmountOut = 0,
    ):
        lego_id = lego_book.getRegId(_lego)

        # pre balances
        pre_user_from_bal = _tokenIn.balanceOf(bob_user_wallet)
        pre_user_to_bal = _tokenOut.balanceOf(bob_user_wallet)

        lego_addr = lego_book.getAddr(lego_id)
        pre_lego_from_bal = _tokenIn.balanceOf(lego_addr)
        pre_lego_to_bal = _tokenOut.balanceOf(lego_addr)

        instruction = (
            lego_id,
            _amountIn,
            _minAmountOut,
            [_tokenIn, _tokenOut],
            [_pool]
        )

        # swap
        tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, usd_value = bob_user_wallet.swapTokens([instruction], sender=bob)

        # event
        log_wallet = filter_logs(bob_user_wallet, "WalletAction")[0]
        assert log_wallet.op == 20  # multi-hop swap (or 21 for single swap)
        assert log_wallet.asset1 == _tokenIn.address
        assert log_wallet.asset2 == _tokenOut.address
        assert log_wallet.amount1 == origAmountIn
        assert log_wallet.amount2 == lastTokenOutAmount
        assert log_wallet.usdValue == usd_value
        assert log_wallet.legoId == lego_id
        assert log_wallet.signer == bob

        assert origAmountIn != 0
        assert lastTokenOutAmount != 0

        if _amountIn == MAX_UINT256:
            _test(origAmountIn, pre_user_from_bal)
        else:
            _test(origAmountIn, _amountIn)

        # lego addr should not have any leftover
        assert _tokenIn.balanceOf(lego_addr) == pre_lego_from_bal
        assert _tokenOut.balanceOf(lego_addr) == pre_lego_to_bal

        # to tokens
        _test(pre_user_to_bal + lastTokenOutAmount, _tokenOut.balanceOf(bob_user_wallet.address))

        # from tokens
        _test(pre_user_from_bal - origAmountIn, _tokenIn.balanceOf(bob_user_wallet.address))

    yield testLegoSwap


# liquidity basic


@pytest.fixture(scope="package")
def testLegoLiquidityAddedBasic(bob_user_wallet, bob, _test, lego_book):
    def testLegoLiquidityAddedBasic(
        _lego,
        _pool,
        _tokenA,
        _tokenB,
        _amountA = MAX_UINT256,
        _amountB = MAX_UINT256,
        _minAmountA = 0,
        _minAmountB = 0,
        _minLpAmount = 0,
    ):
        lp_token_addr = _lego.getLpToken(_pool.address)
        lp_token = lp_token_addr
        if lp_token_addr != ZERO_ADDRESS:
            lp_token = boa.from_etherscan(lp_token_addr)

        # pre balances
        pre_user_bal_a = _tokenA.balanceOf(bob_user_wallet)
        pre_user_bal_b = _tokenB.balanceOf(bob_user_wallet)

        # lp tokens
        pre_user_lp_bal = lp_token.balanceOf(bob_user_wallet)

        pre_lego_bal_a = _tokenA.balanceOf(_lego.address)
        pre_lego_bal_b = _tokenB.balanceOf(_lego.address)

        # add liquidity
        lego_id = lego_book.getRegId(_lego)
        lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(lego_id, _pool.address, _tokenA.address, _tokenB.address, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, sender=bob)

        # event
        log_wallet = filter_logs(bob_user_wallet, "WalletAction")[0]
        assert log_wallet.op == 30  # add liquidity
        assert log_wallet.asset1 == _tokenA.address
        assert log_wallet.asset2 == _tokenB.address
        assert log_wallet.amount1 == liqAmountA
        assert log_wallet.amount2 == liqAmountB
        assert log_wallet.usdValue == usdValue
        assert log_wallet.legoId == lego_id
        assert log_wallet.signer == bob

        assert liqAmountA != 0 or liqAmountB != 0
        assert lpAmountReceived != 0

        # lego addr should not have any leftover
        # rebasing tokens like usdm leaving a little extra
        current_lego_bal_a = _tokenA.balanceOf(_lego.address)
        if current_lego_bal_a <= 5:
            current_lego_bal_a = 0
        assert current_lego_bal_a == pre_lego_bal_a
        current_lego_bal_b = _tokenB.balanceOf(_lego.address)
        if current_lego_bal_b <= 5:
            current_lego_bal_b = 0
        assert current_lego_bal_b == pre_lego_bal_b

        # liq tokens
        _test(pre_user_bal_a - liqAmountA, _tokenA.balanceOf(bob_user_wallet.address))

        # rebasing tokens like usdm leaving a little extra
        current_user_bal_b = _tokenB.balanceOf(bob_user_wallet.address)
        if current_user_bal_b <= 5:
            current_user_bal_b = 0
        expected_user_bal_b = pre_user_bal_b - liqAmountB
        if expected_user_bal_b <= 5:
            expected_user_bal_b = 0
        _test(expected_user_bal_b, current_user_bal_b)

        # lp tokens
        _test(pre_user_lp_bal + lpAmountReceived, lp_token.balanceOf(bob_user_wallet.address))

    yield testLegoLiquidityAddedBasic


@pytest.fixture(scope="package")
def setupRemoveLiq(bob_user_wallet, bob, lego_book):
    def setupRemoveLiq(_lego, _pool, _tokenA, _tokenB, _amountA, _amountB):
        lego_id = lego_book.getRegId(_lego)
        lpAmountReceived, liqAmountA, liqAmountB, usdValue = bob_user_wallet.addLiquidity(lego_id, _pool.address, _tokenA.address, _tokenB.address, _amountA, _amountB, sender=bob)

        return lpAmountReceived, liqAmountA, liqAmountB, usdValue

    yield setupRemoveLiq


@pytest.fixture(scope="package")
def testLegoLiquidityRemovedBasic(bob_user_wallet, bob, _test, lego_book):
    def testLegoLiquidityRemovedBasic(
        _lego,
        _pool,
        _tokenA,
        _tokenB,
        _liqToRemove = MAX_UINT256,
        _minAmountA = 0,
        _minAmountB = 0,
    ):
        lp_token_addr = _lego.getLpToken(_pool.address)
        lp_token = lp_token_addr
        if lp_token_addr != ZERO_ADDRESS:
            lp_token = boa.from_etherscan(lp_token_addr)

        tokenAddrB = ZERO_ADDRESS
        if _tokenB != ZERO_ADDRESS:
            tokenAddrB = _tokenB.address

        # pre balances
        pre_user_bal_a = _tokenA.balanceOf(bob_user_wallet)
        pre_user_bal_b = 0
        if _tokenB != ZERO_ADDRESS:
            pre_user_bal_b = _tokenB.balanceOf(bob_user_wallet)

        # lp tokens
        pre_user_lp_bal = lp_token.balanceOf(bob_user_wallet)

        pre_lego_bal_a = _tokenA.balanceOf(_lego.address)
        pre_lego_bal_b = 0
        if _tokenB != ZERO_ADDRESS:
            pre_lego_bal_b = _tokenB.balanceOf(_lego.address)

        # remove liquidity
        lego_id = lego_book.getRegId(_lego)
        removedAmountA, removedAmountB, lpAmountBurned, usdValue = bob_user_wallet.removeLiquidity(lego_id, _pool, _tokenA, tokenAddrB, lp_token_addr, _liqToRemove, _minAmountA, _minAmountB, sender=bob)

        # event
        log_wallet = filter_logs(bob_user_wallet, "WalletAction")[0]
        assert log_wallet.op == 31  # remove liquidity
        assert log_wallet.asset1 == _tokenA.address
        assert log_wallet.asset2 == tokenAddrB
        assert log_wallet.amount1 == removedAmountA
        assert log_wallet.amount2 == removedAmountB
        assert log_wallet.usdValue == usdValue
        assert log_wallet.legoId == lego_id
        assert log_wallet.signer == bob

        assert removedAmountA != 0 or removedAmountB != 0

        # lego addr should not have any leftover
        assert _tokenA.balanceOf(_lego.address) == pre_lego_bal_a
        if _tokenB != ZERO_ADDRESS:
            assert _tokenB.balanceOf(_lego.address) == pre_lego_bal_b

        # liq tokens
        _test(pre_user_bal_a + removedAmountA, _tokenA.balanceOf(bob_user_wallet.address))
        if _tokenB != ZERO_ADDRESS:
            _test(pre_user_bal_b + removedAmountB, _tokenB.balanceOf(bob_user_wallet.address))

        # lp tokens
        _test(pre_user_lp_bal - lpAmountBurned, lp_token.balanceOf(bob_user_wallet.address))

    yield testLegoLiquidityRemovedBasic


# liquidity concentrated (nfts)


@pytest.fixture(scope="package")
def testLegoLiquidityAdded(bob_user_wallet, bob, _test, lego_book):
    def testLegoLiquidityAdded(
        _lego,
        _nftAddr,
        _nftTokenId,
        _pool,
        _tokenA,
        _tokenB,
        _amountA = MAX_UINT256,
        _amountB = MAX_UINT256,
        _tickLower = MIN_INT24,
        _tickUpper = MAX_INT24,
        _minAmountA = 0,
        _minAmountB = 0,
    ):
        # pre balances
        pre_user_bal_a = _tokenA.balanceOf(bob_user_wallet)
        pre_user_bal_b = _tokenB.balanceOf(bob_user_wallet)

        pre_nft_bal = _nftAddr.balanceOf(bob_user_wallet)          

        pre_lego_bal_a = _tokenA.balanceOf(_lego.address)
        pre_lego_bal_b = _tokenB.balanceOf(_lego.address)

        # add liquidity
        lego_id = lego_book.getRegId(_lego)
        liquidityAdded, liqAmountA, liqAmountB, nftTokenId, usdValue = bob_user_wallet.addLiquidityConcentrated(lego_id, _nftAddr, _nftTokenId, _pool.address, _tokenA.address, _tokenB.address, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, sender=bob)

        # event
        log_wallet = filter_logs(bob_user_wallet, "WalletActionExt")[0]
        assert log_wallet.op == 32  # add liquidity NFT
        assert log_wallet.asset1 == _tokenA.address
        assert log_wallet.asset2 == _tokenB.address
        assert log_wallet.tokenId == nftTokenId
        assert log_wallet.amount1 == liqAmountA
        assert log_wallet.amount2 == liqAmountB
        assert log_wallet.usdValue == usdValue

        assert liqAmountA != 0 or liqAmountB != 0
        assert liquidityAdded != 0

        # lego addr should not have any leftover
        # rebasing tokens like usdm leaving a little extra
        current_lego_bal_a = _tokenA.balanceOf(_lego.address)
        if current_lego_bal_a <= 5:
            current_lego_bal_a = 0
        assert current_lego_bal_a == pre_lego_bal_a
        current_lego_bal_b = _tokenB.balanceOf(_lego.address)
        if current_lego_bal_b <= 5:
            current_lego_bal_b = 0
        assert current_lego_bal_b == pre_lego_bal_b

        # liq tokens
        _test(pre_user_bal_a - liqAmountA, _tokenA.balanceOf(bob_user_wallet.address))

        # rebasing tokens like usdm leaving a little extra
        current_user_bal_b = _tokenB.balanceOf(bob_user_wallet.address)
        if current_user_bal_b <= 5:
            current_user_bal_b = 0
        expected_user_bal_b = pre_user_bal_b - liqAmountB
        if expected_user_bal_b <= 5:
            expected_user_bal_b = 0
        _test(expected_user_bal_b, current_user_bal_b)

        # nft stuff
        assert _nftAddr.balanceOf(_lego.address) == 0

        if _nftTokenId == 0:
            assert _nftAddr.balanceOf(bob_user_wallet.address) == pre_nft_bal + 1
        else:
            # same nft balance
            assert _nftAddr.balanceOf(bob_user_wallet.address) == pre_nft_bal

        return nftTokenId

    yield testLegoLiquidityAdded


@pytest.fixture(scope="package")
def testLegoLiquidityRemoved(bob_user_wallet, bob, _test, lego_book):
    def testLegoLiquidityRemoved(
        _lego,
        _nftAddr,
        _nftTokenId,
        _pool,
        _tokenA,
        _tokenB,
        _liqToRemove = MAX_UINT256,
        _minAmountA = 0,
        _minAmountB = 0,
    ):

        tokenAddrB = ZERO_ADDRESS
        if _tokenB != ZERO_ADDRESS:
            tokenAddrB = _tokenB.address

        # pre balances
        pre_user_bal_a = _tokenA.balanceOf(bob_user_wallet)
        pre_user_bal_b = 0
        if _tokenB != ZERO_ADDRESS:
            pre_user_bal_b = _tokenB.balanceOf(bob_user_wallet)

        # pre nft balance
        pre_nft_bal = _nftAddr.balanceOf(bob_user_wallet)

        pre_lego_bal_a = _tokenA.balanceOf(_lego.address)
        pre_lego_bal_b = 0
        if _tokenB != ZERO_ADDRESS:
            pre_lego_bal_b = _tokenB.balanceOf(_lego.address)

        # remove liquidity
        lego_id = lego_book.getRegId(_lego)
        removedAmountA, removedAmountB, liqRemoved, usdValue = bob_user_wallet.removeLiquidityConcentrated(lego_id, _nftAddr, _nftTokenId, _pool.address, _tokenA.address, tokenAddrB, _liqToRemove, _minAmountA, _minAmountB, sender=bob)

        # event
        log_wallet = filter_logs(bob_user_wallet, "WalletActionExt")[0]
        assert log_wallet.op == 33  # remove liquidity NFT
        assert log_wallet.asset1 == _tokenA.address
        assert log_wallet.asset2 == tokenAddrB
        assert log_wallet.tokenId == _nftTokenId
        assert log_wallet.amount1 == removedAmountA
        assert log_wallet.amount2 == removedAmountB
        assert log_wallet.usdValue == usdValue

        assert removedAmountA != 0 or removedAmountB != 0

        # lego addr should not have any leftover
        assert _tokenA.balanceOf(_lego.address) == pre_lego_bal_a
        if _tokenB != ZERO_ADDRESS:
            assert _tokenB.balanceOf(_lego.address) == pre_lego_bal_b

        # liq tokens
        _test(pre_user_bal_a + removedAmountA, _tokenA.balanceOf(bob_user_wallet.address))
        if _tokenB != ZERO_ADDRESS:
            _test(pre_user_bal_b + removedAmountB, _tokenB.balanceOf(bob_user_wallet.address))

        assert _nftAddr.balanceOf(_lego.address) == 0

        if _liqToRemove == MAX_UINT256:
            assert _nftAddr.balanceOf(bob_user_wallet.address) == pre_nft_bal - 1
        else:
            # same nft balance
            assert _nftAddr.balanceOf(bob_user_wallet.address) == pre_nft_bal


    yield testLegoLiquidityRemoved


# utils


def aliased(env, addr, alias):
    env.alias(addr, alias)
    return addr


@pytest.fixture(scope="session")
def getTokenAndWhale(fork, env, alpha_token, alpha_token_whale):
    def getTokenAndWhale(_token_str):
        if fork == "local":
            if _token_str == "ALPHA":
                return alpha_token, alpha_token_whale
            else:
                pytest.skip("asset not relevant on this fork")
        elif _token_str == "ALPHA":
            pytest.skip("asset not relevant on this fork")

        token = TOKENS[fork][_token_str]
        whale = WHALES[fork][_token_str]
        return boa.from_etherscan(token, name=_token_str), aliased(env, whale, _token_str + "_whale")

    yield getTokenAndWhale
