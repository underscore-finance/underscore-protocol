import pytest
import boa

from constants import ZERO_ADDRESS, ACTION_TYPE


def test_manager_example_test(createGlobalManagerSettings, charlie, alpha_token, bravo_token, bob, createManagerSettings, high_command, user_wallet, user_wallet_config, alice):

    # set global manager settings
    new_global_manager_settings = createGlobalManagerSettings(_canOwnerManage=False)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)

    # add manager
    new_manager_settings = createManagerSettings(_allowedAssets=[alpha_token])
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)

    # owner cannot manage
    assert not high_command.canSignerPerformAction(user_wallet, bob, ACTION_TYPE.EARN_DEPOSIT)

    # not manager
    assert not high_command.canSignerPerformAction(user_wallet, charlie, ACTION_TYPE.EARN_DEPOSIT)

    # manager -- not allowed asset
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [bravo_token])

    # manager -- allowed asset
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token])


# manager role tests


def test_owner_can_manage_when_enabled(createGlobalManagerSettings, bob, high_command, user_wallet, user_wallet_config):
    # set global manager settings with canOwnerManage=True
    new_global_manager_settings = createGlobalManagerSettings(_canOwnerManage=True)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # owner (bob) should be able to perform actions
    assert high_command.canSignerPerformAction(user_wallet, bob, ACTION_TYPE.EARN_DEPOSIT)
    assert high_command.canSignerPerformAction(user_wallet, bob, ACTION_TYPE.TRANSFER)
    assert high_command.canSignerPerformAction(user_wallet, bob, ACTION_TYPE.SWAP)


def test_owner_cannot_manage_when_disabled(createGlobalManagerSettings, bob, high_command, user_wallet, user_wallet_config):
    # set global manager settings with canOwnerManage=False
    new_global_manager_settings = createGlobalManagerSettings(_canOwnerManage=False)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # owner (bob) should not be able to perform actions
    assert not high_command.canSignerPerformAction(user_wallet, bob, ACTION_TYPE.EARN_DEPOSIT)
    assert not high_command.canSignerPerformAction(user_wallet, bob, ACTION_TYPE.TRANSFER)
    assert not high_command.canSignerPerformAction(user_wallet, bob, ACTION_TYPE.SWAP)


def test_non_manager_cannot_perform_actions(sally, high_command, user_wallet):
    # sally is neither owner nor manager
    assert not high_command.canSignerPerformAction(user_wallet, sally, ACTION_TYPE.EARN_DEPOSIT)
    assert not high_command.canSignerPerformAction(user_wallet, sally, ACTION_TYPE.TRANSFER)
    assert not high_command.canSignerPerformAction(user_wallet, sally, ACTION_TYPE.SWAP)


# activation / expiry tests


def test_manager_not_yet_active(createManagerSettings, alice, high_command, user_wallet, user_wallet_config):
    # add manager with future start block
    future_start = boa.env.evm.patch.block_number + 1000
    new_manager_settings = createManagerSettings(_startBlock=future_start)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # manager should not be active before start block
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)


def test_manager_active(createManagerSettings, alice, high_command, user_wallet, user_wallet_config):
    # add manager with current block as start
    current_block = boa.env.evm.patch.block_number
    new_manager_settings = createManagerSettings(_startBlock=current_block)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # manager should be active at start block
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)


def test_manager_expired(createManagerSettings, alice, high_command, user_wallet, user_wallet_config):
    # add manager with short expiry
    current_block = boa.env.evm.patch.block_number
    new_manager_settings = createManagerSettings(_startBlock=current_block, _expiryBlock=current_block + 10)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # travel past expiry
    boa.env.time_travel(blocks=11)
    
    # manager should not be active after expiry
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)


def test_manager_expires_at_current_block(createManagerSettings, alice, high_command, user_wallet, user_wallet_config):
    # edge case: manager expires at exactly the current block
    current_block = boa.env.evm.patch.block_number
    new_manager_settings = createManagerSettings(
        _startBlock=current_block,
        _expiryBlock=current_block  # expires at current block
    )
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should not be active at current block (expiry <= current block)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)


# action permission tests


