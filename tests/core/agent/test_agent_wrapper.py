import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from contracts.core.userWallet import UserWallet, UserWalletConfig
from conf_utils import filter_logs, set_live_cheque_settings
from config.BluePrint import TOKENS, PARAMS


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


@pytest.fixture
def valid_transfer_recipient(user_wallet_config, migrator, sally):
    if user_wallet_config.indexOfWhitelist(sally) == 0:
        user_wallet_config.addWhitelistAddrViaMigrator(sally, sender=migrator.address)
    return sally


def _set_instant_cheque_settings(
    cheque_book,
    user_wallet,
    owner,
    createChequeSettings,
    _instant_usd_threshold,
    _expensive_delay_blocks=1,
    _can_managers_create_cheques=True,
    _can_manager_pay=True,
    _can_be_pulled=False,
):
    wallet_config = UserWalletConfig.at(user_wallet.walletConfig())
    timelock = wallet_config.timeLock()
    min_expensive_delay = cheque_book.MIN_EXPENSIVE_CHEQUE_DELAY()
    settings = createChequeSettings(
        _instantUsdThreshold=_instant_usd_threshold,
        _expensiveDelayBlocks=max(_expensive_delay_blocks, timelock, min_expensive_delay),
        _defaultExpiryBlocks=timelock,
        _canManagersCreateCheques=_can_managers_create_cheques,
        _canManagerPay=_can_manager_pay,
        _canBePulled=_can_be_pulled,
    )
    set_live_cheque_settings(cheque_book, user_wallet.address, *settings, sender=owner)
    return settings


def _set_agent_transfer_perms(
    user_wallet_config,
    high_command,
    starter_agent,
    createManagerSettings,
    createTransferPerms,
    _can_transfer,
    _can_create_cheque,
    _allowed_payees=None,
):
    original_settings = user_wallet_config.managerSettings(starter_agent.address)
    transfer_perms = createTransferPerms(
        _canTransfer=_can_transfer,
        _canCreateCheque=_can_create_cheque,
        _canAddPendingPayee=original_settings.transferPerms.canAddPendingPayee,
        _allowedPayees=list(original_settings.transferPerms.allowedPayees) if _allowed_payees is None else _allowed_payees,
    )
    updated_settings = createManagerSettings(
        _startBlock=original_settings.startBlock,
        _expiryBlock=original_settings.expiryBlock,
        _limits=original_settings.limits,
        _legoPerms=original_settings.legoPerms,
        _swapPerms=original_settings.swapPerms,
        _whitelistPerms=original_settings.whitelistPerms,
        _transferPerms=transfer_perms,
        _allowedAssets=list(original_settings.allowedAssets),
        _canClaimLoot=original_settings.canClaimLoot,
    )
    user_wallet_config.updateManager(starter_agent.address, updated_settings, sender=high_command.address)
    return original_settings


def _set_agent_claim_loot_perm(
    user_wallet_config,
    high_command,
    starter_agent,
    createManagerSettings,
    _can_claim_loot,
):
    original_settings = user_wallet_config.managerSettings(starter_agent.address)
    updated_settings = createManagerSettings(
        _startBlock=original_settings.startBlock,
        _expiryBlock=original_settings.expiryBlock,
        _limits=original_settings.limits,
        _legoPerms=original_settings.legoPerms,
        _swapPerms=original_settings.swapPerms,
        _whitelistPerms=original_settings.whitelistPerms,
        _transferPerms=original_settings.transferPerms,
        _allowedAssets=list(original_settings.allowedAssets),
        _canClaimLoot=_can_claim_loot,
    )
    user_wallet_config.updateManager(starter_agent.address, updated_settings, sender=high_command.address)
    return original_settings


def _set_agent_whitelist_perms(
    user_wallet_config,
    high_command,
    starter_agent,
    createManagerSettings,
    createWhitelistPerms,
    _can_confirm,
    _can_cancel,
    _can_remove,
    _can_add_pending=False,
):
    original_settings = user_wallet_config.managerSettings(starter_agent.address)
    whitelist_perms = createWhitelistPerms(
        _canAddPending=_can_add_pending,
        _canConfirm=_can_confirm,
        _canCancel=_can_cancel,
        _canRemove=_can_remove,
    )
    updated_settings = createManagerSettings(
        _startBlock=original_settings.startBlock,
        _expiryBlock=original_settings.expiryBlock,
        _limits=original_settings.limits,
        _legoPerms=original_settings.legoPerms,
        _swapPerms=original_settings.swapPerms,
        _whitelistPerms=whitelist_perms,
        _transferPerms=original_settings.transferPerms,
        _allowedAssets=list(original_settings.allowedAssets),
        _canClaimLoot=original_settings.canClaimLoot,
    )
    user_wallet_config.updateManager(starter_agent.address, updated_settings, sender=high_command.address)
    return original_settings


@pytest.fixture(scope="module")
def special_admin_sender(undy_hq_deploy, charlie, fork, starter_agent, switchboard_alpha):
    sender = boa.load(
        "contracts/core/agent/AgentSenderSpecialAdmin.vy",
        undy_hq_deploy,
        charlie,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"],
        PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
        name="special_admin_sender",
    )
    starter_agent.addSender(sender, sender=switchboard_alpha.address)
    return sender


####################
# Yield Lego Tests #
####################


