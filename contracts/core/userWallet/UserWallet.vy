# @version 0.4.3
# pragma optimize codesize

implements: wi
from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego

from ethereum.ercs import IERC20Detailed
from ethereum.ercs import IERC20
from ethereum.ercs import IERC721

interface WalletConfig:
    def canPerformAction(_signer: address, _action: wi.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _transferRecipient: address = empty(address)) -> bool: view
    def canTransferToRecipient(_recipient: address) -> bool: view
    def owner() -> address: view

interface WethContract:
    def withdraw(_amount: uint256): nonpayable
    def deposit(): payable

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct ActionData:
    undyHq: address
    legoRegistry: address
    feeRecipient: address
    wallet: address
    walletConfig: address
    walletOwner: address
    trialFundsAsset: address
    trialFundsAmount: uint256
    signer: address
    isManager: bool
    legoId: uint256
    legoAddr: address

struct AssetData:
    assetBalance: uint256
    usdValue: uint256
    lastPrice: uint256
    lastPriceUpdate: uint256
    config: AssetConfig

struct AssetConfig:
    hasConfig: bool
    isYieldAsset: bool
    isRebasing: bool
    maxIncrease: uint256
    performanceFee: uint256
    decimals: uint256

struct WalletTotals:
    usdValue: uint256
    depositPoints: uint256
    lastUpdate: uint256

event YieldDeposit:
    asset: indexed(address)
    assetAmount: uint256
    vaultToken: indexed(address)
    vaultTokenAmount: uint256
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event YieldWithdrawal:
    vaultToken: indexed(address)
    vaultTokenAmountBurned: uint256
    underlyingAsset: indexed(address)
    underlyingAmountReceived: uint256
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event OverallSwapPerformed:
    tokenIn: indexed(address)
    tokenInAmount: uint256
    tokenOut: indexed(address)
    tokenOutAmount: uint256
    numLegos: uint256
    numInstructions: uint256
    signer: indexed(address)
    isManager: bool

event SpecificSwapInstructionPerformed:
    tokenIn: indexed(address)
    tokenInAmount: uint256
    tokenOut: indexed(address)
    tokenOutAmount: uint256
    numTokens: uint256
    numPools: uint256
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event AssetMintedOrRedeemed:
    tokenIn: indexed(address)
    tokenInAmount: uint256
    tokenOut: indexed(address)
    tokenOutAmount: uint256
    isPending: bool
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event AssetMintedOrRedeemedConfirmed:
    tokenIn: indexed(address)
    tokenOut: indexed(address)
    tokenOutAmount: uint256
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event CollateralAdded:
    asset: indexed(address)
    amountDeposited: uint256
    extraAddr: indexed(address)
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event CollateralRemoved:
    asset: indexed(address)
    amountRemoved: uint256
    extraAddr: indexed(address)
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event NewBorrow:
    borrowAsset: indexed(address)
    borrowAmount: uint256
    extraAddr: indexed(address)
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event DebtRepayment:
    paymentAsset: indexed(address)
    repaidAmount: uint256
    extraAddr: indexed(address)
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event LiquidityAdded:
    pool: indexed(address)
    tokenA: indexed(address)
    amountA: uint256
    tokenB: indexed(address)
    amountB: uint256
    lpToken: address
    lpAmountReceived: uint256
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: address
    isManager: bool

event ConcentratedLiquidityAdded:
    nftTokenId: uint256
    pool: indexed(address)
    tokenA: indexed(address)
    amountA: uint256
    tokenB: indexed(address)
    amountB: uint256
    liqAdded: uint256
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: address
    isManager: bool

event LiquidityRemoved:
    pool: indexed(address)
    tokenA: indexed(address)
    amountAReceived: uint256
    tokenB: indexed(address)
    amountBReceived: uint256
    lpToken: address
    lpAmountBurned: uint256
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: address
    isManager: bool

event ConcentratedLiquidityRemoved:
    nftTokenId: uint256
    pool: indexed(address)
    tokenA: indexed(address)
    amountAReceived: uint256
    tokenB: indexed(address)
    amountBReceived: uint256
    liqRemoved: uint256
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: address
    isManager: bool

event FundsTransferred:
    asset: indexed(address)
    amount: uint256
    recipient: indexed(address)
    signer: indexed(address)
    isManager: bool

event EthWrapped:
    amount: uint256
    paidEth: uint256
    weth: indexed(address)
    signer: indexed(address)
    isManager: bool

event WethUnwrapped:
    amount: uint256
    weth: indexed(address)
    signer: indexed(address)
    isManager: bool

event RewardsClaimed:
    rewardToken: indexed(address)
    rewardAmount: uint256
    extraAddr: indexed(address)
    extraVal: uint256
    extraData: bytes32
    legoId: uint256
    legoAddr: address
    signer: indexed(address)
    isManager: bool

event NftRecovered:
    collection: indexed(address)
    nftTokenId: uint256
    owner: indexed(address)

# data 
walletConfig: public(address)
totals: public(WalletTotals)

# asset data
assetData: public(HashMap[address, AssetData]) # asset -> data
assets: public(HashMap[uint256, address]) # index -> asset
indexOfAsset: public(HashMap[address, uint256]) # asset -> index
numAssets: public(uint256) # num assets