def test_manager_yield_permissions(createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with canManageYield=True
    lego_perms = createLegoPerms(_canManageYield=True)
    new_manager_settings = createManagerSettings(_legoPerms=lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be able to perform yield actions
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_WITHDRAW)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_REBALANCE)


def test_manager_no_yield_permissions(createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with canManageYield=False
    lego_perms = createLegoPerms(_canManageYield=False)
    new_manager_settings = createManagerSettings(_legoPerms=lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should not be able to perform yield actions
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_WITHDRAW)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_REBALANCE)


def test_manager_swap_permissions(createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with canBuyAndSell=True
    lego_perms = createLegoPerms(_canBuyAndSell=True)
    new_manager_settings = createManagerSettings(_legoPerms=lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be able to perform swap/trade actions
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.SWAP)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.MINT_REDEEM)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.CONFIRM_MINT_REDEEM)


def test_manager_debt_permissions(createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with canManageDebt=True
    lego_perms = createLegoPerms(_canManageDebt=True)
    new_manager_settings = createManagerSettings(_legoPerms=lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be able to perform debt actions
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.ADD_COLLATERAL)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.REMOVE_COLLATERAL)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.BORROW)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.REPAY_DEBT)


def test_manager_liquidity_permissions(createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with canManageLiq=True
    lego_perms = createLegoPerms(_canManageLiq=True)
    new_manager_settings = createManagerSettings(_legoPerms=lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be able to perform liquidity actions
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.ADD_LIQ)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.REMOVE_LIQ)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.ADD_LIQ_CONC)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.REMOVE_LIQ_CONC)


def test_manager_rewards_permissions(createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with canClaimRewards=True
    lego_perms = createLegoPerms(_canClaimRewards=True)
    new_manager_settings = createManagerSettings(_legoPerms=lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be able to claim rewards
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.REWARDS)


def test_manager_transfer_permissions(createManagerSettings, createTransferPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with canTransfer=True
    transfer_perms = createTransferPerms(_canTransfer=True)
    new_manager_settings = createManagerSettings(_transferPerms=transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be able to transfer
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.TRANSFER)


def test_manager_no_transfer_permissions(createManagerSettings, createTransferPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with canTransfer=False
    transfer_perms = createTransferPerms(_canTransfer=False)
    new_manager_settings = createManagerSettings(_transferPerms=transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should not be able to transfer
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.TRANSFER)


# asset restrictions


def test_manager_allowed_assets_restriction(createManagerSettings, alpha_token, bravo_token, delta_token, alice, high_command, user_wallet, user_wallet_config):
    # add manager with specific allowed assets
    new_manager_settings = createManagerSettings(_allowedAssets=[alpha_token, bravo_token])
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow actions with allowed assets
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [bravo_token])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token, bravo_token])
    
    # should not allow actions with non-allowed assets
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [delta_token])
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token, delta_token])


def test_manager_no_asset_restrictions(createManagerSettings, alpha_token, bravo_token, delta_token, alice, high_command, user_wallet, user_wallet_config):
    # add manager with no asset restrictions (empty array)
    new_manager_settings = createManagerSettings(_allowedAssets=[])
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow actions with any assets
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [bravo_token])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [delta_token])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token, bravo_token, delta_token])


# lego restrictions


def test_manager_allowed_legos_restriction(createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with specific allowed legos
    lego_perms = createLegoPerms(_allowedLegos=[1, 2, 3])
    new_manager_settings = createManagerSettings(_legoPerms=lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow actions with allowed legos
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [1])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [2])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [1, 2])
    
    # should not allow actions with non-allowed legos
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [4])
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [1, 4])


# payee restrictions


def test_manager_allowed_payees_restriction(createManagerSettings, createTransferPerms, alice, bob, charlie, sally, high_command, user_wallet, user_wallet_config):
    # add manager with specific allowed payees for transfers
    transfer_perms = createTransferPerms(_canTransfer=True, _allowedPayees=[bob, charlie])
    new_manager_settings = createManagerSettings(_transferPerms=transfer_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow transfers to allowed payees
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.TRANSFER, [], [], bob)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.TRANSFER, [], [], charlie)
    
    # should not allow transfers to non-allowed payees
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.TRANSFER, [], [], sally)


# transaction limits