def test_agent_deposit_for_yield_basic(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
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

    # Deposit for yield through agent sender (no signature needed when called by owner)
    asset_deposited, vault_token, vault_tokens_received, usd_value = starter_agent_sender.depositForYield(
        starter_agent.address,  # _agentWrapper
        user_wallet.address,
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        b"",
        (b"", 0, 0),  # empty signature (owner bypass)
        sender=charlie  # charlie is the owner of starter_agent_sender
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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

    # Deposit through agent sender
    _, _, vault_tokens, _ = starter_agent_sender.depositForYield(
        starter_agent.address,
        user_wallet.address,
        2,
        yield_underlying_token.address,
        yield_vault_token.address,
        amount,
        b"",
        (b"", 0, 0),
        sender=charlie
    )

    # Now withdraw half through agent sender
    withdraw_amount = vault_tokens // 2
    vault_burned, underlying_asset, underlying_received, usd_value = starter_agent_sender.withdrawFromYield(
        starter_agent.address,
        user_wallet.address,
        2,
        yield_vault_token.address,
        withdraw_amount,
        b"",
        (b"", 0, 0),
        sender=charlie
    )
    withdraw_log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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

    # Perform swap through agent sender
    token_in, amount_in, token_out, amount_out, usd_value = starter_agent_sender.swapTokens(
        starter_agent.address,
        user_wallet.address,
        swap_instructions,
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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

    # Mint through agent sender
    token_out_received, output_amount, is_pending, usd_value = starter_agent_sender.mintOrRedeemAsset(
        starter_agent.address,
        user_wallet.address,
        3,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mint_amount,
        0,  # minAmountOut
        b"",
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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
    amount_in, output_amount, is_pending, usd_value = starter_agent_sender.mintOrRedeemAsset(
        starter_agent.address,
        user_wallet.address,
        lego_id,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        mint_amount,
        0,  # minAmountOut
        b"",
        (b"", 0, 0),
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
    confirmed_amount, confirmed_usd_value = starter_agent_sender.confirmMintOrRedeemAsset(
        starter_agent.address,
        user_wallet.address,
        lego_id,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        b"",
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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

    # Add liquidity through agent sender
    lp_received, added_a, added_b, usd_value = starter_agent_sender.addLiquidity(
        starter_agent.address,
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
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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
    lp_received, _, _, _ = starter_agent_sender.addLiquidity(
        starter_agent.address,
        user_wallet.address,
        3,
        mock_dex_lego.address,
        mock_dex_asset.address,
        mock_dex_asset_alt.address,
        amount_a,
        amount_b,
        0, 0, 0,
        b"",
        (b"", 0, 0),
        sender=charlie
    )

    # Remove half of the liquidity
    lp_to_remove = lp_received // 2
    received_a, received_b, lp_burned, usd_value = starter_agent_sender.removeLiquidity(
        starter_agent.address,
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
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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

    # Add collateral through agent sender
    amount_deposited, usd_value = starter_agent_sender.addCollateral(
        starter_agent.address,
        user_wallet.address,
        3,
        mock_dex_asset.address,
        collateral_amount,
        b"",
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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
    starter_agent_sender.addCollateral(
        starter_agent.address,
        user_wallet.address,
        3,
        mock_dex_asset.address,
        add_amount,
        b"",
        (b"", 0, 0),
        sender=charlie
    )

    # Check balance after adding collateral
    balance_after_add = mock_dex_asset.balanceOf(user_wallet)
    assert balance_after_add == initial_amount - add_amount

    # Now remove some collateral
    remove_amount = 100 * EIGHTEEN_DECIMALS
    amount_removed, usd_value = starter_agent_sender.removeCollateral(
        starter_agent.address,
        user_wallet.address,
        3,
        mock_dex_asset.address,
        remove_amount,
        b"",
        (b"", 0, 0),
        sender=charlie
    )
    remove_log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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

    # Borrow through agent sender
    amount_borrowed, usd_value = starter_agent_sender.borrow(
        starter_agent.address,
        user_wallet.address,
        3,
        mock_dex_debt_token.address,
        borrow_amount,
        b"",
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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
    starter_agent_sender.borrow(
        starter_agent.address,
        user_wallet.address,
        3,
        mock_dex_debt_token.address,
        borrow_amount,
        b"",
        (b"", 0, 0),
        sender=charlie
    )

    # Verify debt tokens were received
    assert mock_dex_debt_token.balanceOf(user_wallet) == borrow_amount

    # Now repay part of the debt
    repay_amount = 200 * EIGHTEEN_DECIMALS
    amount_repaid, usd_value = starter_agent_sender.repayDebt(
        starter_agent.address,
        user_wallet.address,
        3,
        mock_dex_debt_token.address,
        repay_amount,
        b"",
        (b"", 0, 0),
        sender=charlie
    )
    repay_log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
    user_wallet,
    charlie,
    bob,
    valid_transfer_recipient,
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

    # Transfer funds through agent sender
    transfer_amount = 50 * EIGHTEEN_DECIMALS
    actual_transfer_amount, usd_value = starter_agent_sender.transferFunds(
        starter_agent.address,
        user_wallet.address,
        valid_transfer_recipient,
        alpha_token.address,
        transfer_amount,
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
    # Verify events
    assert log.op == 1  # transfer funds
    assert log.asset1 == alpha_token.address
    assert log.asset2 == valid_transfer_recipient
    assert log.amount1 == actual_transfer_amount
    assert log.usdValue == usd_value

    # Verify results
    assert actual_transfer_amount == transfer_amount
    assert usd_value == 100 * EIGHTEEN_DECIMALS  # 50 tokens * $2
    
    # Verify balances
    assert alpha_token.balanceOf(user_wallet) == amount - transfer_amount
    assert alpha_token.balanceOf(valid_transfer_recipient) == transfer_amount


def test_agent_claim_rewards_basic(
    starter_agent,
    starter_agent_sender,
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

    # Claim rewards through agent sender
    amount_claimed, usd_value = starter_agent_sender.claimIncentives(
        starter_agent.address,
        user_wallet.address,
        3,
        mock_dex_asset.address,
        reward_amount,
        [],
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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

    # Convert ETH to WETH through agent sender
    convert_amount = 2 * EIGHTEEN_DECIMALS

    amount_converted, usd_value = starter_agent_sender.convertEthToWeth(
        starter_agent.address,
        user_wallet.address,
        convert_amount,
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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
    starter_agent_sender,
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

    # Convert WETH to ETH through agent sender
    convert_amount = 1 * EIGHTEEN_DECIMALS

    amount_converted, usd_value = starter_agent_sender.convertWethToEth(
        starter_agent.address,
        user_wallet.address,
        convert_amount,
        (b"", 0, 0),
        sender=charlie
    )
    log = filter_logs(starter_agent_sender, "WalletAction")[0]
    
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


def test_agent_create_and_pay_cheque_happy_path(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    mock_ripe,
    bob,
    alice,
    charlie,
    createChequeSettings,
):
    amount = 25 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _expensive_delay_blocks=5,
    )

    recipient_balance_before = alpha_token.balanceOf(alice)
    wallet_balance_before = alpha_token.balanceOf(user_wallet)

    amount_paid, usd_value = starter_agent_sender.createAndPayCheque(
        starter_agent.address,
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        (b"", 0, 0),
        sender=charlie
    )
    agent_log = filter_logs(starter_agent_sender, "AgentAction")[0]
    wallet_log = filter_logs(starter_agent_sender, "WalletAction")[0]

    assert agent_log.action == 4
    assert agent_log.userWallet == user_wallet.address
    assert agent_log.sender == starter_agent_sender.address

    assert wallet_log.op == 1
    assert wallet_log.asset1 == alpha_token.address
    assert wallet_log.amount1 == amount
    assert wallet_log.usdValue == usd_value

    assert amount_paid == amount
    assert usd_value == amount
    assert alpha_token.balanceOf(alice) == recipient_balance_before + amount
    assert alpha_token.balanceOf(user_wallet) == wallet_balance_before - amount
    assert user_wallet_config.cheques(alice).active == False


def test_agent_create_and_pay_cheque_reverts_above_threshold(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    charlie,
    createChequeSettings,
):
    amount = 60 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=50 * EIGHTEEN_DECIMALS,
        _expensive_delay_blocks=10,
    )

    active_cheques_before = user_wallet_config.numActiveCheques()

    with boa.reverts():
        starter_agent_sender.createAndPayCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            amount,
            (b"", 0, 0),
            sender=charlie
        )

    assert user_wallet_config.numActiveCheques() == active_cheques_before
    assert user_wallet_config.cheques(alice).active == False


def test_agent_create_and_pay_cheque_reverts_when_global_can_manager_pay_disabled(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    charlie,
    createChequeSettings,
):
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _can_manager_pay=False,
    )

    with boa.reverts():
        starter_agent_sender.createAndPayCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            25 * EIGHTEEN_DECIMALS,
            (b"", 0, 0),
            sender=charlie
        )


def test_agent_create_and_pay_cheque_reverts_when_managers_cannot_create_cheques(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    charlie,
    createChequeSettings,
):
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _can_managers_create_cheques=False,
    )

    with boa.reverts():
        starter_agent_sender.createAndPayCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            25 * EIGHTEEN_DECIMALS,
            (b"", 0, 0),
            sender=charlie
        )


def test_agent_create_and_pay_cheque_reverts_when_manager_cannot_create_cheque(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    charlie,
    high_command,
    createChequeSettings,
    createManagerSettings,
    createTransferPerms,
):
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
    )

    original_settings = _set_agent_transfer_perms(
        user_wallet_config,
        high_command,
        starter_agent,
        createManagerSettings,
        createTransferPerms,
        _can_transfer=True,
        _can_create_cheque=False,
    )
    active_cheques_before = user_wallet_config.numActiveCheques()

    try:
        with boa.reverts():
            starter_agent_sender.createAndPayCheque(
                starter_agent.address,
                user_wallet.address,
                alice,
                alpha_token.address,
                25 * EIGHTEEN_DECIMALS,
                (b"", 0, 0),
                sender=charlie
            )
        assert user_wallet_config.numActiveCheques() == active_cheques_before
        assert user_wallet_config.cheques(alice).active == False
    finally:
        user_wallet_config.updateManager(starter_agent.address, original_settings, sender=high_command.address)


def test_agent_create_and_pay_cheque_reverts_when_manager_cannot_transfer(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    charlie,
    high_command,
    createChequeSettings,
    createManagerSettings,
    createTransferPerms,
):
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
    )

    original_settings = _set_agent_transfer_perms(
        user_wallet_config,
        high_command,
        starter_agent,
        createManagerSettings,
        createTransferPerms,
        _can_transfer=False,
        _can_create_cheque=True,
    )

    try:
        with boa.reverts():
            starter_agent_sender.createAndPayCheque(
                starter_agent.address,
                user_wallet.address,
                alice,
                alpha_token.address,
                25 * EIGHTEEN_DECIMALS,
                (b"", 0, 0),
                sender=charlie
            )
    finally:
        user_wallet_config.updateManager(starter_agent.address, original_settings, sender=high_command.address)


def test_agent_create_and_pay_cheque_does_not_consume_generic_manager_quota_on_create(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    charlie,
    high_command,
    createChequeSettings,
    createManagerSettings,
    createManagerLimits,
):
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
    )

    original_settings = user_wallet_config.managerSettings(starter_agent.address)
    updated_settings = createManagerSettings(
        _startBlock=original_settings.startBlock,
        _expiryBlock=original_settings.expiryBlock,
        _limits=createManagerLimits(_maxNumTxsPerPeriod=1, _txCooldownBlocks=1),
        _legoPerms=original_settings.legoPerms,
        _swapPerms=original_settings.swapPerms,
        _whitelistPerms=original_settings.whitelistPerms,
        _transferPerms=original_settings.transferPerms,
        _allowedAssets=list(original_settings.allowedAssets),
        _canClaimLoot=original_settings.canClaimLoot,
    )
    user_wallet_config.updateManager(starter_agent.address, updated_settings, sender=high_command.address)

    try:
        amount_paid, usd_value = starter_agent_sender.createAndPayCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            25 * EIGHTEEN_DECIMALS,
            (b"", 0, 0),
            sender=charlie
        )
        manager_data = user_wallet_config.managerPeriodData(starter_agent.address)

        assert amount_paid == 25 * EIGHTEEN_DECIMALS
        assert usd_value == 25 * EIGHTEEN_DECIMALS
        assert manager_data.numTxsInPeriod == 1
        assert manager_data.totalNumTxs == 1
        assert manager_data.lastTxBlock == boa.env.evm.patch.block_number
        assert user_wallet_config.cheques(alice).active == False
    finally:
        user_wallet_config.updateManager(starter_agent.address, original_settings, sender=high_command.address)


def test_agent_create_and_pay_cheque_ignores_allowed_payees_for_cheque_payments(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    sally,
    charlie,
    high_command,
    createChequeSettings,
    createManagerSettings,
    createTransferPerms,
):
    amount = 25 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
    )

    original_settings = _set_agent_transfer_perms(
        user_wallet_config,
        high_command,
        starter_agent,
        createManagerSettings,
        createTransferPerms,
        _can_transfer=True,
        _can_create_cheque=True,
        _allowed_payees=[sally],
    )

    recipient_balance_before = alpha_token.balanceOf(alice)
    wallet_balance_before = alpha_token.balanceOf(user_wallet)

    try:
        amount_paid, usd_value = starter_agent_sender.createAndPayCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            amount,
            (b"", 0, 0),
            sender=charlie
        )
        assert amount_paid == amount
        assert usd_value == amount
        assert alpha_token.balanceOf(alice) == recipient_balance_before + amount
        assert alpha_token.balanceOf(user_wallet) == wallet_balance_before - amount
        assert user_wallet_config.cheques(alice).active == False
    finally:
        user_wallet_config.updateManager(starter_agent.address, original_settings, sender=high_command.address)


def test_agent_create_and_pay_cheque_reverts_for_existing_active_cheque(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    charlie,
    createChequeSettings,
):
    amount = 25 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=100 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
    )

    cheque_book.createCheque(
        user_wallet.address,
        alice,
        alpha_token.address,
        amount,
        0,
        0,
        True,
        False,
        sender=bob
    )

    active_cheques_before = user_wallet_config.numActiveCheques()

    with boa.reverts("recipient has active cheque"):
        starter_agent_sender.createAndPayCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            amount,
            (b"", 0, 0),
            sender=charlie
        )

    assert user_wallet_config.numActiveCheques() == active_cheques_before
    assert user_wallet_config.cheques(alice).active == True

    user_wallet_config.cancelCheque(alice, sender=cheque_book.address)


