# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department

struct PointsData:
    usdValue: uint256
    depositPoints: uint256
    lastUpdate: uint256

struct VaultToken:
    legoId: uint256
    underlyingAsset: address
    decimals: uint256
    isRebasing: bool

# points
userPoints: public(HashMap[address, PointsData]) # user -> points
globalPoints: public(PointsData)

# user wallets (iterable)
userWallets: public(HashMap[uint256, address]) # index -> user wallet
indexOfUserWallet: public(HashMap[address, uint256]) # user wallet -> index
numUserWallets: public(uint256) # num userWallets

# ambassadors
ambassadors: public(HashMap[address, address]) # user -> ambassador

# agents (iterable)
agents: public(HashMap[uint256, address]) # index -> agent
indexOfAgent: public(HashMap[address, uint256]) # agent -> index
numAgents: public(uint256) # num agents

# vault tokens
vaultTokens: public(HashMap[address, VaultToken]) # vault token -> data


@deploy
def __init__(_undyHq: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    self.numUserWallets = 1
    self.numAgents = 1


################
# User Wallets #
################


@external
def createUserWallet(_user: address, _ambassador: address):
    assert msg.sender == addys._getHatcheryAddr() # dev: only hatchery allowed
    assert not deptBasics.isPaused # dev: not activated

    wid: uint256 = self.numUserWallets
    self.userWallets[wid] = _user
    self.indexOfUserWallet[_user] = wid
    self.numUserWallets = wid + 1

    # set ambassador
    if _ambassador != empty(address):
        self.ambassadors[_user] = _ambassador


# utils


@view
@external
def getNumUserWallets() -> uint256:
    return self._getNumUserWallets()


@view
@internal
def _getNumUserWallets() -> uint256:
    return self.numUserWallets - 1


@view
@external
def isUserWallet(_user: address) -> bool:
    return self.indexOfUserWallet[_user] != 0


##################
# Deposit Points #
##################


# set points


@external
def setUserPoints(_user: address, _data: PointsData):
    assert msg.sender == addys._getLootDistributorAddr() # dev: only loot distributor allowed
    self.userPoints[_user] = _data


@external
def setGlobalPoints(_data: PointsData):
    assert msg.sender == addys._getLootDistributorAddr() # dev: only loot distributor allowed
    self.globalPoints = _data


@external
def setUserAndGlobalPoints(_user: address, _userData: PointsData, _globalData: PointsData):
    assert msg.sender == addys._getLootDistributorAddr() # dev: only loot distributor allowed
    self.userPoints[_user] = _userData
    self.globalPoints = _globalData


# utils


@view
@external
def getLastTotalUsdValue(_user: address) -> uint256:
    return self.userPoints[_user].usdValue


@view
@external
def getUserAndGlobalPoints(_user: address) -> (PointsData, PointsData):
    return self.userPoints[_user], self.globalPoints


################
# Vault Tokens #
################


@view
@external
def isRegisteredVaultToken(_vaultToken: address) -> bool:
    return self.vaultTokens[_vaultToken].underlyingAsset != empty(address)


@external
def setVaultToken(
    _vaultToken: address,
    _legoId: uint256,
    _underlyingAsset: address,
    _decimals: uint256,
    _isRebasing: bool,
):
    assert addys._isLegoBookAddr(msg.sender) # dev: no perms
    self.vaultTokens[_vaultToken] = VaultToken(
        legoId = _legoId,
        underlyingAsset = _underlyingAsset,
        decimals = _decimals,
        isRebasing = _isRebasing,
    )


##########
# Agents #
##########


@external
def createAgent(_agent: address):
    assert msg.sender == addys._getHatcheryAddr() # dev: only hatchery allowed
    assert not deptBasics.isPaused # dev: not activated

    aid: uint256 = self.numAgents
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
    return self.numAgents - 1


@view
@external
def isAgent(_agent: address) -> bool:
    return self.indexOfAgent[_agent] != 0