def test_manager_max_txs_per_period_limit(createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # add manager with max 3 txs per period
    limits = createManagerLimits(_maxNumTxsPerPeriod=3)
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # first 3 txs should be allowed
    manager_data = createManagerData(_numTxsInPeriod=0)
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)
    
    manager_data = createManagerData(_numTxsInPeriod=1)
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)
    
    manager_data = createManagerData(_numTxsInPeriod=2)
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)
    
    # 4th tx should be blocked
    manager_data = createManagerData(_numTxsInPeriod=3)
    assert not high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)


def test_manager_tx_cooldown_blocks(createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # add manager with 100 block cooldown between txs
    limits = createManagerLimits(_txCooldownBlocks=100)
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # time travel forward to avoid negative blocks
    boa.env.time_travel(blocks=100)
    
    # tx should be blocked if within cooldown period
    current_block = boa.env.evm.patch.block_number
    manager_data = createManagerData(_lastTxBlock=current_block - 50)  # 50 blocks ago
    assert not high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)
    
    # tx should be allowed if past cooldown period
    boa.env.time_travel(blocks=200)
    current_block = boa.env.evm.patch.block_number
    manager_data = createManagerData(_lastTxBlock=current_block - 150)  # 150 blocks ago
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)


# global vs specific settings


def test_global_manager_settings_restrictions(createGlobalManagerSettings, createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # set restrictive global settings
    global_lego_perms = createLegoPerms(_canManageYield=False, _canBuyAndSell=False)
    new_global_manager_settings = createGlobalManagerSettings(_legoPerms=global_lego_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # add manager with permissive specific settings
    specific_lego_perms = createLegoPerms(_canManageYield=True, _canBuyAndSell=True)
    new_manager_settings = createManagerSettings(_legoPerms=specific_lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be blocked by global settings even if specific settings allow
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.SWAP)


def test_specific_manager_settings_restrictions(createGlobalManagerSettings, createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # set permissive global settings
    global_lego_perms = createLegoPerms(_canManageYield=True, _canBuyAndSell=True)
    new_global_manager_settings = createGlobalManagerSettings(_legoPerms=global_lego_perms)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # add manager with restrictive specific settings
    specific_lego_perms = createLegoPerms(_canManageYield=False, _canBuyAndSell=False)
    new_manager_settings = createManagerSettings(_legoPerms=specific_lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be blocked by specific settings even if global settings allow
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.SWAP)


def test_global_asset_restrictions_apply(createGlobalManagerSettings, createManagerSettings, alpha_token, bravo_token, delta_token, alice, high_command, user_wallet, user_wallet_config):
    # set global asset restrictions
    new_global_manager_settings = createGlobalManagerSettings(_allowedAssets=[alpha_token, bravo_token])
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # add manager with no specific asset restrictions
    new_manager_settings = createManagerSettings(_allowedAssets=[])
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be restricted by global asset list
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [bravo_token])
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [delta_token])


# period reset logic


def test_manager_period_reset(createGlobalManagerSettings, createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # set global manager period to 1000 blocks
    new_global_manager_settings = createGlobalManagerSettings(_managerPeriod=1000)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # add manager with max 2 txs per period
    limits = createManagerLimits(_maxNumTxsPerPeriod=2)
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # time travel forward to avoid negative blocks
    boa.env.time_travel(blocks=600)
    
    # simulate period with 2 txs already (at limit)
    current_block = boa.env.evm.patch.block_number
    manager_data = createManagerData(
        _numTxsInPeriod=2,
        _periodStartBlock=current_block - 500,  # halfway through period
        _totalUsdValueInPeriod=1000
    )
    
    # should be blocked (at limit)
    assert not high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, new_global_manager_settings, ACTION_TYPE.EARN_DEPOSIT)
    
    # travel past period end
    boa.env.time_travel(blocks=600)
    
    # should reset and allow new tx
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, new_global_manager_settings, ACTION_TYPE.EARN_DEPOSIT)


def test_manager_first_transaction_initializes_period(createManagerSettings, createManagerData, alice, high_command, user_wallet_config):
    # add manager
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # fresh manager data with no period initialized
    manager_data = createManagerData(_periodStartBlock=0)
    
    # should allow first transaction
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)


# complex scenarios


