import pytest
import boa

from constants import EIGHTEEN_DECIMALS
from contracts.core.userWallet import UserWallet, UserWalletConfig
from contracts.core.agent import AgentWrapper
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def setupAgentTestAsset(user_wallet, alpha_token, alpha_token_whale, mock_ripe, switchboard_alpha):
    def setupAgentTestAsset(
        _asset = alpha_token,
        _amount = 100 * EIGHTEEN_DECIMALS,
        _whale = alpha_token_whale,
        _user_wallet = user_wallet,
        _price = 2 * EIGHTEEN_DECIMALS,
        _lego_id = 0,
        _shouldCheckYield = False,
    ):
        # set price
        mock_ripe.setPrice(_asset, _price)

        # transfer asset to wallet
        _asset.transfer(_user_wallet, _amount, sender=_whale)

        # make sure asset is registered
        wallet_config = UserWalletConfig.at(_user_wallet.walletConfig())
        wallet_config.updateAssetData(
            _lego_id,
            _asset,
            _shouldCheckYield,
            sender = switchboard_alpha.address
        )
        return _amount

    yield setupAgentTestAsset


####################
# Yield Lego Tests #
####################


def test_agent_deposit_for_yield_basic(
    setupAgentTestAsset, 
    starter_agent, 
    user_wallet, 
    charlie,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale
):
    """Test AgentWrapper depositForYield function"""
    
    # Setup underlying tokens in wallet
    amount = setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _lego_id=1,  # mock_yield_lego
        _shouldCheckYield=False
    )
    
    # Deposit for yield through agent wrapper (no signature needed when called by owner)
    lego_id = 1  # mock_yield_lego is registered with id 1
    asset_deposited, vault_token, vault_tokens_received, usd_value = starter_agent.depositForYield(
        user_wallet.address,
        lego_id,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        b"",
        sender=charlie  # charlie is the owner of starter_agent
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 10  # deposit for yield
    assert log.asset1 == yield_underlying_token.address
    assert log.asset2 == yield_vault_token.address
    assert log.amount1 == asset_deposited
    assert log.amount2 == vault_tokens_received
    assert log.usdValue == usd_value
    assert log.legoId == lego_id

    # Verify results
    assert asset_deposited == amount
    assert vault_token == yield_vault_token.address
    assert vault_tokens_received > 0
    assert usd_value == 1000 * EIGHTEEN_DECIMALS  # 100 tokens * $10
    
    # Verify tokens were transferred
    assert yield_underlying_token.balanceOf(user_wallet) == 0
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens_received


def test_agent_withdraw_from_yield_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    setUserWalletConfig
):
    """Test AgentWrapper withdrawFromYield function"""
    
    # disable yield fees for simplicity
    setUserWalletConfig(_staleBlocks=10, _defaultYieldPerformanceFee=0)
    
    # Setup: first deposit to create yield position
    amount = setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=5 * EIGHTEEN_DECIMALS,
        _lego_id=1,
        _shouldCheckYield=False
    )
    
    # Deposit through agent wrapper
    _, _, vault_tokens, _ = starter_agent.depositForYield(
        user_wallet.address,
        1,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        b"",
        sender=charlie
    )
    
    # Now withdraw half through agent wrapper
    withdraw_amount = vault_tokens // 2
    vault_burned, underlying_asset, underlying_received, usd_value = starter_agent.withdrawFromYield(
        user_wallet.address,
        1,
        yield_vault_token.address,
        withdraw_amount,
        b"",
        sender=charlie
    )
    withdraw_log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert withdraw_log.op == 11  # withdraw from yield (EARN_WITHDRAW)
    assert withdraw_log.asset1 == yield_vault_token.address
    assert withdraw_log.asset2 == yield_underlying_token.address
    assert withdraw_log.amount1 == vault_burned
    assert withdraw_log.amount2 == underlying_received

    # Verify results
    assert vault_burned == withdraw_amount
    assert underlying_asset == yield_underlying_token.address
    assert underlying_received > 0
    assert usd_value > 0
    
    # Verify balances
    assert yield_vault_token.balanceOf(user_wallet) == vault_tokens - withdraw_amount
    assert yield_underlying_token.balanceOf(user_wallet) == underlying_received


##################
# Dex Lego Tests #
##################


