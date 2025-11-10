import pytest
import boa

from contracts.core.userWallet import UserWalletConfig
from constants import EIGHTEEN_DECIMALS, MAX_UINT256
from conf_utils import filter_logs
from config.BluePrint import TOKENS


@pytest.fixture(scope="module")
def prepareAssetForWalletTx(user_wallet, alpha_token, alpha_token_whale, mock_ripe, switchboard_alpha):
    def prepareAssetForWalletTx(
        _asset = alpha_token,
        _amount = 100 * EIGHTEEN_DECIMALS,
        _whale = alpha_token_whale,
        _user_wallet = user_wallet,
        _price = 2 * EIGHTEEN_DECIMALS,
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


def test_prepare_asset_for_wallet_tx_fixture(prepareAssetForWalletTx, alpha_token, user_wallet):
    """Test prepareAssetForWalletTx fixture"""

    amount = prepareAssetForWalletTx()

    # balance
    assert alpha_token.balanceOf(user_wallet) == amount

    # storage
    data = user_wallet.assetData(alpha_token.address)
    assert data.assetBalance == amount
    assert data.usdValue == 200 * EIGHTEEN_DECIMALS
    assert data.isYieldAsset == False
    assert data.lastPricePerShare == 0

    assert user_wallet.assets(1) == alpha_token.address
    assert user_wallet.indexOfAsset(alpha_token.address) == 1
    assert user_wallet.numAssets() == 2


##################
# Transfer Funds #
##################


def test_user_wallet_transfer_funds(prepareAssetForWalletTx, user_wallet, bob, alpha_token):
    """Test basic transfer of funds"""

    original_amount = prepareAssetForWalletTx()

    # transfer funds
    transfer_amount = 50 * EIGHTEEN_DECIMALS
    actual_transfer_amount, usd_value = user_wallet.transferFunds(bob, alpha_token.address, transfer_amount, sender=bob)

    # event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 1
    assert log.asset1 == alpha_token.address
    assert log.asset2 == bob
    assert log.amount1 == transfer_amount == actual_transfer_amount
    assert log.amount2 == 0
    assert log.usdValue == usd_value == 100 * EIGHTEEN_DECIMALS
    assert log.legoId == 0
    assert log.signer == bob

    # storage
    data = user_wallet.assetData(alpha_token.address)
    assert data.assetBalance == original_amount - transfer_amount
    assert data.usdValue == usd_value
    assert data.isYieldAsset == False
    assert data.lastPricePerShare == 0

    # balances
    assert alpha_token.balanceOf(user_wallet) == original_amount - transfer_amount
    assert alpha_token.balanceOf(bob) == transfer_amount


def test_transfer_entire_balance_with_max_value(prepareAssetForWalletTx, user_wallet, bob, alpha_token):
    """Test transferring entire balance using max_value(uint256)"""
    
    original_amount = prepareAssetForWalletTx()
    
    # transfer using max_value to transfer entire balance
    actual_transfer_amount, usd_value = user_wallet.transferFunds(
        bob, 
        alpha_token.address, 
        MAX_UINT256,
        sender=bob
    )
    
    # should transfer entire balance
    assert actual_transfer_amount == original_amount
    assert usd_value == 200 * EIGHTEEN_DECIMALS
    
    # wallet should be empty
    assert alpha_token.balanceOf(user_wallet) == 0
    assert alpha_token.balanceOf(bob) == original_amount
    
    # storage should reflect empty balance
    data = user_wallet.assetData(alpha_token.address)
    assert data.assetBalance == 0


def test_transfer_eth_native_token(user_wallet, bob, fork, mock_ripe):
    """Test transferring ETH (native token)"""
    
    # send ETH to wallet
    eth_amount = 1 * EIGHTEEN_DECIMALS
    boa.env.set_balance(user_wallet.address, eth_amount)
    
    # set ETH price
    ETH = TOKENS[fork]["ETH"]
    mock_ripe.setPrice(ETH, 2000 * EIGHTEEN_DECIMALS)
    
    # get initial balances
    initial_wallet_balance = boa.env.get_balance(user_wallet.address)
    initial_bob_balance = boa.env.get_balance(bob)
    
    # transfer ETH 
    transfer_amount = int(0.5 * EIGHTEEN_DECIMALS) # 0.5 ETH
    actual_transfer_amount, usd_value = user_wallet.transferFunds(
        bob,
        ETH,
        transfer_amount,
        sender=bob
    )

    # verify event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 1
    assert log.asset1 == ETH
    assert log.asset2 == bob
    assert log.amount1 == transfer_amount
    assert log.amount2 == 0
    assert log.usdValue == usd_value
    assert log.legoId == 0
    assert log.signer == bob
    
    # verify transfer amount and USD value
    assert actual_transfer_amount == transfer_amount
    assert usd_value == 1000 * EIGHTEEN_DECIMALS  # 0.5 ETH * 2000 USD/ETH
    
    # verify balances
    assert boa.env.get_balance(user_wallet.address) == initial_wallet_balance - transfer_amount
    assert boa.env.get_balance(bob) == initial_bob_balance + transfer_amount
    

def test_transfer_zero_amount_fails(prepareAssetForWalletTx, user_wallet, bob, alpha_token):
    """Test that transferring zero amount fails"""
    
    prepareAssetForWalletTx()
    
    # attempt to transfer 0 amount should fail
    with boa.reverts("no amt"):
        user_wallet.transferFunds(
            bob,
            alpha_token.address,
            0,
            sender=bob
        )


def test_transfer_amount_exceeding_balance(prepareAssetForWalletTx, user_wallet, bob, alpha_token):
    """Test transferring amount that exceeds balance - should transfer available balance"""
    
    original_amount = prepareAssetForWalletTx()
    
    # attempt to transfer more than balance - should transfer available balance only
    requested_amount = original_amount + 1000 * EIGHTEEN_DECIMALS
    actual_transfer_amount, usd_value = user_wallet.transferFunds(
        bob,
        alpha_token.address,
        requested_amount,
        sender=bob
    )
    
    # should transfer only the available balance
    assert actual_transfer_amount == original_amount
    assert usd_value == 200 * EIGHTEEN_DECIMALS
    
    # wallet should be empty
    assert alpha_token.balanceOf(user_wallet) == 0
    assert alpha_token.balanceOf(bob) == original_amount


def test_multiple_sequential_transfers(prepareAssetForWalletTx, user_wallet, bob, alpha_token):
    """Test multiple sequential transfers to same recipient update balances correctly"""
    
    original_amount = prepareAssetForWalletTx()
    
    # first transfer to bob
    transfer1_amount = 30 * EIGHTEEN_DECIMALS
    actual_transfer1, usd_value1 = user_wallet.transferFunds(
        bob,
        alpha_token.address,
        transfer1_amount,
        sender=bob
    )
    
    assert actual_transfer1 == transfer1_amount
    assert alpha_token.balanceOf(user_wallet) == original_amount - transfer1_amount
    assert alpha_token.balanceOf(bob) == transfer1_amount
    
    # second transfer to bob
    transfer2_amount = 20 * EIGHTEEN_DECIMALS
    actual_transfer2, usd_value2 = user_wallet.transferFunds(
        bob,
        alpha_token.address,
        transfer2_amount,
        sender=bob
    )
    
    assert actual_transfer2 == transfer2_amount
    assert alpha_token.balanceOf(user_wallet) == original_amount - transfer1_amount - transfer2_amount
    assert alpha_token.balanceOf(bob) == transfer1_amount + transfer2_amount
    
    # third transfer to bob
    transfer3_amount = 25 * EIGHTEEN_DECIMALS
    actual_transfer3, usd_value3 = user_wallet.transferFunds(
        bob,
        alpha_token.address,
        transfer3_amount,
        sender=bob
    )
    
    assert actual_transfer3 == transfer3_amount
    assert alpha_token.balanceOf(user_wallet) == original_amount - transfer1_amount - transfer2_amount - transfer3_amount
    assert alpha_token.balanceOf(bob) == transfer1_amount + transfer2_amount + transfer3_amount
    
    # verify final storage state
    data = user_wallet.assetData(alpha_token.address)
    assert data.assetBalance == 25 * EIGHTEEN_DECIMALS  # 100 - 30 - 20 - 25 = 25


def test_transfer_funds_trusted_tx_only_wallet_config(prepareAssetForWalletTx, user_wallet, bob, alice, alpha_token):
    """Test that only UserWalletConfig can call transferFunds with _isTrustedTx=True"""
    
    # prepare tokens
    original_amount = prepareAssetForWalletTx()
    
    # attempt to call transferFunds with _isTrustedTx=True from non-config address
    with boa.reverts("perms"):
        user_wallet.transferFunds(
            alice,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            False,
            True,  # _isTrustedTx = True
            sender=bob  # owner trying to call with trusted tx
        )
    
    # also test with non-owner
    with boa.reverts("perms"):
        user_wallet.transferFunds(
            alice,
            alpha_token.address,
            50 * EIGHTEEN_DECIMALS,
            False,
            True,  # _isTrustedTx = True
            sender=alice  # non-owner trying to call with trusted tx
        )
    
    # verify no transfer happened
    assert alpha_token.balanceOf(user_wallet) == original_amount
    assert alpha_token.balanceOf(alice) == 0


#####################
# Deposit for Yield #
#####################


def test_deposit_for_yield_basic(prepareAssetForWalletTx, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token):
    """Test basic deposit for yield functionality"""
    
    # setup: prepare underlying tokens in wallet
    deposit_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _shouldCheckYield=False
    )
    
    # get initial price per share from vault
    initial_price_per_share = yield_vault_token.convertToAssets(EIGHTEEN_DECIMALS)
    
    # deposit for yield
    lego_id = 2  # mock_yield_lego is registered with id 2
    asset_deposited, vault_token, vault_tokens_received, usd_value = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=bob
    )

    # verify event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 10  # EARN_DEPOSIT operation
    assert log.asset1 == yield_underlying_token.address
    assert log.asset2 == yield_vault_token.address
    assert log.amount1 == deposit_amount
    assert log.amount2 == vault_tokens_received
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob

    # verify return values
    assert asset_deposited == deposit_amount
    assert vault_token == yield_vault_token.address
    assert vault_tokens_received > 0
    assert usd_value == 1000 * EIGHTEEN_DECIMALS  # 100 tokens * 10 USD
    
    # verify balances
    assert yield_underlying_token.balanceOf(user_wallet) == 0
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens_received
        
    # verify vault token is tracked as yield asset
    vault_data = user_wallet.assetData(yield_vault_token.address)
    assert vault_data.assetBalance == vault_tokens_received
    assert vault_data.isYieldAsset == True
    assert vault_data.lastPricePerShare == initial_price_per_share
    assert vault_data.usdValue > 0
    
    # verify underlying token data updated
    underlying_data = user_wallet.assetData(yield_underlying_token.address)
    assert underlying_data.assetBalance == 0


