# @version 0.4.1

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department

# user wallets
userWallets: public(HashMap[uint256, address]) # index -> user wallet
indexOfUserWallet: public(HashMap[address, uint256]) # user wallet -> index
numUserWallets: public(uint256) # num userWallets

# locked
isLockedSigner: public(HashMap[address, bool]) # signer -> is locked


@deploy
def __init__(_undyHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting


################
# User Wallets #
################


@external
def createUserWallet(_user: address):
    assert msg.sender == addys._getWalletFactoryAddr() # dev: only wallet factory allowed
    assert not deptBasics.isPaused # dev: not activated

    wid: uint256 = self.numUserWallets
    if wid == 0:
        wid = 1 # not using 0 index
    self.userWallets[wid] = _user
    self.indexOfUserWallet[_user] = wid
    self.numUserWallets = wid + 1


# utils


@view
@external
def getNumUserWallets() -> uint256:
    return self._getNumUserWallets()


@view
@internal
def _getNumUserWallets() -> uint256:
    numUserWallets: uint256 = self.numUserWallets
    if numUserWallets == 0:
        return 0
    return numUserWallets - 1


@view
@external
def isUserWallet(_user: address) -> bool:
    return self.indexOfUserWallet[_user] != 0


##########
# Locked #
##########


@external
def setLockedSigner(_signer: address, _isLocked: bool):
    assert addys._isSwitchboardAddr(msg.sender) # dev: no perms
    assert not deptBasics.isPaused # dev: not activated
    self.isLockedSigner[_signer] = _isLocked