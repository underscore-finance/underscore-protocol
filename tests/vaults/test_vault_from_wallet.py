import pytest
import boa

from contracts.core.userWallet import UserWalletConfig
from constants import EIGHTEEN_DECIMALS, MAX_UINT256
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def prepareAssetForWalletTx(user_wallet, yield_underlying_token, yield_underlying_token_whale, mock_ripe, switchboard_alpha):
    def prepareAssetForWalletTx(
        _asset = yield_underlying_token,
        _amount = 100 * EIGHTEEN_DECIMALS,
        _whale = yield_underlying_token_whale,
        _user_wallet = user_wallet,
        _price = 1 * EIGHTEEN_DECIMALS,
        _shouldCheckYield = False,
    ):
        # set price
        mock_ripe.setPrice(_asset, _price)

        # transfer asset to wallet
        _asset.transfer(_user_wallet, _amount, sender=_whale)

        # make sure asset is registered
        wallet_config = UserWalletConfig.at(_user_wallet.walletConfig())
        wallet_config.updateAssetData(
            0,
            _asset,
            _shouldCheckYield,
            sender = switchboard_alpha.address
        )
        return _amount

    yield prepareAssetForWalletTx


#####################
# Deposit for Yield #
#####################


def test_deposit_underscore_lego_basic(prepareAssetForWalletTx, lego_book, lego_underscore, user_wallet, bob, yield_underlying_token, undy_usd_vault, vault_registry, switchboard_alpha):
    deposit_amount = prepareAssetForWalletTx()

    # set approved lego
    lego_id = lego_book.getRegId(lego_underscore)
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)


    # get initial price per share from vault
    initial_price_per_share = undy_usd_vault.convertToAssets(EIGHTEEN_DECIMALS)
    
    # deposit for yield
    asset_deposited, vault_token, vault_tokens_received, usd_value = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        undy_usd_vault.address,
        deposit_amount,
        sender=bob
    )

    # verify event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 10  # EARN_DEPOSIT operation
    assert log.asset1 == yield_underlying_token.address
    assert log.asset2 == undy_usd_vault.address
    assert log.amount1 == deposit_amount
    assert log.amount2 == vault_tokens_received
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob

    # verify return values
    assert asset_deposited == deposit_amount
    assert vault_token == undy_usd_vault.address
    assert vault_tokens_received > 0
    assert usd_value == 100 * EIGHTEEN_DECIMALS  # 100 tokens * 1 USD
    
    # verify balances
    assert yield_underlying_token.balanceOf(user_wallet) == 0
    assert undy_usd_vault.balanceOf(user_wallet) == vault_tokens_received
        
    # verify vault token is tracked as yield asset
    vault_data = user_wallet.assetData(undy_usd_vault.address)
    assert vault_data.assetBalance == vault_tokens_received
    assert vault_data.isYieldAsset == True
    assert vault_data.lastPricePerShare == initial_price_per_share
    assert vault_data.usdValue > 0
    
    # verify underlying token data updated
    underlying_data = user_wallet.assetData(yield_underlying_token.address)
    assert underlying_data.assetBalance == 0


def test_deposit_with_max_value(prepareAssetForWalletTx, lego_book, lego_underscore, user_wallet, bob, yield_underlying_token, undy_usd_vault, vault_registry, switchboard_alpha):
    """Test deposit with max_value deposits entire balance"""

    deposit_amount = prepareAssetForWalletTx(
        _amount=75 * EIGHTEEN_DECIMALS,
        _price=5 * EIGHTEEN_DECIMALS
    )

    # set approved lego
    lego_id = lego_book.getRegId(lego_underscore)
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)

    # deposit using max_value
    asset_deposited, vault_token, vault_tokens_received, usd_value = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        undy_usd_vault.address,
        MAX_UINT256,  # max value to deposit entire balance
        sender=bob
    )

    # verify entire balance was deposited
    assert asset_deposited == deposit_amount
    assert usd_value == 375 * EIGHTEEN_DECIMALS  # 75 * 5
    assert yield_underlying_token.balanceOf(user_wallet) == 0
    assert undy_usd_vault.balanceOf(user_wallet) == vault_tokens_received