def test_deposit_for_yield_max_value(prepareAssetForWalletTx, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token):
    """Test depositForYield with max_value deposits entire balance"""
    
    # setup: prepare underlying tokens in wallet
    actual_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=75 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=5 * EIGHTEEN_DECIMALS,
        _shouldCheckYield=False
    )
    
    # deposit using max_value
    lego_id = 2
    asset_deposited, vault_token, vault_tokens_received, usd_value = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        MAX_UINT256,  # max value to deposit entire balance
        sender=bob
    )
    
    # verify entire balance was deposited
    assert asset_deposited == actual_amount
    assert usd_value == 375 * EIGHTEEN_DECIMALS  # 75 * 5
    assert yield_underlying_token.balanceOf(user_wallet) == 0
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens_received


def test_multiple_yield_deposits(prepareAssetForWalletTx, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token):
    """Test multiple deposits accumulate vault tokens correctly"""
    
    lego_id = 2
    
    # first deposit
    deposit1_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=50 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=8 * EIGHTEEN_DECIMALS,
        _shouldCheckYield=False
    )
    
    _, _, vault_tokens1, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit1_amount,
        sender=bob
    )
    
    # verify first deposit
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens1
    vault_data = user_wallet.assetData(yield_vault_token.address)
    assert vault_data.assetBalance == vault_tokens1
    assert vault_data.isYieldAsset == True
    first_price_per_share = vault_data.lastPricePerShare
    
    # second deposit
    deposit2_amount = 30 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, deposit2_amount, sender=yield_underlying_token_whale)
    
    _, _, vault_tokens2, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit2_amount,
        sender=bob
    )
    
    # verify accumulated balance
    total_vault_tokens = vault_tokens1 + vault_tokens2
    assert yield_vault_token.balanceOf(user_wallet) == total_vault_tokens
    
    # verify storage updated correctly
    vault_data = user_wallet.assetData(yield_vault_token.address)
    assert vault_data.assetBalance == total_vault_tokens
    assert vault_data.isYieldAsset == True
    assert vault_data.lastPricePerShare == first_price_per_share  # should remain same if no yield accrued
    
    # third deposit
    deposit3_amount = 20 * EIGHTEEN_DECIMALS
    yield_underlying_token.transfer(user_wallet, deposit3_amount, sender=yield_underlying_token_whale)
    
    _, _, vault_tokens3, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit3_amount,
        sender=bob
    )
    
    # verify final state
    final_total = vault_tokens1 + vault_tokens2 + vault_tokens3
    assert yield_vault_token.balanceOf(user_wallet) == final_total
    vault_data = user_wallet.assetData(yield_vault_token.address)
    assert vault_data.assetBalance == final_total


