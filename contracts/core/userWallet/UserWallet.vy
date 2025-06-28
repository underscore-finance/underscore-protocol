# @version 0.4.3
# pragma optimize codesize

implements: wi
from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego

from ethereum.ercs import IERC20Detailed
from ethereum.ercs import IERC20
from ethereum.ercs import IERC721

interface WalletBackpack:
    def getYieldAssetConfig(_asset: address, _legoId: uint256, _underlyingAsset: address) -> YieldAssetConfig: view
    def performPostActionTasks(_prevTotalUsdValue: uint256, _newTotalUsdValue: uint256): nonpayable
    def updateAndGetPriceFromWallet(_asset: address, _isYieldAsset: bool) -> uint256: nonpayable
    def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address) -> uint256: view
    def isYieldAssetAndGetDecimals(_asset: address) -> (bool, uint256): view
    def getRewardsFee(_user: address, _asset: address) -> uint256: view
    def updateUserDepositPoints() -> uint256: nonpayable

interface WalletConfig:
    def validateAccessAndGetBundle(_signer: address, _action: wi.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _transferRecipient: address = empty(address)) -> ActionData: view
    def addNewManagerTransaction(_manager: address, _txUsdValue: uint256): nonpayable
    def canTransferToRecipient(_recipient: address) -> bool: view

interface WethContract:
    def withdraw(_amount: uint256): nonpayable
    def deposit(): payable

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct WalletAssetData:
    assetBalance: uint256
    usdValue: uint256
    lastPrice: uint256
    lastPriceUpdate: uint256
    decimals: uint256
    isYieldAsset: bool

struct YieldAssetConfig:
    legoId: uint256
    isRebasing: bool
    underlyingAsset: address
    maxYieldIncrease: uint256
    yieldProfitFee: uint256

struct ActionData:
    legoBook: address
    walletBackpack: address
    feeRecipient: address
    wallet: address
    walletConfig: address
    walletOwner: address
    lastTotalUsdValue: uint256
    signer: address
    isManager: bool
    legoId: uint256
    legoAddr: address
    eth: address
    weth: address

event YieldDeposit:
    asset: indexed(address)
    assetAmount: uint256
    vaultToken: indexed(address)
    vaultTokenAmount: uint256
    txUsdValue: uint256
    legoId: uint256
    signer: indexed(address)

event YieldWithdrawal:
    vaultToken: indexed(address)
    vaultTokenAmountBurned: uint256
    underlyingAsset: indexed(address)
    underlyingAmountReceived: uint256
    txUsdValue: uint256
    legoId: uint256
    signer: indexed(address)

event OverallSwapPerformed:
    tokenIn: indexed(address)
    tokenInAmount: uint256
    tokenOut: indexed(address)
    tokenOutAmount: uint256
    txUsdValue: uint256
    numLegos: uint256
    numInstructions: uint256
    signer: indexed(address)

event SpecificSwapInstructionPerformed:
    tokenIn: indexed(address)
    tokenInAmount: uint256
    tokenOut: indexed(address)
    tokenOutAmount: uint256
    txUsdValue: uint256
    numTokens: uint256
    numPools: uint256
    legoId: uint256
    legoAddr: address
    signer: indexed(address)

event AssetMintedOrRedeemed:
    tokenIn: indexed(address)
    tokenInAmount: uint256
    tokenOut: indexed(address)
    tokenOutAmount: uint256
    isPending: bool
    txUsdValue: uint256
    legoId: uint256
    signer: indexed(address)

event AssetMintedOrRedeemedConfirmed:
    tokenIn: indexed(address)
    tokenOut: indexed(address)
    tokenOutAmount: uint256
    txUsdValue: uint256
    legoId: uint256
    signer: indexed(address)

event CollateralAdded:
    asset: indexed(address)
    amountDeposited: uint256
    txUsdValue: uint256
    legoId: uint256
    signer: indexed(address)

event CollateralRemoved:
    asset: indexed(address)
    amountRemoved: uint256
    txUsdValue: uint256
    legoId: uint256
    signer: indexed(address)

event NewBorrow:
    borrowAsset: indexed(address)
    borrowAmount: uint256
    txUsdValue: uint256
    legoId: uint256
    signer: indexed(address)

event DebtRepayment:
    paymentAsset: indexed(address)
    repaidAmount: uint256
    txUsdValue: uint256
    legoId: uint256
    signer: indexed(address)

event LiquidityAdded:
    pool: indexed(address)
    tokenA: indexed(address)
    amountA: uint256
    tokenB: indexed(address)
    amountB: uint256
    txUsdValue: uint256
    lpToken: address
    lpAmountReceived: uint256
    legoId: uint256
    signer: address

event ConcentratedLiquidityAdded:
    nftTokenId: uint256
    pool: indexed(address)
    tokenA: indexed(address)
    amountA: uint256
    tokenB: indexed(address)
    amountB: uint256
    txUsdValue: uint256
    liqAdded: uint256
    legoId: uint256
    signer: address

