#    ________   __  __   _________  ______   ______   ________  __       ______   _________  
#   /_______/\ /_/\/_/\ /________/\/_____/\ /_____/\ /_______/\/_/\     /_____/\ /________/\ 
#   \::: _  \ \\:\ \:\ \\__.::.__\/\:::_ \ \\:::_ \ \\__.::._\/\:\ \    \:::_ \ \\__.::.__\/ 
#    \::(_)  \ \\:\ \:\ \  \::\ \   \:\ \ \ \\:(_) \ \  \::\ \  \:\ \    \:\ \ \ \  \::\ \   
#     \:: __  \ \\:\ \:\ \  \::\ \   \:\ \ \ \\: ___\/  _\::\ \__\:\ \____\:\ \ \ \  \::\ \  
#      \:.\ \  \ \\:\_\:\ \  \::\ \   \:\_\ \ \\ \ \   /__\::\__/\\:\/___/\\:\_\ \ \  \::\ \ 
#       \__\/\__\/ \_____\/   \__\/    \_____\/ \_\/   \________\/ \_____\/ \_____\/   \__\/ 
#                                                                       
#     ╔══════════════════════════════════════════════════════════════════════╗
#     ║  ** Earn Autopilot Vaults **                                         ║
#     ║  Managed by AI agents, enforced by onchain rules. Erc4626 compliant. ║
#     ╚══════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

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

interface VaultRegistry:
    def getDepositConfig(_vaultAddr: address) -> (bool, uint256, bool, address): view
    def canWithdraw(_vaultAddr: address) -> bool: view

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

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%


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
    token.__init__(_tokenName, _tokenSymbol, staticcall IERC20Detailed(_asset).decimals(), _undyHq)
    vaultWallet.__init__(_undyHq, _asset, _startingAgent)


@view
@external
def asset() -> address:
    return vaultWallet.VAULT_ASSET


@view
@external
def totalAssets() -> uint256:
    return self._getTotalAssets(True)


################
# Total Assets #
################


@view
@external
def getTotalAssets(_shouldGetMax: bool) -> uint256:
    return self._getTotalAssets(_shouldGetMax)


@view
@internal
def _getTotalAssets(_shouldGetMax: bool, _vaultRegistry: address = empty(address)) -> uint256:
    vaultRegistry: address = _vaultRegistry
    if vaultRegistry == empty(address):
        vaultRegistry = vaultWallet._getVaultRegistry()
    return self._getUnderlyingData(_shouldGetMax, vaultRegistry)[0]


@view
@internal
def _getUnderlyingData(_shouldGetMax: bool, _vaultRegistry: address) -> (uint256, uint256, uint256, address):
    totalAssets: uint256 = staticcall IERC20(vaultWallet.VAULT_ASSET).balanceOf(self)

    # all underlying assets
    maxTotalAssets: uint256 = 0
    safeTotalAssets: uint256 = 0
    maxBalVaultToken: address = empty(address)
    maxTotalAssets, safeTotalAssets, maxBalVaultToken = vaultWallet._getUnderlyingYieldBalances()

    # new yield
    currentBalance: uint256 = 0
    newYield: uint256 = 0
    currentBalance, newYield = vaultWallet._calcNewYieldAndGetUnderlying(maxTotalAssets)

    # pending fees
    pendingYieldRealized: uint256 = vaultWallet.pendingYieldRealized + newYield
    pendingFees: uint256 = pendingYieldRealized * vaultWallet._getPerformanceFeeRatio(_vaultRegistry) // HUNDRED_PERCENT

    # add total assets
    if _shouldGetMax:
        totalAssets += maxTotalAssets
    else:
        totalAssets += safeTotalAssets
    totalAssets -= min(pendingFees, totalAssets)

    return totalAssets, currentBalance, pendingYieldRealized, maxBalVaultToken


############
# Deposits #
############


@view
@external
def maxDeposit(_receiver: address) -> uint256:
    vaultRegistry: address = vaultWallet._getVaultRegistry()

    # deposit config
    canDeposit: bool = False
    maxDepositAmount: uint256 = 0
    na1: bool = False
    na2: address = empty(address)
    canDeposit, maxDepositAmount, na1, na2 = staticcall VaultRegistry(vaultRegistry).getDepositConfig(self)

    if not canDeposit:
        return 0

    if maxDepositAmount == 0:
        return max_value(uint256)

    totalAssets: uint256 = self._getTotalAssets(True, vaultRegistry)
    if totalAssets >= maxDepositAmount:
        return 0

    return maxDepositAmount - totalAssets


