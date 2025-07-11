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
        mock_ripe.setPrice(alpha_token, _price)

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