def test_deposit_multiple_sequential(prepareAssetForWalletTx, lego_book, lego_underscore, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, undy_usd_vault, vault_registry, switchboard_alpha):
    """Test multiple deposits accumulate vault tokens correctly"""

    lego_id = lego_book.getRegId(lego_underscore)
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)

    # first deposit
    deposit1_amount = prepareAssetForWalletTx(
        _amount=50 * EIGHTEEN_DECIMALS,
        _price=8 * EIGHTEEN_DECIMALS
    )

    _, _, vault_tokens1, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        undy_usd_vault.address,
        deposit1_amount,
        sender=bob
    )

    # verify first deposit
    assert undy_usd_vault.balanceOf(user_wallet) == vault_tokens1
    vault_data = user_wallet.assetData(undy_usd_vault.address)
    assert vault_data.assetBalance == vault_tokens1
    assert vault_data.isYieldAsset == True
    first_price_per_share = vault_data.lastPricePerShare

    # second deposit
    deposit2_amount = 30 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, deposit2_amount, sender=yield_underlying_token_whale)

    _, _, vault_tokens2, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        undy_usd_vault.address,
        deposit2_amount,
        sender=bob
    )

    # verify accumulated balance
    total_vault_tokens = vault_tokens1 + vault_tokens2
    assert undy_usd_vault.balanceOf(user_wallet) == total_vault_tokens

    # verify storage updated correctly
    vault_data = user_wallet.assetData(undy_usd_vault.address)
    assert vault_data.assetBalance == total_vault_tokens
    assert vault_data.isYieldAsset == True

    # third deposit
    deposit3_amount = 20 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, deposit3_amount, sender=yield_underlying_token_whale)

    _, _, vault_tokens3, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        undy_usd_vault.address,
        deposit3_amount,
        sender=bob
    )

    # verify final state
    final_total = vault_tokens1 + vault_tokens2 + vault_tokens3
    assert undy_usd_vault.balanceOf(user_wallet) == final_total
    vault_data = user_wallet.assetData(undy_usd_vault.address)
    assert vault_data.assetBalance == final_total


def test_deposit_amount_exceeding_balance(prepareAssetForWalletTx, lego_book, lego_underscore, user_wallet, bob, yield_underlying_token, undy_usd_vault, vault_registry, switchboard_alpha):
    """Test deposit with amount exceeding balance deposits available balance only"""

    deposit_amount = prepareAssetForWalletTx(
        _amount=100 * EIGHTEEN_DECIMALS,
        _price=2 * EIGHTEEN_DECIMALS
    )

    lego_id = lego_book.getRegId(lego_underscore)
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)

    # attempt to deposit more than balance
    requested_amount = deposit_amount + 1000 * EIGHTEEN_DECIMALS
    asset_deposited, _, vault_tokens_received, usd_value = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        undy_usd_vault.address,
        requested_amount,
        sender=bob
    )

    # should deposit only the available balance
    assert asset_deposited == deposit_amount
    assert usd_value == 200 * EIGHTEEN_DECIMALS  # 100 * 2
    assert yield_underlying_token.balanceOf(user_wallet) == 0
    assert undy_usd_vault.balanceOf(user_wallet) == vault_tokens_received


def test_deposit_zero_amount_fails(prepareAssetForWalletTx, lego_book, lego_underscore, user_wallet, bob, yield_underlying_token, undy_usd_vault, vault_registry, switchboard_alpha):
    """Test that depositing zero amount fails"""

    prepareAssetForWalletTx()

    lego_id = lego_book.getRegId(lego_underscore)
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)

    # attempt to deposit 0 amount should fail
    with boa.reverts():
        user_wallet.depositForYield(
            lego_id,
            yield_underlying_token.address,
            undy_usd_vault.address,
            0,
            sender=bob
        )