event LiquidityRemoved:
    pool: indexed(address)
    tokenA: indexed(address)
    amountAReceived: uint256
    tokenB: indexed(address)
    amountBReceived: uint256
    txUsdValue: uint256
    lpToken: address
    lpAmountBurned: uint256
    legoId: uint256
    signer: address

event ConcentratedLiquidityRemoved:
    nftTokenId: uint256
    pool: indexed(address)
    tokenA: indexed(address)
    amountAReceived: uint256
    tokenB: indexed(address)
    amountBReceived: uint256
    txUsdValue: uint256
    liqRemoved: uint256
    legoId: uint256
    signer: address

event FundsTransferred:
    asset: indexed(address)
    amount: uint256
    recipient: indexed(address)
    signer: indexed(address)

event EthWrapped:
    amount: uint256
    paidEth: uint256
    txUsdValue: uint256
    signer: indexed(address)

event WethUnwrapped:
    amount: uint256
    txUsdValue: uint256
    signer: indexed(address)

event RewardsClaimed:
    rewardToken: indexed(address)
    rewardAmount: uint256
    txUsdValue: uint256
    legoId: uint256
    legoAddr: address
    signer: indexed(address)

event NftRecovered:
    collection: indexed(address)
    nftTokenId: uint256
    recipient: indexed(address)

# data 
walletConfig: public(address)

# asset data
assetData: public(HashMap[address, WalletAssetData]) # asset -> data
assets: public(HashMap[uint256, address]) # index -> asset
indexOfAsset: public(HashMap[address, uint256]) # asset -> index
numAssets: public(uint256) # num assets

# yield asset config
yieldAssetConfig: public(HashMap[address, YieldAssetConfig]) # asset -> config

HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
MAX_SWAP_FEE: constant(uint256) = 5_00 # 5%
MAX_REWARDS_FEE: constant(uint256) = 40_00 # 40%
MAX_YIELD_FEE: constant(uint256) = 40_00 # 40%
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10
WALLET_BACKPACK_ID: constant(uint256) = 7

ERC721_RECEIVE_DATA: constant(Bytes[1024]) = b"UnderscoreErc721"
API_VERSION: constant(String[28]) = "0.1.0"

UNDY_HQ: public(immutable(address))
WETH: public(immutable(address))
ETH: public(immutable(address))


