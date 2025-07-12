import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from contracts.core.userWallet import UserWalletConfig
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


@pytest.fixture(scope="module")
def createActionInstruction():
    def createActionInstruction(
        action,
        usePrevAmountOut=False,
        legoId=0,
        asset=ZERO_ADDRESS,
        target=ZERO_ADDRESS,
        amount=0,
        asset2=ZERO_ADDRESS,
        amount2=0,
        minOut1=0,
        minOut2=0,
        tickLower=0,
        tickUpper=0,
        extraData=b"",
        auxData=b"",
        swapInstructions=None
    ):
        """Helper to create ActionInstruction tuple"""
        if swapInstructions is None:
            swapInstructions = []
        
        return (
            usePrevAmountOut,
            action,
            legoId,
            asset,
            target,
            amount,
            asset2,
            amount2,
            minOut1,
            minOut2,
            tickLower,
            tickUpper,
            extraData,
            auxData,
            swapInstructions
        )

    yield createActionInstruction


def test_batch_deposit_and_withdraw_yield(
    setupAgentTestAsset,
    createActionInstruction,
    starter_agent,
    user_wallet,
    charlie,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
):
    """Test batch actions: deposit then withdraw yield"""
    
    # Setup underlying tokens
    amount = setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=200 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _lego_id=1,
        _shouldCheckYield=False
    )
    
    # Create batch instructions: deposit 100, then withdraw 50
    instructions = [
        createActionInstruction(
            action=1,  # depositForYield
            legoId=1,
            asset=yield_underlying_token.address,
            target=yield_vault_token.address,
            amount=100 * EIGHTEEN_DECIMALS,
        ),
        createActionInstruction(
            action=2,  # withdrawFromYield
            legoId=1,
            asset=yield_vault_token.address,
            amount=50 * EIGHTEEN_DECIMALS,
        )
    ]
    
    # Execute batch actions
    result = starter_agent.performBatchActions(
        user_wallet.address,
        instructions,
        sender=charlie
    )
    
    assert result == True
    
    # Check events - should have both deposit and withdraw
    logs = filter_logs(starter_agent, "WalletAction")
    assert len(logs) == 2
    
    # First action: deposit
    assert logs[0].op == 10  # deposit for yield
    assert logs[0].asset1 == yield_underlying_token.address
    assert logs[0].asset2 == yield_vault_token.address
    assert logs[0].amount1 == 100 * EIGHTEEN_DECIMALS
    
    # Second action: withdraw
    assert logs[1].op == 11  # withdraw from yield
    assert logs[1].asset1 == yield_vault_token.address
    assert logs[1].asset2 == yield_underlying_token.address
    assert logs[1].amount1 == 50 * EIGHTEEN_DECIMALS
    
    # Check final balances
    assert yield_underlying_token.balanceOf(user_wallet) == 100 * EIGHTEEN_DECIMALS + logs[1].amount2
    assert yield_vault_token.balanceOf(user_wallet) == logs[0].amount2 - 50 * EIGHTEEN_DECIMALS


