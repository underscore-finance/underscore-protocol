import pytest
import boa

from constants import EIGHTEEN_DECIMALS, ZERO_ADDRESS
from config.BluePrint import TOKENS
from contracts.core.userWallet import UserWallet, UserWalletConfig
from contracts.core.agent import AgentWrapper


########################
# Payee Validation Test #
########################


def test_payee_example_test(createGlobalPayeeSettings, charlie, alpha_token, bravo_token, bob, createPayeeLimits, createPayeeSettings, paymaster, user_wallet, user_wallet_config, alice):

    # set global payee settings
    new_global_payee_settings = createGlobalPayeeSettings(_canPayOwner=False)
    user_wallet_config.setGlobalPayeeSettings(new_global_payee_settings, sender=paymaster.address)

    # add payee
    unit_limits = createPayeeLimits(_perTxCap=10)
    new_payee_settings = createPayeeSettings(_primaryAsset=alpha_token, _onlyPrimaryAsset=True, _unitLimits=unit_limits)
    user_wallet_config.addPayee(alice, new_payee_settings, sender=paymaster.address)

    # cannot pay owner
    assert not paymaster.isValidPayee(user_wallet, bob, alpha_token, 1, 1)

    # not payee
    assert not paymaster.isValidPayee(user_wallet, charlie, alpha_token, 1, 1)

    # payee -- not primary asset
    assert not paymaster.isValidPayee(user_wallet, alice, bravo_token, 9, 1)

    # payee -- primary asset
    assert paymaster.isValidPayee(user_wallet, alice, alpha_token, 9, 1)

    # payee -- over limit
    assert not paymaster.isValidPayee(user_wallet, alice, alpha_token, 11, 1)
