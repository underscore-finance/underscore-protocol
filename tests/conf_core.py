import pytest
import boa

from config.BluePrint import PARAMS, TOKENS, INTEGRATION_ADDYS
from constants import ZERO_ADDRESS, EIGHTEEN_DECIMALS


###########
# Undy HQ #
###########


@pytest.fixture(scope="session")
def undy_hq_deploy(deploy3r, fork, undy_token):
    return boa.load(
        "contracts/registries/UndyHq.vy",
        undy_token,
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
    undy_token,
    switchboard,
    lego_book,
    deploy3r,
    governance,
    ledger,
    mission_control,
    hatchery,
    appraiser,
    boss_validator,
    paymaster,
    migrator,
    loot_distributor,
):
    # finish token setup
    assert undy_token.finishTokenSetup(undy_hq_deploy, sender=deploy3r)

    # data

    # 2
    assert undy_hq_deploy.startAddNewAddressToRegistry(ledger, "Ledger", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(ledger, sender=deploy3r) == 2

    # 3
    assert undy_hq_deploy.startAddNewAddressToRegistry(mission_control, "Mission Control", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(mission_control, sender=deploy3r) == 3

    # registries

    # 4
    assert undy_hq_deploy.startAddNewAddressToRegistry(lego_book, "Lego Book", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(lego_book, sender=deploy3r) == 4

    # 5
    assert undy_hq_deploy.startAddNewAddressToRegistry(switchboard, "Switchboard", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(switchboard, sender=deploy3r) == 5

    # other

    # 6
    assert undy_hq_deploy.startAddNewAddressToRegistry(hatchery, "Hatchery", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(hatchery, sender=deploy3r) == 6

    # 7
    assert undy_hq_deploy.startAddNewAddressToRegistry(loot_distributor, "Loot Distributor", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(loot_distributor, sender=deploy3r) == 7

    # 8
    assert undy_hq_deploy.startAddNewAddressToRegistry(appraiser, "Appraiser", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(appraiser, sender=deploy3r) == 8

    # 9
    assert undy_hq_deploy.startAddNewAddressToRegistry(boss_validator, "Boss Validator", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(boss_validator, sender=deploy3r) == 9

    # 10
    assert undy_hq_deploy.startAddNewAddressToRegistry(paymaster, "Paymaster", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(paymaster, sender=deploy3r) == 10

    # 11
    assert undy_hq_deploy.startAddNewAddressToRegistry(migrator, "Migrator", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(migrator, sender=deploy3r) == 11

    # special permission setup

    # switchboard can set token blacklists
    undy_hq_deploy.initiateHqConfigChange(5, False, True, sender=deploy3r)
    assert undy_hq_deploy.confirmHqConfigChange(5, sender=deploy3r)

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
        PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"],
        name="switchboard",
    )


@pytest.fixture(scope="session")
def switchboard(switchboard_deploy, deploy3r, switchboard_alpha):

    # alpha
    assert switchboard_deploy.startAddNewAddressToRegistry(switchboard_alpha, "Alpha", sender=deploy3r)
    assert switchboard_deploy.confirmNewAddressToRegistry(switchboard_alpha, sender=deploy3r) == 1

    # finish setup
    assert switchboard_deploy.setRegistryTimeLockAfterSetup(sender=deploy3r)

    # finish setup on switchboard config contracts
    assert switchboard_alpha.setActionTimeLockAfterSetup(sender=deploy3r)

    return switchboard_deploy


# switchboard alpha


@pytest.fixture(scope="session")
def switchboard_alpha(undy_hq_deploy, fork):
    return boa.load(
        "contracts/config/SwitchboardAlpha.vy",
        undy_hq_deploy,
        PARAMS[fork]["GEN_MIN_CONFIG_TIMELOCK"],
        PARAMS[fork]["GEN_MAX_CONFIG_TIMELOCK"],
        name="switchboard_alpha",
    )


# defaults


@pytest.fixture(scope="session")
def defaults(fork, user_wallet_template, user_wallet_config_template, agent_template, agent_eoa):
    d = ZERO_ADDRESS
    if fork == "local":
        d = boa.load("contracts/config/DefaultsLocal.vy", user_wallet_template, user_wallet_config_template, agent_template, agent_eoa)
    elif fork == "base":
        # TODO: get actual agent contract here instead of using `agent_eoa`
        trial_funds_asset = TOKENS[fork]["USDC"]
        trial_funds_amount = 10 * (10 ** 6)
        rewards_asset = TOKENS[fork]["RIPE"]
        d = boa.load("contracts/config/DefaultsBase.vy", user_wallet_template, user_wallet_config_template, agent_template, agent_eoa, trial_funds_asset, trial_funds_amount, rewards_asset)
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
        PARAMS[fork]["UNDY_HQ_MIN_REG_TIMELOCK"],
        PARAMS[fork]["UNDY_HQ_MAX_REG_TIMELOCK"],
        name="lego_book",
    )


@pytest.fixture(scope="session")
def lego_book(lego_book_deploy, deploy3r, mock_dex_lego, mock_yield_lego):

    # register mock yield lego
    assert lego_book_deploy.startAddNewAddressToRegistry(mock_yield_lego, "Mock Yield Lego", sender=deploy3r)
    assert lego_book_deploy.confirmNewAddressToRegistry(mock_yield_lego, sender=deploy3r) == 1

    # register mock dex lego
    assert lego_book_deploy.startAddNewAddressToRegistry(mock_dex_lego, "Mock Dex Lego", sender=deploy3r)
    assert lego_book_deploy.confirmNewAddressToRegistry(mock_dex_lego, sender=deploy3r) == 2

    # finish registry setup
    assert lego_book_deploy.setRegistryTimeLockAfterSetup(sender=deploy3r)

    return lego_book_deploy


########
# Core #
########


# hatchery


@pytest.fixture(scope="session")
def hatchery(undy_hq_deploy, fork, weth):
    return boa.load(
        "contracts/core/Hatchery.vy",
        undy_hq_deploy,
        weth,
        TOKENS[fork]["ETH"],
        name="hatchery",
    )


# loot distributor


@pytest.fixture(scope="session")
def loot_distributor(undy_hq_deploy):
    return boa.load(
        "contracts/core/LootDistributor.vy",
        undy_hq_deploy,
        name="loot_distributor",
    )


# appraiser


@pytest.fixture(scope="session")
def appraiser(undy_hq_deploy, fork, mock_ripe):
    ripe_hq = mock_ripe if fork == "local" else INTEGRATION_ADDYS[fork]["RIPE_HQ"]

    return boa.load(
        "contracts/core/Appraiser.vy",
        undy_hq_deploy,
        ripe_hq,
        TOKENS[fork]["WETH"],
        TOKENS[fork]["ETH"],
        name="appraiser",
    )


# boss validator


@pytest.fixture(scope="session")
def boss_validator(undy_hq_deploy, fork):
    return boa.load(
        "contracts/core/BossValidator.vy",
        undy_hq_deploy,
        PARAMS[fork]["BOSS_MIN_MANAGER_PERIOD"],
        PARAMS[fork]["BOSS_MAX_MANAGER_PERIOD"],
        PARAMS[fork]["BOSS_MIN_ACTIVATION_LENGTH"],
        PARAMS[fork]["BOSS_MAX_ACTIVATION_LENGTH"],
        PARAMS[fork]["BOSS_MAX_START_DELAY"],
        name="boss_validator",
    )


# paymaster


@pytest.fixture(scope="session")
def paymaster(undy_hq_deploy, fork):
    return boa.load(
        "contracts/core/Paymaster.vy",
        undy_hq_deploy,
        PARAMS[fork]["PAYMASTER_MIN_PAYEE_PERIOD"],
        PARAMS[fork]["PAYMASTER_MAX_PAYEE_PERIOD"],
        PARAMS[fork]["PAYMASTER_MIN_ACTIVATION_LENGTH"],
        PARAMS[fork]["PAYMASTER_MAX_ACTIVATION_LENGTH"],
        PARAMS[fork]["PAYMASTER_MAX_START_DELAY"],
        name="paymaster",
    )


# migrator


@pytest.fixture(scope="session")
def migrator(undy_hq_deploy, fork):
    return boa.load(
        "contracts/core/Migrator.vy",
        undy_hq_deploy,
        name="migrator",
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


@pytest.fixture(scope="session")
def agent_template():
    return boa.load_partial("contracts/core/agent/AgentWrapper.vy").deploy_as_blueprint()