def test_batch_multiple_swaps(
    setupAgentTestAsset,
    createActionInstruction,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_asset_alt,
    mock_dex_lp_token,
    whale,
    mock_ripe
):
    """Test batch actions: multiple token swaps in sequence"""
    
    # Setup initial assets
    setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=1000 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )
    
    # Setup alt asset for second swap
    setupAgentTestAsset(
        _asset=mock_dex_asset_alt,
        _amount=500 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=3 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )
    
    # Set LP token price
    mock_ripe.setPrice(mock_dex_lp_token, 5 * EIGHTEEN_DECIMALS)
    
    # Create batch instructions: swap1, then swap2
    instructions = [
        createActionInstruction(
            action=4,  # swapTokens
            legoId=2,
            asset=mock_dex_asset.address,
            target=mock_dex_asset_alt.address,
            amount=200 * EIGHTEEN_DECIMALS,
            extraData=b"\x00" * 32,
            auxData=b"\x00" * 32,
            swapInstructions=[(
                2,  # legoId
                200 * EIGHTEEN_DECIMALS,  # amountIn
                0,  # minAmountOut
                [mock_dex_asset.address, mock_dex_asset_alt.address],  # tokenPath
                []  # poolPath
            )]
        ),
        createActionInstruction(
            action=4,  # swapTokens
            legoId=2,
            asset=mock_dex_asset_alt.address,
            target=mock_dex_lp_token.address,
            amount=100 * EIGHTEEN_DECIMALS,
            extraData=b"\x00" * 32,
            auxData=b"\x00" * 32,
            swapInstructions=[(
                2,
                100 * EIGHTEEN_DECIMALS,
                0,
                [mock_dex_asset_alt.address, mock_dex_lp_token.address],
                []
            )]
        )
    ]
    
    # Execute batch actions
    result = starter_agent.performBatchActions(
        user_wallet.address,
        instructions,
        sender=charlie
    )
    
    assert result == True
    
    # Check events
    logs = filter_logs(starter_agent, "WalletAction")
    assert len(logs) == 2
    
    # First swap
    assert logs[0].op == 20  # swap
    assert logs[0].asset1 == mock_dex_asset.address
    assert logs[0].asset2 == mock_dex_asset_alt.address
    assert logs[0].amount1 == 200 * EIGHTEEN_DECIMALS
    
    # Second swap
    assert logs[1].op == 20  # swap
    assert logs[1].asset1 == mock_dex_asset_alt.address
    assert logs[1].asset2 == mock_dex_lp_token.address
    assert logs[1].amount1 == 100 * EIGHTEEN_DECIMALS
    
    # Check final balances
    assert mock_dex_asset.balanceOf(user_wallet) == 800 * EIGHTEEN_DECIMALS  # Started with 1000, swapped 200
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 600 * EIGHTEEN_DECIMALS  # 500 + 200 - 100
    assert mock_dex_lp_token.balanceOf(user_wallet) == 100 * EIGHTEEN_DECIMALS  # Received from second swap


def test_batch_with_prev_amount_out(
    setupAgentTestAsset,
    createActionInstruction,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_asset_alt,
    mock_dex_lp_token,
    whale,
    mock_ripe
):
    """Test batch actions using previous instruction's output amount"""
    
    # Setup initial asset
    setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=500 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )
    
    # Set prices
    mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(mock_dex_lp_token, 5 * EIGHTEEN_DECIMALS)
    
    # Create batch: swap all of asset1 to asset2, then swap all received asset2 to LP token
    instructions = [
        createActionInstruction(
            action=4,  # swapTokens
            legoId=2,
            asset=mock_dex_asset.address,
            target=mock_dex_asset_alt.address,
            amount=300 * EIGHTEEN_DECIMALS,
            swapInstructions=[(
                2,
                300 * EIGHTEEN_DECIMALS,
                0,
                [mock_dex_asset.address, mock_dex_asset_alt.address],
                []
            )]
        ),
        createActionInstruction(
            action=4,  # swapTokens
            usePrevAmountOut=True,  # Use output from previous instruction
            legoId=2,
            asset=mock_dex_asset_alt.address,
            target=mock_dex_lp_token.address,
            amount=0,  # Will be overridden by prevAmount
            swapInstructions=[(
                2,
                300 * EIGHTEEN_DECIMALS,  # This will be replaced by prevAmount
                0,
                [mock_dex_asset_alt.address, mock_dex_lp_token.address],
                []
            )]
        )
    ]
    
    # Execute batch actions
    result = starter_agent.performBatchActions(
        user_wallet.address,
        instructions,
        sender=charlie
    )
    
    assert result == True
    
    # Check events
    logs = filter_logs(starter_agent, "WalletAction")
    assert len(logs) == 2
    
    # Both should be swaps, second uses output from first
    assert logs[0].op == 20 and logs[1].op == 20
    assert logs[1].amount1 == logs[0].amount2  # Second swap uses output from first
    
    # Final balances
    assert mock_dex_asset.balanceOf(user_wallet) == 200 * EIGHTEEN_DECIMALS  # 500 - 300
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 0  # All swapped in second transaction
    assert mock_dex_lp_token.balanceOf(user_wallet) == 300 * EIGHTEEN_DECIMALS  # Final output


