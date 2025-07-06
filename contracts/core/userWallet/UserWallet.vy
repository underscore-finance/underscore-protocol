# @version 0.4.3
# pragma optimize codesize

implements: wi
from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego

from ethereum.ercs import IERC20
from ethereum.ercs import IERC721

interface WalletConfig:
    def checkSignerPermissionsAndGetBundle(_signer: address, _action: wi.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _transferRecipient: address = empty(address)) -> ActionData: view
    def checkRecipientLimitsAndUpdateData(_recipient: address, _txUsdValue: uint256, _asset: address, _amount: uint256) -> bool: nonpayable
    def checkManagerUsdLimitsAndUpdateData(_manager: address, _txUsdValue: uint256) -> bool: nonpayable
    def getActionDataBundle(_legoId: uint256, _signer: address) -> ActionData: view

interface Backpack:
    def calculateYieldProfits(_asset: address, _currentBalance: uint256, _assetBalance: uint256, _lastYieldPrice: uint256, _missionControl: address, _legoBook: address, _appraiser: address) -> (uint256, uint256, uint256): nonpayable
    def performPostActionTasks(_newUserValue: uint256, _walletConfig: address, _missionControl: address, _legoBook: address, _appraiser: address): nonpayable

interface Appraiser:
    def updatePriceAndGetUsdValueAndIsYieldAsset(_asset: address, _amount: uint256) -> (uint256, bool): nonpayable
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256) -> uint256: nonpayable

interface LootDistributor:
    def addLootFromYieldProfit(_asset: address, _feeAmount: uint256, _totalYieldAmount: uint256): nonpayable
    def addLootFromSwapOrRewards(_asset: address, _amount: uint256, _action: wi.ActionType): nonpayable

interface MissionControl:
    def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address) -> uint256: view
    def getRewardsFee(_user: address, _asset: address) -> uint256: view

interface WethContract:
    def withdraw(_amount: uint256): nonpayable
    def deposit(): payable

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct WalletAssetData:
    assetBalance: uint256
    usdValue: uint256
    isYieldAsset: bool
    lastYieldPrice: uint256

struct ActionData:
    missionControl: address
    legoBook: address
    backpack: address
    appraiser: address
    lootDistributor: address
    wallet: address
    walletConfig: address
    walletOwner: address
    inEjectMode: bool
    isFrozen: bool
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

# data 
walletConfig: public(address)

# asset data
assetData: public(HashMap[address, WalletAssetData]) # asset -> data
assets: public(HashMap[uint256, address]) # index -> asset
indexOfAsset: public(HashMap[address, uint256]) # asset -> index
numAssets: public(uint256) # num assets

# yield
checkedYield: transient(HashMap[address, bool]) # asset -> checked

# constants
HUNDRED_PERCENT: constant(uint256) = 100_00 # 100.00%
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MAX_ASSETS: constant(uint256) = 10
MAX_LEGOS: constant(uint256) = 10
ERC721_RECEIVE_DATA: constant(Bytes[1024]) = b"UE721"
API_VERSION: constant(String[28]) = "0.1"

# max fees
MAX_SWAP_FEE: constant(uint256) = 5_00
MAX_REWARDS_FEE: constant(uint256) = 25_00
MAX_YIELD_FEE: constant(uint256) = 25_00

WETH: public(immutable(address))
ETH: public(immutable(address))


@deploy
def __init__(
    _wethAddr: address,
    _ethAddr: address,
    _walletConfig: address,
):
    assert empty(address) not in [_wethAddr, _ethAddr, _walletConfig] # dev: inv addr
    self.walletConfig = _walletConfig

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
    asset: address = _asset
    if asset == empty(address):
        asset = ETH
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.TRANSFER, False, [asset], [], _recipient)
    return self._transferFunds(_recipient, asset, _amount, True, True, ad)


