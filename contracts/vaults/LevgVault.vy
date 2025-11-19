#            _             _     _          _       _            _           _                   _              _      
#           _\ \          /\ \  /\ \    _ / /\     /\ \         /\ \        / /\                /\ \           /\ \    
#          /\__ \        /  \ \ \ \ \  /_/ / /    /  \ \       /  \ \      / /  \              /  \ \         /  \ \   
#         / /_ \_\      / /\ \ \ \ \ \ \___\/    / /\ \ \     / /\ \ \    / / /\ \            / /\ \_\       / /\ \ \  
#        / / /\/_/     / / /\ \_\/ / /  \ \ \   / / /\ \_\   / / /\ \_\  / / /\ \ \          / / /\/_/      / / /\ \_\ 
#       / / /         / /_/_ \/_/\ \ \   \_\ \ / /_/_ \/_/  / / /_/ / / / / /  \ \ \        / / / ______   / /_/_ \/_/ 
#      / / /         / /____/\    \ \ \  / / // /____/\    / / /__\/ / / / /___/ /\ \      / / / /\_____\ / /____/\    
#     / / / ____    / /\____\/     \ \ \/ / // /\____\/   / / /_____/ / / /_____/ /\ \    / / /  \/____ // /\____\/    
#    / /_/_/ ___/\ / / /______      \ \ \/ // / /______  / / /\ \ \  / /_________/\ \ \  / / /_____/ / // / /______    
#   /_______/\__\// / /_______\      \ \  // / /_______\/ / /  \ \ \/ / /_       __\ \_\/ / /______\/ // / /_______\   
#   \_______\/    \/__________/       \_\/ \/__________/\/_/    \_\/\_\___\     /____/_/\/___________/ \/__________/   
#                                                                                                                   
#     ╔══════════════════════════════════════════════════════════════════════╗
#     ║  ** Leveraged Vaults **                                              ║
#     ║  Managed by AI agents, enforced by onchain rules. Erc4626 compliant. ║
#     ╚══════════════════════════════════════════════════════════════════════╝
#
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
from contracts.vaults.modules import LevgVaultWallet as vaultWallet

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

event LeftoversSwept:
    amount: uint256
    recipient: indexed(address)


@deploy
def __init__(
    _asset: address,
    _tokenName: String[64],
    _tokenSymbol: String[32],
    _undyHq: address,
    _collateralVaultToken: address,
    _collateralVaultTokenLegoId: uint256,
    _collateralVaultTokenRipeVaultId: uint256,
    _leverageVaultToken: address,
    _leverageVaultTokenLegoId: uint256,
    _leverageVaultTokenRipeVaultId: uint256,
    _usdc: address,
    _green: address,
    _savingsGreen: address,
    _minHqTimeLock: uint256,
    _maxHqTimeLock: uint256,
    _startingAgent: address,
    _levgVaultHelper: address,
):
    token.__init__(_tokenName, _tokenSymbol, staticcall IERC20Detailed(_asset).decimals(), _undyHq)
    vaultWallet.__init__(_undyHq, _asset, _collateralVaultToken, _collateralVaultTokenLegoId, _collateralVaultTokenRipeVaultId, _leverageVaultToken, _leverageVaultTokenLegoId, _leverageVaultTokenRipeVaultId, _usdc, _green, _savingsGreen, _startingAgent, _levgVaultHelper)


@view
@external
def asset() -> address:
    return vaultWallet.UNDERLYING_ASSET


@view
@external
def totalAssets() -> uint256:
    return vaultWallet._getTotalAssets(True)


@view
@external
def getTotalAssets(_shouldGetMax: bool) -> uint256:
    return vaultWallet._getTotalAssets(_shouldGetMax)


@view
@external
def isLeveragedVault() -> bool:
    return True


############
# Deposits #
############


@view
@external
def maxDeposit(_receiver: address) -> uint256:
    canDeposit: bool = False
    maxDepositAmount: uint256 = 0
    na1: bool = False
    na2: address = empty(address)
    canDeposit, maxDepositAmount, na1, na2 = staticcall VaultRegistry(vaultWallet._getVaultRegistry()).getDepositConfig(self)

    if not canDeposit:
        return 0

    if maxDepositAmount == 0:
        return max_value(uint256)

    totalAssets: uint256 = vaultWallet._getTotalAssets(True)
    if totalAssets >= maxDepositAmount:
        return 0

    return maxDepositAmount - totalAssets


@view
@external
def previewDeposit(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, vaultWallet._getTotalAssets(True), False)