def test_agent_create_and_pay_cheque_reverts_for_insufficient_balance(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    charlie,
    createChequeSettings,
):
    wallet_amount = 10 * EIGHTEEN_DECIMALS
    requested_amount = 25 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=wallet_amount,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
    )

    active_cheques_before = user_wallet_config.numActiveCheques()

    with boa.reverts():
        starter_agent_sender.createAndPayCheque(
            starter_agent.address,
            user_wallet.address,
            alice,
            alpha_token.address,
            requested_amount,
            (b"", 0, 0),
            sender=charlie
        )

    assert user_wallet_config.numActiveCheques() == active_cheques_before
    assert user_wallet_config.cheques(alice).active == False


def test_agent_create_cheque_and_pay_cheque_expected_block(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    charlie,
    env,
    createChequeSettings,
):
    recipient = env.generate_address("agent_pay_cheque_recipient")
    amount = 12 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=50 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
    )

    assert starter_agent_sender.createCheque(
        starter_agent.address,
        user_wallet.address,
        recipient,
        alpha_token.address,
        amount,
        0,
        0,
        True,
        False,
        (b"", 0, 0),
        sender=charlie
    )
    create_log = filter_logs(starter_agent_sender, "AgentAction")[0]
    assert create_log.action == 5
    cheque = user_wallet_config.cheques(recipient)
    assert cheque.active == True
    assert cheque.canManagerPay == True
    assert cheque.canBePulled == False

    recipient_balance_before = alpha_token.balanceOf(recipient)
    amount_paid, usd_value = starter_agent_sender.payCheque(
        starter_agent.address,
        user_wallet.address,
        recipient,
        alpha_token.address,
        amount,
        cheque.creationBlock,
        (b"", 0, 0),
        sender=charlie
    )
    agent_log = filter_logs(starter_agent_sender, "AgentAction")[0]

    assert agent_log.action == 6
    assert amount_paid == amount
    assert usd_value == amount
    assert alpha_token.balanceOf(recipient) == recipient_balance_before + amount
    assert user_wallet_config.cheques(recipient).active == False