# trial funds info
trialFundsAsset: public(address)
trialFundsAmount: public(uint256)

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10

ERC721_RECEIVE_DATA: constant(Bytes[1024]) = b"UnderscoreErc721"
API_VERSION: constant(String[28]) = "0.1.0"
LEGO_BOOK_ID: constant(uint256) = 4

UNDY_HQ: public(immutable(address))
WETH: public(immutable(address))


@deploy
def __init__(
    _undyHq: address,
    _wethAddr: address,
    _walletConfig: address,
    _trialFundsAsset: address,
    _trialFundsAmount: uint256,
):
    assert empty(address) not in [_undyHq, _wethAddr, _walletConfig] # dev: invalid addrs
    self.walletConfig = _walletConfig

    UNDY_HQ = _undyHq
    WETH = _wethAddr

    # trial funds info
    if _trialFundsAsset != empty(address) and _trialFundsAmount != 0:   
        self.trialFundsAsset = _trialFundsAsset
        self.trialFundsAmount = _trialFundsAmount


@payable
@external
def __default__():
    pass


@view
@external
def onERC721Received(_operator: address, _owner: address, _tokenId: uint256, _data: Bytes[1024]) -> bytes4:
    # must implement method for safe NFT transfers
    return method_id("onERC721Received(address,address,uint256,bytes)", output_type=bytes4)


@pure
@external
def apiVersion() -> String[28]:
    return API_VERSION


##################
# Transfer Funds #
##################


@nonreentrant
@external
def transferFunds(
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
) -> uint256:
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.TRANSFER, False, [_asset], [], _recipient)
    return self._transferFunds(_recipient, _asset, _amount, cd)


@internal
def _transferFunds(
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _cd: ActionData,
) -> uint256:

    # validate recipient
    if _recipient != _cd.walletOwner:
        assert staticcall WalletConfig(_cd.walletConfig).canTransferToRecipient(_recipient) # dev: recipient not allowed

    # handle eth
    amount: uint256 = 0
    if _asset == empty(address):
        amount = min(_amount, self.balance)
        assert amount != 0 # dev: nothing to transfer
        send(_recipient, amount)

    # erc20 tokens
    else:
        amount = min(_amount, staticcall IERC20(_asset).balanceOf(self))
        assert amount != 0 # dev: no balance for _token
        assert extcall IERC20(_asset).transfer(_recipient, amount, default_return_value=True) # dev: transfer failed
        self._performPostActionTasks([_asset])

    log FundsTransferred(
        asset = _asset,
        amount = amount,
        recipient = _recipient,
        signer = _cd.signer,
        isManager = _cd.isManager,
    )
    return amount


#########
# Yield #
#########


# deposit


@nonreentrant
@external
def depositForYield(
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.EARN_DEPOSIT, False, [_asset], [_legoId])
    return self._depositForYield(_asset, _vaultAddr, _amount, _extraAddr, _extraVal, _extraData, True, cd)


