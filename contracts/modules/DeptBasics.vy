# @version 0.4.1

uses: addys
implements: dept

import contracts.modules.Addys as addys
import interfaces.Department as dept
from ethereum.ercs import IERC20

event DepartmentPauseModified:
    isPaused: bool

event DepartmentFundsRecovered:
    asset: indexed(address)
    recipient: indexed(address)
    balance: uint256

isPaused: public(bool)

CAN_MINT_UNDY: immutable(bool)
MAX_RECOVER_ASSETS: constant(uint256) = 20


@deploy
def __init__(_shouldPause: bool, _canMintUndy: bool):
    self.isPaused = _shouldPause
    CAN_MINT_UNDY = _canMintUndy


###########
# Minting #
###########


@view
@external
def canMintUndy() -> bool:
    return CAN_MINT_UNDY


########
# Undy #
########


# activate


@external
def pause(_shouldPause: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _shouldPause != self.isPaused # dev: no change
    self.isPaused = _shouldPause
    log DepartmentPauseModified(isPaused=_shouldPause)


# recover funds


@external
def recoverFunds(_recipient: address, _asset: address):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    self._recoverFunds(_recipient, _asset)


@external
def recoverFundsMany(_recipient: address, _assets: DynArray[address, MAX_RECOVER_ASSETS]):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    for a: address in _assets:
        self._recoverFunds(_recipient, a)


@internal
def _recoverFunds(_recipient: address, _asset: address):
    assert empty(address) not in [_recipient, _asset] # dev: invalid recipient or asset
    balance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    assert balance != 0 # dev: nothing to recover

    assert extcall IERC20(_asset).transfer(_recipient, balance, default_return_value=True) # dev: recovery failed
    log DepartmentFundsRecovered(asset=_asset, recipient=_recipient, balance=balance)