def test_yield_asset_data_tracking(prepareAssetForWalletTx, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, setUserWalletConfig):
    """Test yield asset data is properly tracked with isYieldAsset and lastPricePerShare"""
    
    # set stale blocks to a known value
    setUserWalletConfig(_staleBlocks=10)
    
    # setup: prepare underlying tokens in wallet
    deposit_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _shouldCheckYield=False
    )
    
    # verify vault token not tracked before deposit
    initial_vault_data = user_wallet.assetData(yield_vault_token.address)
    assert initial_vault_data.assetBalance == 0
    assert initial_vault_data.isYieldAsset == False
    assert initial_vault_data.lastPricePerShare == 0
    
    # get vault's current price per share
    current_price_per_share = yield_vault_token.convertToAssets(EIGHTEEN_DECIMALS)
    
    # deposit
    lego_id = 2
    _, _, vault_tokens_received, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=bob
    )
    
    # verify vault token is now tracked as yield asset
    vault_data = user_wallet.assetData(yield_vault_token.address)
    assert vault_data.assetBalance == vault_tokens_received
    assert vault_data.isYieldAsset == True
    assert vault_data.lastPricePerShare == current_price_per_share
    assert vault_data.usdValue > 0
    
    # verify vault token added to assets array
    vault_index = user_wallet.indexOfAsset(yield_vault_token.address)
    assert vault_index > 0  # should be added after ETH
    assert user_wallet.assets(vault_index) == yield_vault_token.address


def test_yield_price_per_share_update_via_updateAssetData(prepareAssetForWalletTx, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, setUserWalletConfig, switchboard_alpha):
    """Test that price per share updates when calling updateAssetData with _shouldCheckYield=True"""
    
    # set stale blocks to a known value
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=0)
    
    # setup: prepare underlying tokens in wallet
    deposit_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _shouldCheckYield=False
    )
    
    # initial deposit
    lego_id = 2
    _, _, vault_tokens_received, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=bob
    )
    
    initial_vault_data = user_wallet.assetData(yield_vault_token.address)
    initial_price_per_share = initial_vault_data.lastPricePerShare
    assert initial_price_per_share == EIGHTEEN_DECIMALS  # should be 1:1 initially
    
    # time travel and simulate yield accrual
    boa.env.time_travel(blocks=15)  # 15 > 10 stale blocks
    
    # Get current vault balance to double the price per share exactly
    current_vault_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    # Transfer same amount to double the assets, which doubles price per share
    yield_underlying_token.transfer(yield_vault_token.address, current_vault_balance, sender=yield_underlying_token_whale)
    
    # verify actual price per share doubled
    new_price_per_share = yield_vault_token.convertToAssets(EIGHTEEN_DECIMALS)
    assert new_price_per_share == 2 * EIGHTEEN_DECIMALS  # should be exactly 2:1 now
    
    # call updateAssetData with _shouldCheckYield=True to trigger yield check
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet_config.updateAssetData(
        0,  # legoId
        yield_vault_token.address,
        True,  # _shouldCheckYield - this will trigger _checkForYieldProfits
        sender=switchboard_alpha.address
    )
    
    # verify price per share was updated
    updated_vault_data = user_wallet.assetData(yield_vault_token.address)
    assert updated_vault_data.lastPricePerShare == 2 * EIGHTEEN_DECIMALS
    assert updated_vault_data.assetBalance == vault_tokens_received  # balance unchanged


def test_yield_profits_detection_on_transfer(prepareAssetForWalletTx, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, setUserWalletConfig):
    """Test that yield profits are detected when transferring yield assets"""
    
    # set stale blocks to a known value and disable yield fee
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=0)
    
    # setup and initial deposit
    deposit_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _shouldCheckYield=False
    )
    
    lego_id = 2
    _, _, vault_tokens_received, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=bob
    )
    
    initial_vault_data = user_wallet.assetData(yield_vault_token.address)
    initial_price_per_share = initial_vault_data.lastPricePerShare
    assert initial_price_per_share == EIGHTEEN_DECIMALS  # should be 1:1 initially
    
    # time travel past stale blocks and simulate yield accrual
    boa.env.time_travel(blocks=15)  # 15 > 10 stale blocks
    
    # Get current vault balance to increase price per share by 50%
    current_vault_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    # Transfer half the current balance to increase price per share to 1.5x
    yield_underlying_token.transfer(yield_vault_token.address, current_vault_balance // 2, sender=yield_underlying_token_whale)
    
    # verify yield accrued (1.5x)
    new_price_per_share = yield_vault_token.convertToAssets(EIGHTEEN_DECIMALS)
    assert new_price_per_share == 15 * EIGHTEEN_DECIMALS // 10  # 1.5x
    
    # transfer some vault tokens - this should trigger yield profit detection
    transfer_amount = vault_tokens_received // 2
    _, _ = user_wallet.transferFunds(
        bob,
        yield_vault_token.address,
        transfer_amount,
        sender=bob
    )
    
    # check that price per share was updated during transfer
    updated_vault_data = user_wallet.assetData(yield_vault_token.address)
    assert updated_vault_data.lastPricePerShare == 15 * EIGHTEEN_DECIMALS // 10  # 1.5x
    assert updated_vault_data.assetBalance == vault_tokens_received - transfer_amount


def test_yield_performance_fee_deduction(prepareAssetForWalletTx, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, setUserWalletConfig, switchboard_alpha, loot_distributor, governance):
    """Test that yield performance fee is deducted when yield profits are detected"""
    
    # set stale blocks, 20% yield performance fee, and remove yield cap
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=20_00, _defaultYieldMaxIncrease=0)  # 20% fee, no cap
    
    # setup and initial deposit
    deposit_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _shouldCheckYield=False
    )
    
    lego_id = 2
    _, _, vault_tokens_received, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=bob
    )
    
    # verify initial state
    initial_vault_data = user_wallet.assetData(yield_vault_token.address)
    assert initial_vault_data.assetBalance == vault_tokens_received
    assert initial_vault_data.lastPricePerShare == EIGHTEEN_DECIMALS  # 1:1
    
    # get initial governance balance (fees go to governance since no ambassador yield fee share configured)
    initial_gov_balance = yield_vault_token.balanceOf(governance.address)

    # time travel and simulate yield accrual
    boa.env.time_travel(blocks=15)  # 15 > 10 stale blocks
    
    # Double the vault's assets to double price per share
    current_vault_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.transfer(yield_vault_token.address, current_vault_balance, sender=yield_underlying_token_whale)
    
    # verify price per share doubled
    new_price_per_share = yield_vault_token.convertToAssets(EIGHTEEN_DECIMALS)
    assert new_price_per_share == 2 * EIGHTEEN_DECIMALS  # 2:1
    
    # Calculate yield profit the way the contract does:
    # 1. Previous underlying value = 100 tokens * 1 = 100
    # 2. Current underlying value = 100 tokens * 2 = 200
    # 3. Profit in underlying = 200 - 100 = 100
    # 4. Profit in vault tokens = 100 / 2 = 50 vault tokens (at new price)
    # 5. Fee = 20% of profit = 0.2 * 50 = 10 vault tokens
    # 6. Expected balance = 100 - 10 = 90 vault tokens
    expected_fee = 10 * EIGHTEEN_DECIMALS
    expected_balance_after_fee = vault_tokens_received - expected_fee
    
    # trigger yield check via updateAssetData
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet_config.updateAssetData(
        0,  # legoId
        yield_vault_token.address,
        True,  # _shouldCheckYield - this will trigger fee deduction
        sender=switchboard_alpha.address
    )
    
    # verify fee was deducted from wallet balance
    updated_vault_data = user_wallet.assetData(yield_vault_token.address)
    assert updated_vault_data.assetBalance == expected_balance_after_fee
    assert updated_vault_data.lastPricePerShare == 2 * EIGHTEEN_DECIMALS

    # verify fee was sent to governance (no ambassador yield fee share configured, so 100% goes to gov)
    gov_balance_increase = yield_vault_token.balanceOf(governance.address) - initial_gov_balance
    assert gov_balance_increase == expected_fee


