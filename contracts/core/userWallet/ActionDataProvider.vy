#    ┓ ┏  ┓┓   
#    ┃┃┃┏┓┃┃┏┓╋
#    ┗┻┛┗┻┗┗┗ ┗
#     ___        __  _                ____        __       
#    /   | _____/ /_(_)___  ____     / __ \____ _/ /_____ _
#   / /| |/ ___/ __/ / __ \/ __ \   / / / / __ `/ __/ __ `/
#  / ___ / /__/ /_/ / /_/ / / / /  / /_/ / /_/ / /_/ /_/ / 
# /_/  |_\___/\__/_/\____/_/ /_/  /_____/\__,_/\__/\__,_/  
                                                                                                                                                       
#     ╔══════════════════════════════════════════════╗
#     ║  ** Action Data Provider **                  ║
#     ║  Read-only helper for wallet action data.    ║
#     ╚══════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

from interfaces import WalletStructs as ws
from interfaces import WalletConfigStructs as wcs

interface UserWalletConfig:
    def managerSettings(_manager: address) -> wcs.ManagerSettings: view
    def managerPeriodData(_manager: address) -> wcs.ManagerData: view
    def globalManagerSettings() -> wcs.GlobalManagerSettings: view
    def indexOfManager(_manager: address) -> uint256: view
    def indexOfWhitelist(_addr: address) -> uint256: view
    def inEjectMode() -> bool: view
    def wallet() -> address: view
    def owner() -> address: view
    def isFrozen() -> bool: view

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view
    def isLockedSigner(_signer: address) -> bool: view

interface Ledger:
    def isRegisteredBackpackItem(_addr: address) -> bool: view
    def getLastTotalUsdValue(_user: address) -> uint256: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view
    def isValidAddr(_addr: address) -> bool: view

interface Sentinel:
    def canSignerPerformActionWithConfig(_isOwner: bool, _isManager: bool, _data: wcs.ManagerData, _config: wcs.ManagerSettings, _globalConfig: wcs.GlobalManagerSettings, _action: ws.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _payee: address = empty(address)) -> bool: view

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface AgentWrapper:
    def isSender(_address: address) -> bool: view

MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

LEDGER_ID: constant(uint256) = 1
MISSION_CONTROL_ID: constant(uint256) = 2
LEGO_BOOK_ID: constant(uint256) = 3
SWITCHBOARD_ID: constant(uint256) = 4
HATCHERY_ID: constant(uint256) = 5
LOOT_DISTRIBUTOR_ID: constant(uint256) = 6
APPRAISER_ID: constant(uint256) = 7
BILLING_ID: constant(uint256) = 9
VAULT_REGISTRY_ID: constant(uint256) = 10


@view
@external
def isValidRegistryAddr(_addr: address, _undyHq: address) -> bool:
    return staticcall Registry(_undyHq).isValidAddr(_addr)


@view
@external
def isSwitchboardAddr(_addr: address, _undyHq: address) -> bool:
    switchboard: address = staticcall Registry(_undyHq).getAddr(SWITCHBOARD_ID)
    if switchboard == empty(address):
        return False
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_addr)


@view
@external
def canPerformSecurityAction(_addr: address, _undyHq: address) -> bool:
    missionControl: address = staticcall Registry(_undyHq).getAddr(MISSION_CONTROL_ID)
    if missionControl == empty(address):
        return False
    return staticcall MissionControl(missionControl).canPerformSecurityAction(_addr)


@view
@external
def canSetBackpackItem(_newBackpackAddr: address, _caller: address, _owner: address, _undyHq: address) -> bool:
    if _caller != _owner:
        return False
    ledger: address = staticcall Registry(_undyHq).getAddr(LEDGER_ID)
    if ledger == empty(address):
        return False
    return staticcall Ledger(ledger).isRegisteredBackpackItem(_newBackpackAddr)


@view
@external
def isAgentSender(_addr: address, _agent: address) -> bool:
    if _agent == empty(address):
        return False
    # Contracts still in construction have no runtime code yet and are treated as non-agents.
    if not _agent.is_contract:
        return False
    return staticcall AgentWrapper(_agent).isSender(_addr)