@deploy
def __init__(
    _undyHq: address,
    _wethAddr: address,
    _ethAddr: address,
    _walletConfig: address,
):
    assert empty(address) not in [_undyHq, _wethAddr, _walletConfig] # dev: invalid addrs
    self.walletConfig = _walletConfig

    UNDY_HQ = _undyHq
    WETH = _wethAddr
    ETH = _ethAddr


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
) -> (uint256, uint256):
    eth: address = ETH
    weth: address = WETH

    asset: address = _asset
    if asset == empty(address):
        asset = eth

    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.TRANSFER, False, [asset], [], _recipient)

    # validate recipient
    if _recipient != cd.walletOwner:
        assert staticcall WalletConfig(cd.walletConfig).canTransferToRecipient(_recipient) # dev: recipient not allowed

    amount: uint256 = 0
    maxBalance: uint256 = 0

    # handle eth
    if asset == eth:
        maxBalance = self.balance
        amount = min(_amount, maxBalance)
        assert amount != 0 # dev: nothing to transfer
        send(_recipient, amount)

    # erc20 tokens
    else:
        maxBalance = staticcall IERC20(asset).balanceOf(self)
        amount = min(_amount, maxBalance)
        assert amount != 0 # dev: no balance for _token
        assert extcall IERC20(asset).transfer(_recipient, amount, default_return_value=True) # dev: transfer failed

    # need decimals for tx usd value
    data: WalletAssetData = self.assetData[asset]
    if data.decimals == 0:
        data.isYieldAsset, data.decimals = self._getCoreAssetData(asset, cd.walletBackpack, cd.eth, cd.weth)

        # only save if there will still be balance
        if maxBalance > amount:
            self.assetData[asset] = data

    # get tx usd value
    price: uint256 = extcall WalletBackpack(cd.walletBackpack).updateAndGetPriceFromWallet(asset, data.isYieldAsset)
    txUsdValue: uint256 = price * amount // (10 ** data.decimals)

    self._performPostActionTasks([asset], txUsdValue, cd)
    log FundsTransferred(
        asset = asset,
        amount = amount,
        recipient = _recipient,
        signer = cd.signer,
    )
    return amount, txUsdValue


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
) -> (uint256, address, uint256, uint256):
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
) -> (uint256, address, uint256, uint256):
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, _cd.legoAddr) # doing approval here

    # deposit for yield
    assetAmount: uint256 = 0
    vaultToken: address = empty(address)
    vaultTokenAmountReceived: uint256 = 0
    txUsdValue: uint256 = 0
    assetAmount, vaultToken, vaultTokenAmountReceived, txUsdValue = extcall Lego(_cd.legoAddr).depositForYield(_asset, amount, _vaultAddr, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_asset).approve(_cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    # save yield asset config
    if empty(address) not in [vaultToken, _asset]:
        self._setYieldAssetConfig(vaultToken, _cd.legoId, _asset, _cd.walletBackpack)

    # perform post action tasks
    if _shouldPerformPostActionTasks:
        self._performPostActionTasks([_asset, vaultToken], txUsdValue, _cd)

    log YieldDeposit(
        asset = _asset,
        assetAmount = assetAmount,
        vaultToken = vaultToken,
        vaultTokenAmount = vaultTokenAmountReceived,
        txUsdValue = txUsdValue,
        legoId = _cd.legoId,
        signer = _cd.signer,
    )
    return assetAmount, vaultToken, vaultTokenAmountReceived, txUsdValue


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
) -> (uint256, address, uint256, uint256):
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
) -> (uint256, address, uint256, uint256):

    amount: uint256 = _amount
    if _vaultToken != empty(address):
        amount = self._getAmountAndApprove(_vaultToken, _amount, empty(address)) # not approving here

        # some vault tokens require max value approval (comp v3)
        assert extcall IERC20(_vaultToken).approve(_cd.legoAddr, max_value(uint256), default_return_value=True) # dev: approval failed

    # withdraw from yield
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    txUsdValue: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount, txUsdValue = extcall Lego(_cd.legoAddr).withdrawFromYield(_vaultToken, amount, _extraAddr, _extraVal, _extraData, self)

    if _vaultToken != empty(address):
        assert extcall IERC20(_vaultToken).approve(_cd.legoAddr, 0, default_return_value=True) # dev: approval failed

        # save yield asset config
        if underlyingAsset != empty(address):
            self._setYieldAssetConfig(_vaultToken, _cd.legoId, underlyingAsset, _cd.walletBackpack)

    # perform post action tasks
    if _shouldPerformPostActionTasks:
        self._performPostActionTasks([underlyingAsset, _vaultToken], txUsdValue, _cd)

    log YieldWithdrawal(
        vaultToken = _vaultToken,
        vaultTokenAmountBurned = vaultTokenAmountBurned,
        underlyingAsset = underlyingAsset,
        underlyingAmountReceived = underlyingAmount,
        txUsdValue = txUsdValue,
        legoId = _cd.legoId,
        signer = _cd.signer,
    )
    return vaultTokenAmountBurned, underlyingAsset, underlyingAmount, txUsdValue


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
) -> (uint256, address, uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.EARN_REBALANCE, False, [_fromVaultToken, _toVaultAddr], [_fromLegoId, _toLegoId])

    # withdraw
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    withdrawTxUsdValue: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount, withdrawTxUsdValue = self._withdrawFromYield(_fromVaultToken, _fromVaultAmount, _extraAddr, _extraVal, _extraData, False, cd)

    # deposit
    toVaultToken: address = empty(address)
    toVaultTokenAmountReceived: uint256 = 0
    depositTxUsdValue: uint256 = 0
    cd.legoId = _toLegoId
    cd.legoAddr = staticcall Registry(cd.legoBook).getAddr(_toLegoId)
    underlyingAmount, toVaultToken, toVaultTokenAmountReceived, depositTxUsdValue = self._depositForYield(underlyingAsset, _toVaultAddr, underlyingAmount, _extraAddr, _extraVal, _extraData, False, cd)

    maxUsdValue: uint256 = max(withdrawTxUsdValue, depositTxUsdValue)
    self._performPostActionTasks([underlyingAsset, _fromVaultToken, toVaultToken], maxUsdValue, cd)
    return underlyingAmount, toVaultToken, toVaultTokenAmountReceived, maxUsdValue


###################
# Swap / Exchange #
###################


@nonreentrant
@external
def swapTokens(_instructions: DynArray[wi.SwapInstruction, MAX_SWAP_INSTRUCTIONS]) -> (address, uint256, address, uint256, uint256):
    tokenIn: address = empty(address)
    tokenOut: address = empty(address)
    legoIds: DynArray[uint256, MAX_LEGOS] = []
    tokenIn, tokenOut, legoIds = self._validateAndGetSwapInfo(_instructions)

    # action data bundle
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.SWAP, False, [tokenIn, tokenOut], legoIds)
    origAmountIn: uint256 = self._getAmountAndApprove(tokenIn, _instructions[0].amountIn, empty(address)) # not approving here

    amountIn: uint256 = origAmountIn
    lastTokenOut: address = empty(address)
    lastTokenOutAmount: uint256 = 0
    maxTxUsdValue: uint256 = 0

    # perform swaps
    for i: wi.SwapInstruction in _instructions:
        if lastTokenOut != empty(address):
            newTokenIn: address = i.tokenPath[0]
            assert lastTokenOut == newTokenIn # dev: must honor token path
            amountIn = min(lastTokenOutAmount, staticcall IERC20(newTokenIn).balanceOf(self))
        
        thisTxUsdValue: uint256 = 0
        lastTokenOut, lastTokenOutAmount, thisTxUsdValue = self._performSwapInstruction(amountIn, i, cd)
        maxTxUsdValue = max(maxTxUsdValue, thisTxUsdValue)

    # handle swap fee
    if lastTokenOut != empty(address):
        swapFee: uint256 = staticcall WalletBackpack(cd.walletBackpack).getSwapFee(self, tokenIn, lastTokenOut)
        if swapFee != 0 and lastTokenOutAmount != 0:
            self._payFee(lastTokenOut, lastTokenOutAmount, min(swapFee, MAX_SWAP_FEE),cd.feeRecipient)

    self._performPostActionTasks([tokenIn, lastTokenOut], maxTxUsdValue, cd)
    log OverallSwapPerformed(
        tokenIn = tokenIn,
        tokenInAmount = origAmountIn,
        tokenOut = lastTokenOut,
        tokenOutAmount = lastTokenOutAmount,
        txUsdValue = maxTxUsdValue,
        numLegos = len(legoIds),
        numInstructions = len(_instructions),
        signer = cd.signer,
    )
    return tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, maxTxUsdValue