def test_manager_multiple_restrictions_all_must_pass(createManagerSettings, createManagerLimits, createLegoPerms, createTransferPerms, alpha_token, bravo_token, alice, bob, high_command, user_wallet, user_wallet_config):
    # add manager with multiple restrictions
    limits = createManagerLimits(_maxNumTxsPerPeriod=10)
    lego_perms = createLegoPerms(_canManageYield=True, _canBuyAndSell=False)
    transfer_perms = createTransferPerms(_canTransfer=True, _allowedPayees=[bob])
    new_manager_settings = createManagerSettings(
        _limits=limits,
        _legoPerms=lego_perms,
        _transferPerms=transfer_perms,
        _allowedAssets=[alpha_token]
    )
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow yield action with allowed asset
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token])
    
    # should block yield action with non-allowed asset
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [bravo_token])
    
    # should block swap action (not allowed)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.SWAP, [alpha_token])
    
    # should allow transfer to allowed payee
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.TRANSFER, [], [], bob)
    
    # should block transfer to non-allowed payee
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.TRANSFER, [], [], alice)


def test_manager_zero_address_assets_ignored(createManagerSettings, alpha_token, alice, high_command, user_wallet, user_wallet_config):
    # add manager with allowed assets
    new_manager_settings = createManagerSettings(_allowedAssets=[alpha_token])
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow action with zero address in assets (ignored)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [ZERO_ADDRESS, alpha_token])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token, ZERO_ADDRESS])


def test_manager_zero_lego_ids_ignored(createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with allowed legos
    lego_perms = createLegoPerms(_allowedLegos=[1, 2])
    new_manager_settings = createManagerSettings(_legoPerms=lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow action with zero lego id (ignored)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [0, 1])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [1, 0])


def test_manager_eth_weth_conversion_actions(createManagerSettings, alice, high_command, user_wallet, user_wallet_config):
    # add basic manager
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # ETH/WETH conversions should be allowed by default (no specific permission needed)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.ETH_TO_WETH)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.WETH_TO_ETH)


def test_manager_boundary_cooldown_exactly_at_limit(createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # add manager with 100 block cooldown
    limits = createManagerLimits(_txCooldownBlocks=100)
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # travel forward to set up test
    boa.env.time_travel(blocks=200)
    
    # tx at exactly cooldown limit should be allowed
    current_block = boa.env.evm.patch.block_number
    manager_data = createManagerData(_lastTxBlock=current_block - 100)
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)
    
    # tx at cooldown - 1 should be blocked
    manager_data = createManagerData(_lastTxBlock=current_block - 99)
    assert not high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)


def test_manager_no_cooldown_when_zero(createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # add manager with no cooldown (0)
    limits = createManagerLimits(_txCooldownBlocks=0)
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow back-to-back transactions
    current_block = boa.env.evm.patch.block_number
    manager_data = createManagerData(_lastTxBlock=current_block)  # just happened
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)


def test_manager_first_tx_no_cooldown_check(createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # add manager with cooldown
    limits = createManagerLimits(_txCooldownBlocks=100)
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # first tx (lastTxBlock = 0) should not be subject to cooldown
    manager_data = createManagerData(_lastTxBlock=0)
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)


# USD value limit tests


def test_manager_usd_per_tx_limit(createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # add manager with $1000 per tx limit
    limits = createManagerLimits(_maxUsdValuePerTx=1000)
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # test with canSignerPerformActionWithConfig (pre-action check doesn't validate USD value)
    manager_data = createManagerData()
    # pre-action check should pass (USD limits are only checked post-action)
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, user_wallet_config.globalManagerSettings(), ACTION_TYPE.EARN_DEPOSIT)


def test_manager_lifetime_tracking_persists_across_periods(createGlobalManagerSettings, createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # set short period for testing
    new_global_manager_settings = createGlobalManagerSettings(_managerPeriod=100)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # add manager
    limits = createManagerLimits()
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # time travel forward to avoid negative blocks
    boa.env.time_travel(blocks=100)
    
    # simulate data with lifetime values
    current_block = boa.env.evm.patch.block_number
    manager_data = createManagerData(
        _totalNumTxs=50,  # lifetime tx count
        _totalUsdValue=100000,  # lifetime USD value
        _periodStartBlock=current_block - 50
    )
    
    # travel past period end
    boa.env.time_travel(blocks=200)
    
    # check that lifetime data would persist (period data would reset)
    # Note: The actual data update happens in the contract, we're just testing validation
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, new_global_manager_settings, ACTION_TYPE.EARN_DEPOSIT)