@view
@external
def getActionDataBundle(
    _walletConfig: address,
    _legoId: uint256,
    _signer: address,
    _undyHq: address,
    _eth: address,
    _weth: address,
) -> ws.ActionData:
    return self._getActionDataBundle(_walletConfig, _legoId, _signer, _undyHq, _eth, _weth)


@view
@external
def checkSignerPermissionsAndGetBundle(
    _walletConfig: address,
    _signer: address,
    _action: ws.ActionType,
    _undyHq: address,
    _eth: address,
    _weth: address,
    _sentinel: address,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS],
    _transferRecipient: address,
) -> ws.ActionData:
    legoId: uint256 = 0
    if len(_legoIds) != 0:
        legoId = _legoIds[0]

    ad: ws.ActionData = self._getActionDataBundle(_walletConfig, legoId, _signer, _undyHq, _eth, _weth)
    if ad.signer == ad.billing:
        return ad

    assert not staticcall MissionControl(ad.missionControl).isLockedSigner(_signer) # dev: signer is locked

    recipient: address = _transferRecipient
    if _transferRecipient != empty(address) and staticcall UserWalletConfig(_walletConfig).indexOfWhitelist(_transferRecipient) != 0:
        recipient = empty(address)

    assert staticcall Sentinel(_sentinel).canSignerPerformActionWithConfig(
        _signer == ad.walletOwner,
        ad.isManager,
        staticcall UserWalletConfig(_walletConfig).managerPeriodData(_signer),
        staticcall UserWalletConfig(_walletConfig).managerSettings(_signer),
        staticcall UserWalletConfig(_walletConfig).globalManagerSettings(),
        _action,
        _assets,
        _legoIds,
        recipient,
    ) # dev: no permission

    return ad


@view
@internal
def _getActionDataBundle(
    _walletConfig: address,
    _legoId: uint256,
    _signer: address,
    _undyHq: address,
    _eth: address,
    _weth: address,
) -> ws.ActionData:
    wallet: address = staticcall UserWalletConfig(_walletConfig).wallet()

    # lego details
    legoBook: address = staticcall Registry(_undyHq).getAddr(LEGO_BOOK_ID)
    legoAddr: address = empty(address)
    if _legoId != 0 and legoBook != empty(address):
        legoAddr = staticcall Registry(legoBook).getAddr(_legoId)

    ledger: address = staticcall Registry(_undyHq).getAddr(LEDGER_ID)
    lastTotalUsdValue: uint256 = 0
    if ledger != empty(address):
        lastTotalUsdValue = staticcall Ledger(ledger).getLastTotalUsdValue(wallet)

    return ws.ActionData(
        ledger = ledger,
        missionControl = staticcall Registry(_undyHq).getAddr(MISSION_CONTROL_ID),
        legoBook = legoBook,
        hatchery = staticcall Registry(_undyHq).getAddr(HATCHERY_ID),
        lootDistributor = staticcall Registry(_undyHq).getAddr(LOOT_DISTRIBUTOR_ID),
        appraiser = staticcall Registry(_undyHq).getAddr(APPRAISER_ID),
        billing = staticcall Registry(_undyHq).getAddr(BILLING_ID),
        vaultRegistry = staticcall Registry(_undyHq).getAddr(VAULT_REGISTRY_ID),
        wallet = wallet,
        walletConfig = _walletConfig,
        walletOwner = staticcall UserWalletConfig(_walletConfig).owner(),
        inEjectMode = staticcall UserWalletConfig(_walletConfig).inEjectMode(),
        isFrozen = staticcall UserWalletConfig(_walletConfig).isFrozen(),
        lastTotalUsdValue = lastTotalUsdValue,
        signer = _signer,
        isManager = staticcall UserWalletConfig(_walletConfig).indexOfManager(_signer) != 0,
        legoId = _legoId,
        legoAddr = legoAddr,
        eth = _eth,
        weth = _weth,
    )