@view
@external
def previewDeposit(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, self._getTotalAssets(True), False)


@nonreentrant
@external
def deposit(_assets: uint256, _receiver: address = msg.sender) -> uint256:
    vaultRegistry: address = vaultWallet._getVaultRegistry()
    asset: address = vaultWallet.VAULT_ASSET

    amount: uint256 = _assets
    if amount == max_value(uint256):
        amount = staticcall IERC20(asset).balanceOf(msg.sender)

    # underlying data
    totalAssets: uint256 = 0
    currentBalance: uint256 = 0
    pendingYieldRealized: uint256 = 0
    maxBalVaultToken: address = empty(address)
    totalAssets, currentBalance, pendingYieldRealized, maxBalVaultToken = self._getUnderlyingData(True, vaultRegistry)

    shares: uint256 = self._amountToShares(amount, token.totalSupply, totalAssets, False)
    self._deposit(asset, amount, shares, _receiver, totalAssets, currentBalance, pendingYieldRealized, maxBalVaultToken, vaultRegistry)
    return shares


# mint


@view
@external
def maxMint(_receiver: address) -> uint256:
    vaultRegistry: address = vaultWallet._getVaultRegistry()

    # deposit config
    canDeposit: bool = False
    maxDepositAmount: uint256 = 0
    na1: bool = False
    na2: address = empty(address)
    canDeposit, maxDepositAmount, na1, na2 = staticcall VaultRegistry(vaultRegistry).getDepositConfig(self)

    if not canDeposit:
        return 0

    if maxDepositAmount == 0:
        return max_value(uint256)

    totalAssets: uint256 = self._getTotalAssets(True, vaultRegistry)
    if totalAssets >= maxDepositAmount:
        return 0

    maxDepositAmt: uint256 = maxDepositAmount - totalAssets
    return self._amountToShares(maxDepositAmt, token.totalSupply, totalAssets, False)


@view
@external
def previewMint(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares, token.totalSupply, self._getTotalAssets(True), True)


@nonreentrant
@external
def mint(_shares: uint256, _receiver: address = msg.sender) -> uint256:
    vaultRegistry: address = vaultWallet._getVaultRegistry()

    # underlying data
    totalAssets: uint256 = 0
    currentBalance: uint256 = 0
    pendingYieldRealized: uint256 = 0
    maxBalVaultToken: address = empty(address)
    totalAssets, currentBalance, pendingYieldRealized, maxBalVaultToken = self._getUnderlyingData(True, vaultRegistry)

    amount: uint256 = self._sharesToAmount(_shares, token.totalSupply, totalAssets, True)
    self._deposit(vaultWallet.VAULT_ASSET, amount, _shares, _receiver, totalAssets, currentBalance, pendingYieldRealized, maxBalVaultToken, vaultRegistry)
    return amount


# shared deposit logic


@internal
def _deposit(
    _asset: address,
    _amount: uint256,
    _shares: uint256,
    _recipient: address,
    _totalAssets: uint256,
    _currentBalance: uint256,
    _pendingYieldRealized: uint256,
    _maxBalVaultToken: address,
    _vaultRegistry: address,
):
    # get all deposit config
    canDeposit: bool = False
    maxDepositAmount: uint256 = 0
    shouldAutoDeposit: bool = False
    defaultTargetVaultToken: address = empty(address)
    canDeposit, maxDepositAmount, shouldAutoDeposit, defaultTargetVaultToken = staticcall VaultRegistry(_vaultRegistry).getDepositConfig(self)

    assert canDeposit # dev: cannot deposit
    assert _amount != 0 # dev: cannot deposit 0 amount
    assert _shares != 0 # dev: cannot receive 0 shares
    assert _recipient != empty(address) # dev: invalid recipient
    if maxDepositAmount != 0:
        assert _totalAssets + _amount <= maxDepositAmount # dev: exceeds max deposit

    # transfer assets to vault
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, _amount, default_return_value=True) # dev: deposit failed

    # put the deposit to work -- start earning
    amountDeposited: uint256 = 0
    if shouldAutoDeposit:
        targetVaultToken: address = defaultTargetVaultToken
        if targetVaultToken == empty(address):
            targetVaultToken = _maxBalVaultToken
        amountDeposited = vaultWallet._onReceiveVaultFunds(targetVaultToken, _recipient, _vaultRegistry)

    # save data
    currentBalance: uint256 = _currentBalance + amountDeposited
    vaultWallet.lastUnderlyingBal = currentBalance
    vaultWallet.pendingYieldRealized = _pendingYieldRealized

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
    availableAssets: uint256 = self._getTotalAssets(False)
    ownerAssets: uint256 = self._sharesToAmount(ownerShares, token.totalSupply, availableAssets, False)
    return min(ownerAssets, availableAssets)