@internal
def _performSwapInstruction(
    _amountIn: uint256,
    _i: wi.SwapInstruction,
    _cd: ActionData,
) -> (address, uint256, uint256):
    legoAddr: address = staticcall Registry(_cd.legoBook).getAddr(_i.legoId)
    assert legoAddr != empty(address) # dev: invalid lego

    # tokens
    tokenIn: address = _i.tokenPath[0]
    tokenOut: address = _i.tokenPath[len(_i.tokenPath) - 1]
    tokenInAmount: uint256 = 0
    tokenOutAmount: uint256 = 0
    txUsdValue: uint256 = 0

    assert extcall IERC20(tokenIn).approve(legoAddr, _amountIn, default_return_value=True) # dev: approval failed
    tokenInAmount, tokenOutAmount, txUsdValue = extcall Lego(legoAddr).swapTokens(_amountIn, _i.minAmountOut, _i.tokenPath, _i.poolPath, self)
    assert extcall IERC20(tokenIn).approve(legoAddr, 0, default_return_value=True) # dev: approval failed

    log SpecificSwapInstructionPerformed(
        tokenIn = tokenIn,
        tokenInAmount = tokenInAmount,
        tokenOut = tokenOut,
        tokenOutAmount = tokenOutAmount,
        txUsdValue = txUsdValue,
        numTokens = len(_i.tokenPath),
        numPools = len(_i.poolPath),
        legoId = _i.legoId,
        legoAddr = legoAddr,
        signer = _cd.signer,
    )
    return tokenOut, tokenOutAmount, txUsdValue


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
) -> (uint256, uint256, bool, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.MINT_REDEEM, False, [_tokenIn, _tokenOut], [_legoId])

    # mint
    tokenInAmount: uint256 = self._getAmountAndApprove(_tokenIn, _amountIn, cd.legoAddr) # doing approval here
    tokenOutAmount: uint256 = 0
    isPending: bool = False
    txUsdValue: uint256 = 0
    tokenInAmount, tokenOutAmount, isPending, txUsdValue = extcall Lego(cd.legoAddr).mintOrRedeemAsset(_tokenIn, _tokenOut, tokenInAmount, _minAmountOut, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_tokenIn).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_tokenIn, _tokenOut], txUsdValue, cd)
    log AssetMintedOrRedeemed(
        tokenIn = _tokenIn,
        tokenInAmount = tokenInAmount,
        tokenOut = _tokenOut,
        tokenOutAmount = tokenOutAmount,
        isPending = isPending,
        txUsdValue = txUsdValue,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return tokenInAmount, tokenOutAmount, isPending, txUsdValue


@nonreentrant
@external
def confirmMintOrRedeemAsset(
    _legoId: uint256,
    _tokenIn: address,
    _tokenOut: address,
    _extraAddr: address = empty(address),
    _extraVal: uint256 = 0,
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.CONFIRM_MINT_REDEEM, False, [_tokenIn, _tokenOut], [_legoId])

    # confirm (if there is a delay on action)
    tokenOutAmount: uint256 = 0
    txUsdValue: uint256 = 0
    tokenOutAmount, txUsdValue = extcall Lego(cd.legoAddr).confirmMintOrRedeemAsset(_tokenIn, _tokenOut, _extraAddr, _extraVal, _extraData, self)

    self._performPostActionTasks([_tokenIn, _tokenOut], txUsdValue, cd)
    log AssetMintedOrRedeemedConfirmed(
        tokenIn = _tokenIn,
        tokenOut = _tokenOut,
        tokenOutAmount = tokenOutAmount,
        txUsdValue = txUsdValue,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return tokenOutAmount, txUsdValue


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
) -> (uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ADD_COLLATERAL, True, [_asset], [_legoId])

    # add collateral
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, cd.legoAddr) # doing approval here
    amountDeposited: uint256 = 0
    txUsdValue: uint256 = 0
    amountDeposited, txUsdValue = extcall Lego(cd.legoAddr).addCollateral(_asset, amount, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_asset).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_asset], txUsdValue, cd)
    log CollateralAdded(
        asset = _asset,
        amountDeposited = amountDeposited,
        txUsdValue = txUsdValue,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return amountDeposited, txUsdValue


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
) -> (uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REMOVE_COLLATERAL, True, [_asset], [_legoId])

    amountRemoved: uint256 = 0
    txUsdValue: uint256 = 0   
    amountRemoved, txUsdValue = extcall Lego(cd.legoAddr).removeCollateral(_asset, _amount, _extraAddr, _extraVal, _extraData, self)

    self._performPostActionTasks([_asset], txUsdValue, cd)
    log CollateralRemoved(
        asset = _asset,
        amountRemoved = amountRemoved,
        txUsdValue = txUsdValue,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return amountRemoved, txUsdValue


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
) -> (uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.BORROW, True, [_borrowAsset], [_legoId])

    # borrow
    borrowAmount: uint256 = 0
    txUsdValue: uint256 = 0
    borrowAmount, txUsdValue = extcall Lego(cd.legoAddr).borrow(_borrowAsset, _amount, _extraAddr, _extraVal, _extraData, self)

    self._performPostActionTasks([_borrowAsset], txUsdValue, cd)
    log NewBorrow(
        borrowAsset = _borrowAsset,
        borrowAmount = borrowAmount,
        txUsdValue = txUsdValue,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return borrowAmount, txUsdValue


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
) -> (uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REPAY_DEBT, True, [_paymentAsset], [_legoId])

    amount: uint256 = self._getAmountAndApprove(_paymentAsset, _paymentAmount, cd.legoAddr) # doing approval here
    repaidAmount: uint256 = 0
    txUsdValue: uint256 = 0
    repaidAmount, txUsdValue = extcall Lego(cd.legoAddr).repayDebt(_paymentAsset, amount, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_paymentAsset).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_paymentAsset], txUsdValue, cd)
    log DebtRepayment(
        paymentAsset = _paymentAsset,
        repaidAmount = repaidAmount,
        txUsdValue = txUsdValue,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return repaidAmount, txUsdValue


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
) -> (uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REWARDS, True, [_rewardToken], [_legoId])

    rewardAmount: uint256 = 0
    txUsdValue: uint256 = 0
    rewardAmount, txUsdValue = extcall Lego(cd.legoAddr).claimRewards(self, _rewardToken, _rewardAmount, _extraAddr, _extraVal, _extraData)

    # handle rewards fee
    if _rewardToken != empty(address):
        rewardsFee: uint256 = staticcall WalletBackpack(cd.walletBackpack).getRewardsFee(self, _rewardToken)
        if rewardsFee != 0 and rewardAmount != 0:
            self._payFee(_rewardToken, rewardAmount, min(rewardsFee, MAX_REWARDS_FEE), cd.feeRecipient)

    self._performPostActionTasks([_rewardToken], txUsdValue, cd)
    log RewardsClaimed(
        rewardToken = _rewardToken,
        rewardAmount = rewardAmount,
        txUsdValue = txUsdValue,
        legoId = cd.legoId,
        legoAddr = cd.legoAddr,
        signer = cd.signer,
    )
    return rewardAmount, txUsdValue