#######################
# Withdraw from Yield #
#######################


@pytest.fixture(scope="module")
def setupUnderscoreYieldPosition(prepareAssetForWalletTx, lego_book, lego_underscore, user_wallet, bob, yield_underlying_token, undy_usd_vault, vault_registry, switchboard_alpha):
    """Setup fixture that deposits into Underscore vault and returns vault tokens"""
    def setupUnderscoreYieldPosition(
        _deposit_amount=100 * EIGHTEEN_DECIMALS,
        _underlying_price=1 * EIGHTEEN_DECIMALS,
    ):
        # prepare underlying tokens
        deposit_amount = prepareAssetForWalletTx(
            _amount=_deposit_amount,
            _price=_underlying_price
        )

        # set approved lego
        lego_id = lego_book.getRegId(lego_underscore)
        vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)

        # deposit to get vault tokens
        _, _, vault_tokens_received, _ = user_wallet.depositForYield(
            lego_id,
            yield_underlying_token.address,
            undy_usd_vault.address,
            deposit_amount,
            sender=bob
        )

        return vault_tokens_received, lego_id

    yield setupUnderscoreYieldPosition


def test_withdraw_basic(setupUnderscoreYieldPosition, user_wallet, bob, yield_underlying_token, undy_usd_vault):
    """Test basic withdrawal from Underscore Earn Vault"""

    vault_tokens, lego_id = setupUnderscoreYieldPosition()

    # verify initial state
    assert undy_usd_vault.balanceOf(user_wallet) == vault_tokens
    assert yield_underlying_token.balanceOf(user_wallet) == 0

    # withdraw half
    withdraw_amount = vault_tokens // 2
    vault_burned, underlying_asset, underlying_received, usd_value = user_wallet.withdrawFromYield(
        lego_id,
        undy_usd_vault.address,
        withdraw_amount,
        sender=bob
    )

    # verify event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 11  # EARN_WITHDRAW operation
    assert log.asset1 == undy_usd_vault.address
    assert log.asset2 == yield_underlying_token.address
    assert log.amount1 == withdraw_amount == vault_burned
    assert log.amount2 == underlying_received
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob

    # verify return values
    assert vault_burned == withdraw_amount
    assert underlying_asset == yield_underlying_token.address
    assert underlying_received > 0
    assert usd_value > 0

    # verify balances
    assert undy_usd_vault.balanceOf(user_wallet) == vault_tokens - withdraw_amount
    assert yield_underlying_token.balanceOf(user_wallet) == underlying_received

    # verify storage updated
    vault_data = user_wallet.assetData(undy_usd_vault.address)
    assert vault_data.assetBalance == vault_tokens - withdraw_amount

    underlying_data = user_wallet.assetData(yield_underlying_token.address)
    assert underlying_data.assetBalance == underlying_received
    assert underlying_data.isYieldAsset == False

    # verify underlying asset is registered
    assert user_wallet.indexOfAsset(yield_underlying_token.address) > 0


def test_withdraw_entire_balance(setupUnderscoreYieldPosition, user_wallet, bob, yield_underlying_token, undy_usd_vault):
    """Test withdrawing entire position deregisters vault token"""

    vault_tokens, lego_id = setupUnderscoreYieldPosition()

    # verify vault token is registered
    vault_index_before = user_wallet.indexOfAsset(undy_usd_vault.address)
    assert vault_index_before > 0

    # withdraw entire balance
    vault_burned, underlying_asset, underlying_received, _ = user_wallet.withdrawFromYield(
        lego_id,
        undy_usd_vault.address,
        vault_tokens,
        sender=bob
    )

    # verify all vault tokens burned
    assert vault_burned == vault_tokens
    assert undy_usd_vault.balanceOf(user_wallet) == 0
    assert underlying_received > 0

    # verify vault token deregistered
    assert user_wallet.indexOfAsset(undy_usd_vault.address) == 0
    vault_data = user_wallet.assetData(undy_usd_vault.address)
    assert vault_data.assetBalance == 0
    assert vault_data.usdValue == 0

    # verify underlying registered and has balance
    assert user_wallet.indexOfAsset(yield_underlying_token.address) > 0
    assert yield_underlying_token.balanceOf(user_wallet) == underlying_received


