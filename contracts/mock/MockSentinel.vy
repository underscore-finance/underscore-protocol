# @version 0.4.3

from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs

MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

# Control flag for testing validation failures
fail_validation: public(bool)

@deploy
def __init__():
    self.fail_validation = False


@view
@external
def canSignerPerformActionWithConfig(
    _isOwner: bool,
    _isManager: bool,
    _managerData: wcs.ManagerData,
    _config: wcs.ManagerSettings,
    _globalConfig: wcs.GlobalManagerSettings,
    _action: ws.ActionType,
    _assets: DynArray[address, MAX_ASSETS] = [],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _payee: address = empty(address),
) -> bool:
    if self.fail_validation:
        return False
    return True


@view
@external
def isValidPayeeAndGetData(
    _isWhitelisted: bool,
    _isOwner: bool,
    _isPayee: bool,
    _asset: address,
    _amount: uint256,
    _txUsdValue: uint256,
    _config: wcs.PayeeSettings,
    _globalConfig: wcs.GlobalPayeeSettings,
    _data: wcs.PayeeData,
) -> (bool, wcs.PayeeData):
    if self.fail_validation:
        return False, _data
    return True, _data


@view
@external
def checkManagerUsdLimitsAndUpdateData(
    _txUsdValue: uint256,
    _specificLimits: wcs.ManagerLimits,
    _globalLimits: wcs.ManagerLimits,
    _managerPeriod: uint256,
    _data: wcs.ManagerData,
) -> (bool, wcs.ManagerData):
    if self.fail_validation:
        return False, _data
    return True, _data


# Helper function for testing
@external
def setFailValidation(_fail: bool):
    self.fail_validation = _fail