###############
# Wrapped ETH #
###############


# eth -> weth


@nonreentrant
@payable
@external
def convertEthToWeth(_amount: uint256 = max_value(uint256)) -> (uint256, uint256):
    eth: address = ETH
    weth: address = WETH
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ETH_TO_WETH, False, [eth, weth], [], empty(address))

    # convert eth to weth
    amount: uint256 = min(_amount, self.balance)
    assert amount != 0 # dev: nothing to convert
    extcall WethContract(weth).deposit(value=amount)

    price: uint256 = extcall WalletBackpack(cd.walletBackpack).updateAndGetPriceFromWallet(weth, False)
    txUsdValue: uint256 = price * amount // (10 ** 18)

    self._performPostActionTasks([eth, weth], txUsdValue, cd)
    log EthWrapped(
        amount = amount,
        paidEth = msg.value,
        txUsdValue = txUsdValue,
        signer = cd.signer,
    )
    return amount, txUsdValue


# weth -> eth


@nonreentrant
@external
def convertWethToEth(_amount: uint256 = max_value(uint256)) -> (uint256, uint256):
    weth: address = WETH
    eth: address = ETH
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.WETH_TO_ETH, False, [weth, eth], [], empty(address))

    # convert weth to eth
    amount: uint256 = self._getAmountAndApprove(weth, _amount, empty(address)) # nothing to approve
    extcall WethContract(weth).withdraw(amount)

    price: uint256 = extcall WalletBackpack(cd.walletBackpack).updateAndGetPriceFromWallet(weth, False)
    txUsdValue: uint256 = price * amount // (10 ** 18)

    self._performPostActionTasks([weth, eth], txUsdValue, cd)
    log WethUnwrapped(
        amount = amount,
        txUsdValue = txUsdValue,
        signer = cd.signer,
    )
    return amount, txUsdValue


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
) -> (uint256, uint256, uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ADD_LIQ, False, [_tokenA, _tokenB], [_legoId])

    # token approvals
    amountA: uint256 = self._getAmountAndApprove(_tokenA, _amountA, cd.legoAddr)
    amountB: uint256 = self._getAmountAndApprove(_tokenB, _amountB, cd.legoAddr)

    # add liquidity via lego partner
    lpToken: address = empty(address)
    lpAmountReceived: uint256 = 0
    addedTokenA: uint256 = 0
    addedTokenB: uint256 = 0
    txUsdValue: uint256 = 0
    lpToken, lpAmountReceived, addedTokenA, addedTokenB, txUsdValue = extcall Lego(cd.legoAddr).addLiquidity(_pool, _tokenA, _tokenB, amountA, amountB, _minAmountA, _minAmountB, _minLpAmount, _extraAddr, _extraVal, _extraData, self)

    # remove approvals
    if amountA != 0:
        assert extcall IERC20(_tokenA).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed
    if amountB != 0:
        assert extcall IERC20(_tokenB).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_tokenA, _tokenB, lpToken], txUsdValue, cd)
    log LiquidityAdded(
        pool = _pool,
        tokenA = _tokenA,
        amountA = addedTokenA,
        tokenB = _tokenB,
        amountB = addedTokenB,
        txUsdValue = txUsdValue,
        lpToken = lpToken,
        lpAmountReceived = lpAmountReceived,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return lpAmountReceived, addedTokenA, addedTokenB, txUsdValue


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
) -> (uint256, uint256, uint256, uint256):
    cd: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REMOVE_LIQ, False, [_tokenA, _tokenB], [_legoId])

    # remove liquidity via lego partner
    amountAReceived: uint256 = 0
    amountBReceived: uint256 = 0
    lpAmountBurned: uint256 = 0
    txUsdValue: uint256 = 0
    lpAmount: uint256 = self._getAmountAndApprove(_lpToken, _lpAmount, cd.legoAddr)
    amountAReceived, amountBReceived, lpAmountBurned, txUsdValue = extcall Lego(cd.legoAddr).removeLiquidity(_pool, _tokenA, _tokenB, _lpToken, lpAmount, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, self)
    assert extcall IERC20(_lpToken).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_tokenA, _tokenB, _lpToken], txUsdValue, cd)
    log LiquidityRemoved(
        pool = _pool,
        tokenA = _tokenA,
        amountAReceived = amountAReceived,
        tokenB = _tokenB,
        amountBReceived = amountBReceived,
        txUsdValue = txUsdValue,
        lpToken = _lpToken,
        lpAmountBurned = lpAmountBurned,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return amountAReceived, amountBReceived, lpAmountBurned, txUsdValue


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
) -> (uint256, uint256, uint256, uint256, uint256):
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
    txUsdValue: uint256 = 0
    liqAdded, addedTokenA, addedTokenB, nftTokenId, txUsdValue = extcall Lego(cd.legoAddr).addLiquidityConcentrated(_nftTokenId, _pool, _tokenA, _tokenB, _tickLower, _tickUpper, amountA, amountB, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, self)

    # make sure nft is back
    assert staticcall IERC721(_nftAddr).ownerOf(nftTokenId) == self # dev: nft not returned

    # remove approvals
    if amountA != 0:
        assert extcall IERC20(_tokenA).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed
    if amountB != 0:
        assert extcall IERC20(_tokenB).approve(cd.legoAddr, 0, default_return_value=True) # dev: approval failed

    self._performPostActionTasks([_tokenA, _tokenB], txUsdValue, cd)
    log ConcentratedLiquidityAdded(
        nftTokenId = nftTokenId,
        pool = _pool,
        tokenA = _tokenA,
        amountA = addedTokenA,
        tokenB = _tokenB,
        amountB = addedTokenB,
        txUsdValue = txUsdValue,
        liqAdded = liqAdded,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return liqAdded, addedTokenA, addedTokenB, nftTokenId, txUsdValue


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
) -> (uint256, uint256, uint256, uint256):
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
    txUsdValue: uint256 = 0
    amountAReceived, amountBReceived, liqRemoved, isDepleted, txUsdValue = extcall Lego(cd.legoAddr).removeLiquidityConcentrated(_nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, self)

    # validate the nft came back (if not depleted)
    if not isDepleted:
        assert staticcall IERC721(_nftAddr).ownerOf(_nftTokenId) == self # dev: nft not returned

    self._performPostActionTasks([_tokenA, _tokenB], txUsdValue, cd)
    log ConcentratedLiquidityRemoved(
        nftTokenId = _nftTokenId,
        pool = _pool,
        tokenA = _tokenA,
        amountAReceived = amountAReceived,
        tokenB = _tokenB,
        amountBReceived = amountBReceived,
        txUsdValue = txUsdValue,
        liqRemoved = liqRemoved,
        legoId = cd.legoId,
        signer = cd.signer,
    )
    return amountAReceived, amountBReceived, liqRemoved, txUsdValue


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
    cd: ActionData = staticcall WalletConfig(self.walletConfig).validateAccessAndGetBundle(_signer, _action, _assets, _legoIds, _transferRecipient)
    cd.eth = ETH
    cd.weth = WETH

    # get specific lego addr if specified
    if len(_legoIds) != 0:
        cd.legoId = _legoIds[0]
        cd.legoAddr = staticcall Registry(cd.legoBook).getAddr(cd.legoId)
        assert cd.legoAddr != empty(address) # dev: invalid lego

    # make sure lego can perform the action
    if _shouldCheckAccess and cd.legoAddr != empty(address):
        self._checkLegoAccessForAction(cd.legoAddr, _action)

    # update deposit points
    extcall WalletBackpack(cd.walletBackpack).updateUserDepositPoints()

    # check for yield to realize
    checkedAssets: DynArray[address, MAX_ASSETS] = []
    for a: address in _assets:
        if a in checkedAssets:
            continue
        if a in [cd.eth, cd.weth]:
            continue
        self._checkForYieldProfits(a, cd.legoId, cd.feeRecipient, cd.walletBackpack)
        checkedAssets.append(a)

    return cd


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
def _performPostActionTasks(
    _assets: DynArray[address, MAX_ASSETS],
    _txUsdValue: uint256,
    _cd: ActionData,
):
    # first, check and update manager caps
    if _cd.isManager:
        extcall WalletConfig(_cd.walletConfig).addNewManagerTransaction(_cd.signer, _txUsdValue)

    # update each asset that was touched
    newTotalUsdValue: uint256 = _cd.lastTotalUsdValue
    for a: address in _assets:
        newTotalUsdValue = self._updateAssetData(a, _cd.legoId, newTotalUsdValue, _cd.walletBackpack, _cd.eth, _cd.weth)

    # update global points + check trial funds
    extcall WalletBackpack(_cd.walletBackpack).performPostActionTasks(_cd.lastTotalUsdValue, newTotalUsdValue)