# fail on zero price tests


def test_manager_fail_on_zero_price_global_setting(createGlobalManagerSettings, createManagerSettings, createManagerLimits, alice, high_command, user_wallet, user_wallet_config):
    # set global setting with failOnZeroPrice=True
    limits = createManagerLimits(_failOnZeroPrice=True)
    new_global_manager_settings = createGlobalManagerSettings(_limits=limits)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # add manager without specific failOnZeroPrice setting
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow action (zero price check happens post-action with actual price data)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)


def test_manager_fail_on_zero_price_specific_setting(createManagerSettings, createManagerLimits, alice, high_command, user_wallet, user_wallet_config):
    # add manager with failOnZeroPrice=True in specific settings
    limits = createManagerLimits(_failOnZeroPrice=True)
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow action (zero price check happens post-action with actual price data)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)


# empty arrays / edge cases


def test_manager_empty_assets_array_in_call(createManagerSettings, alice, high_command, user_wallet, user_wallet_config):
    # add manager with allowed assets
    new_manager_settings = createManagerSettings(_allowedAssets=[])
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow action with empty assets array
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [])


def test_manager_empty_legos_array_in_call(createManagerSettings, alice, high_command, user_wallet, user_wallet_config):
    # add manager
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow action with empty legos array
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [])


def test_manager_empty_payee_address(createManagerSettings, alice, high_command, user_wallet, user_wallet_config):
    # add manager
    new_manager_settings = createManagerSettings()
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow action with empty payee address
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [], ZERO_ADDRESS)


# complex permission combinations


def test_manager_all_permissions_enabled(createManagerSettings, createLegoPerms, createTransferPerms, alice, high_command, user_wallet, user_wallet_config):
    # create manager with all permissions enabled
    lego_perms = createLegoPerms(
        _canManageYield=True,
        _canBuyAndSell=True,
        _canManageDebt=True,
        _canManageLiq=True,
        _canClaimRewards=True
    )
    transfer_perms = createTransferPerms(
        _canTransfer=True,
        _canCreateCheque=True,
        _canAddPendingPayee=True
    )
    new_manager_settings = createManagerSettings(
        _legoPerms=lego_perms,
        _transferPerms=transfer_perms
    )
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be able to perform all action types
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.SWAP)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.BORROW)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.ADD_LIQ)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.REWARDS)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.TRANSFER)


def test_manager_all_permissions_disabled(createManagerSettings, createLegoPerms, createTransferPerms, alice, high_command, user_wallet, user_wallet_config):
    # create manager with all permissions disabled
    lego_perms = createLegoPerms(
        _canManageYield=False,
        _canBuyAndSell=False,
        _canManageDebt=False,
        _canManageLiq=False,
        _canClaimRewards=False
    )
    transfer_perms = createTransferPerms(
        _canTransfer=False,
        _canCreateCheque=False,
        _canAddPendingPayee=False
    )
    new_manager_settings = createManagerSettings(
        _legoPerms=lego_perms,
        _transferPerms=transfer_perms
    )
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should not be able to perform restricted actions
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.SWAP)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.BORROW)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.ADD_LIQ)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.REWARDS)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.TRANSFER)
    
    # but ETH/WETH conversions should still work (no specific permission needed)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.ETH_TO_WETH)
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.WETH_TO_ETH)


# global limits applying to managers


