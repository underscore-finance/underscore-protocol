# @version 0.4.3

uses: addys

import contracts.modules.Addys as addys
from ethereum.ercs import IERC20

event LegoPauseModified:
    isPaused: bool

event LegoFundsRecovered:
    asset: indexed(address)
    recipient: indexed(address)
    balance: uint256

# config
isPaused: public(bool)

MAX_RECOVER_ASSETS: constant(uint256) = 20


@deploy
def __init__(_shouldPause: bool):
    self.isPaused = _shouldPause


###########
# General #
###########


# activate


@external
def pause(_shouldPause: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert _shouldPause != self.isPaused # dev: no change
    self.isPaused = _shouldPause
    log LegoPauseModified(isPaused=_shouldPause)


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
    log LegoFundsRecovered(asset=_asset, recipient=_recipient, balance=balance)