##############
# Asset Data #
##############


# update asset data


@internal
def _updateAssetData(
    _asset: address,
    _legoId: uint256,
    _totalUsdValue: uint256,
    _walletBackpack: address,
    _eth: address,
    _weth: address,
) -> uint256:
    if _asset == empty(address):
        return _totalUsdValue

    data: WalletAssetData = self.assetData[_asset]
    prevUsdValue: uint256 = data.usdValue

    # ETH / ERC20
    currentBalance: uint256 = 0
    if _asset == _eth:
        currentBalance = self.balance
    else:
        currentBalance = staticcall IERC20(_asset).balanceOf(self)

    # no balance, deregister asset
    if currentBalance == 0:
        data.assetBalance = 0
        data.usdValue = 0
        self.assetData[_asset] = data
        self._deregisterAsset(_asset)
        return _totalUsdValue - prevUsdValue

    # not saved yet, let's make sure we have what we need
    if data.decimals == 0:
        data.isYieldAsset, data.decimals = self._getCoreAssetData(_asset, _walletBackpack, _eth, _weth)

    # yield asset config
    if data.isYieldAsset:
        self._setYieldAssetConfig(_asset, _legoId, empty(address), _walletBackpack)

    # price
    if data.lastPriceUpdate != block.number:
        data.lastPrice = extcall WalletBackpack(_walletBackpack).updateAndGetPriceFromWallet(_asset, data.isYieldAsset)
        data.lastPriceUpdate = block.number

    # usd value
    data.usdValue = 0
    if data.lastPrice != 0:
        data.usdValue = data.lastPrice * currentBalance // (10 ** data.decimals)

    # register asset (if necessary)
    if self.indexOfAsset[_asset] == 0:
        self._registerAsset(_asset)

    # save data
    data.assetBalance = currentBalance
    self.assetData[_asset] = data
    return _totalUsdValue - prevUsdValue + data.usdValue