def test_yield_no_update_within_stale_blocks(prepareAssetForWalletTx, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, setUserWalletConfig):
    """Test that price per share doesn't update within stale blocks period"""
    
    # set stale blocks to 20
    setUserWalletConfig(_staleBlocks=20)
    
    # setup and initial deposit
    deposit_amount = prepareAssetForWalletTx(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _shouldCheckYield=False
    )
    
    lego_id = 2
    _, _, vault_tokens_received, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        deposit_amount,
        sender=bob
    )
    
    initial_vault_data = user_wallet.assetData(yield_vault_token.address)
    initial_price_per_share = initial_vault_data.lastPricePerShare
    
    # time travel less than stale blocks (10 < 20)
    boa.env.time_travel(blocks=10)
    
    # simulate yield accrual
    yield_underlying_token.transfer(yield_vault_token.address, 30 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    # verify actual price per share increased
    new_actual_price_per_share = yield_vault_token.convertToAssets(EIGHTEEN_DECIMALS)
    assert new_actual_price_per_share > initial_price_per_share
    
    # deposit more - price per share should NOT update (within stale blocks)
    yield_underlying_token.transfer(user_wallet, 50 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
    
    _, _, _, _ = user_wallet.depositForYield(
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        50 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    # verify price per share was NOT updated (still using cached value)
    vault_data = user_wallet.assetData(yield_vault_token.address)
    assert vault_data.lastPricePerShare == initial_price_per_share  # unchanged
    
    # time travel beyond stale blocks
    boa.env.time_travel(blocks=15)  # total 25 blocks > 20 stale blocks
    
    # now transfer should update price per share
    _, _ = user_wallet.transferFunds(
        bob,
        yield_vault_token.address,
        10 * EIGHTEEN_DECIMALS,
        sender=bob
    )
    
    # verify price per share was finally updated
    final_vault_data = user_wallet.assetData(yield_vault_token.address)
    assert final_vault_data.lastPricePerShare == new_actual_price_per_share


#######################
# Withdraw from Yield #
#######################


@pytest.fixture(scope="module")
def setupYieldPosition(prepareAssetForWalletTx, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token):
    """Setup fixture that deposits yield tokens and returns relevant data"""
    def setupYieldPosition(
        _deposit_amount=100 * EIGHTEEN_DECIMALS,
        _underlying_price=10 * EIGHTEEN_DECIMALS,
    ):
        # prepare underlying tokens
        deposit_amount = prepareAssetForWalletTx(
            _asset=yield_underlying_token,
            _amount=_deposit_amount,
            _whale=yield_underlying_token_whale,
            _price=_underlying_price,
            _shouldCheckYield=False
        )
        
        # deposit to get vault tokens
        _, _, vault_tokens_received, _ = user_wallet.depositForYield(
            2,  # mock_yield_lego is registered with id 2
            yield_underlying_token.address,
            yield_vault_token.address,
            deposit_amount,
            sender=bob
        )
        
        return vault_tokens_received
    
    yield setupYieldPosition


def test_withdraw_yield_basic(setupYieldPosition, user_wallet, bob, yield_underlying_token, yield_vault_token, setUserWalletConfig):
    """Test basic withdrawal from yield position"""
    
    # disable yield fees for simplicity
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=0)
    
    # setup position
    vault_tokens = setupYieldPosition()
    
    # verify initial state
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens
    assert yield_underlying_token.balanceOf(user_wallet) == 0
    
    # withdraw half
    withdraw_amount = vault_tokens // 2
    vault_burned, underlying_asset, underlying_received, usd_value = user_wallet.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw_amount,
        sender=bob
    )

    # verify event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 11  # EARN_WITHDRAW operation
    assert log.asset1 == yield_vault_token.address
    assert log.asset2 == yield_underlying_token.address
    assert log.amount1 == withdraw_amount == vault_burned
    assert log.amount2 == underlying_received
    assert log.usdValue == usd_value
    assert log.legoId == 2
    assert log.signer == bob

    # verify return values
    assert vault_burned == withdraw_amount
    assert underlying_asset == yield_underlying_token.address
    assert underlying_received == withdraw_amount  # 1:1 price
    assert usd_value > 0
    
    # verify balances
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens - withdraw_amount
    assert yield_underlying_token.balanceOf(user_wallet) == underlying_received
    
    # verify storage updated
    vault_data = user_wallet.assetData(yield_vault_token.address)
    assert vault_data.assetBalance == vault_tokens - withdraw_amount
    
    underlying_data = user_wallet.assetData(yield_underlying_token.address)
    assert underlying_data.assetBalance == underlying_received
    assert underlying_data.isYieldAsset == False  # underlying is not a yield asset
    
    # verify underlying asset is registered
    assert user_wallet.indexOfAsset(yield_underlying_token.address) > 0


def test_withdraw_yield_entire_balance(setupYieldPosition, user_wallet, bob, yield_underlying_token, yield_vault_token, setUserWalletConfig):
    """Test withdrawing entire yield position deregisters vault token"""
    
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=0)
    
    # setup position
    vault_tokens = setupYieldPosition()
    
    # verify vault token is registered
    vault_index_before = user_wallet.indexOfAsset(yield_vault_token.address)
    assert vault_index_before > 0
    
    # withdraw entire balance
    vault_burned, underlying_asset, underlying_received, _ = user_wallet.withdrawFromYield(
        2,
        yield_vault_token.address,
        vault_tokens,
        sender=bob
    )
    
    # verify all vault tokens burned
    assert vault_burned == vault_tokens
    assert yield_vault_token.balanceOf(user_wallet) == 0
    assert underlying_received == vault_tokens  # 1:1 price
    
    # verify vault token deregistered
    assert user_wallet.indexOfAsset(yield_vault_token.address) == 0
    vault_data = user_wallet.assetData(yield_vault_token.address)
    assert vault_data.assetBalance == 0
    assert vault_data.usdValue == 0
    
    # verify underlying registered and has balance
    assert user_wallet.indexOfAsset(yield_underlying_token.address) > 0
    assert yield_underlying_token.balanceOf(user_wallet) == underlying_received


