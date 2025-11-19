import pytest
import boa

from constants import EIGHTEEN_DECIMALS
from contracts.core.userWallet import UserWalletConfig
from conf_utils import filter_logs
from config.BluePrint import TOKENS


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
        _lego_id=2,  # mock_yield_lego
        _shouldCheckYield=False
    )
    
    # Deposit for yield through agent wrapper (no signature needed when called by owner)
    asset_deposited, vault_token, vault_tokens_received, usd_value = starter_agent.depositForYield(
        user_wallet.address,
        2,
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
    assert log.legoId == 2

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
    setUserWalletConfig(_defaultYieldPerformanceFee=0)
    
    # Setup: first deposit to create yield position
    amount = setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=5 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )
    
    # Deposit through agent wrapper
    _, _, vault_tokens, _ = starter_agent.depositForYield(
        user_wallet.address,
        2,
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
        2,
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




def test_agent_swap_tokens_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_asset_alt,
    whale,
    mock_ripe
):
    """Test AgentWrapper swapTokens function"""
    
    # Setup mock_dex_asset in wallet
    amount = setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=3,  # mock_dex_lego
        _shouldCheckYield=False
    )
    
    # Setup mock_dex_asset_alt price and register it
    mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)  # $3
    
    # Create swap instruction
    swap_amount = 100 * EIGHTEEN_DECIMALS
    swap_instructions = [
        (
            3,  # legoId (mock_dex_lego)
            swap_amount,  # amountIn
            0,  # minAmountOut
            [mock_dex_asset.address, mock_dex_asset_alt.address],  # tokenPath
            []  # poolPath (not used in mock)
        )
    ]
    
    # Perform swap through agent wrapper
    token_in, amount_in, token_out, amount_out, usd_value = starter_agent.swapTokens(
        user_wallet.address,
        swap_instructions,
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 20  # swap operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    assert log.amount1 == amount_in
    assert log.amount2 == amount_out
    assert log.usdValue == usd_value
    assert log.legoId == 3
    
    # Verify results
    assert token_in == mock_dex_asset.address
    assert amount_in == swap_amount
    assert token_out == mock_dex_asset_alt.address
    assert amount_out == swap_amount  # MockDexLego does 1:1 swap
    # USD value is the max of input ($200) and output ($300) values
    assert usd_value == 300 * EIGHTEEN_DECIMALS  # max(100 * $2, 100 * $3)
    
    # Verify balances changed
    assert mock_dex_asset.balanceOf(user_wallet) == amount - swap_amount
    assert mock_dex_asset_alt.balanceOf(user_wallet) == amount_out


def test_agent_mint_or_redeem_asset_immediate(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_asset_alt,
    mock_dex_lego,
    whale,
    mock_ripe
):
    """Test AgentWrapper mintOrRedeemAsset function (immediate mode)"""
    
    # Setup assets
    initial_amount = setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=200 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=3,
        _shouldCheckYield=False
    )
    
    # Set prices
    mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)  # $3
    
    # Set immediate mint/redeem mode
    mock_dex_lego.setImmediateMintOrRedeem(True)
    
    mint_amount = 100 * EIGHTEEN_DECIMALS
    
    # Mint through agent wrapper
    token_out_received, output_amount, is_pending, usd_value = starter_agent.mintOrRedeemAsset(
        user_wallet.address,
        3,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mint_amount,
        0,  # minAmountOut
        b"",
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 21  # MINT_REDEEM operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    assert log.amount1 == mint_amount
    assert log.amount2 == output_amount
    assert log.usdValue == usd_value
    assert log.legoId == 3
    
    # Verify results for immediate mint
    assert token_out_received == mint_amount  # 1:1 exchange
    assert output_amount == mint_amount
    assert is_pending == False  # Immediate mode
    assert usd_value == 300 * EIGHTEEN_DECIMALS  # 100 tokens * $3
    
    # Check balances updated
    assert mock_dex_asset.balanceOf(user_wallet) == initial_amount - mint_amount
    assert mock_dex_asset_alt.balanceOf(user_wallet) == mint_amount


def test_agent_confirm_mint_or_redeem_asset_pending(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_asset_alt,
    mock_dex_lego,
    whale,
    mock_ripe
):
    """Test AgentWrapper confirmMintOrRedeemAsset function (pending mode)"""
    
    # Setup assets
    initial_amount = setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=300 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=3,
        _shouldCheckYield=False
    )
    
    # Set prices
    mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)  # $3
    
    # Set pending mint/redeem mode (not immediate)
    mock_dex_lego.setImmediateMintOrRedeem(False)

    lego_id = 3
    mint_amount = 150 * EIGHTEEN_DECIMALS
    
    # Initiate mint - should go to pending state
    amount_in, output_amount, is_pending, usd_value = starter_agent.mintOrRedeemAsset(
        user_wallet.address,
        lego_id,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mint_amount,
        0,  # minAmountOut
        b"",
        sender=charlie
    )
    
    # Verify return values for pending mint
    assert amount_in == mint_amount
    assert output_amount == 0
    assert is_pending == True  # Pending mode
    assert usd_value == 0  # No value yet
    
    # Check that input tokens were taken but output not received yet
    assert mock_dex_asset.balanceOf(user_wallet) == initial_amount - mint_amount
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 0  # No change yet
    
    # Now confirm the mint
    confirmed_amount, confirmed_usd_value = starter_agent.confirmMintOrRedeemAsset(
        user_wallet.address,
        lego_id,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        b"",
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events for confirmation
    assert log.op == 22  # CONFIRM_MINT_REDEEM operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    assert log.amount1 == 0  # No input on confirm
    assert log.amount2 == confirmed_amount  # Output received
    assert log.usdValue == confirmed_usd_value
    assert log.legoId == lego_id
    
    # Verify confirmation results
    assert confirmed_amount == mint_amount  # Now received
    assert confirmed_usd_value == 450 * EIGHTEEN_DECIMALS  # 150 tokens * $3
    
    # Check final balances
    assert mock_dex_asset.balanceOf(user_wallet) == initial_amount - mint_amount
    assert mock_dex_asset_alt.balanceOf(user_wallet) == mint_amount


def test_agent_add_liquidity_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_asset_alt,
    mock_dex_lego,
    mock_dex_lp_token,
    whale,
    mock_ripe
):
    """Test AgentWrapper addLiquidity function"""
    
    # Setup assets
    setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=3,
        _shouldCheckYield=False
    )
    
    setupAgentTestAsset(
        _asset=mock_dex_asset_alt,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=3 * EIGHTEEN_DECIMALS,
        _lego_id=3,
        _shouldCheckYield=False
    )
    
    # Set LP token price
    mock_ripe.setPrice(mock_dex_lp_token, 5 * EIGHTEEN_DECIMALS)  # $5 per LP token
    
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 150 * EIGHTEEN_DECIMALS
    
    # Get initial balances
    initial_asset_balance = mock_dex_asset.balanceOf(user_wallet)
    initial_alt_balance = mock_dex_asset_alt.balanceOf(user_wallet)
    
    # Add liquidity through agent wrapper
    lp_received, added_a, added_b, usd_value = starter_agent.addLiquidity(
        user_wallet.address,
        3,
        mock_dex_lego.address,  # pool address
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        amount_a,
        amount_b,
        0,  # minAmountA
        0,  # minAmountB
        0,  # minLpAmount
        b"",
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 30  # ADD_LIQ operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    assert log.amount1 == added_a
    assert log.amount2 == added_b
    assert log.usdValue == usd_value
    assert log.legoId == 3
    
    # Verify results
    assert added_a == amount_a
    assert added_b == amount_b
    assert lp_received == amount_a + amount_b  # MockDexLego mints LP tokens as sum of inputs
    assert usd_value == amount_a * 2 + amount_b * 3  # $2 per asset, $3 per alt
    
    # Check balances
    assert mock_dex_asset.balanceOf(user_wallet) == initial_asset_balance - amount_a
    assert mock_dex_asset_alt.balanceOf(user_wallet) == initial_alt_balance - amount_b
    assert mock_dex_lp_token.balanceOf(user_wallet) == lp_received


def test_agent_remove_liquidity_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_asset_alt,
    mock_dex_lego,
    mock_dex_lp_token,
    whale
):
    """Test AgentWrapper removeLiquidity function"""
    
    # Setup assets and add liquidity first
    setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=3,
        _shouldCheckYield=False
    )
    
    setupAgentTestAsset(
        _asset=mock_dex_asset_alt,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=3 * EIGHTEEN_DECIMALS,
        _lego_id=3,
        _shouldCheckYield=False
    )
    
    amount_a = 100 * EIGHTEEN_DECIMALS
    amount_b = 100 * EIGHTEEN_DECIMALS
    
    # First add liquidity
    lp_received, _, _, _ = starter_agent.addLiquidity(
        user_wallet.address,
        3,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        amount_a,
        amount_b,
        0, 0, 0,
        b"",
        sender=charlie
    )
    
    # Remove half of the liquidity
    lp_to_remove = lp_received // 2
    received_a, received_b, lp_burned, usd_value = starter_agent.removeLiquidity(
        user_wallet.address,
        3,
        mock_dex_lego.address,  # pool
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mock_dex_lp_token.address,
        lp_to_remove,
        0,  # minAmountA
        0,  # minAmountB
        b"",
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 31  # REMOVE_LIQ operation
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_asset_alt.address
    assert log.amount1 == received_a
    assert log.amount2 == received_b
    assert log.usdValue == usd_value
    assert log.legoId == 3
    
    # MockDexLego returns half of LP amount for each token
    expected_per_token = lp_to_remove // 2
    assert received_a == expected_per_token
    assert received_b == expected_per_token
    assert lp_burned == lp_to_remove
    assert usd_value == expected_per_token * 2 + expected_per_token * 3  # $2 + $3 per token
    
    # Check balances
    assert mock_dex_lp_token.balanceOf(user_wallet) == lp_received - lp_to_remove


###################
# Debt Management #
###################


def test_agent_add_collateral_basic(
    setupAgentTestAsset,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_lego,
    whale
):
    """Test AgentWrapper addCollateral function"""
    
    # Setup asset in wallet
    initial_amount = setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=3,  # mock_dex_lego
        _shouldCheckYield=False
    )
    
    # Set access for mock_dex_lego
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    collateral_amount = 200 * EIGHTEEN_DECIMALS
    
    # Add collateral through agent wrapper
    amount_deposited, usd_value = starter_agent.addCollateral(
        user_wallet.address,
        3,
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
    assert log.legoId == 3
    
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
        _lego_id=3,
        _shouldCheckYield=False
    )
    
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    add_amount = 300 * EIGHTEEN_DECIMALS
    
    # First add collateral
    starter_agent.addCollateral(
        user_wallet.address,
        3,
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
        3,
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
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_debt_token,
    mock_dex_lego,
    mock_ripe
):
    """Test AgentWrapper borrow function"""

    mock_ripe.setPrice(mock_dex_debt_token, 1 * EIGHTEEN_DECIMALS)  # $3
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    borrow_amount = 300 * EIGHTEEN_DECIMALS
    
    # Borrow through agent wrapper
    amount_borrowed, usd_value = starter_agent.borrow(
        user_wallet.address,
        3,
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
    assert log.legoId == 3

    # Verify results
    assert amount_borrowed == borrow_amount
    assert usd_value == 300 * EIGHTEEN_DECIMALS  # 300 tokens * $1
    
    # Verify balance (debt token should be minted to wallet)
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow_amount


def test_agent_repay_debt_basic(
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_debt_token,
    mock_dex_lego,
    mock_ripe
):
    """Test AgentWrapper repayDebt function"""

    mock_ripe.setPrice(mock_dex_debt_token, 1 * EIGHTEEN_DECIMALS)  # $3
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    borrow_amount = 500 * EIGHTEEN_DECIMALS
    
    # First borrow
    starter_agent.borrow(
        user_wallet.address,
        3,
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
        3,
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


#########
# Other #
#########


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


def test_agent_claim_rewards_basic(
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_lego,
    mock_ripe
):
    """Test AgentWrapper claimIncentives function"""
    
    # Setup asset price
    mock_ripe.setPrice(mock_dex_asset, 5 * EIGHTEEN_DECIMALS)  # $5
    
    # Set lego access (required for rewards operations)
    mock_dex_lego.setLegoAccess(mock_dex_lego.address, sender=user_wallet.address)
    
    reward_amount = 100 * EIGHTEEN_DECIMALS
    
    # Claim rewards through agent wrapper
    amount_claimed, usd_value = starter_agent.claimIncentives(
        user_wallet.address,
        3,
        mock_dex_asset.address,
        reward_amount,
        [],
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 50  # rewards
    assert log.asset1 == mock_dex_asset.address
    assert log.asset2 == mock_dex_lego.address
    assert log.amount1 == amount_claimed
    assert log.amount2 == amount_claimed
    assert log.usdValue == usd_value
    assert log.legoId == 3
    
    # Verify results
    assert amount_claimed == reward_amount
    assert usd_value == 500 * EIGHTEEN_DECIMALS  # 100 tokens * $5
    
    # Verify balance (reward tokens should be minted to wallet)
    assert mock_dex_asset.balanceOf(user_wallet) == reward_amount


def test_agent_convert_eth_to_weth_basic(
    starter_agent,
    user_wallet,
    charlie,
    weth,
    fork,
    mock_ripe
):
    """Test AgentWrapper convertEthToWeth function"""
    
    # Set ETH price
    ETH = TOKENS[fork]["ETH"]
    eth_price = 2000 * EIGHTEEN_DECIMALS  # $2000 per ETH
    mock_ripe.setPrice(ETH, eth_price)
    mock_ripe.setPrice(weth, eth_price)

    # Send ETH to wallet first 
    boa.env.set_balance(user_wallet.address, 5 * EIGHTEEN_DECIMALS)
    
    # Convert ETH to WETH through agent wrapper
    convert_amount = 2 * EIGHTEEN_DECIMALS
    
    amount_converted, usd_value = starter_agent.convertEthToWeth(
        user_wallet.address,
        convert_amount,
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 3  # ETH_TO_WETH (op code 3 in contract)
    assert log.asset1 == ETH
    assert log.asset2 == weth.address
    assert log.amount1 == 0  # msg.value (0 for non-payable)
    assert log.amount2 == amount_converted
    assert log.usdValue == usd_value
    
    # Verify results
    assert amount_converted == convert_amount
    expected_usd_value = convert_amount * eth_price // EIGHTEEN_DECIMALS  # 2 ETH * $2000 = $4000
    assert usd_value == expected_usd_value
    
    # Verify balances
    assert weth.balanceOf(user_wallet) == convert_amount
    assert boa.env.get_balance(user_wallet.address) == 3 * EIGHTEEN_DECIMALS  # 5 - 2


def test_agent_convert_weth_to_eth_basic(
    starter_agent,
    user_wallet,
    charlie,
    weth,
    whale,
    fork,
    mock_ripe,
    switchboard_alpha
):
    """Test AgentWrapper convertWethToEth function"""
    
    # Set ETH price (WETH uses same price as ETH)
    ETH = TOKENS[fork]["ETH"]
    eth_price = 1800 * EIGHTEEN_DECIMALS  # $1800 per ETH
    mock_ripe.setPrice(ETH, eth_price)
    mock_ripe.setPrice(weth, eth_price)  # WETH same price as ETH
    
    # Give whale ETH and have them deposit to WETH
    weth_amount = 3 * EIGHTEEN_DECIMALS
    boa.env.set_balance(whale, weth_amount)
    weth.deposit(value=weth_amount, sender=whale)
    
    # Transfer WETH to wallet
    weth.transfer(user_wallet, weth_amount, sender=whale)
    
    # Register WETH in wallet config
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    wallet_config.updateAssetData(0, weth.address, False, sender=switchboard_alpha.address)
    
    # Convert WETH to ETH through agent wrapper
    convert_amount = 1 * EIGHTEEN_DECIMALS
    
    amount_converted, usd_value = starter_agent.convertWethToEth(
        user_wallet.address,
        convert_amount,
        sender=charlie
    )
    log = filter_logs(starter_agent, "WalletAction")[0]
    
    # Verify events
    assert log.op == 2  # WETH_TO_ETH (op code 2 in contract)
    assert log.asset1 == weth.address
    assert log.asset2 == ETH
    assert log.amount1 == amount_converted
    assert log.amount2 == amount_converted  # Both amounts are the same for WETH_TO_ETH
    assert log.usdValue == usd_value
    
    # Verify results
    assert amount_converted == convert_amount
    expected_usd_value = convert_amount * eth_price // EIGHTEEN_DECIMALS  # 1 ETH * $1800 = $1800
    assert usd_value == expected_usd_value
    
    # Verify balances
    assert weth.balanceOf(user_wallet) == weth_amount - convert_amount

