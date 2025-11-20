#             _                   _                 _               _                 _
#            / /\                /\ \              /\ \            /\ \     _        /\ \
#           / /  \              /  \ \            /  \ \          /  \ \   /\_\      \_\ \
#          / / /\ \            / /\ \_\          / /\ \ \        / /\ \ \_/ / /      /\__ \
#         / / /\ \ \          / / /\/_/         / / /\ \_\      / / /\ \___/ /      / /_ \ \
#        / / /  \ \ \        / / / ______      / /_/_ \/_/     / / /  \/____/      / / /\ \ \
#       / / /___/ /\ \      / / / /\_____\    / /____/\       / / /    / / /      / / /  \/_/
#      / / /_____/ /\ \    / / /  \/____ /   / /\____\/      / / /    / / /      / / /
#     / /_________/\ \ \  / / /_____/ / /   / / /______     / / /    / / /      / / /
#    / / /_       __\ \_\/ / /______\/ /   / / /_______\   / / /    / / /      /_/ /
#    \_\___\     /____/_/\/___________/    \/__________/   \/_/     \/_/       \_\/
#
#     ╔══════════════════════════════════════════════════════════════╗
#     ║  ** Agent Wrapper **                                         ║
#     ║  Thin wrapper for User Wallet with sender access control.    ║
#     ╚══════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: AgentWrapper

from interfaces import Wallet
from interfaces import AgentWrapper

interface Switchboard:
    def isSwitchboardAddr(_addr: address) -> bool: view

interface UndyHq:
    def getAddr(_regId: uint256) -> address: view

groupId: public(uint256)

# senders management
senders: public(HashMap[uint256, address]) # index -> sender
indexOfSender: public(HashMap[address, uint256]) # sender -> index
numSenders: public(uint256) # num senders

UNDY_HQ: immutable(address)

MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25
SWITCHBOARD_ID: constant(uint256) = 4


@deploy
def __init__(_undyHq: address, _groupId: uint256):
    assert _undyHq != empty(address) # dev: invalid undy hq
    UNDY_HQ = _undyHq

    # group id
    self.groupId = _groupId

    # not using 0 index
    self.numSenders = 1


##################
# Transfer Funds #
##################


@external
def transferFunds(
    _userWallet: address,
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _isCheque: bool = False,
) -> (uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).transferFunds(_recipient, _asset, _amount, _isCheque, False)


#########
# Yield #
#########


@external
def depositForYield(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).depositForYield(_legoId, _asset, _vaultAddr, _amount, _extraData)


@external
def withdrawFromYield(
    _userWallet: address,
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).withdrawFromYield(_legoId, _vaultToken, _amount, _extraData, False)


@external
def rebalanceYieldPosition(
    _userWallet: address,
    _fromLegoId: uint256,
    _fromVaultToken: address,
    _toLegoId: uint256,
    _toVaultAddr: address = empty(address),
    _fromVaultAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).rebalanceYieldPosition(_fromLegoId, _fromVaultToken, _toLegoId, _toVaultAddr, _fromVaultAmount, _extraData)


###################
# Swap / Exchange #
###################


@external
def swapTokens(
    _userWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
) -> (address, uint256, address, uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).swapTokens(_swapInstructions)


@external
def mintOrRedeemAsset(
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256 = max_value(uint256),
    _minAmountOut: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, bool, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).mintOrRedeemAsset(_legoId, _tokenIn, _tokenOut, _amountIn, _minAmountOut, _extraData)


@external
def confirmMintOrRedeemAsset(
    _userWallet: address,
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).confirmMintOrRedeemAsset(_legoId, _tokenIn, _tokenOut, _extraData)


###################
# Debt Management #
###################


@external
def addCollateral(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).addCollateral(_legoId, _asset, _amount, _extraData)


@external
def removeCollateral(
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).removeCollateral(_legoId, _asset, _amount, _extraData)


@external
def borrow(
    _userWallet: address,
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).borrow(_legoId, _borrowAsset, _amount, _extraData)


@external
def repayDebt(
    _userWallet: address,
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).repayDebt(_legoId, _paymentAsset, _paymentAmount, _extraData)


#################
# Claim Rewards #
#################


@external
def claimIncentives(
    _userWallet: address,
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _proofs: DynArray[bytes32, MAX_PROOFS] = [],
) -> (uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).claimIncentives(_legoId, _rewardToken, _rewardAmount, _proofs)


###############
# Wrapped ETH #
###############


@external
def convertWethToEth(_userWallet: address, _amount: uint256 = max_value(uint256)) -> (uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).convertWethToEth(_amount)


@external
def convertEthToWeth(_userWallet: address, _amount: uint256 = max_value(uint256)) -> (uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).convertEthToWeth(_amount)


#############
# Liquidity #
#############


@external
def addLiquidity(
    _userWallet: address,
    _legoId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _amountA: uint256 = max_value(uint256),
    _amountB: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _minLpAmount: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).addLiquidity(_legoId, _pool, _tokenA, _tokenB, _amountA, _amountB, _minAmountA, _minAmountB, _minLpAmount, _extraData)


@external
def removeLiquidity(
    _userWallet: address,
    _legoId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpToken: address,
    _lpAmount: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).removeLiquidity(_legoId, _pool, _tokenA, _tokenB, _lpToken, _lpAmount, _minAmountA, _minAmountB, _extraData)


@external
def addLiquidityConcentrated(
    _userWallet: address,
    _legoId: uint256,
    _nftAddr: address,
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _amountA: uint256 = max_value(uint256),
    _amountB: uint256 = max_value(uint256),
    _tickLower: int24 = min_value(int24),
    _tickUpper: int24 = max_value(int24),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).addLiquidityConcentrated(_legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _amountA, _amountB, _tickLower, _tickUpper, _minAmountA, _minAmountB, _extraData)


@external
def removeLiquidityConcentrated(
    _userWallet: address,
    _legoId: uint256,
    _nftAddr: address,
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _liqToRemove: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
    assert self.indexOfSender[msg.sender] != 0 # dev: not approved sender
    return extcall Wallet(_userWallet).removeLiquidityConcentrated(_legoId, _nftAddr, _nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraData)


#####################
# Sender Management #
#####################


@view
@external
def isSender(_address: address) -> bool:
    return self.indexOfSender[_address] != 0


@external
def addSender(_sender: address):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms
    self._registerSender(_sender)


@external
def removeSender(_sender: address):
    assert self._isSwitchboardAddr(msg.sender) # dev: no perms

    numSenders: uint256 = self.numSenders
    if numSenders == 1:
        return

    targetIndex: uint256 = self.indexOfSender[_sender]
    if targetIndex == 0:
        return

    # update data
    lastIndex: uint256 = numSenders - 1
    self.numSenders = lastIndex
    self.indexOfSender[_sender] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.senders[lastIndex]
        self.senders[targetIndex] = lastItem
        self.indexOfSender[lastItem] = targetIndex


@internal
def _registerSender(_sender: address):
    if self.indexOfSender[_sender] != 0:
        return
    sid: uint256 = self.numSenders
    self.senders[sid] = _sender
    self.indexOfSender[_sender] = sid
    self.numSenders = sid + 1


# permissions


@view
@internal
def _isSwitchboardAddr(_addr: address) -> bool:
    switchboard: address = staticcall UndyHq(UNDY_HQ).getAddr(SWITCHBOARD_ID)
    if switchboard == empty(address):
        return False
    return staticcall Switchboard(switchboard).isSwitchboardAddr(_addr)