def test_withdraw_yield_with_max_value(setupYieldPosition, user_wallet, bob, yield_underlying_token, yield_vault_token, setUserWalletConfig):
    """Test withdrawing with max_value withdraws entire balance"""
    
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=0)
    
    # setup position
    vault_tokens = setupYieldPosition()
    
    # withdraw with max_value
    vault_burned, _, underlying_received, _ = user_wallet.withdrawFromYield(
        2,
        yield_vault_token.address,
        MAX_UINT256,  # max value
        sender=bob
    )
    
    # verify entire balance withdrawn
    assert vault_burned == vault_tokens
    assert yield_vault_token.balanceOf(user_wallet) == 0
    assert yield_underlying_token.balanceOf(user_wallet) == underlying_received


def test_withdraw_yield_with_accrued_yield(setupYieldPosition, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, setUserWalletConfig):
    """Test withdrawal after yield has accrued updates price per share"""
    
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=0)
    
    # setup position
    vault_tokens = setupYieldPosition()
    
    # time travel and simulate yield accrual
    boa.env.time_travel(blocks=15)
    
    # double the vault's assets to double price per share
    current_vault_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.transfer(yield_vault_token.address, current_vault_balance, sender=yield_underlying_token_whale)
    
    # withdraw half - this should detect yield and update price per share
    withdraw_amount = vault_tokens // 2
    vault_burned, _, underlying_received, _ = user_wallet.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw_amount,
        sender=bob
    )
    
    # with 2x price, should receive 2x underlying
    assert vault_burned == withdraw_amount
    assert underlying_received == withdraw_amount * 2  # 2:1 price
    
    # verify price per share was updated
    vault_data = user_wallet.assetData(yield_vault_token.address)
    assert vault_data.lastPricePerShare == 2 * EIGHTEEN_DECIMALS


def test_withdraw_yield_with_performance_fee(setupYieldPosition, user_wallet, bob, yield_underlying_token, yield_underlying_token_whale, yield_vault_token, setUserWalletConfig, loot_distributor, governance):
    """Test withdrawal with yield accrued deducts performance fee"""
    
    # 20% performance fee, no yield cap
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=20_00, _defaultYieldMaxIncrease=0)
    
    # setup position
    vault_tokens = setupYieldPosition()
    
    # time travel and double price per share
    boa.env.time_travel(blocks=15)
    current_vault_balance = yield_underlying_token.balanceOf(yield_vault_token.address)
    yield_underlying_token.transfer(yield_vault_token.address, current_vault_balance, sender=yield_underlying_token_whale)
    
    # get initial governance balance (fees go to governance since no ambassador yield fee share configured)
    initial_gov_balance = yield_vault_token.balanceOf(governance.address)

    # withdraw triggers yield check and fee deduction
    # With 2x price: profit = 50 vault tokens, fee = 10 vault tokens
    expected_fee = 10 * EIGHTEEN_DECIMALS
    expected_vault_balance_after_fee = vault_tokens - expected_fee

    # withdraw remaining balance after fee
    vault_burned, _, underlying_received, _ = user_wallet.withdrawFromYield(
        2,
        yield_vault_token.address,
        expected_vault_balance_after_fee,
        sender=bob
    )

    # verify fee was sent to governance (no ambassador yield fee share configured, so 100% goes to gov)
    gov_balance_increase = yield_vault_token.balanceOf(governance.address) - initial_gov_balance
    assert gov_balance_increase == expected_fee
    
    # verify correct amount withdrawn
    assert vault_burned == expected_vault_balance_after_fee
    assert underlying_received == expected_vault_balance_after_fee * 2  # 2:1 price


def test_withdraw_yield_multiple_sequential(setupYieldPosition, user_wallet, bob, yield_underlying_token, yield_vault_token, setUserWalletConfig):
    """Test multiple sequential withdrawals"""
    
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=0)
    
    # setup position with 90 tokens (divisible by 3)
    vault_tokens = setupYieldPosition(_deposit_amount=90 * EIGHTEEN_DECIMALS)
    
    # first withdrawal - 1/3
    withdraw1 = vault_tokens // 3
    _, _, underlying1, _ = user_wallet.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw1,
        sender=bob
    )
    
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens - withdraw1
    assert yield_underlying_token.balanceOf(user_wallet) == underlying1
    
    # second withdrawal - another 1/3
    withdraw2 = vault_tokens // 3
    _, _, underlying2, _ = user_wallet.withdrawFromYield(
        2,
        yield_vault_token.address,
        withdraw2,
        sender=bob
    )
    
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens - withdraw1 - withdraw2
    assert yield_underlying_token.balanceOf(user_wallet) == underlying1 + underlying2
    
    # final withdrawal - remaining balance
    _, _, underlying3, _ = user_wallet.withdrawFromYield(
        2,
        yield_vault_token.address,
        MAX_UINT256,  # withdraw all remaining
        sender=bob
    )
    
    # verify all withdrawn
    assert yield_vault_token.balanceOf(user_wallet) == 0
    assert yield_underlying_token.balanceOf(user_wallet) == vault_tokens  # total 1:1
    
    # verify vault token deregistered
    assert user_wallet.indexOfAsset(yield_vault_token.address) == 0