@internal
def _transferFunds(
    _recipient: address,
    _asset: address,
    _amount: uint256,
    _shouldCheckRecipientLimits: bool,
    _shouldCheckManagerLimits: bool,
    _ad: ActionData,
) -> (uint256, uint256):
    amount: uint256 = 0

    # finalize amount
    if _asset == _ad.eth:
        amount = min(_amount, self.balance)
    else:
        amount = min(_amount, staticcall IERC20(_asset).balanceOf(self))
    assert amount != 0 # dev: no amt

    # get tx usd value
    txUsdValue: uint256 = self._updatePriceAndGetUsdValue(_asset, amount, _ad.inEjectMode, _ad.appraiser)

    # check recipient limits
    if _shouldCheckRecipientLimits:
        assert extcall WalletConfig(_ad.walletConfig).checkRecipientLimitsAndUpdateData(_recipient, txUsdValue, _asset, amount) # dev: recip

    # do the actual transfer
    if _asset == _ad.eth:
        send(_recipient, amount)
    else:
        assert extcall IERC20(_asset).transfer(_recipient, amount, default_return_value=True) # dev: xfer
    
    self._performPostActionTasks([_asset], txUsdValue, _ad, _shouldCheckManagerLimits)
    log FundsTransferred(
        asset = _asset,
        amount = amount,
        recipient = _recipient,
        signer = _ad.signer,
    )
    return amount, txUsdValue


# trusted call from wallet config (remove trial funds, migration)


@external
def transferFundsTrusted(
    _recipient: address,
    _asset: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _ad: ActionData = empty(ActionData),
) -> (uint256, uint256):
    walletConfig: address = self.walletConfig
    assert msg.sender == walletConfig # dev: perms

    ad: ActionData = _ad
    if ad.signer == empty(address):
        ad = staticcall WalletConfig(walletConfig).getActionDataBundle(0, walletConfig)

    asset: address = _asset
    if asset == empty(address):
        asset = ETH
    self._checkForYieldProfits(asset, ad)
    return self._transferFunds(_recipient, asset, _amount, False, False, ad)


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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.EARN_DEPOSIT, False, [_asset], [_legoId])
    return self._depositForYield(_asset, _vaultAddr, _amount, _extraAddr, _extraVal, _extraData, True, ad)


@internal
def _depositForYield(
    _asset: address,
    _vaultAddr: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _shouldPerformPostActionTasks: bool,
    _ad: ActionData,
) -> (uint256, address, uint256, uint256):
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, _ad.legoAddr) # doing approval here

    # deposit for yield
    assetAmount: uint256 = 0
    vaultToken: address = empty(address)
    vaultTokenAmountReceived: uint256 = 0
    txUsdValue: uint256 = 0
    assetAmount, vaultToken, vaultTokenAmountReceived, txUsdValue = extcall Lego(_ad.legoAddr).depositForYield(_asset, amount, _vaultAddr, _extraAddr, _extraVal, _extraData, self)
    self._resetApproval(_asset, _ad.legoAddr)

    # perform post action tasks
    if _shouldPerformPostActionTasks:
        self._performPostActionTasks([_asset, vaultToken], txUsdValue, _ad)

    log YieldDeposit(
        asset = _asset,
        assetAmount = assetAmount,
        vaultToken = vaultToken,
        vaultTokenAmount = vaultTokenAmountReceived,
        txUsdValue = txUsdValue,
        legoId = _ad.legoId,
        signer = _ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.EARN_WITHDRAW, False, [_vaultToken], [_legoId])
    return self._withdrawFromYield(_vaultToken, _amount, _extraAddr, _extraVal, _extraData, True, True, ad)


@internal
def _withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraAddr: address,
    _extraVal: uint256,
    _extraData: bytes32,
    _shouldPerformPostActionTasks: bool,
    _shouldCheckManagerLimits: bool,
    _ad: ActionData,
) -> (uint256, address, uint256, uint256):

    amount: uint256 = _amount
    if _vaultToken != empty(address):
        amount = self._getAmountAndApprove(_vaultToken, _amount, empty(address)) # not approving here

        # some vault tokens require max value approval (comp v3)
        assert extcall IERC20(_vaultToken).approve(_ad.legoAddr, max_value(uint256), default_return_value=True) # dev: appr

    # withdraw from yield
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    txUsdValue: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount, txUsdValue = extcall Lego(_ad.legoAddr).withdrawFromYield(_vaultToken, amount, _extraAddr, _extraVal, _extraData, self)

    if _vaultToken != empty(address):
        self._resetApproval(_vaultToken, _ad.legoAddr)

    # perform post action tasks
    if _shouldPerformPostActionTasks:
        self._performPostActionTasks([underlyingAsset, _vaultToken], txUsdValue, _ad, _shouldCheckManagerLimits)

    log YieldWithdrawal(
        vaultToken = _vaultToken,
        vaultTokenAmountBurned = vaultTokenAmountBurned,
        underlyingAsset = underlyingAsset,
        underlyingAmountReceived = underlyingAmount,
        txUsdValue = txUsdValue,
        legoId = _ad.legoId,
        signer = _ad.signer,
    )
    return vaultTokenAmountBurned, underlyingAsset, underlyingAmount, txUsdValue