def test_agent_batch_transfer_cannot_flip_into_cheque_mode(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    charlie,
    env,
    createChequeSettings,
):
    recipient = env.generate_address("agent_batch_cheque_flip_recipient")
    amount = 8 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=50 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
    )
    cheque_book.createCheque(
        user_wallet.address,
        recipient,
        alpha_token.address,
        amount,
        0,
        0,
        True,
        False,
        sender=bob
    )

    instruction = (
        False,
        1,
        0,
        alpha_token.address,
        recipient,
        amount,
        ZERO_ADDRESS,
        0,
        0,
        0,
        0,
        0,
        (1).to_bytes(32, "big"),
        b"\x00" * 32,
        [],
        [],
    )

    # This bubbles through nested wallet/payee validation without a stable Boa-visible reason.
    # The state checks below verify the standard transfer path did not pay the cheque.
    with boa.reverts():
        starter_agent_sender.performBatchActions(
            starter_agent.address,
            user_wallet.address,
            [instruction],
            (b"", 0, 0),
            sender=charlie
        )

    assert user_wallet_config.cheques(recipient).active == True
    assert alpha_token.balanceOf(recipient) == 0
    cheque_book.cancelCheque(user_wallet.address, recipient, sender=bob)


def test_agent_cancel_cheque_requires_owner_or_security_wrapper(
    setupAgentTestAsset,
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    charlie,
    switchboard_alpha,
    mission_control,
    undy_hq_deploy,
    env,
    createChequeSettings,
):
    recipient = env.generate_address("agent_cancel_cheque_recipient")
    amount = 9 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=50 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
    )
    cheque_book.createCheque(
        user_wallet.address,
        recipient,
        alpha_token.address,
        amount,
        0,
        0,
        True,
        False,
        sender=bob
    )

    with boa.reverts("no perms"):
        starter_agent_sender.cancelCheque(
            starter_agent.address,
            user_wallet.address,
            recipient,
            (b"", 0, 0),
            sender=charlie
        )

    security_agent = boa.load(
        "contracts/core/agent/AgentWrapper.vy",
        undy_hq_deploy,
        1,
        name="security_agent",
    )
    security_agent.addSender(starter_agent_sender, sender=switchboard_alpha.address)
    mission_control.setCanPerformSecurityAction(security_agent.address, True, sender=switchboard_alpha.address)

    assert starter_agent_sender.cancelCheque(
        security_agent.address,
        user_wallet.address,
        recipient,
        (b"", 0, 0),
        sender=charlie
    )
    assert filter_logs(starter_agent_sender, "AgentAction")[0].action == 7
    assert user_wallet_config.cheques(recipient).active == False