def test_batch_mixed_operations(
    setupAgentTestAsset,
    createActionInstruction,
    starter_agent,
    user_wallet,
    charlie,
    yield_underlying_token,
    yield_vault_token,
    yield_underlying_token_whale,
    mock_dex_asset,
    mock_dex_asset_alt,
    whale,
    mock_ripe,
    bob,
):
    """Test batch with mixed operation types: transfer, deposit yield, swap"""
    
    # Setup yield underlying token
    setupAgentTestAsset(
        _asset=yield_underlying_token,
        _amount=300 * EIGHTEEN_DECIMALS,
        _whale=yield_underlying_token_whale,
        _price=10 * EIGHTEEN_DECIMALS,
        _lego_id=1,
        _shouldCheckYield=False
    )
    
    # Setup dex asset
    setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=200 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )
    
    mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)
    
    # Create diverse batch
    instructions = [
        createActionInstruction(
            action=0,  # transferFunds
            legoId=0,
            asset=yield_underlying_token.address,
            target=bob,  # Transfer to bob (owner of wallet)
            amount=50 * EIGHTEEN_DECIMALS,
        ),
        createActionInstruction(
            action=1,  # depositForYield
            legoId=1,
            asset=yield_underlying_token.address,
            target=yield_vault_token.address,
            amount=100 * EIGHTEEN_DECIMALS,
        ),
        createActionInstruction(
            action=4,  # swapTokens
            legoId=2,
            asset=mock_dex_asset.address,
            target=mock_dex_asset_alt.address,
            amount=150 * EIGHTEEN_DECIMALS,
            swapInstructions=[(
                2,
                150 * EIGHTEEN_DECIMALS,
                0,
                [mock_dex_asset.address, mock_dex_asset_alt.address],
                []
            )]
        )
    ]
    
    # Execute batch
    result = starter_agent.performBatchActions(
        user_wallet.address,
        instructions,
        sender=charlie
    )
    
    assert result == True
    
    # Verify events
    logs = filter_logs(starter_agent, "WalletAction")
    assert len(logs) == 3
    
    # Check each operation
    assert logs[0].op == 1  # transfer
    assert logs[0].asset1 == yield_underlying_token.address
    assert logs[0].amount1 == 50 * EIGHTEEN_DECIMALS
    
    assert logs[1].op == 10  # deposit for yield
    assert logs[1].asset1 == yield_underlying_token.address
    assert logs[1].amount1 == 100 * EIGHTEEN_DECIMALS
    
    assert logs[2].op == 20  # swap
    assert logs[2].asset1 == mock_dex_asset.address
    assert logs[2].amount1 == 150 * EIGHTEEN_DECIMALS
    
    # Check final balances
    assert yield_underlying_token.balanceOf(bob) == 50 * EIGHTEEN_DECIMALS
    assert yield_underlying_token.balanceOf(user_wallet) == 150 * EIGHTEEN_DECIMALS
    assert yield_vault_token.balanceOf(user_wallet) > 0
    assert mock_dex_asset.balanceOf(user_wallet) == 50 * EIGHTEEN_DECIMALS
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 150 * EIGHTEEN_DECIMALS