# prepare payment (special withdraw from yield)


@external
def preparePayment(
    _legoId: uint256,
    _vaultToken: address,
    _vaultAmount: uint256 = max_value(uint256),
    _ad: ActionData = empty(ActionData),
) -> (uint256, address, uint256, uint256):
    walletConfig: address = self.walletConfig
    assert msg.sender == walletConfig # dev: perms

    ad: ActionData = _ad
    if ad.signer == empty(address):
        ad = staticcall WalletConfig(walletConfig).getActionDataBundle(_legoId, walletConfig)

    self._checkForYieldProfits(_vaultToken, ad)
    return self._withdrawFromYield(_vaultToken, _vaultAmount, empty(address), 0, empty(bytes32), True, False, ad)


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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.EARN_REBALANCE, False, [_fromVaultToken, _toVaultAddr], [_fromLegoId, _toLegoId])

    # withdraw
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    withdrawTxUsdValue: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount, withdrawTxUsdValue = self._withdrawFromYield(_fromVaultToken, _fromVaultAmount, _extraAddr, _extraVal, _extraData, False, True, ad)

    # deposit
    toVaultToken: address = empty(address)
    toVaultTokenAmountReceived: uint256 = 0
    depositTxUsdValue: uint256 = 0
    ad.legoId = _toLegoId
    ad.legoAddr = staticcall Registry(ad.legoBook).getAddr(_toLegoId)
    underlyingAmount, toVaultToken, toVaultTokenAmountReceived, depositTxUsdValue = self._depositForYield(underlyingAsset, _toVaultAddr, underlyingAmount, _extraAddr, _extraVal, _extraData, False, ad)

    maxUsdValue: uint256 = max(withdrawTxUsdValue, depositTxUsdValue)
    self._performPostActionTasks([underlyingAsset, _fromVaultToken, toVaultToken], maxUsdValue, ad)
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.SWAP, False, [tokenIn, tokenOut], legoIds)
    origAmountIn: uint256 = self._getAmountAndApprove(tokenIn, _instructions[0].amountIn, empty(address)) # not approving here

    amountIn: uint256 = origAmountIn
    lastTokenOut: address = empty(address)
    lastTokenOutAmount: uint256 = 0
    maxTxUsdValue: uint256 = 0

    # perform swaps
    for i: wi.SwapInstruction in _instructions:
        if lastTokenOut != empty(address):
            newTokenIn: address = i.tokenPath[0]
            assert lastTokenOut == newTokenIn # dev: path
            amountIn = min(lastTokenOutAmount, staticcall IERC20(newTokenIn).balanceOf(self))
        
        thisTxUsdValue: uint256 = 0
        lastTokenOut, lastTokenOutAmount, thisTxUsdValue = self._performSwapInstruction(amountIn, i, ad)
        maxTxUsdValue = max(maxTxUsdValue, thisTxUsdValue)

    # handle swap fee
    if lastTokenOut != empty(address):
        swapFee: uint256 = staticcall MissionControl(ad.missionControl).getSwapFee(self, tokenIn, lastTokenOut)
        if swapFee != 0 and lastTokenOutAmount != 0:
            self._payTransactionFee(lastTokenOut, lastTokenOutAmount, min(swapFee, MAX_SWAP_FEE), wi.ActionType.SWAP, ad.lootDistributor)

    self._performPostActionTasks([tokenIn, lastTokenOut], maxTxUsdValue, ad)
    log OverallSwapPerformed(
        tokenIn = tokenIn,
        tokenInAmount = origAmountIn,
        tokenOut = lastTokenOut,
        tokenOutAmount = lastTokenOutAmount,
        txUsdValue = maxTxUsdValue,
        numLegos = len(legoIds),
        numInstructions = len(_instructions),
        signer = ad.signer,
    )
    return tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, maxTxUsdValue


@internal
def _performSwapInstruction(
    _amountIn: uint256,
    _i: wi.SwapInstruction,
    _ad: ActionData,
) -> (address, uint256, uint256):
    legoAddr: address = staticcall Registry(_ad.legoBook).getAddr(_i.legoId)
    assert legoAddr != empty(address) # dev: lego

    # tokens
    tokenIn: address = _i.tokenPath[0]
    tokenOut: address = _i.tokenPath[len(_i.tokenPath) - 1]
    tokenInAmount: uint256 = 0
    tokenOutAmount: uint256 = 0
    txUsdValue: uint256 = 0

    assert extcall IERC20(tokenIn).approve(legoAddr, _amountIn, default_return_value=True) # dev: appr
    tokenInAmount, tokenOutAmount, txUsdValue = extcall Lego(legoAddr).swapTokens(_amountIn, _i.minAmountOut, _i.tokenPath, _i.poolPath, self)
    self._resetApproval(tokenIn, legoAddr)
    return tokenOut, tokenOutAmount, txUsdValue