def test_agent_whitelist_and_empty_loot_actions(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    loot_distributor,
    kernel,
    bob,
    charlie,
    env,
):
    pending_addr = env.generate_address("agent_pending_whitelist")
    cancel_addr = env.generate_address("agent_cancel_whitelist")

    kernel.addPendingWhitelistAddr(user_wallet.address, pending_addr, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    assert starter_agent_sender.confirmWhitelistAddr(
        starter_agent.address,
        user_wallet.address,
        pending_addr,
        (b"", 0, 0),
        sender=charlie
    )
    assert filter_logs(starter_agent_sender, "AgentAction")[0].action == 60
    assert user_wallet_config.indexOfWhitelist(pending_addr) != 0

    assert starter_agent_sender.removeWhitelistAddr(
        starter_agent.address,
        user_wallet.address,
        pending_addr,
        (b"", 0, 0),
        sender=charlie
    )
    assert filter_logs(starter_agent_sender, "AgentAction")[0].action == 62
    assert user_wallet_config.indexOfWhitelist(pending_addr) == 0

    kernel.addPendingWhitelistAddr(user_wallet.address, cancel_addr, sender=bob)
    assert starter_agent_sender.cancelPendingWhitelistAddr(
        starter_agent.address,
        user_wallet.address,
        cancel_addr,
        (b"", 0, 0),
        sender=charlie
    )
    assert filter_logs(starter_agent_sender, "AgentAction")[0].action == 61
    assert user_wallet_config.pendingWhitelist(cancel_addr).initiatedBlock == 0

    assert starter_agent_sender.canClaimLootFor(starter_agent.address, user_wallet.address) == True
    result = starter_agent_sender.claimAllLoot(
        starter_agent.address,
        user_wallet.address,
        (b"", 0, 0),
        sender=charlie
    )
    assert filter_logs(starter_agent_sender, "AgentAction")[0].action == 80
    assert result == False
    assert loot_distributor.lastClaim(user_wallet.address) == 0

    with boa.reverts("no assets claimed"):
        starter_agent_sender.claimRevShareAndBonusLoot(
            starter_agent.address,
            user_wallet.address,
            (b"", 0, 0),
            sender=charlie,
        )

    with boa.reverts("nothing to claim"):
        starter_agent_sender.claimDepositRewards(
            starter_agent.address,
            user_wallet.address,
            (b"", 0, 0),
            sender=charlie,
        )


def test_agent_whitelist_permission_matrix_and_security_fallback(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    kernel,
    high_command,
    mission_control,
    switchboard_alpha,
    migrator,
    bob,
    charlie,
    env,
    createGlobalManagerSettings,
    createManagerSettings,
    createWhitelistPerms,
):
    assert not hasattr(starter_agent_sender, "addPendingWhitelistAddr")

    global_whitelist_perms = createWhitelistPerms(
        _canAddPending=True,
        _canConfirm=True,
        _canCancel=True,
        _canRemove=True,
    )
    user_wallet_config.setGlobalManagerSettings(
        createGlobalManagerSettings(_whitelistPerms=global_whitelist_perms),
        sender=high_command.address,
    )
    _set_agent_whitelist_perms(
        user_wallet_config,
        high_command,
        starter_agent,
        createManagerSettings,
        createWhitelistPerms,
        _can_confirm=True,
        _can_cancel=False,
        _can_remove=False,
    )

    confirm_addr = env.generate_address("agent_matrix_confirm")
    kernel.addPendingWhitelistAddr(user_wallet.address, confirm_addr, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    assert starter_agent_sender.confirmWhitelistAddr(
        starter_agent.address,
        user_wallet.address,
        confirm_addr,
        (b"", 0, 0),
        sender=charlie,
    )

    cancel_addr = env.generate_address("agent_matrix_cancel")
    kernel.addPendingWhitelistAddr(user_wallet.address, cancel_addr, sender=bob)
    with boa.reverts("no perms"):
        starter_agent_sender.cancelPendingWhitelistAddr(
            starter_agent.address,
            user_wallet.address,
            cancel_addr,
            (b"", 0, 0),
            sender=charlie,
        )

    remove_addr = env.generate_address("agent_matrix_remove")
    user_wallet_config.addWhitelistAddrViaMigrator(remove_addr, sender=migrator.address)
    with boa.reverts("no perms"):
        starter_agent_sender.removeWhitelistAddr(
            starter_agent.address,
            user_wallet.address,
            remove_addr,
            (b"", 0, 0),
            sender=charlie,
        )

    _set_agent_whitelist_perms(
        user_wallet_config,
        high_command,
        starter_agent,
        createManagerSettings,
        createWhitelistPerms,
        _can_confirm=True,
        _can_cancel=True,
        _can_remove=True,
    )
    restricted_global_perms = createWhitelistPerms(
        _canAddPending=True,
        _canConfirm=False,
        _canCancel=False,
        _canRemove=False,
    )
    user_wallet_config.setGlobalManagerSettings(
        createGlobalManagerSettings(_whitelistPerms=restricted_global_perms),
        sender=high_command.address,
    )

    restricted_confirm_addr = env.generate_address("agent_matrix_global_confirm")
    kernel.addPendingWhitelistAddr(user_wallet.address, restricted_confirm_addr, sender=bob)
    boa.env.time_travel(blocks=user_wallet_config.timeLock())
    with boa.reverts("no perms"):
        starter_agent_sender.confirmWhitelistAddr(
            starter_agent.address,
            user_wallet.address,
            restricted_confirm_addr,
            (b"", 0, 0),
            sender=charlie,
        )

    mission_control.setCanPerformSecurityAction(starter_agent.address, True, sender=switchboard_alpha.address)

    security_cancel_addr = env.generate_address("agent_matrix_security_cancel")
    kernel.addPendingWhitelistAddr(user_wallet.address, security_cancel_addr, sender=bob)
    assert starter_agent_sender.cancelPendingWhitelistAddr(
        starter_agent.address,
        user_wallet.address,
        security_cancel_addr,
        (b"", 0, 0),
        sender=charlie,
    )

    security_remove_addr = env.generate_address("agent_matrix_security_remove")
    user_wallet_config.addWhitelistAddrViaMigrator(security_remove_addr, sender=migrator.address)
    assert starter_agent_sender.removeWhitelistAddr(
        starter_agent.address,
        user_wallet.address,
        security_remove_addr,
        (b"", 0, 0),
        sender=charlie,
    )


def test_agent_loot_requires_claim_permission_for_all_methods(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    high_command,
    charlie,
    createManagerSettings,
):
    _set_agent_claim_loot_perm(
        user_wallet_config,
        high_command,
        starter_agent,
        createManagerSettings,
        False,
    )

    assert starter_agent_sender.canClaimLootFor(starter_agent.address, user_wallet.address) == False

    with boa.reverts("no perms"):
        starter_agent_sender.claimAllLoot(
            starter_agent.address,
            user_wallet.address,
            (b"", 0, 0),
            sender=charlie,
        )

    with boa.reverts("no perms"):
        starter_agent_sender.claimRevShareAndBonusLoot(
            starter_agent.address,
            user_wallet.address,
            (b"", 0, 0),
            sender=charlie,
        )

    with boa.reverts("no perms"):
        starter_agent_sender.claimDepositRewards(
            starter_agent.address,
            user_wallet.address,
            (b"", 0, 0),
            sender=charlie,
        )


def test_agent_loot_claims_rev_share_and_all_loot_success(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    loot_distributor,
    yield_vault_token,
    yield_underlying_token,
    yield_underlying_token_whale,
    mock_yield_lego,
    mock_ripe_token,
    mock_ripe,
    whale,
    setUserWalletConfig,
    setAssetConfig,
    createAssetYieldConfig,
    charlie,
):
    setUserWalletConfig(_lootClaimCoolOffPeriod=0)
    yield_config = createAssetYieldConfig(
        _bonusRatio=30_00,
        _bonusAsset=mock_ripe_token.address,
    )
    setAssetConfig(yield_vault_token, _yieldConfig=yield_config)
    mock_ripe.setPrice(yield_vault_token, 10 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(yield_underlying_token, 10 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_ripe_token, 4 * EIGHTEEN_DECIMALS)
    mock_ripe_token.transfer(loot_distributor, 500 * EIGHTEEN_DECIMALS, sender=whale)

    def add_user_yield_bonus():
        yield_underlying_token.approve(mock_yield_lego, 1000 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
        mock_yield_lego.depositForYield(
            yield_underlying_token,
            1000 * EIGHTEEN_DECIMALS,
            yield_vault_token,
            sender=yield_underlying_token_whale,
        )
        yield_vault_token.transfer(loot_distributor, 10 * EIGHTEEN_DECIMALS, sender=yield_underlying_token_whale)
        loot_distributor.addLootFromYieldProfit(
            yield_vault_token,
            10 * EIGHTEEN_DECIMALS,
            100 * EIGHTEEN_DECIMALS,
            sender=user_wallet.address,
        )

    add_user_yield_bonus()
    assert loot_distributor.claimableLoot(user_wallet.address, mock_ripe_token.address) > 0
    assert starter_agent_sender.claimRevShareAndBonusLoot(
        starter_agent.address,
        user_wallet.address,
        (b"", 0, 0),
        sender=charlie,
    ) > 0
    assert filter_logs(starter_agent_sender, "AgentAction")[0].action == 81

    add_user_yield_bonus()
    assert starter_agent_sender.claimAllLoot(
        starter_agent.address,
        user_wallet.address,
        (b"", 0, 0),
        sender=charlie,
    ) == True
    assert filter_logs(starter_agent_sender, "AgentAction")[0].action == 80


def test_agent_loot_cooloff_applies_to_wrapper_but_not_switchboard(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    user_wallet_config,
    loot_distributor,
    alpha_token,
    alpha_token_whale,
    setUserWalletConfig,
    switchboard_alpha,
    charlie,
):
    setUserWalletConfig(_depositRewardsAsset=alpha_token.address, _lootClaimCoolOffPeriod=50)

    def add_deposit_rewards():
        alpha_token.approve(loot_distributor.address, 500 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
        loot_distributor.addDepositRewards(alpha_token.address, 500 * EIGHTEEN_DECIMALS, sender=alpha_token_whale)
        loot_distributor.updateDepositPointsWithNewValue(
            user_wallet.address,
            100 * EIGHTEEN_DECIMALS,
            sender=user_wallet_config.address,
        )
        boa.env.time_travel(blocks=1)
        loot_distributor.updateDepositPoints(user_wallet.address, sender=switchboard_alpha.address)

    add_deposit_rewards()
    assert starter_agent_sender.claimDepositRewards(
        starter_agent.address,
        user_wallet.address,
        (b"", 0, 0),
        sender=charlie,
    ) > 0
    assert filter_logs(starter_agent_sender, "AgentAction")[0].action == 82
    assert loot_distributor.lastClaim(user_wallet.address) == boa.env.evm.patch.block_number

    add_deposit_rewards()
    with boa.reverts("no perms"):
        starter_agent_sender.claimDepositRewards(
            starter_agent.address,
            user_wallet.address,
            (b"", 0, 0),
            sender=charlie,
        )

    assert loot_distributor.claimDepositRewards(user_wallet.address, sender=switchboard_alpha.address) > 0


def test_agent_remove_self_as_manager_multi_manager_preserves_pending_ops(
    starter_agent,
    starter_agent_sender,
    user_wallet,
    hatchery,
    high_command,
    kernel,
    bob,
    alice,
    charlie,
    env,
    createManagerLimits,
    createLegoPerms,
    createSwapPerms,
    createWhitelistPerms,
    createTransferPerms,
):
    fresh_wallet = UserWallet.at(hatchery.createUserWallet(bob, ZERO_ADDRESS, 1, sender=bob))
    fresh_config = UserWalletConfig.at(fresh_wallet.walletConfig())
    assert fresh_config.indexOfManager(starter_agent.address) != 0

    high_command.addManager(
        fresh_wallet.address,
        alice,
        createManagerLimits(),
        createLegoPerms(),
        createSwapPerms(),
        createWhitelistPerms(),
        createTransferPerms(),
        [],
        False,
        sender=bob,
    )
    assert fresh_config.numManagers() > 1

    pending_addr = env.generate_address("self_remove_pending_whitelist")
    kernel.addPendingWhitelistAddr(fresh_wallet.address, pending_addr, sender=bob)
    pending_block = fresh_config.pendingWhitelist(pending_addr).initiatedBlock
    assert pending_block != 0

    assert starter_agent_sender.removeSelfAsManager(
        starter_agent.address,
        fresh_wallet.address,
        (b"", 0, 0),
        sender=charlie,
    )
    assert filter_logs(starter_agent_sender, "AgentAction")[0].action == 70
    assert fresh_config.indexOfManager(starter_agent.address) == 0
    assert fresh_config.pendingWhitelist(pending_addr).initiatedBlock == pending_block

    with boa.reverts("no permission"):
        starter_agent_sender.transferFunds(
            starter_agent.address,
            fresh_wallet.address,
            bob,
            ZERO_ADDRESS,
            1,
            (b"", 0, 0),
            sender=charlie,
        )

    assert starter_agent_sender.canClaimLootFor(starter_agent.address, user_wallet.address) == True


def test_agent_remove_self_as_manager_single_manager_reverts(
    starter_agent,
    starter_agent_sender,
    hatchery,
    bob,
    charlie,
):
    fresh_wallet = UserWallet.at(hatchery.createUserWallet(bob, ZERO_ADDRESS, 1, sender=bob))
    fresh_config = UserWalletConfig.at(fresh_wallet.walletConfig())
    assert fresh_config.numManagers() == 2  # sentinel index + starter agent

    with boa.reverts("only manager"):
        starter_agent_sender.removeSelfAsManager(
            starter_agent.address,
            fresh_wallet.address,
            (b"", 0, 0),
            sender=charlie,
        )
    assert fresh_config.indexOfManager(starter_agent.address) != 0


def test_special_admin_issue_pull_cheques_and_duplicate_whitelist_precheck(
    setupAgentTestAsset,
    special_admin_sender,
    starter_agent,
    user_wallet,
    user_wallet_config,
    cheque_book,
    alpha_token,
    alpha_token_whale,
    bob,
    alice,
    charlie,
    env,
    createChequeSettings,
):
    recipient_a = env.generate_address("agent_pull_cheque_a")
    recipient_b = env.generate_address("agent_pull_cheque_b")
    amount = 7 * EIGHTEEN_DECIMALS
    setupAgentTestAsset(
        _asset=alpha_token,
        _amount=50 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=1 * EIGHTEEN_DECIMALS,
    )
    _set_instant_cheque_settings(
        cheque_book,
        user_wallet,
        bob,
        createChequeSettings,
        _instant_usd_threshold=100 * EIGHTEEN_DECIMALS,
        _can_manager_pay=False,
        _can_be_pulled=True,
    )

    with boa.reverts("invalid pull cheque flags"):
        special_admin_sender.issuePullCheques(
            starter_agent.address,
            user_wallet.address,
            [(recipient_a, alpha_token.address, amount, 0, 0, True, False)],
            (b"", 0, 0),
            sender=charlie
        )
    assert user_wallet_config.cheques(recipient_a).active == False

    cheques = [
        (recipient_a, alpha_token.address, amount, 0, 0, False, True),
        (recipient_b, alpha_token.address, amount, 0, 0, False, True),
    ]
    special_admin_sender.issuePullCheques(
        starter_agent.address,
        user_wallet.address,
        cheques,
        (b"", 0, 0),
        sender=charlie
    )

    cheque_a = user_wallet_config.cheques(recipient_a)
    cheque_b = user_wallet_config.cheques(recipient_b)
    assert cheque_a.active == True and cheque_b.active == True
    assert cheque_a.canManagerPay == False and cheque_b.canManagerPay == False
    assert cheque_a.canBePulled == True and cheque_b.canBePulled == True

    nonce_before = special_admin_sender.currentNonce(user_wallet.address)
    with boa.reverts("duplicate addr"):
        special_admin_sender.whitelistMaintenance(
            starter_agent.address,
            user_wallet.address,
            [alice],
            [alice],
            [],
            (b"\x00" * 65, nonce_before, boa.env.evm.patch.timestamp + 1000),
            sender=alice
        )
    assert special_admin_sender.currentNonce(user_wallet.address) == nonce_before

    with boa.reverts("duplicate addr"):
        special_admin_sender.whitelistMaintenance(
            starter_agent.address,
            user_wallet.address,
            [alice, alice],
            [],
            [],
            (b"\x00" * 65, nonce_before, boa.env.evm.patch.timestamp + 1000),
            sender=alice
        )
    assert special_admin_sender.currentNonce(user_wallet.address) == nonce_before

    with boa.reverts("empty cheque recipient"):
        special_admin_sender.harvestAndIssueCheque(
            starter_agent.address,
            user_wallet.address,
            0,
            ZERO_ADDRESS,
            0,
            [],
            [],
            (ZERO_ADDRESS, alpha_token.address, amount, 0, 0, False, True),
            (b"", 0, 0),
            sender=charlie
        )