@nonreentrant
@external
def deposit(_assets: uint256, _receiver: address = msg.sender) -> uint256:
    return self._deposit(_assets, msg.sender, _receiver, 0)


@nonreentrant
@external
def depositWithMinAmountOut(_assets: uint256, _minAmountOut: uint256, _receiver: address = msg.sender) -> uint256:
    return self._deposit(_assets, msg.sender, _receiver, _minAmountOut)


@internal
def _deposit(_assets: uint256, _sender: address, _receiver: address, _minAmountOut: uint256) -> uint256:
    asset: address = vaultWallet.UNDERLYING_ASSET

    amount: uint256 = _assets
    if amount == max_value(uint256):
        amount = staticcall IERC20(asset).balanceOf(_sender)

    totalAssets: uint256 = vaultWallet._getTotalAssets(True)
    shares: uint256 = self._amountToShares(amount, token.totalSupply, totalAssets, False)
    self._depositIntoVault(asset, amount, shares, _sender, _receiver, totalAssets, vaultWallet._getVaultRegistry(), _minAmountOut)
    return shares


# mint


@view
@external
def maxMint(_receiver: address) -> uint256:
    canDeposit: bool = False
    maxDepositAmount: uint256 = 0
    na1: bool = False
    na2: address = empty(address)
    canDeposit, maxDepositAmount, na1, na2 = staticcall VaultRegistry(vaultWallet._getVaultRegistry()).getDepositConfig(self)

    if not canDeposit:
        return 0

    if maxDepositAmount == 0:
        return max_value(uint256)

    totalAssets: uint256 = vaultWallet._getTotalAssets(True)
    if totalAssets >= maxDepositAmount:
        return 0

    maxDepositAmt: uint256 = maxDepositAmount - totalAssets
    return self._amountToShares(maxDepositAmt, token.totalSupply, totalAssets, False)


@view
@external
def previewMint(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares, token.totalSupply, vaultWallet._getTotalAssets(True), True)


@nonreentrant
@external
def mint(_shares: uint256, _receiver: address = msg.sender) -> uint256:
    totalAssets: uint256 = vaultWallet._getTotalAssets(True)
    amount: uint256 = self._sharesToAmount(_shares, token.totalSupply, totalAssets, True)
    self._depositIntoVault(vaultWallet.UNDERLYING_ASSET, amount, _shares, msg.sender, _receiver, totalAssets, vaultWallet._getVaultRegistry(), 0)
    return amount


# shared deposit logic


@internal
def _depositIntoVault(
    _asset: address,
    _amount: uint256,
    _shares: uint256,
    _sender: address,
    _recipient: address,
    _totalAssets: uint256,
    _vaultRegistry: address,
    _minAmountOut: uint256,
):
    # get all deposit config
    canDeposit: bool = False
    maxDepositAmount: uint256 = 0
    shouldAutoDeposit: bool = False
    na: address = empty(address)
    canDeposit, maxDepositAmount, shouldAutoDeposit, na = staticcall VaultRegistry(_vaultRegistry).getDepositConfig(self)

    if not canDeposit:
        assert _sender == vaultWallet._getGovernanceAddr() # dev: cannot deposit

    assert _amount != 0 # dev: cannot deposit 0 amount
    assert _shares != 0 # dev: cannot receive 0 shares
    assert _recipient != empty(address) # dev: invalid recipient

    if maxDepositAmount != 0:
        assert _totalAssets + _amount <= maxDepositAmount # dev: exceeds max deposit

    if _minAmountOut != 0:
        assert _shares >= _minAmountOut # dev: insufficient shares

    # transfer assets to vault
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, _amount, default_return_value=True) # dev: deposit failed

    # put the deposit to work -- start earning
    if shouldAutoDeposit:
        vaultWallet._onReceiveVaultFunds(_recipient, _vaultRegistry)

    token._mint(_recipient, _shares)

    # track user capital for maxDebtRatio enforcement
    vaultWallet.netUserCapital += _amount

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
    return self._amountToShares(_assets, token.totalSupply, vaultWallet._getTotalAssets(False), True)


@nonreentrant
@external
def withdraw(_assets: uint256, _receiver: address = msg.sender, _owner: address = msg.sender) -> uint256:
    shares: uint256 = self._amountToShares(_assets, token.totalSupply, vaultWallet._getTotalAssets(False), True)
    self._redeemFromVault(vaultWallet.UNDERLYING_ASSET, _assets, shares, msg.sender, _receiver, _owner, vaultWallet._getVaultRegistry(), 0)
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
    return self._redeem(_shares, msg.sender, _receiver, _owner, 0)