@internal
def _validateAndGetSwapInfo(_instructions: DynArray[wi.SwapInstruction, MAX_SWAP_INSTRUCTIONS]) -> (address, address, DynArray[uint256, MAX_LEGOS]):
    numSwapInstructions: uint256 = len(_instructions)
    assert numSwapInstructions != 0 # dev: swaps

    # lego ids, make sure token paths are valid
    legoIds: DynArray[uint256, MAX_LEGOS] = []
    for i: wi.SwapInstruction in _instructions:
        assert len(i.tokenPath) >= 2 # dev: path
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

    assert empty(address) not in [tokenIn, tokenOut] # dev: path
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.MINT_REDEEM, False, [_tokenIn, _tokenOut], [_legoId])

    # mint or redeem asset
    tokenInAmount: uint256 = self._getAmountAndApprove(_tokenIn, _amountIn, ad.legoAddr) # doing approval here
    tokenOutAmount: uint256 = 0
    isPending: bool = False
    txUsdValue: uint256 = 0
    tokenInAmount, tokenOutAmount, isPending, txUsdValue = extcall Lego(ad.legoAddr).mintOrRedeemAsset(_tokenIn, _tokenOut, tokenInAmount, _minAmountOut, _extraAddr, _extraVal, _extraData, self)
    self._resetApproval(_tokenIn, ad.legoAddr)

    self._performPostActionTasks([_tokenIn, _tokenOut], txUsdValue, ad)
    log AssetMintedOrRedeemed(
        tokenIn = _tokenIn,
        tokenInAmount = tokenInAmount,
        tokenOut = _tokenOut,
        tokenOutAmount = tokenOutAmount,
        isPending = isPending,
        txUsdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.CONFIRM_MINT_REDEEM, False, [_tokenIn, _tokenOut], [_legoId])

    # confirm mint or redeem asset (if there is a delay on action)
    tokenOutAmount: uint256 = 0
    txUsdValue: uint256 = 0
    tokenOutAmount, txUsdValue = extcall Lego(ad.legoAddr).confirmMintOrRedeemAsset(_tokenIn, _tokenOut, _extraAddr, _extraVal, _extraData, self)

    self._performPostActionTasks([_tokenIn, _tokenOut], txUsdValue, ad)
    log AssetMintedOrRedeemedConfirmed(
        tokenIn = _tokenIn,
        tokenOut = _tokenOut,
        tokenOutAmount = tokenOutAmount,
        txUsdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ADD_COLLATERAL, True, [_asset], [_legoId])

    # add collateral
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, ad.legoAddr) # doing approval here
    amountDeposited: uint256 = 0
    txUsdValue: uint256 = 0
    amountDeposited, txUsdValue = extcall Lego(ad.legoAddr).addCollateral(_asset, amount, _extraAddr, _extraVal, _extraData, self)
    self._resetApproval(_asset, ad.legoAddr)

    self._performPostActionTasks([_asset], txUsdValue, ad)
    log CollateralAdded(
        asset = _asset,
        amountDeposited = amountDeposited,
        txUsdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REMOVE_COLLATERAL, True, [_asset], [_legoId])

    # remove collateral
    amountRemoved: uint256 = 0
    txUsdValue: uint256 = 0   
    amountRemoved, txUsdValue = extcall Lego(ad.legoAddr).removeCollateral(_asset, _amount, _extraAddr, _extraVal, _extraData, self)

    self._performPostActionTasks([_asset], txUsdValue, ad)
    log CollateralRemoved(
        asset = _asset,
        amountRemoved = amountRemoved,
        txUsdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.BORROW, True, [_borrowAsset], [_legoId])

    # borrow
    borrowAmount: uint256 = 0
    txUsdValue: uint256 = 0
    borrowAmount, txUsdValue = extcall Lego(ad.legoAddr).borrow(_borrowAsset, _amount, _extraAddr, _extraVal, _extraData, self)

    self._performPostActionTasks([_borrowAsset], txUsdValue, ad)
    log NewBorrow(
        borrowAsset = _borrowAsset,
        borrowAmount = borrowAmount,
        txUsdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REPAY_DEBT, True, [_paymentAsset], [_legoId])

    # repay debt
    amount: uint256 = self._getAmountAndApprove(_paymentAsset, _paymentAmount, ad.legoAddr) # doing approval here
    repaidAmount: uint256 = 0
    txUsdValue: uint256 = 0
    repaidAmount, txUsdValue = extcall Lego(ad.legoAddr).repayDebt(_paymentAsset, amount, _extraAddr, _extraVal, _extraData, self)
    self._resetApproval(_paymentAsset, ad.legoAddr)

    self._performPostActionTasks([_paymentAsset], txUsdValue, ad)
    log DebtRepayment(
        paymentAsset = _paymentAsset,
        repaidAmount = repaidAmount,
        txUsdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REWARDS, True, [_rewardToken], [_legoId])

    # claim rewards
    rewardAmount: uint256 = 0
    txUsdValue: uint256 = 0
    rewardAmount, txUsdValue = extcall Lego(ad.legoAddr).claimRewards(self, _rewardToken, _rewardAmount, _extraAddr, _extraVal, _extraData)

    # handle rewards fee
    if _rewardToken != empty(address):
        rewardsFee: uint256 = staticcall MissionControl(ad.missionControl).getRewardsFee(self, _rewardToken)
        if rewardsFee != 0 and rewardAmount != 0:
            self._payTransactionFee(_rewardToken, rewardAmount, min(rewardsFee, MAX_REWARDS_FEE), wi.ActionType.REWARDS, ad.lootDistributor)

    self._performPostActionTasks([_rewardToken], txUsdValue, ad)
    log RewardsClaimed(
        rewardToken = _rewardToken,
        rewardAmount = rewardAmount,
        txUsdValue = txUsdValue,
        legoId = ad.legoId,
        legoAddr = ad.legoAddr,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ETH_TO_WETH, False, [eth, weth], [], empty(address))

    # convert eth to weth
    amount: uint256 = min(_amount, self.balance)
    assert amount != 0 # dev: no amt
    extcall WethContract(weth).deposit(value=amount)

    txUsdValue: uint256 = self._updatePriceAndGetUsdValue(weth, amount, ad.inEjectMode, ad.appraiser)
    self._performPostActionTasks([eth, weth], txUsdValue, ad)
    log EthWrapped(
        amount = amount,
        paidEth = msg.value,
        txUsdValue = txUsdValue,
        signer = ad.signer,
    )
    return amount, txUsdValue


