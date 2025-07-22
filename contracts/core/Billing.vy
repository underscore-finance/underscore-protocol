#                                                                            ___           ___     
#         _____        ___                                     ___          /__/\         /  /\    
#        /  /::\      /  /\                                   /  /\         \  \:\       /  /:/_   
#       /  /:/\:\    /  /:/      ___     ___   ___     ___   /  /:/          \  \:\     /  /:/ /\  
#      /  /:/~/::\  /__/::\     /__/\   /  /\ /__/\   /  /\ /__/::\      _____\__\:\   /  /:/_/::\ 
#     /__/:/ /:/\:| \__\/\:\__  \  \:\ /  /:/ \  \:\ /  /:/ \__\/\:\__  /__/::::::::\ /__/:/__\/\:\
#     \  \:\/:/~/:/    \  \:\/\  \  \:\  /:/   \  \:\  /:/     \  \:\/\ \  \:\~~\~~\/ \  \:\ /~~/:/
#      \  \::/ /:/      \__\::/   \  \:\/:/     \  \:\/:/       \__\::/  \  \:\  ~~~   \  \:\  /:/ 
#       \  \:\/:/       /__/:/     \  \::/       \  \::/        /__/:/    \  \:\        \  \:\/:/  
#        \  \::/        \__\/       \__\/         \__\/         \__\/      \  \:\        \  \::/   
#         \__\/                                                             \__\/         \__\/    
#
#     ╔═════════════════════════════════════════════════════╗
#     ║  ** Billing **                                      ║
#     ║  Where payees / cheque recipients can pull payment. ║
#     ╚═════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Department

exports: addys.__interface__
exports: deptBasics.__interface__

initializes: addys
initializes: deptBasics[addys := addys]

import contracts.modules.Addys as addys
import contracts.modules.DeptBasics as deptBasics
from interfaces import Department
from interfaces import WalletConfigStructs as wcs

from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed

interface UserWalletConfig:
    def preparePayment(_targetAsset: address, _legoId: uint256, _vaultToken: address, _vaultAmount: uint256 = max_value(uint256)) -> (uint256, uint256): nonpayable
    def payeeSettings(_payee: address) -> wcs.PayeeSettings: view
    def globalPayeeSettings() -> wcs.GlobalPayeeSettings: view
    def deregisterAsset(_asset: address) -> bool: nonpayable
    def cheques(_recipient: address) -> wcs.Cheque: view
    def chequeSettings() -> wcs.ChequeSettings: view

interface UserWallet:
    def transferFunds(_recipient: address, _asset: address = empty(address), _amount: uint256 = max_value(uint256), _isCheque: bool = False, _isSpecialTx: bool = False) -> (uint256, uint256): nonpayable
    def assetData(asset: address) -> WalletAssetData: view
    def assets(i: uint256) -> address: view
    def walletConfig() -> address: view
    def numAssets() -> uint256: view

interface Ledger:
    def vaultTokens(_vaultToken: address) -> VaultToken: view
    def isUserWallet(_user: address) -> bool: view

interface Appraiser:
    def getPricePerShareWithConfig(asset: address, legoAddr: address, staleBlocks: uint256, _decimals: uint256) -> uint256: view

interface MissionControl:
    def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct WalletAssetData:
    assetBalance: uint256
    usdValue: uint256
    isYieldAsset: bool
    lastYieldPrice: uint256

struct VaultToken:
    legoId: uint256
    underlyingAsset: address
    decimals: uint256
    isRebasing: bool

struct AssetUsdValueConfig:
    legoId: uint256
    legoAddr: address
    decimals: uint256
    staleBlocks: uint256
    isYieldAsset: bool
    underlyingAsset: address

event ChequePaymentPulled:
    asset: indexed(address)
    amount: uint256
    usdValue: uint256
    chequeRecipient: indexed(address)
    userWallet: indexed(address)

event PayeePaymentPulled:
    asset: indexed(address)
    amount: uint256
    usdValue: uint256
    payee: indexed(address)
    userWallet: indexed(address)

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
MAX_DEREGISTER_ASSETS: constant(uint256) = 25

WETH: public(immutable(address))
ETH: public(immutable(address))


@deploy
def __init__(_undyHq: address, _wethAddr: address, _ethAddr: address):
    addys.__init__(_undyHq)
    deptBasics.__init__(False, False) # no minting

    WETH = _wethAddr
    ETH = _ethAddr


#########################
# Cheque - Pull Payment #
#########################