# from wallet backpack


@external
def updateAssetData(
    _asset: address,
    _shouldCheckYield: bool,
    _lastTotalUsdValue: uint256,
    _feeRecipient: address,
) -> uint256:
    walletBackpack: address = staticcall Registry(UNDY_HQ).getAddr(WALLET_BACKPACK_ID)
    assert msg.sender == walletBackpack # dev: no perms

    # check for yield
    if _shouldCheckYield:
        self._checkForYieldProfits(_asset, 0, _feeRecipient, walletBackpack)

    # update asset data
    return self._updateAssetData(_asset, 0, _lastTotalUsdValue, walletBackpack, ETH, WETH)


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
def _checkForYieldProfits(
    _asset: address,
    _legoId: uint256,
    _feeRecipient: address,
    _walletBackpack: address,
):
    if _asset == empty(address):
        return

    # nothing to do here (nothing saved, not a yield asset)
    data: WalletAssetData = self.assetData[_asset]
    if data.assetBalance == 0 or not data.isYieldAsset:
        return

    # no balance, nothing to do here
    currentBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    if currentBalance == 0:
        return

    config: YieldAssetConfig = self._setYieldAssetConfig(_asset, _legoId, empty(address), _walletBackpack)

    # rebase asset
    if config.isRebasing:
        self._realizeRebaseYield(_asset, data.assetBalance, currentBalance, _feeRecipient, config)

    # price increase
    else:
        self._realizeNormalYield(_asset, data, currentBalance, _feeRecipient, config, _walletBackpack)


