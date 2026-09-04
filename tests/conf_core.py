import pytest
import boa
from eth_utils import keccak, to_checksum_address

from config.BluePrint import PARAMS, TOKENS, INTEGRATION_ADDYS, VAULT_INFO
from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS, ONE_YEAR_IN_BLOCKS


CANONICAL_CREATE2_SINGLETON = "0x4e59b44847b379578588920cA78FbF26c0B4956C"
CANONICAL_CREATE2_SINGLETON_RUNTIME = bytes.fromhex(
    "7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe0"
    "3601600081602082378035828234f58015156039578182fd5b8082525050506014"
    "600cf3"
)
USER_WALLET_IMPL_V1_SALT = bytes.fromhex(
    "da9e0e08155d5e49d144d1878faacbcf25fec5790c5ca4cfea6c03788d80329d"
)
USER_WALLET_CONFIG_IMPL_V1_SALT = bytes.fromhex(
    "c54fd3bd79f3df3298ee349c311ac2d48d1dd8bdbc6e4c795ec0b851c7321227"
)


def _predict_create2(deployer, salt, initcode):
    digest = keccak(
        b"\xff"
        + bytes.fromhex(str(deployer)[2:])
        + salt
        + keccak(initcode)
    )
    return to_checksum_address(digest[-20:])


def _deploy_fixed_wallet_implementation(env, path, salt):
    existing_singleton = env.get_code(CANONICAL_CREATE2_SINGLETON)
    if existing_singleton:
        assert existing_singleton == CANONICAL_CREATE2_SINGLETON_RUNTIME
    else:
        env.set_code(
            CANONICAL_CREATE2_SINGLETON,
            CANONICAL_CREATE2_SINGLETON_RUNTIME,
        )

    partial = boa.load_partial(path)
    creation_bytecode = partial.compiler_data.bytecode
    expected = _predict_create2(
        CANONICAL_CREATE2_SINGLETON,
        salt,
        creation_bytecode,
    )
    runtime = partial.compiler_data.bytecode_runtime

    existing_code = env.get_code(expected)
    if existing_code:
        assert existing_code == runtime
    else:
        computation = env.raw_call(
            CANONICAL_CREATE2_SINGLETON,
            data=salt + creation_bytecode,
        )
        assert to_checksum_address(computation.output[-20:]) == expected
        assert env.get_code(expected) == runtime
    return partial.at(expected)

###########
# Undy HQ #
###########


@pytest.fixture(scope="session")
def undy_hq_deploy(deploy3r, fork):
    return boa.load(
        "contracts/registries/UndyHq.vy",
        deploy3r,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"],
        name="undy_hq",
    )