@view
@external
def previewWithdraw(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, self._getTotalAssets(True), True)


@nonreentrant
@external
def withdraw(_assets: uint256, _receiver: address = msg.sender, _owner: address = msg.sender) -> uint256:
    vaultRegistry: address = vaultWallet._getVaultRegistry()

    # underlying data
    totalAssets: uint256 = 0
    currentBalance: uint256 = 0
    pendingYieldRealized: uint256 = 0
    maxBalVaultToken: address = empty(address)
    totalAssets, currentBalance, pendingYieldRealized, maxBalVaultToken = self._getUnderlyingData(True, vaultRegistry)

    shares: uint256 = self._amountToShares(_assets, token.totalSupply, totalAssets, True)
    self._redeem(vaultWallet.VAULT_ASSET, _assets, shares, msg.sender, _receiver, _owner, currentBalance, pendingYieldRealized, maxBalVaultToken, vaultRegistry)
    return shares


# redeem


@view
@external
def maxRedeem(_owner: address) -> uint256:
    return token.balanceOf[_owner]


@view
@external
def previewRedeem(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares, token.totalSupply, self._getTotalAssets(False), False)


@nonreentrant
@external
def redeem(_shares: uint256, _receiver: address = msg.sender, _owner: address = msg.sender) -> uint256:
    vaultRegistry: address = vaultWallet._getVaultRegistry()

    shares: uint256 = _shares
    if shares == max_value(uint256):
        shares = token.balanceOf[_owner]

    # underlying data
    totalAssets: uint256 = 0
    currentBalance: uint256 = 0
    pendingYieldRealized: uint256 = 0
    maxBalVaultToken: address = empty(address)
    totalAssets, currentBalance, pendingYieldRealized, maxBalVaultToken = self._getUnderlyingData(False, vaultRegistry)

    amount: uint256 = self._sharesToAmount(shares, token.totalSupply, totalAssets, False)
    return self._redeem(vaultWallet.VAULT_ASSET, amount, shares, msg.sender, _receiver, _owner, currentBalance, pendingYieldRealized, maxBalVaultToken, vaultRegistry)


# shared redeem logic


@internal
def _redeem(
    _asset: address,
    _amount: uint256,
    _shares: uint256,
    _sender: address,
    _recipient: address,
    _owner: address,
    _currentBalance: uint256,
    _pendingYieldRealized: uint256,
    _maxBalVaultToken: address,
    _vaultRegistry: address,
) -> uint256:
    assert staticcall VaultRegistry(_vaultRegistry).canWithdraw(self) # dev: cannot withdraw

    assert _amount != 0 # dev: cannot withdraw 0 amount
    assert _shares != 0 # dev: cannot redeem 0 shares
    assert _recipient != empty(address) # dev: invalid recipient

    assert token.balanceOf[_owner] >= _shares # dev: insufficient shares

    if _sender != _owner:
        token._spendAllowance(_owner, _sender, _shares)

    # withdraw from yield opportunity
    availAmount: uint256 = 0
    withdrawnAmount: uint256 = 0
    availAmount, withdrawnAmount = vaultWallet._prepareRedemption(_asset, _amount, _maxBalVaultToken, _sender, _vaultRegistry)
    actualAmount: uint256 = min(availAmount, _amount)
    assert actualAmount >= _amount - (_amount // 10) # dev: insufficient funds (0.1% tolerance)

    # save data
    currentBalance: uint256 = _currentBalance - min(_currentBalance, withdrawnAmount)
    vaultWallet.lastUnderlyingBal = currentBalance
    vaultWallet.pendingYieldRealized = _pendingYieldRealized

    # burn shares, transfer assets
    token._burn(_owner, _shares)
    assert extcall IERC20(_asset).transfer(_recipient, actualAmount, default_return_value=True) # dev: withdrawal failed

    log Withdraw(sender=_sender, receiver=_recipient, owner=_owner, assets=actualAmount, shares=_shares)
    return actualAmount


##########
# Shares #
##########


@view
@external
def convertToShares(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, self._getTotalAssets(True), False)


@view
@external
def convertToSharesSafe(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, self._getTotalAssets(False), False)


@view
@external
def convertToAssets(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares, token.totalSupply, self._getTotalAssets(True), False)


@view
@external
def convertToAssetsSafe(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares, token.totalSupply, self._getTotalAssets(False), False)


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