@internal
def _depositForYield(
    _asset: address,
    _vaultAddr: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _shouldPerformPostActionTasks: bool,
    _cd: ActionData,
) -> (uint256, address, uint256):
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, _cd.legoAddr) # doing approval here

    # deposit for yield
    assetAmount: uint256 = 0
    vaultToken: address = empty(address)
    vaultTokenAmountReceived: uint256 = 0
    assetAmount, vaultToken, vaultTokenAmountReceived = extcall Lego(_cd.legoAddr).depositForYield(_asset, amount, _vaultAddr, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_asset).approve(_cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    if _shouldPerformPostActionTasks:
        self._performPostActionTasks([_asset, vaultToken])

    log YieldDeposit(
        asset = _asset,
        assetAmount = assetAmount,
        vaultToken = vaultToken,
        vaultTokenAmount = vaultTokenAmountReceived,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = _cd.legoId,
        legoAddr = _cd.legoAddr,
        signer = _cd.signer,
        isManager = _cd.isManager,
    )
    return assetAmount, vaultToken, vaultTokenAmountReceived


# withdraw


@nonreentrant
@external
def withdrawFromYield(
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.EARN_WITHDRAW, False, [_vaultToken], [_legoId])
    return self._withdrawFromYield(_vaultToken, _amount, _extraAddr, _extraVal, _extraData, True, cd)


@internal
def _withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _shouldPerformPostActionTasks: bool,
    _cd: ActionData,
) -> (uint256, address, uint256):

    amount: uint256 = _amount
    if _vaultToken != empty(address):
        amount = self._getAmountAndApprove(_vaultToken, _amount, empty(address)) # not approving here

        # some vault tokens require max value approval (comp v3)
        assert extcall IERC20(_vaultToken).approve(_cd.legoAddr, max_value(uint256), default_return_value=True) # dev: approval failed

    # withdraw from yield
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount = extcall Lego(_cd.legoAddr).withdrawFromYield(_vaultToken, amount, _extraAddr, _extraVal, _extraData, self)

    if _vaultToken != empty(address):
        assert extcall IERC20(_vaultToken).approve(_cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    if _shouldPerformPostActionTasks:
        self._performPostActionTasks([underlyingAsset, _vaultToken])

    log YieldWithdrawal(
        vaultToken = _vaultToken,
        vaultTokenAmountBurned = vaultTokenAmountBurned,
        underlyingAsset = underlyingAsset,
        underlyingAmountReceived = underlyingAmount,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = _cd.legoId,
        legoAddr = _cd.legoAddr,
        signer = _cd.signer,
        isManager = _cd.isManager,
    )
    return vaultTokenAmountBurned, underlyingAsset, underlyingAmount


# rebalance position


@nonreentrant
@external
def rebalanceYieldPosition(
    _fromLegoId: uint256,
    _fromVaultToken: address,
    _toLegoId: uint256,
    _toVaultAddr: address = empty(address),
    _fromVaultAmount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.EARN_REBALANCE, False, [_fromVaultToken, _toVaultAddr], [_fromLegoId, _toLegoId])

    # withdraw
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount = self._withdrawFromYield(_fromVaultToken, _fromVaultAmount, _extraAddr, _extraVal, _extraData, False, cd)

    # deposit
    toVaultToken: address = empty(address)
    toVaultTokenAmountReceived: uint256 = 0
    cd.legoId = _toLegoId
    cd.legoAddr = staticcall Registry(cd.legoRegistry).getAddr(_toLegoId)
    underlyingAmount, toVaultToken, toVaultTokenAmountReceived = self._depositForYield(underlyingAsset, _toVaultAddr, underlyingAmount, _extraAddr, _extraVal, _extraData, False, cd)

    self._performPostActionTasks([underlyingAsset, _fromVaultToken, toVaultToken])
    return underlyingAmount, toVaultToken, toVaultTokenAmountReceived


###################
# Swap / Exchange #
###################


@nonreentrant
@external
def swapTokens(_instructions: DynArray[wi.SwapInstruction, MAX_SWAP_INSTRUCTIONS]) -> (address, uint256, address, uint256):
    tokenIn: address = empty(address)
    tokenOut: address = empty(address)
    legoIds: DynArray[uint256, MAX_LEGOS] = []
    tokenIn, tokenOut, legoIds = self._validateAndGetSwapInfo(_instructions)

    # action data bundle
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.SWAP, False, [tokenIn, tokenOut], legoIds)
    origAmountIn: uint256 = self._getAmountAndApprove(tokenIn, _instructions[0].amountIn, empty(address)) # not approving here

    # perform swaps
    amountIn: uint256 = origAmountIn
    lastTokenOut: address = empty(address)
    lastTokenOutAmount: uint256 = 0
    for i: wi.SwapInstruction in _instructions:
        if lastTokenOut != empty(address):
            newTokenIn: address = i.tokenPath[0]
            assert lastTokenOut == newTokenIn # dev: must honor token path
            amountIn = min(lastTokenOutAmount, staticcall IERC20(newTokenIn).balanceOf(self))
        lastTokenOut, lastTokenOutAmount = self._performSwapInstruction(amountIn, i, cd)

    # TODO: handle tx fees
    # if cd.isManager:
    #     self._handleTransactionFees(wi.ActionType.REWARDS, _rewardToken, rewardAmount, cd)

    self._performPostActionTasks([tokenIn, tokenOut])
    log OverallSwapPerformed(
        tokenIn = tokenIn,
        tokenInAmount = origAmountIn,
        tokenOut = lastTokenOut,
        tokenOutAmount = lastTokenOutAmount,
        numLegos = len(legoIds),
        numInstructions = len(_instructions),
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount


@internal
def _performSwapInstruction(
    _amountIn: uint256,
    _i: wi.SwapInstruction,
    _cd: ActionData,
) -> (address, uint256):
    legoAddr: address = staticcall Registry(_cd.legoRegistry).getAddr(_i.legoId)
    assert legoAddr != empty(address) # dev: invalid lego

    # tokens
    tokenIn: address = _i.tokenPath[0]
    tokenOut: address = _i.tokenPath[len(_i.tokenPath) - 1]
    tokenInAmount: uint256 = 0
    tokenOutAmount: uint256 = 0

    assert extcall IERC20(tokenIn).approve(legoAddr, _amountIn, default_return_value=True) # dev: approval failed
    tokenInAmount, tokenOutAmount = extcall Lego(legoAddr).swapTokens(_amountIn, _i.minAmountOut, _i.tokenPath, _i.poolPath, self)
    assert extcall IERC20(tokenIn).approve(legoAddr, 0, default_return_value=True) # dev: approval failed

    log SpecificSwapInstructionPerformed(
        tokenIn = tokenIn,
        tokenInAmount = tokenInAmount,
        tokenOut = tokenOut,
        tokenOutAmount = tokenOutAmount,
        numTokens = len(_i.tokenPath),
        numPools = len(_i.poolPath),
        legoId = _i.legoId,
        legoAddr = legoAddr,
        signer = _cd.signer,
        isManager = _cd.isManager,
    )
    return tokenOut, tokenOutAmount


@internal
def _validateAndGetSwapInfo(_instructions: DynArray[wi.SwapInstruction, MAX_SWAP_INSTRUCTIONS]) -> (address, address, DynArray[uint256, MAX_LEGOS]):
    numSwapInstructions: uint256 = len(_instructions)
    assert numSwapInstructions != 0 # dev: no swaps

    # lego ids, make sure token paths are valid
    legoIds: DynArray[uint256, MAX_LEGOS] = []
    for i: wi.SwapInstruction in _instructions:
        assert len(i.tokenPath) >= 2 # dev: invalid token path
        if i.legoId not in legoIds:
            legoIds.append(i.legoId)

    # finalize tokens
    firstRoutePath: DynArray[address, MAX_TOKEN_PATH] = _instructions[0].tokenPath
    tokenIn: address = firstRoutePath[0]
    tokenOut: address = empty(address)

    if numSwapInstructions == 1:
        tokenOut = firstRoutePath[len(firstRoutePath) - 1]
    else:
        lastRoutePath: DynArray[address, MAX_TOKEN_PATH] = _instructions[numSwapInstructions - 1].tokenPath
        tokenOut = lastRoutePath[len(lastRoutePath) - 1]

    assert empty(address) not in [tokenIn, tokenOut] # dev: invalid token path
    return tokenIn, tokenOut, legoIds


# mint / redeem


@nonreentrant
@external
def mintOrRedeemAsset(
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _amountIn: uint256 = max_value(uint256),
    _minAmountOut: uint256 = 0,
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, bool):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.MINT_REDEEM, False, [_tokenIn, _tokenOut], [_legoId])

    # mint
    tokenInAmount: uint256 = self._getAmountAndApprove(_tokenIn, _amountIn, cd.legoAddr) # doing approval here
    tokenOutAmount: uint256 = 0
    isPending: bool = False
    tokenInAmount, tokenOutAmount, isPending = extcall Lego(cd.legoAddr).mintOrRedeemAsset(_tokenIn, _tokenOut, tokenInAmount, _minAmountOut, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_tokenIn).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_tokenIn, _tokenOut])
    log AssetMintedOrRedeemed(
        tokenIn = _tokenIn,
        tokenInAmount = tokenInAmount,
        tokenOut = _tokenOut,
        tokenOutAmount = tokenOutAmount,
        isPending = isPending,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return tokenInAmount, tokenOutAmount, isPending


@nonreentrant
@external
def confirmMintOrRedeemAsset(
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> uint256:
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.CONFIRM_MINT_REDEEM, False, [_tokenIn, _tokenOut], [_legoId])

    # confirm (if there is a delay on action)
    tokenOutAmount: uint256 = extcall Lego(cd.legoAddr).confirmMintOrRedeemAsset(_tokenIn, _tokenOut, _extraAddr, _extraVal, _extraData, self)

    self._performPostActionTasks([_tokenIn, _tokenOut])
    log AssetMintedOrRedeemedConfirmed(
        tokenIn = _tokenIn,
        tokenOut = _tokenOut,
        tokenOutAmount = tokenOutAmount,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return tokenOutAmount


###################
# Debt Management #
###################


# NOTE: these functions assume there is no vault token involved (i.e. Ripe Protocol)
# You can also use `depositIntoProtocol` and `withdrawFromProtocol` if a vault token is involved


# add collateral


@nonreentrant
@external
def addCollateral(
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> uint256:
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ADD_COLLATERAL, True, [_asset], [_legoId])

    # add collateral
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, cd.legoAddr) # doing approval here
    amountDeposited: uint256 = extcall Lego(cd.legoAddr).addCollateral(_asset, amount, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_asset).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_asset])
    log CollateralAdded(
        asset = _asset,
        amountDeposited = amountDeposited,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return amountDeposited


# remove collateral


@nonreentrant
@external
def removeCollateral(
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> uint256:
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REMOVE_COLLATERAL, True, [_asset], [_legoId])
    amountRemoved: uint256 = extcall Lego(cd.legoAddr).removeCollateral(_asset, _amount, _extraAddr, _extraVal, _extraData, self)

    self._performPostActionTasks([_asset])
    log CollateralRemoved(
        asset = _asset,
        amountRemoved = amountRemoved,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return amountRemoved


# borrow


@nonreentrant
@external
def borrow(
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> uint256:
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.BORROW, True, [_borrowAsset], [_legoId])

    # borrow
    borrowAmount: uint256 = extcall Lego(cd.legoAddr).borrow(_borrowAsset, _amount, _extraAddr, _extraVal, _extraData, self)

    self._performPostActionTasks([_borrowAsset])
    log NewBorrow(
        borrowAsset = _borrowAsset,
        borrowAmount = borrowAmount,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return borrowAmount


# repay debt


@nonreentrant
@external
def repayDebt(
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> uint256:
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REPAY_DEBT, True, [_paymentAsset], [_legoId])

    amount: uint256 = self._getAmountAndApprove(_paymentAsset, _paymentAmount, cd.legoAddr) # doing approval here
    repaidAmount: uint256 = extcall Lego(cd.legoAddr).repayDebt(_paymentAsset, amount, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_paymentAsset).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_paymentAsset])
    log DebtRepayment(
        paymentAsset = _paymentAsset,
        repaidAmount = repaidAmount,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return repaidAmount


#################
# Claim Rewards #
#################


@nonreentrant
@external
def claimRewards(
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> uint256:
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REWARDS, True, [_rewardToken], [_legoId])
    rewardAmount: uint256 = extcall Lego(cd.legoAddr).claimRewards(self, _rewardToken, _rewardAmount, _extraAddr, _extraVal, _extraData)

    # TODO: handle tx fees
    # if cd.isManager:
    #     self._handleTransactionFees(wi.ActionType.REWARDS, _rewardToken, rewardAmount, cd)

    self._performPostActionTasks([_rewardToken])
    log RewardsClaimed(
        rewardToken = _rewardToken,
        rewardAmount = rewardAmount,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return rewardAmount


################
# Wrapped ETH #
################


# eth -> weth


@nonreentrant
@payable
@external
def convertEthToWeth(_amount: uint256 = max_value(uint256)) -> uint256:
    weth: address = WETH
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ETH_TO_WETH, False, [weth])

    # convert eth to weth
    amount: uint256 = min(_amount, self.balance)
    assert amount != 0 # dev: nothing to convert
    extcall WethContract(weth).deposit(value=amount)

    self._performPostActionTasks([weth])
    log EthWrapped(
        amount = amount,
        paidEth = msg.value,
        weth = weth,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return amount


# weth -> eth


@nonreentrant
@external
def convertWethToEth(_amount: uint256 = max_value(uint256)) -> uint256:
    weth: address = WETH
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.WETH_TO_ETH, False, [weth])

    # convert weth to eth
    amount: uint256 = self._getAmountAndApprove(weth, _amount, empty(address)) # nothing to approve
    extcall WethContract(weth).withdraw(amount)

    self._performPostActionTasks([weth])
    log WethUnwrapped(
        amount = amount,
        weth = weth,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return amount


#############
# Liquidity #
#############


# add / remove liquidity (simple)


@nonreentrant
@external
def addLiquidity(
    _legoId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _amountA: uint256 = max_value(uint256),
    _amountB: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _minLpAmount: uint256 = 0,
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ADD_LIQ, False, [_tokenA, _tokenB], [_legoId])

    # token approvals
    amountA: uint256 = self._getAmountAndApprove(_tokenA, _amountA, cd.legoAddr)
    amountB: uint256 = self._getAmountAndApprove(_tokenB, _amountB, cd.legoAddr)

    # add liquidity via lego partner
    lpToken: address = empty(address)
    lpAmountReceived: uint256 = 0
    addedTokenA: uint256 = 0
    addedTokenB: uint256 = 0
    lpToken, lpAmountReceived, addedTokenA, addedTokenB = extcall Lego(cd.legoAddr).addLiquidity(_pool, _tokenA, _tokenB, amountA, amountB, _minAmountA, _minAmountB, _minLpAmount, _extraAddr, _extraVal, _extraData, self)

    # remove approvals
    if amountA != 0:
        assert extcall IERC20(_tokenA).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed
    if amountB != 0:
        assert extcall IERC20(_tokenB).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_tokenA, _tokenB, lpToken])
    log LiquidityAdded(
        pool = _pool,
        tokenA = _tokenA,
        amountA = addedTokenA,
        tokenB = _tokenB,
        amountB = addedTokenB,
        lpToken = lpToken,
        lpAmountReceived = lpAmountReceived,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return lpAmountReceived, addedTokenA, addedTokenB


@nonreentrant
@external
def removeLiquidity(
    _legoId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _lpToken: address,
    _lpAmount: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REMOVE_LIQ, False, [_tokenA, _tokenB], [_legoId])

    # remove liquidity via lego partner
    amountAReceived: uint256 = 0
    amountBReceived: uint256 = 0
    lpAmountBurned: uint256 = 0
    lpAmount: uint256 = self._getAmountAndApprove(_lpToken, _lpAmount, cd.legoAddr)
    amountAReceived, amountBReceived, lpAmountBurned = extcall Lego(cd.legoAddr).removeLiquidity(_pool, _tokenA, _tokenB, _lpToken, lpAmount, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_lpToken).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_tokenA, _tokenB, _lpToken])
    log LiquidityRemoved(
        pool = _pool,
        tokenA = _tokenA,
        amountAReceived = amountAReceived,
        tokenB = _tokenB,
        amountBReceived = amountBReceived,
        lpToken = _lpToken,
        lpAmountBurned = lpAmountBurned,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return amountAReceived, amountBReceived, lpAmountBurned


# concentrated liquidity


@nonreentrant
@external
def addLiquidityConcentrated(
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
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ADD_LIQ_CONC, False, [_tokenA, _tokenB], [_legoId])

    # token approvals
    amountA: uint256 = self._getAmountAndApprove(_tokenA, _amountA, cd.legoAddr)
    amountB: uint256 = self._getAmountAndApprove(_tokenB, _amountB, cd.legoAddr)

    # transfer nft to lego (if applicable)
    hasNftLiqPosition: bool = _nftAddr != empty(address) and _nftTokenId != 0
    if hasNftLiqPosition:
        extcall IERC721(_nftAddr).safeTransferFrom(self, cd.legoAddr, _nftTokenId, ERC721_RECEIVE_DATA)

    # add liquidity via lego partner
    liqAdded: uint256 = 0
    addedTokenA: uint256 = 0
    addedTokenB: uint256 = 0
    nftTokenId: uint256 = 0
    liqAdded, addedTokenA, addedTokenB, nftTokenId = extcall Lego(cd.legoAddr).addLiquidityConcentrated(_nftTokenId, _pool, _tokenA, _tokenB, _tickLower, _tickUpper, amountA, amountB, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, self)

    # make sure nft is back
    assert staticcall IERC721(_nftAddr).ownerOf(nftTokenId) == self # dev: nft not returned

    # remove approvals
    if amountA != 0:
        assert extcall IERC20(_tokenA).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed
    if amountB != 0:
        assert extcall IERC20(_tokenB).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_tokenA, _tokenB])
    log ConcentratedLiquidityAdded(
        nftTokenId = nftTokenId,
        pool = _pool,
        tokenA = _tokenA,
        amountA = addedTokenA,
        tokenB = _tokenB,
        amountB = addedTokenB,
        liqAdded = liqAdded,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return liqAdded, addedTokenA, addedTokenB, nftTokenId


@nonreentrant
@external
def removeLiquidityConcentrated(
    _legoId: uint256,
    _nftAddr: address,
    _nftTokenId: uint256,
    _pool: address,
    _tokenA: address,
    _tokenB: address,
    _liqToRemove: uint256 = max_value(uint256),
    _minAmountA: uint256 = 0,
    _minAmountB: uint256 = 0,
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REMOVE_LIQ_CONC, False, [_tokenA, _tokenB], [_legoId])

    # must have nft liq position
    assert _nftAddr != empty(address) # dev: invalid nft addr
    assert _nftTokenId != 0 # dev: invalid nft token id
    extcall IERC721(_nftAddr).safeTransferFrom(self, cd.legoAddr, _nftTokenId, ERC721_RECEIVE_DATA)

    # remove liquidity via lego partner
    amountAReceived: uint256 = 0
    amountBReceived: uint256 = 0
    liqRemoved: uint256 = 0
    isDepleted: bool = False
    amountAReceived, amountBReceived, liqRemoved, isDepleted = extcall Lego(cd.legoAddr).removeLiquidityConcentrated(_nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, self)

    # validate the nft came back (if not depleted)
    if not isDepleted:
        assert staticcall IERC721(_nftAddr).ownerOf(_nftTokenId) == self # dev: nft not returned

    self._performPostActionTasks([_tokenA, _tokenB])
    log ConcentratedLiquidityRemoved(
        nftTokenId = _nftTokenId,
        pool = _pool,
        tokenA = _tokenA,
        amountAReceived = amountAReceived,
        tokenB = _tokenB,
        amountBReceived = amountBReceived,
        liqRemoved = liqRemoved,
        extraAddr = _extraAddr,
        extraVal = _extraVal,
        extraData = _extraData,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
        isManager = cd.isManager,
    )
    return amountAReceived, amountBReceived, liqRemoved


####################
# Pre Action Tasks #
####################


@internal
def _performPreActionTasks(
    _signer: address,
    _action: wi.ActionType,
    _shouldCheckAccess: bool,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> ActionData:
    cd: ActionData = self._getActionDataBundle()

    # access control
    cd.signer = _signer
    if _signer != cd.walletOwner:
        assert staticcall WalletConfig(cd.walletConfig).canPerformAction(_signer, _action, _assets, _legoIds, _transferRecipient) # dev: signer cannot access wallet
        cd.isManager = True

    # get specific lego addr if specified
    if len(_legoIds) != 0:
        cd.legoId = _legoIds[0]
        cd.legoAddr = staticcall Registry(cd.legoRegistry).getAddr(cd.legoId)
        assert cd.legoAddr != empty(address) # dev: invalid lego

    # make sure lego can perform the action
    if _shouldCheckAccess and cd.legoAddr != empty(address):
        self._checkLegoAccessForAction(cd.legoAddr, _action)

    # update deposit points
    self._updateDepositPointsPreAction()

    # check for yield to realize
    checkedAssets: DynArray[address, MAX_ASSETS] = []
    for a: address in _assets:
        if a == empty(address) or a in checkedAssets:
            continue
        self._checkForYieldProfits(a, cd.feeRecipient)
        checkedAssets.append(a)

    return cd


# update deposit points


@internal
def _updateDepositPointsPreAction():
    totalData: WalletTotals = self.totals

    # nothing to do here -- `lastUpdate` will be saved in `_performPostActionTasks`
    if totalData.usdValue == 0 or totalData.lastUpdate == 0 or block.number <= totalData.lastUpdate:
        return

    newDepositPoints: uint256 = totalData.usdValue * (block.number - totalData.lastUpdate)
    totalData.depositPoints += newDepositPoints
    totalData.lastUpdate = block.number
    self.totals = totalData


# core data


@view
@internal
def _getActionDataBundle() -> ActionData:
    undyHq: address = UNDY_HQ
    walletConfig: address = self.walletConfig
    return ActionData(
        undyHq = undyHq,
        legoRegistry = staticcall Registry(undyHq).getAddr(LEGO_BOOK_ID),
        feeRecipient = self._getFeeRecipient(undyHq),
        wallet = self,
        walletConfig = walletConfig,
        walletOwner = staticcall WalletConfig(walletConfig).owner(),
        trialFundsAsset = self.trialFundsAsset,
        trialFundsAmount = self.trialFundsAmount,
        signer = empty(address),
        isManager = False,
        legoId = 0,
        legoAddr = empty(address),
    )


# allow lego to perform action


@internal
def _checkLegoAccessForAction(_legoAddr: address, _action: wi.ActionType):
    targetAddr: address = empty(address)
    accessAbi: String[64] = empty(String[64])
    numInputs: uint256 = 0
    targetAddr, accessAbi, numInputs = staticcall Lego(_legoAddr).getAccessForLego(self, _action)

    # nothing to do here
    if targetAddr == empty(address):
        return

    method_abi: bytes4 = convert(slice(keccak256(accessAbi), 0, 4), bytes4)
    success: bool = False
    response: Bytes[32] = b""

    # assumes input is: lego addr (operator)
    if numInputs == 1:
        success, response = raw_call(
            targetAddr,
            concat(
                method_abi,
                convert(_legoAddr, bytes32),
            ),
            revert_on_failure=False,
            max_outsize=32,
        )
    
    # assumes input (and order) is: user (self), lego addr (operator)
    elif numInputs == 2:
        success, response = raw_call(
            targetAddr,
            concat(
                method_abi,
                convert(self, bytes32),
                convert(_legoAddr, bytes32),
            ),
            revert_on_failure=False,
            max_outsize=32,
        )

    # assumes input (and order) is: user (self), lego addr (operator), allowed bool
    elif numInputs == 3:
        success, response = raw_call(
            targetAddr,
            concat(
                method_abi,
                convert(self, bytes32),
                convert(_legoAddr, bytes32),
                convert(True, bytes32),
            ),
            revert_on_failure=False,
            max_outsize=32,
        )

    assert success # dev: failed to set operator


#####################
# Post Action Tasks #
#####################


@internal
def _performPostActionTasks(_assets: DynArray[address, MAX_ASSETS]):
    totalData: WalletTotals = self.totals
    prevTotalUsdValue: uint256 = totalData.usdValue

    # update each asset that was touched
    for a: address in _assets:
        totalData.usdValue = self._updateAssetData(a, totalData.usdValue)

    totalData.lastUpdate = block.number
    self.totals = totalData

    # make sure user still has trial funds
    assert self._stillHasTrialFunds() # dev: user no longer has trial funds

    # update global points
    self._updateGlobalDepositPoints(prevTotalUsdValue, totalData.usdValue)


##############
# Asset Data #
##############


@external
def updateAsset(_asset: address, _shouldCheckYield: bool):

    # TODO: access control around this

    assert _asset != empty(address) # dev: invalid asset
    totalData: WalletTotals = self.totals
    prevTotalUsdValue: uint256 = totalData.usdValue

    # update deposit points
    if totalData.usdValue != 0 and totalData.lastUpdate != 0 and block.number > totalData.lastUpdate:
        newDepositPoints: uint256 = totalData.usdValue * (block.number - totalData.lastUpdate)
        totalData.depositPoints += newDepositPoints

    # check for yield
    if _shouldCheckYield:
        self._checkForYieldProfits(_asset, self._getFeeRecipient(UNDY_HQ))

    # update asset data
    totalData.usdValue = self._updateAssetData(_asset, totalData.usdValue)
    totalData.lastUpdate = block.number
    self.totals = totalData

    # update global points
    self._updateGlobalDepositPoints(prevTotalUsdValue, totalData.usdValue)


# update asset data


@internal
def _updateAssetData(_asset: address, _totalUsdValue: uint256) -> uint256:
    if _asset == empty(address):
        return _totalUsdValue

    data: AssetData = self.assetData[_asset]
    prevUsdValue: uint256 = data.usdValue

    # update balance
    currentBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    if currentBalance != 0:
        data.assetBalance = currentBalance

        # price
        if data.lastPriceUpdate != block.number:
            data.lastPrice = self._getPrice(_asset)
            data.lastPriceUpdate = block.number

        # config (decimals needed)
        if not data.config.hasConfig:
            data.config = self._getAssetConfig(_asset)

        # usd value
        data.usdValue = 0
        if data.lastPrice != 0 and data.config.decimals != 0:
            data.usdValue = data.lastPrice * currentBalance // (10 ** data.config.decimals)

        # register asset (if necessary)
        if self.indexOfAsset[_asset] == 0:
            self._registerAsset(_asset)

    # no balance, deregister asset
    else:
        data = empty(AssetData)
        self._deregisterAsset(_asset)

    # save data
    self.assetData[_asset] = data
    return _totalUsdValue - prevUsdValue + data.usdValue


# register/deregister asset


@internal
def _registerAsset(_asset: address):
    aid: uint256 = self.numAssets
    if aid == 0:
        aid = 1 # not using 0 index
    self.assets[aid] = _asset
    self.indexOfAsset[_asset] = aid
    self.numAssets = aid + 1


@internal
def _deregisterAsset(_asset: address) -> bool:
    numAssets: uint256 = self.numAssets
    if numAssets == 0:
        return False

    targetIndex: uint256 = self.indexOfAsset[_asset]
    if targetIndex == 0:
        return False

    # update data
    lastIndex: uint256 = numAssets - 1
    self.numAssets = lastIndex
    self.indexOfAsset[_asset] = 0

    # get last item, replace the removed item
    if targetIndex != lastIndex:
        lastItem: address = self.assets[lastIndex]
        self.assets[targetIndex] = lastItem
        self.indexOfAsset[lastItem] = targetIndex

    return True


##################
# Yield Handling #
##################


@internal
def _checkForYieldProfits(_asset: address, _feeRecipient: address):
    # not saved previously, nothing to do here
    data: AssetData = self.assetData[_asset]
    if data.assetBalance == 0:
        return

    # no config for yield, nothing to do here
    if not data.config.hasConfig or not data.config.isYieldAsset or data.config.performanceFee == 0:
        return

    # no balance, nothing to do here
    currentBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    if currentBalance == 0:
        return

    # rebase asset
    if data.config.isRebasing:
        self._realizeRebaseYield(_asset, data, currentBalance, _feeRecipient)

    # price increase
    else:
        self._realizeNormalYield(_asset, data, currentBalance, _feeRecipient)


@internal
def _realizeRebaseYield(_asset: address, _data: AssetData, _currentBal: uint256, _feeRecipient: address):
    currentBalance: uint256 = _currentBal
    if _data.config.maxIncrease != 0:
        currentBalance = min(_currentBal, _data.assetBalance + (_data.assetBalance * _data.config.maxIncrease // HUNDRED_PERCENT))

    # no profits
    if currentBalance <= _data.assetBalance:
        return

    # calc fee (if any)
    profitAmount: uint256 = currentBalance - _data.assetBalance
    feeAmount: uint256 = profitAmount * _data.config.performanceFee // HUNDRED_PERCENT
    if feeAmount != 0 and _feeRecipient != empty(address):
        assert extcall IERC20(_asset).transfer(_feeRecipient, feeAmount) # dev: transfer failed


@internal
def _realizeNormalYield(_asset: address, _data: AssetData, _currentBal: uint256, _feeRecipient: address):
    data: AssetData = _data
    prevUsdValue: uint256 = data.usdValue

    # only updating price in asset data
    if data.lastPriceUpdate != block.number:
        data.lastPrice = self._getPrice(_asset)
        data.lastPriceUpdate = block.number

    # nothing to do here
    if data.lastPrice == 0:
        return

    # new values (with ceiling)
    assetBalance: uint256 = min(_currentBal, data.assetBalance)
    newUsdValue: uint256 = data.lastPrice * assetBalance // (10 ** data.config.decimals)
    if data.config.maxIncrease != 0:
        newUsdValue = min(newUsdValue, prevUsdValue + (prevUsdValue * data.config.maxIncrease // HUNDRED_PERCENT))

    # no profits
    if newUsdValue <= prevUsdValue:
        return

    # calc fee (if any)
    profitUsdValue: uint256 = newUsdValue - prevUsdValue
    feeUsdValue: uint256 = profitUsdValue * data.config.performanceFee // HUNDRED_PERCENT
    if feeUsdValue != 0 and _feeRecipient != empty(address):
        feeAmount: uint256 = feeUsdValue * (10 ** data.config.decimals) // data.lastPrice
        assert extcall IERC20(_asset).transfer(_feeRecipient, feeAmount) # dev: transfer failed

    # `lastPrice` is only thing saved here
    self.assetData[_asset] = data


#############
# Utilities #
#############


@view
@internal
def _getPrice(_asset: address) -> uint256:
    # TODO: integrate with Ripe's PriceDesk
    return 0


@internal
def _updateGlobalDepositPoints(_prevUsdValue: uint256, _newUsdValue: uint256):
    # TODO: notify "AgentFactory (????)" of new totalUsdValue (to update `totalUsdValue` for global points)
    # only call if prevUsdValue != _newUsdValue
    pass


@view
@internal
def _getAssetConfig(_asset: address) -> AssetConfig:
    
    # TODO: get asset config (MissionControl???)

    return empty(AssetConfig)


@view
@internal
def _getFeeRecipient(_undyHq: address) -> address:
    # TODO: get proper fee recipient
    return _undyHq


@view
@internal
def _stillHasTrialFunds() -> bool:
    # TODO: check if wallet still has trial funds
    return True


# approve


@internal
def _getAmountAndApprove(_token: address, _amount: uint256, _legoAddr: address) -> uint256:
    if _amount == 0:
        return 0
    amount: uint256 = min(_amount, staticcall IERC20(_token).balanceOf(self))
    assert amount != 0 # dev: no balance for _token
    if _legoAddr != empty(address):
        assert extcall IERC20(_token).approve(_legoAddr, amount, default_return_value=True) # dev: approval failed
    return amount


# recover nft


@external
def recoverNft(_collection: address, _nftTokenId: uint256) -> bool:
    owner: address = staticcall WalletConfig(self.walletConfig).owner()
    assert msg.sender == owner # dev: no perms

    if staticcall IERC721(_collection).ownerOf(_nftTokenId) != self:
        return False

    extcall IERC721(_collection).safeTransferFrom(self, owner, _nftTokenId)
    log NftRecovered(
        collection=_collection,
        nftTokenId=_nftTokenId,
        owner=owner,
    )
    return True