def test_withdraw_from_yield_trusted_tx_only_wallet_config(setupYieldPosition, user_wallet, bob, alice, yield_vault_token):
    """Test that only UserWalletConfig can call withdrawFromYield with _isTrustedTx=True"""
    
    # setup position
    vault_tokens = setupYieldPosition()
    
    # attempt to call withdrawFromYield with _isTrustedTx=True from non-config address
    with boa.reverts("perms"):
        user_wallet.withdrawFromYield(
            2,
            yield_vault_token.address,
            vault_tokens // 2,
            b"",
            True,  # _isTrustedTx = True
            sender=bob  # owner trying to call with trusted tx
        )
    
    # also test with non-owner
    with boa.reverts("perms"):
        user_wallet.withdrawFromYield(
            2,
            yield_vault_token.address,
            vault_tokens // 2,
            b"",
            True,  # _isTrustedTx = True
            sender=alice  # non-owner trying to call with trusted tx
        )


def test_withdraw_from_yield_trusted_tx_from_config(setupYieldPosition, user_wallet, yield_underlying_token, yield_vault_token, hatchery):
    """Test that UserWalletConfig can successfully call withdrawFromYield with _isTrustedTx=True via switchboard"""
    
    # setup position
    vault_tokens = setupYieldPosition()
    
    # get wallet config
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    
    # wallet config should be able to call withdrawFromYield via switchboard
    underlying_amount, usd_value = wallet_config.preparePayment(
        yield_underlying_token.address,
        2,
        yield_vault_token.address,
        vault_tokens // 2,
        sender=hatchery.address
    )
    
    # verify withdrawal happened
    assert underlying_amount == vault_tokens // 2  # 1:1 price
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens - (vault_tokens // 2)
    assert yield_underlying_token.balanceOf(user_wallet) == underlying_amount


############################
# Rebalance Yield Position #
############################












def test_claim_rewards_basic(user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_ripe, switchboard_alpha, setUserWalletConfig, createTxFees):
    """Test basic rewards claiming functionality"""
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Setup: no rewards fee initially
    setUserWalletConfig(_txFees=createTxFees(_rewardsFee=0))
    
    # Set price for reward token
    mock_ripe.setPrice(mock_dex_asset, 5 * EIGHTEEN_DECIMALS)  # $5
    
    # Register asset in wallet config
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet_config.updateAssetData(lego_id, mock_dex_asset, False, sender=switchboard_alpha.address)
    
    # Set lego access (required for rewards operations)
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    # Check initial balance
    initial_balance = mock_dex_asset.balanceOf(user_wallet)
    assert initial_balance == 0
    
    # Claim rewards
    reward_amount = 100 * EIGHTEEN_DECIMALS
    amount_claimed, usd_value = user_wallet.claimRewards(
        lego_id,
        mock_dex_asset.address,
        reward_amount,
        b"",  # extraData
        sender=bob
    )
    
    # Verify return values (no fee)
    assert amount_claimed == reward_amount
    assert usd_value == 500 * EIGHTEEN_DECIMALS  # 100 tokens * $5
    
    # Check balance increased
    assert mock_dex_asset.balanceOf(user_wallet) == reward_amount
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 50  # REWARDS operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_lego.address
    assert log.amount1 == reward_amount
    assert log.amount2 == 0
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    assert log.signer == bob
    
    # Check storage updated
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    assert asset_data.assetBalance == reward_amount
    assert asset_data.usdValue == usd_value
    assert asset_data.isYieldAsset == False


def test_claim_rewards_with_fee(user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_ripe, switchboard_alpha, setUserWalletConfig, createTxFees, loot_distributor, governance):
    """Test rewards claiming with fee deduction"""
    lego_id = 3  # mock_dex_lego is always id 3

    # Setup: 10% rewards fee
    setUserWalletConfig(_txFees=createTxFees(_rewardsFee=10_00))  # 10%

    # Set price for reward token
    mock_ripe.setPrice(mock_dex_asset, 5 * EIGHTEEN_DECIMALS)  # $5

    # Register asset in wallet config
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet_config.updateAssetData(lego_id, mock_dex_asset, False, sender=switchboard_alpha.address)

    # Set lego access
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)

    # Get initial governance balance (fees go to governance since no ambassador rewards fee share configured)
    initial_gov_balance = mock_dex_asset.balanceOf(governance.address)
    
    # Claim rewards
    reward_amount = 200 * EIGHTEEN_DECIMALS
    amount_claimed, usd_value = user_wallet.claimRewards(
        lego_id,
        mock_dex_asset.address,
        reward_amount,
        sender=bob
    )
    
    # Calculate expected values with 10% fee
    expected_fee = 20 * EIGHTEEN_DECIMALS  # 10% of 200
    expected_net_amount = reward_amount - expected_fee  # 180
    
    # Verify return values (after fee deduction)
    assert amount_claimed == expected_net_amount
    assert usd_value == 1000 * EIGHTEEN_DECIMALS  # 200 tokens * $5 (before fee)
    
    # Check wallet balance (should have net amount after fee)
    assert mock_dex_asset.balanceOf(user_wallet) == expected_net_amount

    # Check fee was sent to governance (no ambassador rewards fee share configured, so 100% goes to gov)
    gov_balance_increase = mock_dex_asset.balanceOf(governance.address) - initial_gov_balance
    assert gov_balance_increase == expected_fee
    
    # Check event shows net amount after fee
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 50  # REWARDS operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_lego.address
    assert log.amount1 == expected_net_amount  # Net amount after fee
    assert log.amount2 == 0
    assert log.usdValue == usd_value  # USD value before fee
    
    # Check storage reflects net amount
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    assert asset_data.assetBalance == expected_net_amount