@pytest.fixture(scope="session", autouse=True)
def undy_hq(
    undy_hq_deploy,
    switchboard,
    lego_book,
    deploy3r,
    governance,
    ledger,
    mission_control,
    hatchery,
    appraiser,
    wallet_backpack_deploy,
    loot_distributor,
    billing,
    vault_registry,
    helpers_deploy,
):
    # data

    # 1
    assert undy_hq_deploy.startAddNewAddressToRegistry(ledger, "Ledger", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(ledger, sender=deploy3r) == 1

    # 2
    assert undy_hq_deploy.startAddNewAddressToRegistry(mission_control, "Mission Control", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(mission_control, sender=deploy3r) == 2

    # registries

    # 3
    assert undy_hq_deploy.startAddNewAddressToRegistry(lego_book, "Lego Book", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(lego_book, sender=deploy3r) == 3

    # 4
    assert undy_hq_deploy.startAddNewAddressToRegistry(switchboard, "Switchboard", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(switchboard, sender=deploy3r) == 4

    # other

    # 5
    assert undy_hq_deploy.startAddNewAddressToRegistry(hatchery, "Hatchery", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(hatchery, sender=deploy3r) == 5

    # 6
    assert undy_hq_deploy.startAddNewAddressToRegistry(loot_distributor, "Loot Distributor", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(loot_distributor, sender=deploy3r) == 6

    # 7
    assert undy_hq_deploy.startAddNewAddressToRegistry(appraiser, "Appraiser", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(appraiser, sender=deploy3r) == 7

    # 8
    assert undy_hq_deploy.startAddNewAddressToRegistry(wallet_backpack_deploy, "Wallet Backpack", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(wallet_backpack_deploy, sender=deploy3r) == 8

    # 9
    assert undy_hq_deploy.startAddNewAddressToRegistry(billing, "Billing", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(billing, sender=deploy3r) == 9

    # 10
    assert undy_hq_deploy.startAddNewAddressToRegistry(vault_registry, "Vault Registry", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(vault_registry, sender=deploy3r) == 10

    # 11
    assert undy_hq_deploy.startAddNewAddressToRegistry(helpers_deploy, "Helpers", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(helpers_deploy, sender=deploy3r) == 11

    # special permission setup

    # switchboard can set token blacklists
    undy_hq_deploy.initiateHqConfigChange(4, False, True, sender=deploy3r)
    assert undy_hq_deploy.confirmHqConfigChange(4, sender=deploy3r)

    # finish undy hq setup
    assert undy_hq_deploy.setRegistryTimeLockAfterSetup(sender=deploy3r)
    assert undy_hq_deploy.finishUndyHqSetup(governance, sender=deploy3r)

    return undy_hq_deploy


##########
# Tokens #
##########


@pytest.fixture(scope="session")
def undy_token(deploy3r, fork, whale):
    return boa.load(
        "contracts/tokens/UndyToken.vy",
        ZERO_ADDRESS,
        deploy3r,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        10_000_000 * EIGHTEEN_DECIMALS,
        whale,
        name="undy_token",
    )


########
# Data #
########


# ledger


@pytest.fixture(scope="session")
def ledger(undy_hq_deploy):
    return boa.load(
        "contracts/data/Ledger.vy",
        undy_hq_deploy,
        name="ledger",
    )


# mission control


@pytest.fixture(scope="session")
def mission_control(undy_hq_deploy, defaults):
    return boa.load(
        "contracts/data/MissionControl.vy",
        undy_hq_deploy,
        defaults,
        name="mission_control",
    )


######################
# Switchboard Config #
######################


@pytest.fixture(scope="session")
def switchboard_deploy(undy_hq_deploy, fork):
    return boa.load(
        "contracts/registries/Switchboard.vy",
        undy_hq_deploy,
        ZERO_ADDRESS,
        PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"],
        name="switchboard",
    )


@pytest.fixture(scope="session")
def switchboard(switchboard_deploy, deploy3r, switchboard_alpha, switchboard_bravo, switchboard_charlie):

    # alpha
    assert switchboard_deploy.startAddNewAddressToRegistry(switchboard_alpha, "Alpha", sender=deploy3r)
    assert switchboard_deploy.confirmNewAddressToRegistry(switchboard_alpha, sender=deploy3r) == 1

    # bravo
    assert switchboard_deploy.startAddNewAddressToRegistry(switchboard_bravo, "Bravo", sender=deploy3r)
    assert switchboard_deploy.confirmNewAddressToRegistry(switchboard_bravo, sender=deploy3r) == 2

    # charlie
    assert switchboard_deploy.startAddNewAddressToRegistry(switchboard_charlie, "Charlie", sender=deploy3r)
    assert switchboard_deploy.confirmNewAddressToRegistry(switchboard_charlie, sender=deploy3r) == 3

    # finish setup
    assert switchboard_deploy.setRegistryTimeLockAfterSetup(sender=deploy3r)

    # finish setup on switchboard config contracts
    assert switchboard_alpha.setActionTimeLockAfterSetup(sender=deploy3r)
    assert switchboard_bravo.setActionTimeLockAfterSetup(sender=deploy3r)
    assert switchboard_charlie.setActionTimeLockAfterSetup(sender=deploy3r)

    return switchboard_deploy


# switchboard alpha


@pytest.fixture(scope="session")
def switchboard_alpha(undy_hq_deploy, fork):
    return boa.load(
        "contracts/config/SwitchboardAlpha.vy",
        undy_hq_deploy,
        ZERO_ADDRESS,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"],
        PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
        name="switchboard_alpha",
    )


# switchboard bravo


@pytest.fixture(scope="session")
def switchboard_bravo(undy_hq_deploy, fork):
    return boa.load(
        "contracts/config/SwitchboardBravo.vy",
        undy_hq_deploy,
        ZERO_ADDRESS,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"],
        PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
        name="switchboard_bravo",
    )


# switchboard charlie


@pytest.fixture(scope="session")
def switchboard_charlie(undy_hq_deploy, fork):
    return boa.load(
        "contracts/config/SwitchboardCharlie.vy",
        undy_hq_deploy,
        ZERO_ADDRESS,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"],
        PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
        name="switchboard_charlie",
    )


# defaults


@pytest.fixture(scope="session")
def defaults(fork, user_wallet_template, user_wallet_config_template, undy_hq_deploy):
    default_agent = boa.load(
        "contracts/core/agent/AgentWrapper.vy",
        undy_hq_deploy,
        1,
        [],
        name="default_starting_agent",
    )
    d = ZERO_ADDRESS
    if fork == "local":
        d = boa.load("contracts/config/DefaultsLocal.vy", user_wallet_template,
                     user_wallet_config_template, default_agent)
    elif fork == "base":
        rewards_asset = TOKENS[fork]["RIPE"]
        d = boa.load("contracts/config/DefaultsBase.vy", user_wallet_template,
                     user_wallet_config_template, default_agent, rewards_asset)
    return d


#########
# Legos #
#########


# lego book


@pytest.fixture(scope="session")
def lego_book_deploy(undy_hq_deploy, fork):
    return boa.load(
        "contracts/registries/LegoBook.vy",
        undy_hq_deploy,
        ZERO_ADDRESS,
        PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"],
        name="lego_book",
    )


@pytest.fixture(scope="session")
def lego_book(lego_book_deploy, deploy3r, mock_dex_lego, mock_yield_lego, lego_ripe):

    # register ripe lego
    assert lego_book_deploy.startAddNewAddressToRegistry(lego_ripe, "Ripe Lego", sender=deploy3r)
    assert lego_book_deploy.confirmNewAddressToRegistry(lego_ripe, sender=deploy3r) == 1

    # register mock yield lego
    assert lego_book_deploy.startAddNewAddressToRegistry(mock_yield_lego, "Mock Yield Lego", sender=deploy3r)
    assert lego_book_deploy.confirmNewAddressToRegistry(mock_yield_lego, sender=deploy3r) == 2

    # register mock dex lego
    assert lego_book_deploy.startAddNewAddressToRegistry(mock_dex_lego, "Mock Dex Lego", sender=deploy3r)
    assert lego_book_deploy.confirmNewAddressToRegistry(mock_dex_lego, sender=deploy3r) == 3

    # finish registry setup
    assert lego_book_deploy.setRegistryTimeLockAfterSetup(sender=deploy3r)

    return lego_book_deploy


########
# Core #
########


# deterministic wallet artifacts


@pytest.fixture(scope="session")
def user_wallet_implementation(env):
    return _deploy_fixed_wallet_implementation(
        env,
        "contracts/core/userWallet/UserWallet.vy",
        USER_WALLET_IMPL_V1_SALT,
    )


@pytest.fixture(scope="session")
def user_wallet_config_implementation(env, user_wallet_implementation):
    implementation = _deploy_fixed_wallet_implementation(
        env,
        "contracts/core/userWallet/UserWalletConfig.vy",
        USER_WALLET_CONFIG_IMPL_V1_SALT,
    )
    assert (
        implementation._constants.USER_WALLET_IMPLEMENTATION
        == user_wallet_implementation.address
    )
    return implementation


@pytest.fixture(scope="session")
def user_wallet_factory(
    undy_hq_deploy,
    user_wallet_implementation,
    user_wallet_config_implementation,
):
    # The shared test environment intentionally uses normal CREATE for the
    # factory, leaving the canonical factory salt exclusively to the focused
    # singleton tests. Proxy determinism depends on this factory's address,
    # while its hardcoded implementation trust roots remain the fixed V1 ones.
    factory = boa.load(
        "contracts/core/userWallet/UserWalletFactory.vy",
        name="user_wallet_factory",
    )
    assert factory.USER_WALLET_IMPLEMENTATION() == user_wallet_implementation.address
    assert (
        factory.USER_WALLET_CONFIG_IMPLEMENTATION()
        == user_wallet_config_implementation.address
    )
    factory.setUndyHq(undy_hq_deploy, sender=ZERO_ADDRESS)
    return factory


# hatchery


@pytest.fixture(scope="session")
def hatchery(undy_hq_deploy, fork, weth, user_wallet_factory):
    return boa.load(
        "contracts/core/Hatchery.vy",
        undy_hq_deploy,
        weth,
        TOKENS[fork]["ETH"],
        (True, True, True, True),
        (weth.address, ONE_YEAR_IN_BLOCKS),
        (weth.address, ONE_YEAR_IN_BLOCKS),
        ZERO_ADDRESS,
        user_wallet_factory,
        name="hatchery",
    )


# loot distributor


@pytest.fixture(scope="session")
def loot_distributor(undy_hq_deploy, mock_ripe_token, mock_ripe, fork):
    return boa.load(
        "contracts/core/LootDistributor.vy",
        undy_hq_deploy,
        mock_ripe_token,
        mock_ripe,
        name="loot_distributor",
    )


# appraiser


@pytest.fixture(scope="session")
def appraiser(undy_hq_deploy, fork, mock_ripe):
    ripe_hq = mock_ripe if fork == "local" else INTEGRATION_ADDYS[fork]["RIPE_HQ_V1"]
    return boa.load(
        "contracts/core/Appraiser.vy",
        undy_hq_deploy,
        ripe_hq,
        name="appraiser",
    )


# billing


@pytest.fixture(scope="session")
def billing(undy_hq_deploy):
    return boa.load(
        "contracts/core/Billing.vy",
        undy_hq_deploy,
        name="billing",
    )


# vault registry


@pytest.fixture(scope="session")
def vault_registry(undy_hq_deploy, fork):
    return boa.load(
        "contracts/registries/VaultRegistry.vy",
        undy_hq_deploy,
        ZERO_ADDRESS,
        PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"],
        name="vault_registry",
    )


###################
# Wallet Backpack #
###################


@pytest.fixture(scope="session")
def wallet_backpack_deploy(undy_hq_deploy, fork):
    return boa.load(
        "contracts/registries/WalletBackpack.vy",
        undy_hq_deploy,
        ZERO_ADDRESS,
        PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"],
        name="wallet_backpack",
    )


@pytest.fixture(scope="session", autouse=True)
def wallet_backpack(wallet_backpack_deploy, kernel, sentinel, high_command, paymaster, cheque_book, migrator, action_data_provider, governance):

    # set kernel
    wallet_backpack_deploy.addPendingKernel(kernel, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack_deploy.actionTimeLock())
    wallet_backpack_deploy.confirmPendingKernel(sender=governance.address)

    # set sentinel
    wallet_backpack_deploy.addPendingSentinel(sentinel, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack_deploy.actionTimeLock())
    wallet_backpack_deploy.confirmPendingSentinel(sender=governance.address)

    # set high command
    wallet_backpack_deploy.addPendingHighCommand(high_command, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack_deploy.actionTimeLock())
    wallet_backpack_deploy.confirmPendingHighCommand(sender=governance.address)

    # set paymaster
    wallet_backpack_deploy.addPendingPaymaster(paymaster, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack_deploy.actionTimeLock())
    wallet_backpack_deploy.confirmPendingPaymaster(sender=governance.address)

    # set cheque book
    wallet_backpack_deploy.addPendingChequeBook(cheque_book, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack_deploy.actionTimeLock())
    wallet_backpack_deploy.confirmPendingChequeBook(sender=governance.address)

    # set migrator
    wallet_backpack_deploy.addPendingMigrator(migrator, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack_deploy.actionTimeLock())
    wallet_backpack_deploy.confirmPendingMigrator(sender=governance.address)

    # set action data provider
    wallet_backpack_deploy.addPendingActionDataProvider(action_data_provider, sender=governance.address)
    boa.env.time_travel(blocks=wallet_backpack_deploy.actionTimeLock())
    wallet_backpack_deploy.confirmPendingActionDataProvider(sender=governance.address)

    # set action time lock
    wallet_backpack_deploy.setActionTimeLockAfterSetup(sender=governance.address)

    return wallet_backpack_deploy


# kernel


@pytest.fixture(scope="session")
def kernel(undy_hq_deploy):
    return boa.load(
        "contracts/core/walletBackpack/Kernel.vy",
        undy_hq_deploy,
        name="kernel",
    )


# high command


@pytest.fixture(scope="session")
def high_command(undy_hq_deploy, fork):
    return boa.load(
        "contracts/core/walletBackpack/HighCommand.vy",
        undy_hq_deploy,
        PARAMS[fork]["BOSS_MIN_MANAGER_PERIOD"],
        PARAMS[fork]["BOSS_MAX_MANAGER_PERIOD"],
        PARAMS[fork]["BOSS_MIN_ACTIVATION_LENGTH"],
        PARAMS[fork]["BOSS_MAX_ACTIVATION_LENGTH"],
        PARAMS[fork]["BOSS_MAX_START_DELAY"],
        True,
        name="high_command",
    )


# paymaster


@pytest.fixture(scope="session")
def paymaster(undy_hq_deploy, fork):
    return boa.load(
        "contracts/core/walletBackpack/Paymaster.vy",
        undy_hq_deploy,
        PARAMS[fork]["PAYMASTER_MIN_PAYEE_PERIOD"],
        PARAMS[fork]["PAYMASTER_MAX_PAYEE_PERIOD"],
        PARAMS[fork]["PAYMASTER_MIN_ACTIVATION_LENGTH"],
        PARAMS[fork]["PAYMASTER_MAX_ACTIVATION_LENGTH"],
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],
        True,
        True,
        name="paymaster",
    )


# cheque book


@pytest.fixture(scope="session")
def cheque_book(undy_hq_deploy, fork):
    return boa.load(
        "contracts/core/walletBackpack/ChequeBook.vy",
        undy_hq_deploy,
        PARAMS[fork]["CHEQUE_MIN_PERIOD"],
        PARAMS[fork]["CHEQUE_MAX_PERIOD"],
        PARAMS[fork]["CHEQUE_MIN_EXPENSIVE_DELAY"],
        PARAMS[fork]["CHEQUE_MAX_UNLOCK_BLOCKS"],
        PARAMS[fork]["CHEQUE_MAX_EXPIRY_BLOCKS"],
        True,
        name="cheque_book",
    )


# migrator


@pytest.fixture(scope="session")
def migrator(undy_hq_deploy):
    return boa.load(
        "contracts/core/walletBackpack/Migrator.vy",
        undy_hq_deploy,
        False,
        name="migrator",
    )


# sentinel


@pytest.fixture(scope="session")
def sentinel():
    return boa.load(
        "contracts/core/walletBackpack/Sentinel.vy",
        name="sentinel",
    )


# action data provider


@pytest.fixture(scope="session")
def action_data_provider():
    return boa.load(
        "contracts/core/userWallet/ActionDataProvider.vy",
        name="action_data_provider",
    )


#############
# Templates #
#############


@pytest.fixture(scope="session")
def user_wallet_template():
    return boa.load_partial("contracts/core/userWallet/UserWallet.vy").deploy_as_blueprint()


@pytest.fixture(scope="session")
def user_wallet_config_template():
    return boa.load_partial("contracts/core/userWallet/UserWalletConfig.vy").deploy_as_blueprint()


###############
# Earn Vaults #
###############


# usdc vault


@pytest.fixture(scope="session")
def undy_usd_vault(undy_hq, vault_registry, governance, fork, starter_agent, yield_underlying_token, switchboard_alpha,
                   yield_vault_token, yield_vault_token_2, yield_vault_token_3, yield_vault_token_4):
    asset = yield_underlying_token.address if fork == "local" else TOKENS[fork]["USDC"]
    vault = boa.load(
        "contracts/vaults/EarnVault.vy",
        asset,
        VAULT_INFO['USDC']["name"],
        VAULT_INFO['USDC']["symbol"],
        undy_hq,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent,
        name="undy_usd_vault",
    )

    # Register vault in VaultRegistry (requires governance from undy_hq after finishUndyHqSetup)
    vault_registry.startAddNewAddressToRegistry(vault.address, "UndyUSD Vault", sender=governance.address)
    boa.env.time_travel(blocks=vault_registry.registryChangeTimeLock())

    # confirmNewAddressToRegistry now auto-initializes vault config
    vault_registry.confirmNewAddressToRegistry(
        vault.address,
        False,  # isLeveragedVault
        False,  # shouldEnforceAllowlist
        [  # approvedVaultTokens
            yield_vault_token.address,
            yield_vault_token_2.address,
            yield_vault_token_3.address,
            yield_vault_token_4.address,
        ],
        0,  # maxDepositAmount (0 = unlimited)
        10000,  # minYieldWithdrawAmount (0.01 USDC with 6 decimals)
        20_00,  # performanceFee (20%) - will be set to 0 below for tests
        ZERO_ADDRESS,  # defaultTargetVaultToken
        True,  # shouldAutoDeposit
        True,  # canDeposit
        True,  # canWithdraw
        False,  # isVaultOpsFrozen
        2_00,  # redemptionBuffer (2%)
        sender=governance.address
    )

    # Set performance fee to 0 for snapshot tests (after initialization)
    vault_registry.setPerformanceFee(vault.address, 0, sender=switchboard_alpha.address)

    return vault


# weth vault


@pytest.fixture(scope="session")
def undy_eth_vault(undy_hq, vault_registry, governance, fork, starter_agent, weth, switchboard_alpha):
    asset = weth.address if fork == "local" else TOKENS[fork]["WETH"]
    vault = boa.load(
        "contracts/vaults/EarnVault.vy",
        asset,
        VAULT_INFO['WETH']["name"],
        VAULT_INFO['WETH']["symbol"],
        undy_hq,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent,
        name="undy_eth_vault",
    )

    # Register vault in VaultRegistry (requires governance from undy_hq after finishUndyHqSetup)
    vault_registry.startAddNewAddressToRegistry(vault.address, "UndyETH Vault", sender=governance.address)
    boa.env.time_travel(blocks=vault_registry.registryChangeTimeLock())

    # confirmNewAddressToRegistry now auto-initializes vault config
    vault_registry.confirmNewAddressToRegistry(
        vault.address,
        False,  # isLeveragedVault
        False,  # shouldEnforceAllowlist
        [],  # approvedVaultTokens (empty for now, tests will add them as needed)
        0,  # maxDepositAmount (0 = unlimited)
        10000000000000000,  # minYieldWithdrawAmount (0.01 WETH with 18 decimals)
        20_00,  # performanceFee (20%) - will be set to 0 below for tests
        ZERO_ADDRESS,  # defaultTargetVaultToken
        True,  # shouldAutoDeposit
        True,  # canDeposit
        True,  # canWithdraw
        False,  # isVaultOpsFrozen
        2_00,  # redemptionBuffer (2%)
        sender=governance.address
    )

    # Set performance fee to 0 for snapshot tests (after initialization)
    vault_registry.setPerformanceFee(vault.address, 0, sender=switchboard_alpha.address)

    return vault


# cbbtc vault


@pytest.fixture(scope="session")
def undy_btc_vault(undy_hq, vault_registry, governance, fork, starter_agent, switchboard_alpha):
    asset = TOKENS[fork]["CBBTC"]
    vault = boa.load(
        "contracts/vaults/EarnVault.vy",
        asset,
        VAULT_INFO['CBBTC']["name"],
        VAULT_INFO['CBBTC']["symbol"],
        undy_hq,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent,
        name="undy_btc_vault",
    )

    # Register vault in VaultRegistry (requires governance from undy_hq after finishUndyHqSetup)
    vault_registry.startAddNewAddressToRegistry(vault.address, "UndyBTC Vault", sender=governance.address)
    boa.env.time_travel(blocks=vault_registry.registryChangeTimeLock())

    # confirmNewAddressToRegistry now auto-initializes vault config
    vault_registry.confirmNewAddressToRegistry(
        vault.address,
        False,  # isLeveragedVault
        False,  # shouldEnforceAllowlist
        [],  # approvedVaultTokens (empty for now, tests will add them as needed)
        0,  # maxDepositAmount (0 = unlimited)
        1000000,  # minYieldWithdrawAmount (0.01 cbBTC with 8 decimals)
        20_00,  # performanceFee (20%) - will be set to 0 below for tests
        ZERO_ADDRESS,  # defaultTargetVaultToken
        True,  # shouldAutoDeposit
        True,  # canDeposit
        True,  # canWithdraw
        False,  # isVaultOpsFrozen
        2_00,  # redemptionBuffer (2%)
        sender=governance.address
    )

    # Set performance fee to 0 for snapshot tests (after initialization)
    vault_registry.setPerformanceFee(vault.address, 0, sender=switchboard_alpha.address)

    return vault


###################
# Leverage Vaults #
###################


@pytest.fixture(scope="session")
def levg_vault_helper(mock_ripe, mock_usdc, fork, undy_hq_deploy):
    RIPE_REGISTRY = mock_ripe if fork == "local" else INTEGRATION_ADDYS[fork]["RIPE_HQ_V1"]
    USDC = mock_usdc if fork == "local" else TOKENS[fork]["USDC"]
    return boa.load("contracts/vaults/LevgVaultHelper.vy", undy_hq_deploy, RIPE_REGISTRY, USDC, name="levg_vault_helper")


@pytest.fixture(scope="session")
def levg_vault_tools(mock_ripe, mock_usdc, fork, undy_hq_deploy):
    RIPE_REGISTRY = mock_ripe if fork == "local" else INTEGRATION_ADDYS[fork]["RIPE_HQ_V1"]
    USDC = mock_usdc if fork == "local" else TOKENS[fork]["USDC"]
    return boa.load("contracts/helpers/LevgVaultTools.vy", undy_hq_deploy, RIPE_REGISTRY, USDC, name="levg_vault_tools")


@pytest.fixture(scope="session")
def helpers_deploy(undy_hq_deploy, fork):
    return boa.load(
        "contracts/registries/Helpers.vy",
        undy_hq_deploy,
        ZERO_ADDRESS,
        PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"],
        name="helpers",
    )


@pytest.fixture(scope="session")
def helpers(helpers_deploy, governance, lego_tools, levg_vault_tools):
    # Register LegoTools first
    assert helpers_deploy.startAddNewAddressToRegistry(lego_tools, "LegoTools", sender=governance.address)
    assert helpers_deploy.confirmNewAddressToRegistry(lego_tools, sender=governance.address) == 1

    # Register LevgVaultTools second
    assert helpers_deploy.startAddNewAddressToRegistry(levg_vault_tools, "LevgVaultTools", sender=governance.address)
    assert helpers_deploy.confirmNewAddressToRegistry(levg_vault_tools, sender=governance.address) == 2

    # Finish setup
    assert helpers_deploy.setRegistryTimeLockAfterSetup(sender=governance.address)

    return helpers_deploy


# usdc leverage vault


@pytest.fixture(scope="session")
def undy_levg_vault_usdc(undy_hq, levg_vault_helper, mock_usdc_collateral_vault, mock_usdc_leverage_vault, vault_registry, governance, fork, starter_agent, mock_usdc, mock_green_token, mock_savings_green_token):
    vault = boa.load(
        "contracts/vaults/LevgVault.vy",
        mock_usdc.address,
        VAULT_INFO['LEVG_USDC']["name"],
        VAULT_INFO['LEVG_USDC']["symbol"],
        undy_hq.address,
        mock_usdc_collateral_vault.address,
        2,
        1,
        mock_usdc_leverage_vault.address,
        2,
        1,
        mock_usdc.address,
        mock_green_token.address,
        mock_savings_green_token.address,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent.address,
        levg_vault_helper.address,
        name="undy_levg_vault_usdc",
    )

    # Register vault in VaultRegistry (requires governance from undy_hq after finishUndyHqSetup)
    vault_registry.startAddNewAddressToRegistry(vault.address, "Undy Levg USDC Vault", sender=governance.address)
    boa.env.time_travel(blocks=vault_registry.registryChangeTimeLock())

    # confirmNewAddressToRegistry now auto-initializes vault config
    vault_registry.confirmNewAddressToRegistry(
        vault.address,
        True,  # isLeveragedVault
        False,  # shouldEnforceAllowlist
        [],  # doesn't matter for leverage vault
        0,  # maxDepositAmount (0 = unlimited)
        100_000_000_000,  # doesn't matter for leverage vault
        0,  # doesn't matter for leverage vault
        ZERO_ADDRESS,  # doesn't matter for leverage vault
        True,  # shouldAutoDeposit
        True,  # canDeposit
        True,  # canWithdraw
        False,  # isVaultOpsFrozen
        2_00,  # redemptionBuffer (2%)
        sender=governance.address
    )
    return vault


# cbbtc leverage vault


@pytest.fixture(scope="session")
def undy_levg_vault_cbbtc(undy_hq, levg_vault_helper, mock_cbbtc_collateral_vault, mock_usdc_leverage_vault, mock_usdc, vault_registry, governance, fork, starter_agent, mock_cbbtc, mock_green_token, mock_savings_green_token):
    vault = boa.load(
        "contracts/vaults/LevgVault.vy",
        mock_cbbtc.address,
        VAULT_INFO['LEVG_CBBTC']["name"],
        VAULT_INFO['LEVG_CBBTC']["symbol"],
        undy_hq.address,
        mock_cbbtc_collateral_vault.address,
        2,
        1,
        mock_usdc_leverage_vault.address,
        2,
        1,
        mock_usdc.address,
        mock_green_token.address,
        mock_savings_green_token.address,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent.address,
        levg_vault_helper.address,
        name="undy_levg_vault_cbbtc",
    )

    # Register vault in VaultRegistry (requires governance from undy_hq after finishUndyHqSetup)
    vault_registry.startAddNewAddressToRegistry(vault.address, "Undy Levg cbBTC Vault", sender=governance.address)
    boa.env.time_travel(blocks=vault_registry.registryChangeTimeLock())

    # confirmNewAddressToRegistry now auto-initializes vault config
    vault_registry.confirmNewAddressToRegistry(
        vault.address,
        True,  # isLeveragedVault
        False,  # shouldEnforceAllowlist
        [],  # doesn't matter for leverage vault
        0,  # maxDepositAmount (0 = unlimited)
        100_000_000_000,  # doesn't matter for leverage vault
        0,  # doesn't matter for leverage vault
        ZERO_ADDRESS,  # doesn't matter for leverage vault
        True,  # shouldAutoDeposit
        True,  # canDeposit
        True,  # canWithdraw
        False,  # isVaultOpsFrozen
        2_00,  # redemptionBuffer (2%)
        sender=governance.address
    )
    return vault


# weth leverage vault


@pytest.fixture(scope="session")
def undy_levg_vault_weth(undy_hq, levg_vault_helper, mock_weth_collateral_vault, mock_usdc_leverage_vault, mock_usdc, vault_registry, governance, fork, starter_agent, mock_weth, mock_green_token, mock_savings_green_token):
    vault = boa.load(
        "contracts/vaults/LevgVault.vy",
        mock_weth.address,
        VAULT_INFO['LEVG_WETH']["name"],
        VAULT_INFO['LEVG_WETH']["symbol"],
        undy_hq.address,
        mock_weth_collateral_vault.address,
        2,
        1,
        mock_usdc_leverage_vault.address,
        2,
        1,
        mock_usdc.address,
        mock_green_token.address,
        mock_savings_green_token.address,
        PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        starter_agent.address,
        levg_vault_helper.address,
        name="undy_levg_vault_weth",
    )

    # Register vault in VaultRegistry (requires governance from undy_hq after finishUndyHqSetup)
    vault_registry.startAddNewAddressToRegistry(vault.address, "Undy Levg WETH Vault", sender=governance.address)
    boa.env.time_travel(blocks=vault_registry.registryChangeTimeLock())

    # confirmNewAddressToRegistry now auto-initializes vault config
    vault_registry.confirmNewAddressToRegistry(
        vault.address,
        True,  # isLeveragedVault
        False,  # shouldEnforceAllowlist
        [],  # doesn't matter for leverage vault
        0,  # maxDepositAmount (0 = unlimited)
        100_000_000_000,  # doesn't matter for leverage vault
        0,  # doesn't matter for leverage vault
        ZERO_ADDRESS,  # doesn't matter for leverage vault
        True,  # shouldAutoDeposit
        True,  # canDeposit
        True,  # canWithdraw
        False,  # isVaultOpsFrozen
        2_00,  # redemptionBuffer (2%)
        sender=governance.address
    )
    return vault