@nonreentrant
@external
def pullPaymentAsCheque(_userWallet: address, _paymentAsset: address, _paymentAmount: uint256) -> (uint256, uint256):
    a: addys.Addys = addys._getAddys()
    assert staticcall Ledger(a.ledger).isUserWallet(_userWallet) # dev: not a user wallet

    # validate cheque recipient can pull payment
    chequeRecipient: address = msg.sender
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    assert self._canPullPaymentAsCheque(chequeRecipient, walletConfig) # dev: no perms

    # pull payment
    amount: uint256 = 0
    usdValue: uint256 = 0
    amount, usdValue = self._pullPayment(_paymentAsset, _paymentAmount, chequeRecipient, True, _userWallet, walletConfig, a.missionControl, a.legoBook, a.appraiser, a.ledger)
    assert amount != 0 # dev: insufficient funds
    
    log ChequePaymentPulled(asset = _paymentAsset, amount = amount, usdValue = usdValue, chequeRecipient = chequeRecipient, userWallet = _userWallet)
    return amount, usdValue


# validation 


@view
@external
def canPullPaymentAsCheque(_userWallet: address, _chequeRecipient: address) -> bool:
    return self._canPullPaymentAsCheque(_chequeRecipient, staticcall UserWallet(_userWallet).walletConfig())


@view
@internal
def _canPullPaymentAsCheque(_chequeRecipient: address, _walletConfig: address) -> bool:
    # NOTE: a lot more validation will occur later in flow as to whether this cheque is valid
    # UserWallet.transferFunds() -> WalletConfig.validateCheque() -> Sentinel.isValidChequeAndGetData()
    # For now, we are only checking if the cheque recipient can pull payment
    chequeSettings: wcs.ChequeSettings = staticcall UserWalletConfig(_walletConfig).chequeSettings()
    if not chequeSettings.canBePulled:
        return False

    cheque: wcs.Cheque = staticcall UserWalletConfig(_walletConfig).cheques(_chequeRecipient)
    return cheque.canBePulled


########################
# Payee - Pull Payment #
########################


@nonreentrant
@external
def pullPaymentAsPayee(_userWallet: address, _paymentAsset: address, _paymentAmount: uint256) -> (uint256, uint256):
    a: addys.Addys = addys._getAddys()
    assert staticcall Ledger(a.ledger).isUserWallet(_userWallet) # dev: not a user wallet

    # validate payee can pull payment
    payee: address = msg.sender
    walletConfig: address = staticcall UserWallet(_userWallet).walletConfig()
    assert self._canPullPaymentAsPayee(payee, walletConfig) # dev: no perms

    # pull payment
    amount: uint256 = 0
    usdValue: uint256 = 0
    amount, usdValue = self._pullPayment(_paymentAsset, _paymentAmount, payee, False, _userWallet, walletConfig, a.missionControl, a.legoBook, a.appraiser, a.ledger)
    assert amount != 0 # dev: insufficient funds
    
    log PayeePaymentPulled(asset = _paymentAsset, amount = amount, usdValue = usdValue, payee = payee, userWallet = _userWallet)
    return amount, usdValue


# validation 


@view
@external
def canPullPaymentAsPayee(_userWallet: address, _payee: address) -> bool:
    return self._canPullPaymentAsPayee(_payee, staticcall UserWallet(_userWallet).walletConfig())


@view
@internal
def _canPullPaymentAsPayee(_payee: address, _walletConfig: address) -> bool:
    # NOTE: a lot more validation will occur later in flow as to whether this payee is valid
    # UserWallet.transferFunds() -> WalletConfig.checkRecipientLimitsAndUpdateData() -> Sentinel.isValidPayeeAndGetData()
    # For now, we are only checking if the payee can pull payment
    globalPayeeSettings: wcs.GlobalPayeeSettings = staticcall UserWalletConfig(_walletConfig).globalPayeeSettings()
    if not globalPayeeSettings.canPull:
        return False
    
    payeeSettings: wcs.PayeeSettings = staticcall UserWalletConfig(_walletConfig).payeeSettings(_payee)
    return payeeSettings.canPull


#############
# Utilities #
#############


# pull payment (shared between payees and cheque recipients)


@internal
def _pullPayment(
    _paymentAsset: address,
    _paymentAmount: uint256,
    _recipient: address,
    _isCheque: bool,
    _userWallet: address,
    _userWalletConfig: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
    _ledger: address,
) -> (uint256, uint256):
    availPaymentAmount: uint256 = staticcall IERC20(_paymentAsset).balanceOf(_userWallet)

    # withdraw from any yield opportunities
    if availPaymentAmount < _paymentAmount:
        amountNeeded: uint256 = _paymentAmount - availPaymentAmount
        self._withdrawFromYieldOpportunities(_paymentAsset, amountNeeded, _userWallet, _userWalletConfig, _missionControl, _legoBook, _appraiser, _ledger)

    # cheque payments must be full amount -- payees can pull partial payments
    availPaymentAmount = staticcall IERC20(_paymentAsset).balanceOf(_userWallet)
    if _isCheque and availPaymentAmount < _paymentAmount:
        return 0, 0

    # transfer assets
    amount: uint256 = 0
    usdValue: uint256 = 0
    if availPaymentAmount != 0:
        amount, usdValue = extcall UserWallet(_userWallet).transferFunds(_recipient, _paymentAsset, _paymentAmount, _isCheque, False)
        extcall UserWalletConfig(_userWalletConfig).deregisterAsset(_paymentAsset) # deregister asset if it has no balance left

    return amount, usdValue