def test_claim_rewards_multiple_claims(user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_ripe, switchboard_alpha, setUserWalletConfig, createTxFees):
    """Test multiple sequential reward claims accumulate correctly"""
    lego_id = 3  # mock_dex_lego is always id 3
    
    # Setup: no rewards fee for simplicity
    setUserWalletConfig(_txFees=createTxFees(_rewardsFee=0))
    
    # Set price for reward token
    mock_ripe.setPrice(mock_dex_asset, 3 * EIGHTEEN_DECIMALS)  # $3
    
    # Register asset in wallet config
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet_config.updateAssetData(lego_id, mock_dex_asset, False, sender=switchboard_alpha.address)
    
    # Set lego access
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    # First claim
    claim1_amount = 50 * EIGHTEEN_DECIMALS
    amount1, usd1 = user_wallet.claimRewards(
        lego_id,
        mock_dex_asset.address,
        claim1_amount,
        sender=bob
    )
    
    assert amount1 == claim1_amount
    assert mock_dex_asset.balanceOf(user_wallet) == claim1_amount
    
    # Second claim
    claim2_amount = 75 * EIGHTEEN_DECIMALS
    amount2, usd2 = user_wallet.claimRewards(
        lego_id,
        mock_dex_asset.address,
        claim2_amount,
        sender=bob
    )
    
    assert amount2 == claim2_amount
    assert mock_dex_asset.balanceOf(user_wallet) == claim1_amount + claim2_amount
    
    # Third claim
    claim3_amount = 25 * EIGHTEEN_DECIMALS
    amount3, usd3 = user_wallet.claimRewards(
        lego_id,
        mock_dex_asset.address,
        claim3_amount,
        sender=bob
    )
    
    assert amount3 == claim3_amount
    
    # Verify total accumulated rewards
    total_claimed = claim1_amount + claim2_amount + claim3_amount
    assert mock_dex_asset.balanceOf(user_wallet) == total_claimed
    
    # Check storage
    asset_data = user_wallet.assetData(mock_dex_asset.address)
    assert asset_data.assetBalance == total_claimed
    assert asset_data.usdValue == total_claimed * 3  # $3 per token


def test_claim_rewards_with_max_fee_cap(user_wallet, bob, mock_dex_lego, mock_dex_asset, mock_ripe, switchboard_alpha, setUserWalletConfig, createTxFees, loot_distributor, governance):
    """Test that rewards fee is capped at 25% maximum"""
    lego_id = 3  # mock_dex_lego is always id 3

    # Setup: 50% rewards fee (should be capped to 25%)
    setUserWalletConfig(_txFees=createTxFees(_rewardsFee=50_00))  # 50%

    # Set price for reward token
    mock_ripe.setPrice(mock_dex_asset, 4 * EIGHTEEN_DECIMALS)  # $4

    # Register asset in wallet config
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet_config.updateAssetData(lego_id, mock_dex_asset, False, sender=switchboard_alpha.address)

    # Set lego access
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)

    # Get initial governance balance (fees go to governance since no ambassador rewards fee share configured)
    initial_gov_balance = mock_dex_asset.balanceOf(governance.address)
    
    # Claim rewards
    reward_amount = 400 * EIGHTEEN_DECIMALS
    amount_claimed, usd_value = user_wallet.claimRewards(
        lego_id,
        mock_dex_asset.address,
        reward_amount,
        sender=bob
    )
    
    # Fee should be capped at 25% (not 50%)
    expected_fee = 100 * EIGHTEEN_DECIMALS  # 25% of 400
    expected_net_amount = reward_amount - expected_fee  # 300
    
    # Verify return values
    assert amount_claimed == expected_net_amount
    assert usd_value == 1600 * EIGHTEEN_DECIMALS  # 400 tokens * $4
    
    # Check wallet balance
    assert mock_dex_asset.balanceOf(user_wallet) == expected_net_amount

    # Check fee was capped at 25% and sent to governance (no ambassador rewards fee share configured)
    gov_balance_increase = mock_dex_asset.balanceOf(governance.address) - initial_gov_balance
    assert gov_balance_increase == expected_fee
    
    # Verify fee percentage
    fee_percentage = (expected_fee * 10000) // reward_amount
    assert fee_percentage == 2500  # 25%


###############
# Wrapped ETH #
###############


def test_convert_eth_to_weth_basic(user_wallet, bob, weth, fork, mock_ripe):
    """Test basic ETH to WETH conversion"""
    # Get ETH address
    ETH = TOKENS[fork]["ETH"]
    
    # Set prices
    mock_ripe.setPrice(ETH, 2000 * EIGHTEEN_DECIMALS)  # $2000/ETH
    mock_ripe.setPrice(weth, 2000 * EIGHTEEN_DECIMALS)  # $2000/WETH (same as ETH)
    
    # Send ETH to wallet
    eth_amount = 1 * EIGHTEEN_DECIMALS  # 1 ETH
    boa.env.set_balance(user_wallet.address, eth_amount)
    
    # Check initial balances
    assert boa.env.get_balance(user_wallet.address) == eth_amount
    assert weth.balanceOf(user_wallet) == 0
    
    # Convert half ETH to WETH
    convert_amount = int(0.5 * EIGHTEEN_DECIMALS)
    amount_converted, usd_value = user_wallet.convertEthToWeth(convert_amount, sender=bob)
    
    # Verify return values
    assert amount_converted == convert_amount
    assert usd_value == 1000 * EIGHTEEN_DECIMALS  # 0.5 ETH * $2000
    
    # Check balances after conversion
    assert boa.env.get_balance(user_wallet.address) == eth_amount - convert_amount
    assert weth.balanceOf(user_wallet) == convert_amount
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 3  # ETH_TO_WETH operation
    assert log.asset1 == ETH
    assert log.asset2 == weth.address
    assert log.amount1 == 0  # msg.value (0 for non-payable)
    assert log.amount2 == convert_amount
    assert log.usdValue == usd_value
    assert log.legoId == 0
    assert log.signer == bob
    
    # Check storage updated for WETH
    weth_data = user_wallet.assetData(weth.address)
    assert weth_data.assetBalance == convert_amount
    assert weth_data.usdValue == usd_value
    assert weth_data.isYieldAsset == False