def test_withdraw_with_max_value(setupUnderscoreYieldPosition, user_wallet, bob, yield_underlying_token, undy_usd_vault):
    """Test withdrawing with max_value withdraws entire balance"""

    vault_tokens, lego_id = setupUnderscoreYieldPosition()

    # withdraw with max_value
    vault_burned, _, underlying_received, _ = user_wallet.withdrawFromYield(
        lego_id,
        undy_usd_vault.address,
        MAX_UINT256,  # max value
        sender=bob
    )

    # verify entire balance withdrawn
    assert vault_burned == vault_tokens
    assert undy_usd_vault.balanceOf(user_wallet) == 0
    assert yield_underlying_token.balanceOf(user_wallet) == underlying_received


def test_withdraw_multiple_sequential(setupUnderscoreYieldPosition, user_wallet, bob, yield_underlying_token, undy_usd_vault):
    """Test multiple sequential withdrawals"""

    # setup position with 90 tokens (divisible by 3)
    vault_tokens, lego_id = setupUnderscoreYieldPosition(_deposit_amount=90 * EIGHTEEN_DECIMALS)

    # first withdrawal - 1/3
    withdraw1 = vault_tokens // 3
    _, _, underlying1, _ = user_wallet.withdrawFromYield(
        lego_id,
        undy_usd_vault.address,
        withdraw1,
        sender=bob
    )

    assert undy_usd_vault.balanceOf(user_wallet) == vault_tokens - withdraw1
    assert yield_underlying_token.balanceOf(user_wallet) == underlying1

    # second withdrawal - another 1/3
    withdraw2 = vault_tokens // 3
    _, _, underlying2, _ = user_wallet.withdrawFromYield(
        lego_id,
        undy_usd_vault.address,
        withdraw2,
        sender=bob
    )

    assert undy_usd_vault.balanceOf(user_wallet) == vault_tokens - withdraw1 - withdraw2
    assert yield_underlying_token.balanceOf(user_wallet) == underlying1 + underlying2

    # final withdrawal - remaining balance
    _, _, underlying3, _ = user_wallet.withdrawFromYield(
        lego_id,
        undy_usd_vault.address,
        MAX_UINT256,  # withdraw all remaining
        sender=bob
    )

    # verify all withdrawn
    assert undy_usd_vault.balanceOf(user_wallet) == 0
    total_underlying = underlying1 + underlying2 + underlying3
    assert yield_underlying_token.balanceOf(user_wallet) == total_underlying

    # verify vault token deregistered
    assert user_wallet.indexOfAsset(undy_usd_vault.address) == 0


def test_withdraw_zero_amount_fails(setupUnderscoreYieldPosition, user_wallet, bob, undy_usd_vault):
    """Test that withdrawing zero amount fails"""

    vault_tokens, lego_id = setupUnderscoreYieldPosition()

    # attempt to withdraw 0 amount should fail
    with boa.reverts():
        user_wallet.withdrawFromYield(
            lego_id,
            undy_usd_vault.address,
            0,
            sender=bob
        )