# withdraw from yield opportunities


@internal
def _withdrawFromYieldOpportunities(
    _paymentAsset: address,
    _amountNeeded: uint256,
    _userWallet: address,
    _userWalletConfig: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
    _ledger: address,
) -> uint256:

    # add 1% buffer to make sure there is enough
    targetWithdrawalAmount: uint256 = _amountNeeded * 101_00 // HUNDRED_PERCENT

    numAssets: uint256 = staticcall UserWallet(_userWallet).numAssets()
    if numAssets == 0:
        return 0

    amountWithdraw: uint256 = 0
    assetsToDeregister: DynArray[address, MAX_DEREGISTER_ASSETS] = []

    for i: uint256 in range(1, numAssets, bound=max_value(uint256)):
        if amountWithdraw >= targetWithdrawalAmount:
            break

        asset: address = staticcall UserWallet(_userWallet).assets(i)
        if asset == empty(address):
            continue

        data: WalletAssetData = staticcall UserWallet(_userWallet).assetData(asset)
        if not data.isYieldAsset or data.assetBalance == 0:
            continue

        # get underlying details
        config: AssetUsdValueConfig = self._getAssetUsdValueConfig(asset, _missionControl, _legoBook, _ledger)
        if config.underlyingAsset != _paymentAsset or config.legoId == 0:
            continue

        # get price per share for this vault token
        pricePerShare: uint256 = staticcall Appraiser(_appraiser).getPricePerShareWithConfig(asset, config.legoAddr, config.staleBlocks, config.decimals)
        if pricePerShare == 0:
            continue

        # calculate how many vault tokens we need to withdraw
        amountStillNeeded: uint256 = targetWithdrawalAmount - amountWithdraw
        vaultTokensNeeded: uint256 = amountStillNeeded * (10 ** config.decimals) // pricePerShare

        # withdraw vault tokens to get underlying
        underlyingAmount: uint256 = 0
        na: uint256 = 0
        underlyingAmount, na = extcall UserWalletConfig(_userWalletConfig).preparePayment(config.underlyingAsset, config.legoId, asset, vaultTokensNeeded)

        # update recovered amount
        amountWithdraw += underlyingAmount

        # add to deregister list
        if len(assetsToDeregister) < MAX_DEREGISTER_ASSETS:
            assetsToDeregister.append(asset)

    # deregister assets -- this will only deregister if it truly has no balance left
    for asset: address in assetsToDeregister:
        extcall UserWalletConfig(_userWalletConfig).deregisterAsset(asset)

    return amountWithdraw

        
# get asset usd value config


@view
@external
def getAssetUsdValueConfig(_asset: address) -> AssetUsdValueConfig:
    a: addys.Addys = addys._getAddys()
    return self._getAssetUsdValueConfig(_asset, a.missionControl, a.legoBook, a.ledger)


@view
@internal
def _getAssetUsdValueConfig(
    _asset: address,
    _missionControl: address,
    _legoBook: address,
    _ledger: address,
) -> AssetUsdValueConfig:
    config: AssetUsdValueConfig = staticcall MissionControl(_missionControl).getAssetUsdValueConfig(_asset)

    # if no specific config, fallback to vault token registration
    if config.decimals == 0:
        vaultToken: VaultToken = staticcall Ledger(_ledger).vaultTokens(_asset)
        if vaultToken.underlyingAsset != empty(address):
            config.legoId = vaultToken.legoId
            config.decimals = vaultToken.decimals
            config.isYieldAsset = True
            config.underlyingAsset = vaultToken.underlyingAsset

    # get lego addr if needed
    if config.legoId != 0 and config.legoAddr == empty(address):
        config.legoAddr = staticcall Registry(_legoBook).getAddr(config.legoId)

    # get decimals if needed
    if config.decimals == 0:
        config.decimals = self._getDecimals(_asset)

    return config


# get decimals


@view
@internal
def _getDecimals(_asset: address) -> uint256:
    if _asset in [WETH, ETH]:
        return 18
    return convert(staticcall IERC20Detailed(_asset).decimals(), uint256)