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
    backpack,
    appraiser,
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
    assert undy_hq_deploy.startAddNewAddressToRegistry(backpack, "Backpack", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(backpack, sender=deploy3r) == 7

    # 8
    assert undy_hq_deploy.startAddNewAddressToRegistry(appraiser, "Appraiser", sender=deploy3r)
    assert undy_hq_deploy.confirmNewAddressToRegistry(appraiser, sender=deploy3r) == 8

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
def mission_control(undy_hq_deploy):
    return boa.load(
        "contracts/data/MissionControl.vy",
        undy_hq_deploy,
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
def lego_book(lego_book_deploy, deploy3r, mock_lego):

    # register mock lego
    assert lego_book_deploy.startAddNewAddressToRegistry(mock_lego, "Mock Lego", sender=deploy3r)
    assert lego_book_deploy.confirmNewAddressToRegistry(mock_lego, sender=deploy3r) == 1

    # finish registry setup
    assert lego_book_deploy.setRegistryTimeLockAfterSetup(sender=deploy3r)

    return lego_book_deploy


########
# Core #
########


# hatchery


@pytest.fixture(scope="session")
def hatchery(undy_hq_deploy, fork):
    return boa.load(
        "contracts/core/Hatchery.vy",
        undy_hq_deploy,
        TOKENS[fork]["WETH"],
        TOKENS[fork]["ETH"],
        name="hatchery",
    )


# backpack


@pytest.fixture(scope="session")
def backpack(undy_hq_deploy, fork):
    return boa.load(
        "contracts/core/Backpack.vy",
        undy_hq_deploy,
        TOKENS[fork]["WETH"],
        TOKENS[fork]["ETH"],
        name="backpack",
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