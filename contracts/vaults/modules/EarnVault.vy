#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

implements: IERC4626
implements: IERC20

exports: token.__interface__
initializes: token
from contracts.vaults.modules import VaultErc20Token as token

exports: vaultWallet.__interface__
initializes: vaultWallet
from contracts.vaults.modules import EarnVaultWallet as vaultWallet

from ethereum.ercs import IERC4626
from ethereum.ercs import IERC20
from ethereum.ercs import IERC20Detailed
from interfaces import WalletConfigStructs as wcs

interface VaultRegistry:
    def maxDepositAmount(_vaultAddr: address) -> uint256: view
    def canWithdraw(_vaultAddr: address) -> bool: view
    def canDeposit(_vaultAddr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

event Deposit:
    sender: indexed(address)
    owner: indexed(address)
    assets: uint256
    shares: uint256

event Withdraw:
    sender: indexed(address)
    receiver: indexed(address)
    owner: indexed(address)
    assets: uint256
    shares: uint256

ASSET: immutable(address)
UNDY_HQ: immutable(address)

VAULT_REGISTRY_ID: constant(uint256) = 10
HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
ONE_PERCENT: constant(uint256) = 1_00 # 1%


@deploy
def __init__(
    _asset: address,
    _tokenName: String[64],
    _tokenSymbol: String[32],
    _undyHq: address,
    _minHqTimeLock: uint256,
    _maxHqTimeLock: uint256,
    _startingAgent: address,
):
    assert _asset != empty(address) # dev: invalid asset
    ASSET = _asset
    UNDY_HQ = _undyHq

    token.__init__(_tokenName, _tokenSymbol, staticcall IERC20Detailed(_asset).decimals(), _undyHq, _minHqTimeLock, _maxHqTimeLock)
    vaultWallet.__init__(_undyHq, _asset, _startingAgent)


@view
@internal
def _getVaultRegistry() -> address:
    return staticcall Registry(UNDY_HQ).getAddr(VAULT_REGISTRY_ID)


@view
@external
def asset() -> address:
    return ASSET


@view
@external
def totalAssets() -> uint256:
    return vaultWallet._getTotalAssets(True)


############
# Deposits #
############


@view
@external
def maxDeposit(_receiver: address) -> uint256:
    vaultRegistry: address = self._getVaultRegistry()
    if not staticcall VaultRegistry(vaultRegistry).canDeposit(self):
        return 0

    maxAmount: uint256 = staticcall VaultRegistry(vaultRegistry).maxDepositAmount(self)
    if maxAmount == 0:
        return max_value(uint256)

    totalAssets: uint256 = vaultWallet._getTotalAssets(True)
    if totalAssets >= maxAmount:
        return 0

    return maxAmount - totalAssets


@view
@external
def previewDeposit(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, vaultWallet._getTotalAssets(True), False)


@nonreentrant
@external
def deposit(_assets: uint256, _receiver: address = msg.sender) -> uint256:
    asset: address = ASSET

    amount: uint256 = _assets
    if amount == max_value(uint256):
        amount = staticcall IERC20(asset).balanceOf(msg.sender)

    totalAssets: uint256 = vaultWallet._getTotalAssets(True)
    shares: uint256 = self._amountToShares(amount, token.totalSupply, totalAssets, False)
    self._deposit(asset, amount, shares, _receiver, totalAssets)
    return shares


# mint


@view
@external
def maxMint(_receiver: address) -> uint256:
    vaultRegistry: address = self._getVaultRegistry()
    if not staticcall VaultRegistry(vaultRegistry).canDeposit(self):
        return 0

    maxAmount: uint256 = staticcall VaultRegistry(vaultRegistry).maxDepositAmount(self)
    if maxAmount == 0:
        return max_value(uint256)

    totalAssets: uint256 = vaultWallet._getTotalAssets(True)
    if totalAssets >= maxAmount:
        return 0

    maxDepositAmt: uint256 = maxAmount - totalAssets
    return self._amountToShares(maxDepositAmt, token.totalSupply, totalAssets, False)


@view
@external
def previewMint(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares, token.totalSupply, vaultWallet._getTotalAssets(True), True)


@nonreentrant
@external
def mint(_shares: uint256, _receiver: address = msg.sender) -> uint256:
    asset: address = ASSET
    totalAssets: uint256 = vaultWallet._getTotalAssets(True)
    amount: uint256 = self._sharesToAmount(_shares, token.totalSupply, totalAssets, True)
    self._deposit(asset, amount, _shares, _receiver, totalAssets)
    return amount


# shared deposit logic


@internal
def _deposit(_asset: address, _amount: uint256, _shares: uint256, _recipient: address, _totalAssets: uint256):
    vaultRegistry: address = self._getVaultRegistry()
    assert staticcall VaultRegistry(vaultRegistry).canDeposit(self) # dev: cannot deposit

    assert _amount != 0 # dev: cannot deposit 0 amount
    assert _shares != 0 # dev: cannot receive 0 shares
    assert _recipient != empty(address) # dev: invalid recipient

    maxAmount: uint256 = staticcall VaultRegistry(vaultRegistry).maxDepositAmount(self)
    if maxAmount != 0:
        assert _totalAssets + _amount <= maxAmount # dev: exceeds max deposit

    assert extcall IERC20(_asset).transferFrom(msg.sender, self, _amount, default_return_value=True) # dev: deposit failed
    token._mint(_recipient, _shares)

    log Deposit(sender=msg.sender, owner=_recipient, assets=_amount, shares=_shares)


###############
# Withdrawals #
###############


@view
@external
def maxWithdraw(_owner: address) -> uint256:
    ownerShares: uint256 = token.balanceOf[_owner]
    if ownerShares == 0:
        return 0
    availableAssets: uint256 = vaultWallet._getTotalAssets(False)
    ownerAssets: uint256 = self._sharesToAmount(ownerShares, token.totalSupply, availableAssets, False)
    return min(ownerAssets, availableAssets)


@view
@external
def previewWithdraw(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, vaultWallet._getTotalAssets(True), True)


@nonreentrant
@external
def withdraw(_assets: uint256, _receiver: address = msg.sender, _owner: address = msg.sender) -> uint256:
    asset: address = ASSET
    shares: uint256 = self._amountToShares(_assets, token.totalSupply, vaultWallet._getTotalAssets(True), True)
    self._redeem(asset, _assets, shares, msg.sender, _receiver, _owner)
    return shares


# redeem


@view
@external
def maxRedeem(_owner: address) -> uint256:
    return token.balanceOf[_owner]


@view
@external
def previewRedeem(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares, token.totalSupply, vaultWallet._getTotalAssets(False), False)


@nonreentrant
@external
def redeem(_shares: uint256, _receiver: address = msg.sender, _owner: address = msg.sender) -> uint256:
    asset: address = ASSET

    shares: uint256 = _shares
    if shares == max_value(uint256):
        shares = token.balanceOf[_owner]

    amount: uint256 = self._sharesToAmount(shares, token.totalSupply, vaultWallet._getTotalAssets(False), False)
    return self._redeem(asset, amount, shares, msg.sender, _receiver, _owner)


# shared redeem logic


@internal
def _redeem(
    _asset: address,
    _amount: uint256,
    _shares: uint256,
    _sender: address,
    _recipient: address,
    _owner: address,
) -> uint256:
    vaultRegistry: address = self._getVaultRegistry()
    assert staticcall VaultRegistry(vaultRegistry).canWithdraw(self) # dev: cannot withdraw

    assert _amount != 0 # dev: cannot withdraw 0 amount
    assert _shares != 0 # dev: cannot redeem 0 shares
    assert _recipient != empty(address) # dev: invalid recipient

    assert token.balanceOf[_owner] >= _shares # dev: insufficient shares

    if _sender != _owner:
        token._spendAllowance(_owner, _sender, _shares)

    # withdraw from yield opportunity
    actualAmount: uint256 = vaultWallet._prepareRedemption(_amount, _sender, vaultRegistry)
    assert self._isCloseEnough(_amount, actualAmount) # dev: insufficient funds

    # burn shares, transfer assets
    token._burn(_owner, _shares)
    assert extcall IERC20(_asset).transfer(_recipient, actualAmount, default_return_value=True) # dev: withdrawal failed

    log Withdraw(sender=_sender, receiver=_recipient, owner=_owner, assets=actualAmount, shares=_shares)
    return actualAmount


# is close enough


@pure
@internal
def _isCloseEnough(_requestedAmount: uint256, _actualAmount: uint256) -> bool:
    # extra safety check to make sure what was redeemed was actually close-ish to what was requested
    buffer: uint256 = _requestedAmount * ONE_PERCENT // HUNDRED_PERCENT
    lowerBound: uint256 = _requestedAmount - buffer
    return _actualAmount >= lowerBound


##########
# Shares #
##########


@view
@external
def convertToShares(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, vaultWallet._getTotalAssets(False), False)


@view
@external
def convertToAssets(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares, token.totalSupply, vaultWallet._getTotalAssets(False), False)


# amount -> shares


@view
@internal
def _amountToShares(
    _amount: uint256,
    _totalShares: uint256,
    _totalBalance: uint256,
    _shouldRoundUp: bool,
) -> uint256:
    if _amount == max_value(uint256) or _amount == 0:
        return _amount

    # first deposit, price per share = 1
    if _totalShares == 0:
        return _amount

    # no underlying balance, price per share = 0
    if _totalBalance == 0:
        return 0

    # calc shares
    numerator: uint256 = _amount * _totalShares
    shares: uint256 = numerator // _totalBalance

    # rounding
    if _shouldRoundUp and (numerator % _totalBalance != 0):
        shares += 1

    return shares


# shares -> amount


@view
@internal
def _sharesToAmount(
    _shares: uint256,
    _totalShares: uint256,
    _totalBalance: uint256,
    _shouldRoundUp: bool,
) -> uint256:
    if _shares == max_value(uint256) or _shares == 0:
        return _shares

    # first deposit, price per share = 1
    if _totalShares == 0:
        return _shares

    # calc amount
    numerator: uint256 = _shares * _totalBalance
    amount: uint256 = numerator // _totalShares

    # rounding
    if _shouldRoundUp and (numerator % _totalShares != 0):
        amount += 1

    return amount