@internal
def _realizeRebaseYield(
    _asset: address,
    _lastBalance: uint256,
    _currentBalance: uint256,
    _feeRecipient: address,
    _config: YieldAssetConfig,
):
    currentBalance: uint256 = _currentBalance
    if _config.maxYieldIncrease != 0:
        maxBalance: uint256 = _lastBalance + (_lastBalance * _config.maxYieldIncrease // HUNDRED_PERCENT)

        # possible edge case where user may have directly sent yield-bearing token into wallet
        # let's treat max balance as the point at which we exit early, as this appears to be the case
        if currentBalance >= maxBalance:
            return

        currentBalance = min(currentBalance, maxBalance)

    # no profits
    if currentBalance <= _lastBalance:
        return

    # calc fee (if any)
    profitAmount: uint256 = currentBalance - _lastBalance
    self._payFee(_asset, profitAmount, min(_config.yieldProfitFee, MAX_YIELD_FEE), _feeRecipient)


@internal
def _realizeNormalYield(
    _asset: address,
    _data: WalletAssetData,
    _currentBal: uint256,
    _feeRecipient: address,
    _config: YieldAssetConfig,
    _walletBackpack: address,
):
    data: WalletAssetData = _data

    # only updating price in asset data
    prevLastPrice: uint256 = data.lastPrice
    if data.lastPriceUpdate != block.number:
        data.lastPrice = extcall WalletBackpack(_walletBackpack).updateAndGetPriceFromWallet(_asset, data.isYieldAsset)
        data.lastPriceUpdate = block.number

    # nothing to do here
    if data.lastPrice == 0 or data.lastPrice == prevLastPrice:
        return

    prevUsdValue: uint256 = data.usdValue

    # new values (with ceiling)
    assetBalance: uint256 = min(_currentBal, data.assetBalance) # only count what we last saved
    newUsdValue: uint256 = data.lastPrice * assetBalance // (10 ** data.decimals)
    if _config.maxYieldIncrease != 0:
        newUsdValue = min(newUsdValue, prevUsdValue + (prevUsdValue * _config.maxYieldIncrease // HUNDRED_PERCENT))

    # no profits
    if newUsdValue <= prevUsdValue:
        return

    # calc fee (if any)
    profitUsdValue: uint256 = newUsdValue - prevUsdValue
    profitAmount: uint256 = profitUsdValue * (10 ** data.decimals) // data.lastPrice
    self._payFee(_asset, profitAmount, min(_config.yieldProfitFee, MAX_YIELD_FEE), _feeRecipient)

    # `lastPrice` is only thing saved here
    self.assetData[_asset] = data


@internal
def _payFee(_asset: address, _amount: uint256, _feeRatio: uint256, _feeRecipient: address):
    feeAmount: uint256 = _amount * _feeRatio // HUNDRED_PERCENT
    if feeAmount != 0 and _feeRecipient != empty(address):
        assert extcall IERC20(_asset).transfer(_feeRecipient, feeAmount) # dev: transfer failed


#############
# Utilities #
#############


# set yield asset config


@internal 
def _setYieldAssetConfig(
    _yieldAsset: address,
    _legoId: uint256,
    _underlyingAsset: address,
    _walletBackpack: address,
) -> YieldAssetConfig:
    config: YieldAssetConfig = self.yieldAssetConfig[_yieldAsset]
    if config.maxYieldIncrease == 0: # using this param to see if we have a config
        config = staticcall WalletBackpack(_walletBackpack).getYieldAssetConfig(_yieldAsset, _legoId, _underlyingAsset)
        self.yieldAssetConfig[_yieldAsset] = config
    return config


# get asset config


@view
@internal
def _getCoreAssetData(
    _asset: address,
    _walletBackpack: address,
    _eth: address,
    _weth: address,
) -> (bool, uint256):
    if _asset in [_eth, _weth]:
        return False, 18

    # get data
    isYieldAsset: bool = False
    decimals: uint256 = 0
    isYieldAsset, decimals = staticcall WalletBackpack(_walletBackpack).isYieldAssetAndGetDecimals(_asset)

    # no config, at least get decimals
    if decimals == 0:
        decimals = convert(staticcall IERC20Detailed(_asset).decimals(), uint256)

    return isYieldAsset, decimals


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
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address) -> bool:
    walletBackpack: address = staticcall Registry(UNDY_HQ).getAddr(WALLET_BACKPACK_ID)
    assert msg.sender == walletBackpack # dev: no perms

    if staticcall IERC721(_collection).ownerOf(_nftTokenId) != self or _recipient == empty(address):
        return False

    extcall IERC721(_collection).safeTransferFrom(self, _recipient, _nftTokenId)
    log NftRecovered(
        collection = _collection,
        nftTokenId = _nftTokenId,
        recipient = _recipient,
    )
    return True