def test_batch_mint_and_redeem(
    setupAgentTestAsset,
    createActionInstruction,
    starter_agent,
    user_wallet,
    charlie,
    mock_dex_asset,
    mock_dex_asset_alt,
    mock_dex_lego,
    whale,
    mock_ripe
):
    """Test batch actions: mint then redeem assets"""
    
    # Setup assets
    setupAgentTestAsset(
        _asset=mock_dex_asset,
        _amount=400 * EIGHTEEN_DECIMALS,
        _whale=whale,
        _price=2 * EIGHTEEN_DECIMALS,
        _lego_id=2,
        _shouldCheckYield=False
    )
    
    mock_ripe.setPrice(mock_dex_asset_alt, 3 * EIGHTEEN_DECIMALS)
    
    # Set immediate mode for testing
    mock_dex_lego.setImmediateMintOrRedeem(True)
    
    # Create batch: mint asset_alt using asset, then redeem back
    instructions = [
        createActionInstruction(
            action=5,  # mintOrRedeemAsset
            legoId=2,
            asset=mock_dex_asset.address,
            target=mock_dex_asset_alt.address,
            amount=200 * EIGHTEEN_DECIMALS,
        ),
        createActionInstruction(
            action=5,  # mintOrRedeemAsset (redeem)
            usePrevAmountOut=True,  # Redeem all minted tokens
            legoId=2,
            asset=mock_dex_asset_alt.address,
            target=mock_dex_asset.address,
            amount=0,  # Will use prev amount
        )
    ]
    
    # Execute batch
    result = starter_agent.performBatchActions(
        user_wallet.address,
        instructions,
        sender=charlie
    )
    
    assert result == True
    
    # Check events
    logs = filter_logs(starter_agent, "WalletAction")
    assert len(logs) == 2
    
    # Both should be mint/redeem operations
    assert logs[0].op == 21  # MINT_REDEEM
    assert logs[1].op == 21  # MINT_REDEEM
    
    # Second operation uses output from first
    assert logs[1].amount1 == logs[0].amount2
    
    # Should end up with roughly same amount (minus any fees)
    assert mock_dex_asset.balanceOf(user_wallet) == 400 * EIGHTEEN_DECIMALS
    assert mock_dex_asset_alt.balanceOf(user_wallet) == 0


def test_batch_empty_instructions_reverts(
    starter_agent,
    user_wallet,
    charlie
):
    """Test that empty instruction array reverts"""
    
    with boa.reverts("no instructions"):
        starter_agent.performBatchActions(
            user_wallet.address,
            [],
            sender=charlie
        )


def test_batch_yield_rebalance(
    setupAgentTestAsset,
    createActionInstruction,
    starter_agent,
    user_wallet,
    charlie,
    alpha_token,
    alpha_token_whale,
    alpha_token_vault,
    alpha_token_vault_2,
):
    """Test batch actions with yield rebalancing"""
    
    # Setup alpha token
    amount = setupAgentTestAsset(
        _asset=alpha_token,
        _amount=300 * EIGHTEEN_DECIMALS,
        _whale=alpha_token_whale,
        _price=5 * EIGHTEEN_DECIMALS,
        _lego_id=1,
        _shouldCheckYield=False
    )
    
    # Create batch: deposit to vault1, then rebalance half to vault2
    instructions = [
        createActionInstruction(
            action=1,  # depositForYield
            legoId=1,
            asset=alpha_token.address,
            target=alpha_token_vault.address,
            amount=200 * EIGHTEEN_DECIMALS,
        ),
        createActionInstruction(
            action=3,  # rebalanceYieldPosition
            legoId=1,
            asset=alpha_token_vault.address,  # from vault token
            target=alpha_token_vault_2.address,  # to vault address
            amount=100 * EIGHTEEN_DECIMALS,  # vault tokens to rebalance
            amount2=1,  # toLegoId (same lego, different vault)
        )
    ]
    
    # Execute batch
    result = starter_agent.performBatchActions(
        user_wallet.address,
        instructions,
        sender=charlie
    )
    
    assert result == True
    
    # Check events
    logs = filter_logs(starter_agent, "WalletAction")
    assert len(logs) >= 2  # At least initial deposit and rebalance operations
    
    # First should be deposit
    assert logs[0].op == 10  # deposit for yield
    assert logs[0].asset1 == alpha_token.address
    assert logs[0].asset2 == alpha_token_vault.address
    
    # Check final state - should have tokens in both vaults
    assert alpha_token_vault.balanceOf(user_wallet) > 0
    assert alpha_token_vault_2.balanceOf(user_wallet) > 0
    assert alpha_token.balanceOf(user_wallet) == 100 * EIGHTEEN_DECIMALS  # Remaining balance