def test_agent_add_collateral_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_lego,
    lego_book,
    whale
):
    """Test AgentWrapper addCollateral function"""
    
    # Setup asset in wallet
    initial_amount = setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=2,  # mock_dex_lego
        _shouldCheckYield=False
    )
    
    # Set access for mock_dex_lego
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    lego_id = 2  # mock_dex_lego is always id 2
    collateral_amount = 200 * EIGHTEEN_DECIMALS
    
    # Add collateral through agent wrapper
    amount_deposited, usd_value = starter_agent.addCollateral(
        user_wallet.address,
        lego_id,
        mock_dex_asset.address,
        collateral_amount,
        b"",
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 40  # add collateral
    assert log.asset1 == mock_dex_asset.address
    assert log.amount1 == amount_deposited
    assert log.usdValue == usd_value
    assert log.legoId == lego_id
    
    # Verify results
    assert amount_deposited == collateral_amount
    assert usd_value == 400 * EIGHTEEN_DECIMALS  # 200 tokens * $2
    
    # Verify balances
    assert mock_dex_asset.balanceOf(user_wallet) == initial_amount - collateral_amount


def test_agent_remove_collateral_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_lego,
    whale
):
    """Test AgentWrapper removeCollateral function"""
    
    # Setup asset and add collateral first
    initial_amount = setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )
    
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    lego_id = 2
    add_amount = 300 * EIGHTEEN_DECIMALS
    
    # First add collateral
    starter_agent.addCollateral(
        user_wallet.address,
        lego_id,
        mock_dex_asset.address,
        add_amount,
        b"",
        sender=charlie
    )
    
    # Check balance after adding collateral
    balance_after_add = mock_dex_asset.balanceOf(user_wallet)
    assert balance_after_add == initial_amount - add_amount
    
    # Now remove some collateral
    remove_amount = 100 * EIGHTEEN_DECIMALS
    amount_removed, usd_value = starter_agent.removeCollateral(
        user_wallet.address,
        lego_id,
        mock_dex_asset.address,
        remove_amount,
        b"",
        sender=charlie
    )
    remove_log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert remove_log.op == 41  # remove collateral
    assert remove_log.asset1 == mock_dex_asset.address
    assert remove_log.amount1 == amount_removed

    # Verify results
    assert amount_removed == remove_amount
    assert usd_value == 200 * EIGHTEEN_DECIMALS  # 100 tokens * $2
    
    # Verify balances
    assert mock_dex_asset.balanceOf(user_wallet) == balance_after_add + remove_amount


def test_agent_borrow_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_debt_token,
    mock_dex_lego,
    mock_ripe,
    whale
):
    """Test AgentWrapper borrow function"""
    
    # Setup mock_dex_asset as collateral first
    setupAgentTestAsset(
        _asset=mock_dex_debt_token,  # Actually using debt token here for setup
        _amount=0,  # No initial balance needed
        _whale=whale,
        _price=1 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )
    
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    lego_id = 2
    borrow_amount = 300 * EIGHTEEN_DECIMALS
    
    # Borrow through agent wrapper
    amount_borrowed, usd_value = starter_agent.borrow(
        user_wallet.address,
        lego_id,
        mock_dex_debt_token.address,
        borrow_amount,
        b"",
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 42  # borrow
    assert log.asset1 == mock_dex_debt_token.address
    assert log.amount1 == amount_borrowed
    assert log.usdValue == usd_value
    assert log.legoId == lego_id

    # Verify results
    assert amount_borrowed == borrow_amount
    assert usd_value == 300 * EIGHTEEN_DECIMALS  # 300 tokens * $1
    
    # Verify balance (debt token should be minted to wallet)
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow_amount


def test_agent_repay_debt_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_debt_token,
    mock_dex_lego,
    mock_ripe,
    whale
):
    """Test AgentWrapper repayDebt function"""
    
    # Setup and borrow first
    setupAgentTestAsset(
        _asset=mock_dex_debt_token,
        _amount=0,
        _whale=whale,
        _price=1 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )
    
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    lego_id = 2
    borrow_amount = 500 * EIGHTEEN_DECIMALS
    
    # First borrow
    starter_agent.borrow(
        user_wallet.address,
        lego_id,
        mock_dex_debt_token.address,
        borrow_amount,
        b"",
        sender=charlie
    )
    
    # Verify debt tokens were received
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow_amount
    
    # Now repay part of the debt
    repay_amount = 200 * EIGHTEEN_DECIMALS
    amount_repaid, usd_value = starter_agent.repayDebt(
        user_wallet.address,
        lego_id,
        mock_dex_debt_token.address,
        repay_amount,
        b"",
        sender=charlie
    )
    repay_log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert repay_log.op == 43  # repay debt
    assert repay_log.asset1 == mock_dex_debt_token.address
    assert repay_log.amount1 == amount_repaid

    # Verify results
    assert amount_repaid == repay_amount
    assert usd_value == 200 * EIGHTEEN_DECIMALS  # 200 tokens * $1
    
    # Verify balance (debt tokens should be burned)
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow_amount - repay_amount
    

####################
# Transfer & Other #
####################


def test_agent_transfer_funds_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    bob,
    alpha_token,
    alpha_token_whale
):
    """Test AgentWrapper transferFunds function"""
    
    # Setup asset in wallet
    amount = setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=0,
        _shouldCheckYield=False
    )
    
    # Transfer funds through agent wrapper
    transfer_amount = 50 * EIGHTEEN_DECIMALS
    actual_transfer_amount, usd_value = starter_agent.transferFunds(
        user_wallet.address,
        bob,
        alpha_token.address,
        transfer_amount,
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 1  # transfer funds
    assert log.asset1 == alpha_token.address
    assert log.asset2 == bob
    assert log.amount1 == actual_transfer_amount
    assert log.usdValue == usd_value

    # Verify results
    assert actual_transfer_amount == transfer_amount
    assert usd_value == 100 * EIGHTEEN_DECIMALS  # 50 tokens * $2
    
    # Verify balances
    assert alpha_token.balanceOf(user_wallet) == amount - transfer_amount
    assert alpha_token.balanceOf(bob) == transfer_amount