# weth -> eth


@nonreentrant
@external
def convertWethToEth(_amount: uint256 = max_value(uint256)) -> (uint256, uint256):
    weth: address = WETH
    eth: address = ETH
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.WETH_TO_ETH, False, [weth, eth], [], empty(address))

    # convert weth to eth
    amount: uint256 = self._getAmountAndApprove(weth, _amount, empty(address)) # nothing to approve
    extcall WethContract(weth).withdraw(amount)

    txUsdValue: uint256 = self._updatePriceAndGetUsdValue(weth, amount, ad.inEjectMode, ad.appraiser)
    self._performPostActionTasks([weth, eth], txUsdValue, ad)
    log WethUnwrapped(
        amount = amount,
        txUsdValue = txUsdValue,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ADD_LIQ, False, [_tokenA, _tokenB], [_legoId])

    # token approvals
    amountA: uint256 = self._getAmountAndApprove(_tokenA, _amountA, ad.legoAddr)
    amountB: uint256 = self._getAmountAndApprove(_tokenB, _amountB, ad.legoAddr)

    # add liquidity via lego partner
    lpToken: address = empty(address)
    lpAmountReceived: uint256 = 0
    addedTokenA: uint256 = 0
    addedTokenB: uint256 = 0
    txUsdValue: uint256 = 0
    lpToken, lpAmountReceived, addedTokenA, addedTokenB, txUsdValue = extcall Lego(ad.legoAddr).addLiquidity(_pool, _tokenA, _tokenB, amountA, amountB, _minAmountA, _minAmountB, _minLpAmount, _extraAddr, _extraVal, _extraData, self)

    # remove approvals
    if amountA != 0:
        self._resetApproval(_tokenA, ad.legoAddr)
    if amountB != 0:
        self._resetApproval(_tokenB, ad.legoAddr)

    self._performPostActionTasks([_tokenA, _tokenB, lpToken], txUsdValue, ad)
    log LiquidityAdded(
        pool = _pool,
        tokenA = _tokenA,
        amountA = addedTokenA,
        tokenB = _tokenB,
        amountB = addedTokenB,
        txUsdValue = txUsdValue,
        lpToken = lpToken,
        lpAmountReceived = lpAmountReceived,
        legoId = ad.legoId,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REMOVE_LIQ, False, [_tokenA, _tokenB], [_legoId])

    # remove liquidity via lego partner
    amountAReceived: uint256 = 0
    amountBReceived: uint256 = 0
    lpAmountBurned: uint256 = 0
    txUsdValue: uint256 = 0
    lpAmount: uint256 = self._getAmountAndApprove(_lpToken, _lpAmount, ad.legoAddr)
    amountAReceived, amountBReceived, lpAmountBurned, txUsdValue = extcall Lego(ad.legoAddr).removeLiquidity(_pool, _tokenA, _tokenB, _lpToken, lpAmount, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, self)
    self._resetApproval(_lpToken, ad.legoAddr)

    self._performPostActionTasks([_tokenA, _tokenB, _lpToken], txUsdValue, ad)
    log LiquidityRemoved(
        pool = _pool,
        tokenA = _tokenA,
        amountAReceived = amountAReceived,
        tokenB = _tokenB,
        amountBReceived = amountBReceived,
        txUsdValue = txUsdValue,
        lpToken = _lpToken,
        lpAmountBurned = lpAmountBurned,
        legoId = ad.legoId,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.ADD_LIQ_CONC, False, [_tokenA, _tokenB], [_legoId])

    # token approvals
    amountA: uint256 = self._getAmountAndApprove(_tokenA, _amountA, ad.legoAddr)
    amountB: uint256 = self._getAmountAndApprove(_tokenB, _amountB, ad.legoAddr)

    # transfer nft to lego (if applicable)
    hasNftLiqPosition: bool = _nftAddr != empty(address) and _nftTokenId != 0
    if hasNftLiqPosition:
        extcall IERC721(_nftAddr).safeTransferFrom(self, ad.legoAddr, _nftTokenId, ERC721_RECEIVE_DATA)

    # add liquidity via lego partner
    liqAdded: uint256 = 0
    addedTokenA: uint256 = 0
    addedTokenB: uint256 = 0
    nftTokenId: uint256 = 0
    txUsdValue: uint256 = 0
    liqAdded, addedTokenA, addedTokenB, nftTokenId, txUsdValue = extcall Lego(ad.legoAddr).addLiquidityConcentrated(_nftTokenId, _pool, _tokenA, _tokenB, _tickLower, _tickUpper, amountA, amountB, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, self)

    # make sure nft is back
    assert staticcall IERC721(_nftAddr).ownerOf(nftTokenId) == self # dev: nft not returned

    # remove approvals
    if amountA != 0:
        self._resetApproval(_tokenA, ad.legoAddr)
    if amountB != 0:
        self._resetApproval(_tokenB, ad.legoAddr)

    self._performPostActionTasks([_tokenA, _tokenB], txUsdValue, ad)
    log ConcentratedLiquidityAdded(
        nftTokenId = nftTokenId,
        pool = _pool,
        tokenA = _tokenA,
        amountA = addedTokenA,
        tokenB = _tokenB,
        amountB = addedTokenB,
        txUsdValue = txUsdValue,
        liqAdded = liqAdded,
        legoId = ad.legoId,
        signer = ad.signer,
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
    ad: ActionData = self._performPreActionTasks(msg.sender, wi.ActionType.REMOVE_LIQ_CONC, False, [_tokenA, _tokenB], [_legoId])

    # must have nft liq position
    assert _nftAddr != empty(address) # dev: invalid nft addr
    assert _nftTokenId != 0 # dev: invalid nft token id
    extcall IERC721(_nftAddr).safeTransferFrom(self, ad.legoAddr, _nftTokenId, ERC721_RECEIVE_DATA)

    # remove liquidity via lego partner
    amountAReceived: uint256 = 0
    amountBReceived: uint256 = 0
    liqRemoved: uint256 = 0
    isDepleted: bool = False
    txUsdValue: uint256 = 0
    amountAReceived, amountBReceived, liqRemoved, isDepleted, txUsdValue = extcall Lego(ad.legoAddr).removeLiquidityConcentrated(_nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraAddr, _extraVal, _extraData, self)

    # validate the nft came back (if not depleted)
    if not isDepleted:
        assert staticcall IERC721(_nftAddr).ownerOf(_nftTokenId) == self # dev: nft not returned

    self._performPostActionTasks([_tokenA, _tokenB], txUsdValue, ad)
    log ConcentratedLiquidityRemoved(
        nftTokenId = _nftTokenId,
        pool = _pool,
        tokenA = _tokenA,
        amountAReceived = amountAReceived,
        tokenB = _tokenB,
        amountBReceived = amountBReceived,
        txUsdValue = txUsdValue,
        liqRemoved = liqRemoved,
        legoId = ad.legoId,
        signer = ad.signer,
    )
    return amountAReceived, amountBReceived, liqRemoved, txUsdValue


#################
# House Keeping #
#################


# pre action tasks


@internal
def _performPreActionTasks(
    _signer: address,
    _action: wi.ActionType,
    _shouldCheckAccess: bool,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> ActionData:
    legoId: uint256 = 0
    if len(_legoIds) != 0:
        legoId = _legoIds[0]
    ad: ActionData = staticcall WalletConfig(self.walletConfig).checkSignerPermissionsAndGetBundle(_signer, _action, _assets, _legoIds, _transferRecipient)

    # cannot perform any actions if wallet is frozen
    assert not ad.isFrozen # dev: frozen wallet

    # eject mode can only do transfer and eth conversions
    if ad.inEjectMode:
        assert _action in (wi.ActionType.TRANSFER | wi.ActionType.ETH_TO_WETH | wi.ActionType.WETH_TO_ETH) # dev: invalid action in eject mode
        return ad

    # make sure lego can perform the action
    if _shouldCheckAccess:
        self._checkLegoAccessForAction(ad.legoAddr, _action)

    # check for yield to realize
    checkedAssets: DynArray[address, MAX_ASSETS] = []
    for a: address in _assets:
        if a in checkedAssets:
            continue
        self._checkForYieldProfits(a, ad)
        checkedAssets.append(a)

    return ad


# post action tasks


@internal
def _performPostActionTasks(
    _assets: DynArray[address, MAX_ASSETS],
    _txUsdValue: uint256,
    _ad: ActionData,
    _shouldCheckManagerLimits: bool = True,
):
    # first, check and update manager caps
    if _shouldCheckManagerLimits:
        assert extcall WalletConfig(_ad.walletConfig).checkManagerUsdLimitsAndUpdateData(_ad.signer, _txUsdValue) # dev: manager limits not allowed

    # update each asset that was touched
    newTotalUsdValue: uint256 = _ad.lastTotalUsdValue
    for a: address in _assets:
        newTotalUsdValue = self._updateAssetData(a, newTotalUsdValue, _ad.inEjectMode, _ad.appraiser, _ad.eth)

    # update points + check trial funds
    if not _ad.inEjectMode:
        extcall Backpack(_ad.backpack).performPostActionTasks(newTotalUsdValue, _ad.walletConfig, _ad.missionControl, _ad.legoBook, _ad.appraiser)


##############
# Asset Data #
##############


# from wallet backpack


@external
def updateAssetData(
    _legoId: uint256,
    _asset: address,
    _shouldCheckYield: bool,
    _totalUsdValue: uint256,
    _ad: ActionData = empty(ActionData),
) -> uint256:
    walletConfig: address = self.walletConfig
    assert msg.sender == walletConfig # dev: perms

    ad: ActionData = _ad
    if ad.signer == empty(address):
        ad = staticcall WalletConfig(walletConfig).getActionDataBundle(_legoId, walletConfig)

    # check for yield
    if _shouldCheckYield and not ad.inEjectMode:
        self._checkForYieldProfits(_asset, ad)

    # update asset data
    return self._updateAssetData(_asset, _totalUsdValue, ad.inEjectMode, ad.appraiser, ad.eth)


# update asset data


@internal
def _updateAssetData(
    _asset: address,
    _newTotalUsdValue: uint256,
    _inEjectMode: bool,
    _appraiser: address,
    _eth: address,
) -> uint256:
    if _asset == empty(address):
        return _newTotalUsdValue

    data: WalletAssetData = self.assetData[_asset]
    newTotalUsdValue: uint256 = _newTotalUsdValue - min(data.usdValue, _newTotalUsdValue)

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
        return newTotalUsdValue

    # update usd value
    data.usdValue = 0
    data.isYieldAsset = False
    if not _inEjectMode:
        data.usdValue, data.isYieldAsset = extcall Appraiser(_appraiser).updatePriceAndGetUsdValueAndIsYieldAsset(_asset, currentBalance)
        newTotalUsdValue += data.usdValue

    # save data
    data.assetBalance = currentBalance
    self.assetData[_asset] = data

    # register asset (if necessary)
    if self.indexOfAsset[_asset] == 0:
        self._registerAsset(_asset)

    return newTotalUsdValue


# register asset


@internal
def _registerAsset(_asset: address):
    aid: uint256 = self.numAssets
    if aid == 0:
        aid = 1 # not using 0 index
    self.assets[aid] = _asset
    self.indexOfAsset[_asset] = aid
    self.numAssets = aid + 1


# deregister asset


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
def _checkForYieldProfits(_asset: address, _ad: ActionData):
    if _asset in [empty(address), _ad.eth, _ad.weth]:
        return

    # skip if already checked
    if self.checkedYield[_asset]:
        return

    # nothing to do here (nothing saved, not a yield asset)
    data: WalletAssetData = self.assetData[_asset]
    if data.assetBalance == 0 or not data.isYieldAsset:
        return

    # no balance, nothing to do here
    currentBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    if currentBalance == 0:
        return

    # calculate yield profits
    yieldProfit: uint256 = 0
    feeRatio: uint256 = 0
    data.lastYieldPrice, yieldProfit, feeRatio = extcall Backpack(_ad.backpack).calculateYieldProfits(_asset, currentBalance, data.assetBalance, data.lastYieldPrice, _ad.missionControl, _ad.legoBook, _ad.appraiser)

    # only save if backpack returns a price
    if data.lastYieldPrice != 0:
        self.assetData[_asset] = data

    # pay yield fee
    self._payYieldFee(_asset, yieldProfit, min(feeRatio, MAX_YIELD_FEE), _ad.lootDistributor)

    # mark as checked
    self.checkedYield[_asset] = True


#############
# Utilities #
#############


# pay transaction fees (swap / rewards)


@internal
def _payTransactionFee(
    _asset: address,
    _transactionValue: uint256,
    _feeRatio: uint256,
    _action: wi.ActionType,
    _lootDistributor: address,
):
    feeAmount: uint256 = _transactionValue * _feeRatio // HUNDRED_PERCENT
    if _lootDistributor != empty(address) and feeAmount != 0:
        assert extcall IERC20(_asset).approve(_lootDistributor, feeAmount, default_return_value=True) # dev: appr
        extcall LootDistributor(_lootDistributor).addLootFromSwapOrRewards(_asset, feeAmount, _action)
        self._resetApproval(_asset, _lootDistributor)


# pay fees


@internal
def _payYieldFee(
    _asset: address,
    _totalYieldAmount: uint256,
    _feeRatio: uint256,
    _lootDistributor: address,
):
    if _lootDistributor == empty(address):
        return

    feeAmount: uint256 = _totalYieldAmount * _feeRatio // HUNDRED_PERCENT
    if feeAmount != 0:
        assert extcall IERC20(_asset).transfer(_lootDistributor, feeAmount, default_return_value=True) # dev: xfer

    # notify loot distributor
    if feeAmount != 0 or _totalYieldAmount != 0:
        extcall LootDistributor(_lootDistributor).addLootFromYieldProfit(_asset, feeAmount, _totalYieldAmount)


# update price and get usd value


@internal
def _updatePriceAndGetUsdValue(
    _asset: address,
    _amount: uint256,
    _inEjectMode: bool,
    _appraiser: address,
) -> uint256:
    if _inEjectMode:
        return 0
    return extcall Appraiser(_appraiser).updatePriceAndGetUsdValue(_asset, _amount)


# approve


@internal
def _getAmountAndApprove(_token: address, _amount: uint256, _legoAddr: address) -> uint256:
    if _amount == 0:
        return 0
    amount: uint256 = min(_amount, staticcall IERC20(_token).balanceOf(self))
    assert amount != 0 # dev: no balance for _token
    if _legoAddr != empty(address):
        assert extcall IERC20(_token).approve(_legoAddr, amount, default_return_value=True) # dev: appr
    return amount


# reset approval


@internal
def _resetApproval(_token: address, _legoAddr: address):
    if _legoAddr != empty(address):
        assert extcall IERC20(_token).approve(_legoAddr, 0, default_return_value=True) # dev: appr


# recover nft


@external
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address):
    assert msg.sender == self.walletConfig # dev: perms
    extcall IERC721(_collection).safeTransferFrom(self, _recipient, _nftTokenId)


# allow lego to perform action


@internal
def _checkLegoAccessForAction(_legoAddr: address, _action: wi.ActionType):
    if _legoAddr == empty(address):
        return

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