def test_global_tx_limit_applies_to_manager(createGlobalManagerSettings, createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # set global limit of 5 txs per period
    global_limits = createManagerLimits(_maxNumTxsPerPeriod=5)
    new_global_manager_settings = createGlobalManagerSettings(_limits=global_limits)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # add manager with higher limit (10 txs)
    manager_limits = createManagerLimits(_maxNumTxsPerPeriod=10)
    new_manager_settings = createManagerSettings(_limits=manager_limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should be blocked by global limit (5) even though manager limit is higher (10)
    manager_data = createManagerData(_numTxsInPeriod=5)
    assert not high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, new_global_manager_settings, ACTION_TYPE.EARN_DEPOSIT)


def test_global_cooldown_applies_to_manager(createGlobalManagerSettings, createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # set global cooldown of 200 blocks
    global_limits = createManagerLimits(_txCooldownBlocks=200)
    new_global_manager_settings = createGlobalManagerSettings(_limits=global_limits)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # add manager with shorter cooldown (50 blocks)
    manager_limits = createManagerLimits(_txCooldownBlocks=50)
    new_manager_settings = createManagerSettings(_limits=manager_limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # time travel forward to avoid negative blocks
    boa.env.time_travel(blocks=150)
    
    # should be blocked by global cooldown (200) even though manager cooldown is shorter (50)
    current_block = boa.env.evm.patch.block_number
    manager_data = createManagerData(_lastTxBlock=current_block - 100)  # 100 blocks ago
    assert not high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, new_global_manager_settings, ACTION_TYPE.EARN_DEPOSIT)


# more edge cases


def test_manager_multiple_assets_some_allowed_some_not(createManagerSettings, alpha_token, bravo_token, delta_token, alice, high_command, user_wallet, user_wallet_config):
    # add manager with only alpha and bravo allowed
    new_manager_settings = createManagerSettings(_allowedAssets=[alpha_token, bravo_token])
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should block if ANY asset is not allowed
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [bravo_token])
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token, bravo_token, delta_token])


def test_manager_multiple_legos_some_allowed_some_not(createManagerSettings, createLegoPerms, alice, high_command, user_wallet, user_wallet_config):
    # add manager with only legos 1 and 2 allowed
    lego_perms = createLegoPerms(_allowedLegos=[1, 2])
    new_manager_settings = createManagerSettings(_legoPerms=lego_perms)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should block if ANY lego is not allowed
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [1])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [2])
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [], [1, 2, 3])


def test_manager_period_exactly_at_boundary(createGlobalManagerSettings, createManagerSettings, createManagerLimits, createManagerData, alice, high_command, user_wallet_config):
    # set period to 100 blocks
    new_global_manager_settings = createGlobalManagerSettings(_managerPeriod=100)
    user_wallet_config.setGlobalManagerSettings(new_global_manager_settings, sender=high_command.address)
    
    # add manager
    limits = createManagerLimits(_maxNumTxsPerPeriod=1)
    new_manager_settings = createManagerSettings(_limits=limits)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # time travel forward to avoid negative blocks
    boa.env.time_travel(blocks=150)
    
    # set up data at exactly period boundary
    current_block = boa.env.evm.patch.block_number
    manager_data = createManagerData(
        _numTxsInPeriod=1,
        _periodStartBlock=current_block - 100  # exactly at period boundary
    )
    
    # should reset period and allow new tx
    assert high_command.canSignerPerformActionWithConfig(False, True, manager_data, new_manager_settings, new_global_manager_settings, ACTION_TYPE.EARN_DEPOSIT)


def test_manager_start_block_equals_expiry_block(createManagerSettings, alice, high_command, user_wallet, user_wallet_config):
    # edge case: start and expiry at same block
    current_block = boa.env.evm.patch.block_number
    new_manager_settings = createManagerSettings(
        _startBlock=current_block,
        _expiryBlock=current_block
    )
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should not be active (expires at current block)
    assert not high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT)


def test_manager_large_allowed_assets_list(createManagerSettings, alice, high_command, user_wallet, user_wallet_config, 
                                          alpha_token, bravo_token, charlie_token, delta_token, 
                                          yield_underlying_token, mock_dex_asset, mock_dex_asset_alt):
    # add manager with many allowed assets
    allowed_assets = [alpha_token, bravo_token, charlie_token, delta_token, 
                     yield_underlying_token, mock_dex_asset, mock_dex_asset_alt]
    new_manager_settings = createManagerSettings(_allowedAssets=allowed_assets)
    user_wallet_config.addManager(alice, new_manager_settings, sender=high_command.address)
    
    # should allow actions with any of the allowed assets
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [mock_dex_asset_alt])
    assert high_command.canSignerPerformAction(user_wallet, alice, ACTION_TYPE.EARN_DEPOSIT, [alpha_token, delta_token, mock_dex_asset])