@nonreentrant
@external
def redeemWithMinAmountOut(_shares: uint256, _minAmountOut: uint256, _receiver: address = msg.sender, _owner: address = msg.sender) -> uint256:
    return self._redeem(_shares, msg.sender, _receiver, _owner, _minAmountOut)


@internal
def _redeem(_shares: uint256, _sender: address, _receiver: address, _owner: address, _minAmountOut: uint256) -> uint256:
    shares: uint256 = _shares
    if shares == max_value(uint256):
        shares = token.balanceOf[_owner]
    
    amount: uint256 = self._sharesToAmount(shares, token.totalSupply, vaultWallet._getTotalAssets(False), False)
    return self._redeemFromVault(vaultWallet.UNDERLYING_ASSET, amount, shares, _sender, _receiver, _owner, vaultWallet._getVaultRegistry(), _minAmountOut)


# shared redeem logic


@internal
def _redeemFromVault(
    _asset: address,
    _amount: uint256,
    _shares: uint256,
    _sender: address,
    _recipient: address,
    _owner: address,
    _vaultRegistry: address,
    _minAmountOut: uint256,
) -> uint256:
    if not staticcall VaultRegistry(_vaultRegistry).canWithdraw(self):
        assert _sender == vaultWallet._getGovernanceAddr() # dev: cannot withdraw

    assert _amount != 0 # dev: cannot withdraw 0 amount
    assert _shares != 0 # dev: cannot redeem 0 shares
    assert _recipient != empty(address) # dev: invalid recipient

    assert token.balanceOf[_owner] >= _shares # dev: insufficient shares

    if _sender != _owner:
        token._spendAllowance(_owner, _sender, _shares)

    # withdraw from yield opportunity
    availAmount: uint256 = vaultWallet._prepareRedemption(_asset, _amount, _sender, _vaultRegistry)
    actualAmount: uint256 = min(availAmount, _amount)

    # check amount out
    if _minAmountOut != 0:
        assert actualAmount >= _minAmountOut # dev: insufficient amount out
    else:
        assert self._isRedemptionCloseEnough(_amount, actualAmount) # dev: insufficient funds

    # burn shares
    token._burn(_owner, _shares)

    # track user capital for maxDebtRatio enforcement
    netUserCapital: uint256 = vaultWallet.netUserCapital
    vaultWallet.netUserCapital = netUserCapital - min(netUserCapital, actualAmount)

    # transfer assets to recipient
    assert extcall IERC20(_asset).transfer(_recipient, actualAmount, default_return_value=True) # dev: withdrawal failed

    log Withdraw(sender=_sender, receiver=_recipient, owner=_owner, assets=actualAmount, shares=_shares)
    return actualAmount


@view
@internal
def _isRedemptionCloseEnough(_requestedAmount: uint256, _actualAmount: uint256) -> bool:
    # extra check to make sure what was sent was actually close-ish to what was requested
    buffer: uint256 = _requestedAmount * 10 // 100_00  # 0.1%
    lowerBound: uint256 = _requestedAmount - buffer
    return _actualAmount >= lowerBound


##########
# Shares #
##########


@view
@external
def convertToShares(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, vaultWallet._getTotalAssets(True), False)


@view
@external
def convertToSharesSafe(_assets: uint256) -> uint256:
    return self._amountToShares(_assets, token.totalSupply, vaultWallet._getTotalAssets(False), False)


@view
@external
def convertToAssets(_shares: uint256) -> uint256:
    return self._sharesToAmount(_shares, token.totalSupply, vaultWallet._getTotalAssets(True), False)


@view
@external
def convertToAssetsSafe(_shares: uint256) -> uint256:
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


###################
# Sweep Leftovers #
###################


@external
def sweepLeftovers() -> uint256:
    governance: address = vaultWallet._getGovernanceAddr()
    assert vaultWallet._isSwitchboardAddr(msg.sender) or governance == msg.sender # dev: no perms
    assert token.totalSupply == 0 # dev: shares outstanding

    vaultAsset: address = vaultWallet.UNDERLYING_ASSET
    balance: uint256 = staticcall IERC20(vaultAsset).balanceOf(self)
    assert balance != 0 # dev: no balance

    assert extcall IERC20(vaultAsset).transfer(governance, balance, default_return_value=True) # dev: transfer failed
    log LeftoversSwept(amount=balance, recipient=governance)
    return balance