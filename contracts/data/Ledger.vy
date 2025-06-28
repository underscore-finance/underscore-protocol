# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department

struct UserWalletData:
    usdValue: uint256
    depositPoints: uint256
    lastUpdate: uint256
    ambassador: address

# user wallet data
userWalletData: public(HashMap[address, UserWalletData]) # user wallet -> data

# user wallets (iterable)
userWallets: public(HashMap[uint256, address]) # index -> user wallet
indexOfUserWallet: public(HashMap[address, uint256]) # user wallet -> index
numUserWallets: public(uint256) # num userWallets

# agents (iterable)
agents: public(HashMap[uint256, address]) # index -> agent
indexOfAgent: public(HashMap[address, uint256]) # agent -> index
numAgents: public(uint256) # num agents


@deploy
def __init__(_undyHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting


################
# User Wallets #
################


@external
def createUserWallet(_user: address, _ambassador: address):
    assert msg.sender == addys._getHatcheryAddr() # dev: only hatchery allowed
    assert not deptBasics.isPaused # dev: not activated

    wid: uint256 = self.numUserWallets
    if wid == 0:
        wid = 1 # not using 0 index
    self.userWallets[wid] = _user
    self.indexOfUserWallet[_user] = wid
    self.numUserWallets = wid + 1

    # set data
    self.userWalletData[_user] = UserWalletData(
        usdValue = 0,
        depositPoints = 0,
        lastUpdate = block.number,
        ambassador = _ambassador,
    )


# set user wallet data


@external
def setUserWalletData(_user: address, _data: UserWalletData):
    assert msg.sender == addys._getWalletBackpackAddr() # dev: only wallet backpack allowed
    self.userWalletData[_user] = _data


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


@view
@external
def getLastTotalUsdValue(_user: address) -> uint256:
    return self.userWalletData[_user].usdValue


##########
# Agents #
##########


@external
def createAgent(_agent: address):
    assert msg.sender == addys._getHatcheryAddr() # dev: only hatchery allowed
    assert not deptBasics.isPaused # dev: not activated

    aid: uint256 = self.numAgents
    if aid == 0:
        aid = 1 # not using 0 index
    self.agents[aid] = _agent
    self.indexOfAgent[_agent] = aid
    self.numAgents = aid + 1


# utils


@view
@external
def getNumAgents() -> uint256:
    return self._getNumAgents()


@view
@internal
def _getNumAgents() -> uint256:
    numAgents: uint256 = self.numAgents
    if numAgents == 0:
        return 0
    return numAgents - 1


@view
@external
def isAgent(_agent: address) -> bool:
    return self.indexOfAgent[_agent] != 0