def test_withdraw_amount_exceeding_balance(setupUnderscoreYieldPosition, user_wallet, bob, yield_underlying_token, undy_usd_vault):
    """Test withdrawing amount exceeding balance withdraws available balance only"""

    vault_tokens, lego_id = setupUnderscoreYieldPosition()

    # attempt to withdraw more than balance
    requested_amount = vault_tokens + 1000 * EIGHTEEN_DECIMALS
    vault_burned, _, underlying_received, _ = user_wallet.withdrawFromYield(
        lego_id,
        undy_usd_vault.address,
        requested_amount,
        sender=bob
    )

    # should withdraw only the available balance
    assert vault_burned == vault_tokens
    assert undy_usd_vault.balanceOf(user_wallet) == 0
    assert yield_underlying_token.balanceOf(user_wallet) == underlying_received


def test_deposit_and_withdraw_cycle(prepareAssetForWalletTx, lego_book, lego_underscore, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, undy_usd_vault, vault_registry, switchboard_alpha):
    """Test multiple deposit/withdraw cycles"""

    lego_id = lego_book.getRegId(lego_underscore)
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)

    # Cycle 1: Deposit and partial withdraw
    deposit1 = prepareAssetForWalletTx(_amount=100 * EIGHTEEN_DECIMALS)
    _, _, vault_tokens1, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        undy_usd_vault.address,
        deposit1,
        sender=bob
    )

    # partial withdraw
    _, _, underlying1, _ = user_wallet.withdrawFromYield(
        lego_id,
        undy_usd_vault.address,
        vault_tokens1 // 2,
        sender=bob
    )

    remaining_vault_tokens = undy_usd_vault.balanceOf(user_wallet)
    assert remaining_vault_tokens > 0

    # Cycle 2: Deposit again (now have both underlying and vault tokens)
    deposit2 = 50 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, deposit2, sender=yield_underlying_token_whale)
    _, _, vault_tokens2, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        undy_usd_vault.address,
        deposit2,
        sender=bob
    )

    total_vault_tokens = remaining_vault_tokens + vault_tokens2
    assert undy_usd_vault.balanceOf(user_wallet) == total_vault_tokens

    # Cycle 3: Withdraw everything
    user_wallet.withdrawFromYield(
        lego_id,
        undy_usd_vault.address,
        MAX_UINT256,
        sender=bob
    )

    assert undy_usd_vault.balanceOf(user_wallet) == 0
    assert yield_underlying_token.balanceOf(user_wallet) > underlying1


def test_vault_asset_data_tracking(prepareAssetForWalletTx, lego_book, lego_underscore, user_wallet, bob, yield_underlying_token, undy_usd_vault, vault_registry, switchboard_alpha):
    """Test vault asset data is properly tracked with isYieldAsset and lastPricePerShare"""

    deposit_amount = prepareAssetForWalletTx(
        _amount=100 * EIGHTEEN_DECIMALS,
        _price=10 * EIGHTEEN_DECIMALS
    )

    # verify vault token not tracked before deposit
    initial_vault_data = user_wallet.assetData(undy_usd_vault.address)
    assert initial_vault_data.assetBalance == 0
    assert initial_vault_data.isYieldAsset == False
    assert initial_vault_data.lastPricePerShare == 0

    # get vault's current price per share
    current_price_per_share = undy_usd_vault.convertToAssets(EIGHTEEN_DECIMALS)

    # deposit
    lego_id = lego_book.getRegId(lego_underscore)
    vault_registry.setApprovedYieldLego(undy_usd_vault.address, lego_id, True, sender=switchboard_alpha.address)

    _, _, vault_tokens_received, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        undy_usd_vault.address,
        deposit_amount,
        sender=bob
    )

    # verify vault token is now tracked as yield asset
    vault_data = user_wallet.assetData(undy_usd_vault.address)
    assert vault_data.assetBalance == vault_tokens_received
    assert vault_data.isYieldAsset == True
    assert vault_data.lastPricePerShare == current_price_per_share
    assert vault_data.usdValue > 0

    # verify vault token added to assets array
    vault_index = user_wallet.indexOfAsset(undy_usd_vault.address)
    assert vault_index > 0
    assert user_wallet.assets(vault_index) == undy_usd_vault.address