def test_convert_weth_to_eth_basic(user_wallet, bob, weth, fork, mock_ripe, whale, switchboard_alpha):
    """Test basic WETH to ETH conversion"""
    # Get ETH address
    ETH = TOKENS[fork]["ETH"]
    
    # Set prices
    mock_ripe.setPrice(ETH, 2000 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(weth, 2000 * EIGHTEEN_DECIMALS)
    
    # Give whale ETH and have them deposit to WETH
    weth_amount = 3 * EIGHTEEN_DECIMALS  # 3 WETH
    boa.env.set_balance(whale, weth_amount)
    weth.deposit(value=weth_amount, sender=whale)
    
    # Transfer WETH to wallet
    weth.transfer(user_wallet, weth_amount, sender=whale)
    
    # Register WETH in wallet config
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet_config.updateAssetData(0, weth.address, False, sender=switchboard_alpha.address)
    
    # Check initial balances
    initial_eth_balance = boa.env.get_balance(user_wallet.address)
    assert weth.balanceOf(user_wallet) == weth_amount
    
    # Convert 1 WETH to ETH
    convert_amount = 1 * EIGHTEEN_DECIMALS
    amount_converted, usd_value = user_wallet.convertWethToEth(convert_amount, sender=bob)
    
    # Verify return values
    assert amount_converted == convert_amount
    assert usd_value == 2000 * EIGHTEEN_DECIMALS  # 1 WETH * $2000
    
    # Check balances after conversion
    assert boa.env.get_balance(user_wallet.address) == initial_eth_balance + convert_amount
    assert weth.balanceOf(user_wallet) == weth_amount - convert_amount
    
    # Check event
    log = filter_logs(user_wallet, "WalletAction")[0]
    assert log.op == 2  # WETH_TO_ETH operation
    assert log.asset1 == weth.address
    assert log.asset2 == ETH
    assert log.amount1 == convert_amount
    assert log.amount2 == convert_amount
    assert log.usdValue == usd_value
    assert log.legoId == 0
    assert log.signer == bob
    
    # Check storage updated for WETH
    weth_data = user_wallet.assetData(weth.address)
    assert weth_data.assetBalance == weth_amount - convert_amount


def test_convert_eth_to_weth_zero_balance_fails(user_wallet, bob):
    """Test converting ETH when wallet has no ETH balance fails"""
    # Ensure wallet has no ETH
    assert boa.env.get_balance(user_wallet.address) == 0
    
    # Attempt to convert should fail
    with boa.reverts("no amt"):
        user_wallet.convertEthToWeth(1 * EIGHTEEN_DECIMALS, sender=bob)


def test_convert_weth_to_eth_zero_balance_fails(user_wallet, bob, weth):
    """Test converting WETH when wallet has no WETH balance fails"""
    # Ensure wallet has no WETH
    assert weth.balanceOf(user_wallet) == 0
    
    # Attempt to convert should fail
    with boa.reverts("no balance for _token"):
        user_wallet.convertWethToEth(1 * EIGHTEEN_DECIMALS, sender=bob)


def test_eth_weth_conversions_cycle(user_wallet, bob, weth, fork, mock_ripe, switchboard_alpha):
    """Test multiple ETH<->WETH conversions in a cycle"""
    # Get ETH address
    ETH = TOKENS[fork]["ETH"]
    
    # Set prices
    mock_ripe.setPrice(ETH, 2000 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(weth, 2000 * EIGHTEEN_DECIMALS)
    
    # Start with ETH
    initial_eth = 2 * EIGHTEEN_DECIMALS
    boa.env.set_balance(user_wallet.address, initial_eth)
    
    # Register WETH for later use
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet_config.updateAssetData(0, weth.address, False, sender=switchboard_alpha.address)
    
    # Step 1: Convert 1 ETH to WETH
    amount1, _ = user_wallet.convertEthToWeth(1 * EIGHTEEN_DECIMALS, sender=bob)
    assert boa.env.get_balance(user_wallet.address) == 1 * EIGHTEEN_DECIMALS
    assert weth.balanceOf(user_wallet) == 1 * EIGHTEEN_DECIMALS
    
    # Step 2: Convert 0.5 ETH to WETH
    amount2, _ = user_wallet.convertEthToWeth(int(0.5 * EIGHTEEN_DECIMALS), sender=bob)
    assert boa.env.get_balance(user_wallet.address) == int(0.5 * EIGHTEEN_DECIMALS)
    assert weth.balanceOf(user_wallet) == int(1.5 * EIGHTEEN_DECIMALS)
    
    # Step 3: Convert 0.75 WETH back to ETH
    amount3, _ = user_wallet.convertWethToEth(int(0.75 * EIGHTEEN_DECIMALS), sender=bob)
    assert boa.env.get_balance(user_wallet.address) == int(1.25 * EIGHTEEN_DECIMALS)
    assert weth.balanceOf(user_wallet) == int(0.75 * EIGHTEEN_DECIMALS)
    
    # Step 4: Convert remaining WETH to ETH
    amount4, _ = user_wallet.convertWethToEth(MAX_UINT256, sender=bob)
    assert boa.env.get_balance(user_wallet.address) == initial_eth  # Back to original
    assert weth.balanceOf(user_wallet) == 0


def test_convert_eth_to_weth_updates_asset_tracking(user_wallet, bob, weth, fork, mock_ripe):
    """Test that converting ETH to WETH properly registers WETH as an asset"""
    # Get ETH address
    ETH = TOKENS[fork]["ETH"]
    
    # Set prices
    mock_ripe.setPrice(ETH, 2000 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(weth, 2000 * EIGHTEEN_DECIMALS)
    
    # Send ETH to wallet
    boa.env.set_balance(user_wallet.address, 1 * EIGHTEEN_DECIMALS)
    
    # Check if WETH is already tracked (from previous tests)
    initial_weth_index = user_wallet.indexOfAsset(weth.address)
    initial_num_assets = user_wallet.numAssets()
    
    # Convert ETH to WETH
    user_wallet.convertEthToWeth(int(0.5 * EIGHTEEN_DECIMALS), sender=bob)
    
    # Verify WETH is tracked (either was already or newly added)
    weth_index = user_wallet.indexOfAsset(weth.address)
    assert weth_index > 0
    assert user_wallet.assets(weth_index) == weth.address
    
    # The conversion might add both ETH and WETH as tracked assets
    # So we check that WETH is tracked, and the number of assets increased appropriately
    final_num_assets = user_wallet.numAssets()
    
    # Check ETH tracking
    eth_index = user_wallet.indexOfAsset(ETH)
    
    # The number of assets should have increased by the number of newly tracked assets
    newly_tracked = 0
    if initial_weth_index == 0:
        newly_tracked += 1  # WETH was newly tracked
    
    # Note: ETH might also be newly tracked by the conversion
    # So we just verify the final count makes sense
    assert final_num_assets >= initial_num_assets
    assert final_num_assets <= initial_num_assets + 2  # At most ETH and WETH added
    
    # Verify storage
    weth_data = user_wallet.assetData(weth.address)
    assert weth_data.assetBalance == int(0.5 * EIGHTEEN_DECIMALS)
    assert weth_data.usdValue == 1000 * EIGHTEEN_DECIMALS  # 0.5 * $2000