#    ┳┳     
#    ┃┃┏┏┓┏┓
#    ┗┛┛┗ ┛ 
#               .---.             ,--,    ,--,                 ___     
#              /. ./|           ,--.'|  ,--.'|               ,--.'|_   
#          .--'.  ' ;           |  | :  |  | :               |  | :,'  
#         /__./ \ : |           :  : '  :  : '               :  : ' :  
#     .--'.  '   \' .  ,--.--.  |  ' |  |  ' |      ,---.  .;__,'  /   
#    /___/ \ |    ' ' /       \ '  | |  '  | |     /     \ |  |   |    
#    ;   \  \;      :.--.  .-. ||  | :  |  | :    /    /  |:__,'| :    
#     \   ;  `      | \__\/: . .'  : |__'  : |__ .    ' / |  '  : |__  
#      .   \    .\  ; ," .--.; ||  | '.'|  | '.'|'   ;   /|  |  | '.'| 
#       \   \   ' \ |/  /  ,.  |;  :    ;  :    ;'   |  / |  ;  :    ; 
#        :   '  |--";  :   .'   \  ,   /|  ,   / |   :    |  |  ,   /  
#         \   \ ;   |  ,     .-./---`-'  ---`-'   \   \  /    ---`-'   
#          '---"     `--`---'                      `----'              
#     ╔══════════════════════════════════════════╗
#     ║  ** User Wallet **                       ║
#     ║  Handles all user wallet functionality   ║
#     ╚══════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

implements: wi
from interfaces import Wallet as wi
from interfaces import LegoPartner as Lego
from interfaces import WalletStructs as ws

from ethereum.ercs import IERC20
from ethereum.ercs import IERC721

interface Appraiser:
    def calculateYieldProfits(_asset: address, _currentBalance: uint256, _lastBalance: uint256, _lastPricePerShare: uint256, _missionControl: address, _legoBook: address) -> (uint256, uint256, uint256): nonpayable
    def updatePriceAndGetUsdValueAndIsYieldAsset(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> (uint256, bool): nonpayable
    def updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _missionControl: address = empty(address), _legoBook: address = empty(address)) -> uint256: nonpayable
    def lastPricePerShare(_asset: address) -> uint256: view

interface WalletConfig:
    def checkSignerPermissionsAndGetBundle(_signer: address, _action: ws.ActionType, _assets: DynArray[address, MAX_ASSETS] = [], _legoIds: DynArray[uint256, MAX_LEGOS] = [], _transferRecipient: address = empty(address)) -> ws.ActionData: view
    def checkRecipientLimitsAndUpdateData(_recipient: address, _txUsdValue: uint256, _asset: address, _amount: uint256) -> bool: nonpayable
    def validateCheque(_recipient: address, _asset: address, _amount: uint256, _txUsdValue: uint256, _signer: address) -> bool: nonpayable
    def checkManagerUsdLimitsAndUpdateData(_manager: address, _txUsdValue: uint256) -> bool: nonpayable
    def getActionDataBundle(_legoId: uint256, _signer: address) -> ws.ActionData: view

interface LootDistributor:
    def addLootFromYieldProfit(_asset: address, _feeAmount: uint256, _yieldRealized: uint256, _missionControl: address = empty(address), _appraiser: address = empty(address), _legoBook: address = empty(address)): nonpayable
    def addLootFromSwapOrRewards(_asset: address, _amount: uint256, _action: ws.ActionType, _missionControl: address = empty(address)): nonpayable
    def getSwapFee(_user: address, _tokenIn: address, _tokenOut: address, _missionControl: address = empty(address)) -> uint256: view
    def getRewardsFee(_user: address, _asset: address, _missionControl: address = empty(address)) -> uint256: view
    def updateDepositPointsWithNewValue(_user: address, _newUsdValue: uint256): nonpayable

interface WethContract:
    def withdraw(_amount: uint256): nonpayable
    def deposit(): payable

interface Registry:
    def getAddr(_regId: uint256) -> address: view

event WalletAction:
    op: uint8 
    asset1: indexed(address)
    asset2: indexed(address)
    amount1: uint256
    amount2: uint256
    usdValue: uint256
    legoId: uint256
    signer: indexed(address)

event WalletActionExt:
    op: uint8
    asset1: indexed(address)
    asset2: indexed(address)
    tokenId: uint256
    amount1: uint256
    amount2: uint256
    usdValue: uint256
    extra: uint256

# data 
walletConfig: public(address)

# asset data
assetData: public(HashMap[address, ws.WalletAssetData]) # asset -> data
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
MAX_PROOFS: constant(uint256) = 25
ERC721_RECEIVE_DATA: constant(Bytes[1024]) = b"UE721"
API_VERSION: constant(String[28]) = "0.1.0"

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
    self.numAssets = 1

    WETH = _wethAddr
    ETH = _ethAddr


@view
@external
def onERC721Received(_operator: address, _owner: address, _tokenId: uint256, _data: Bytes[1024]) -> bytes4:
    # must implement method for safe NFT transfers
    return method_id("onERC721Received(address,address,uint256,bytes)", output_type = bytes4)


@payable
@external
def __default__():
    pass


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
    _isCheque: bool = False,
    _isSpecialTx: bool = False,
) -> (uint256, uint256):
    asset: address = empty(address)
    ad: ws.ActionData = empty(ws.ActionData)
    asset, ad = self._validateCanTransfer(msg.sender, _recipient, _asset, _isSpecialTx, _isCheque)

    # finalize amount
    amount: uint256 = 0
    if asset == ad.eth:
        amount = min(_amount, self.balance)
    else:
        amount = min(_amount, staticcall IERC20(asset).balanceOf(self))
    assert amount != 0 # dev: no amt

    # get usd value
    txUsdValue: uint256 = self._updatePriceAndGetUsdValue(asset, amount, ad)

    # make sure recipient can actually receive funds
    if not _isSpecialTx:
        if _isCheque:
            assert extcall WalletConfig(ad.walletConfig).validateCheque(_recipient, asset, amount, txUsdValue, ad.signer) # dev: cheque invalid
        else:
            assert extcall WalletConfig(ad.walletConfig).checkRecipientLimitsAndUpdateData(_recipient, txUsdValue, asset, amount) # dev: recipient limits exceeded

    # do actual transfer
    if asset == ad.eth:
        send(_recipient, amount)
    else:
        assert extcall IERC20(asset).transfer(_recipient, amount, default_return_value = True) # dev: xfer
    
    self._performPostActionTasks([asset], txUsdValue, ad, _isSpecialTx)
    log WalletAction(
        op = 1,
        asset1 = asset,
        asset2 = _recipient,
        amount1 = amount,
        amount2 = 0,
        usdValue = txUsdValue,
        legoId = 0,
        signer = ad.signer,
    )
    return amount, txUsdValue


@internal
def _validateCanTransfer(
    _signer: address,
    _recipient: address,
    _asset: address,
    _isSpecialTx: bool,
    _isCheque: bool,
) -> (address, ws.ActionData):
    ad: ws.ActionData = empty(ws.ActionData)
    assert _recipient != empty(address) # dev: inv recipient

    # finalize asset
    asset: address = _asset
    if asset == empty(address):
        asset = ETH

    # only wallet config can do trusted txs (migration, clawback trial funds)
    if _isSpecialTx:
        walletConfig: address = self.walletConfig
        assert _signer == walletConfig # dev: perms
        ad = staticcall WalletConfig(walletConfig).getActionDataBundle(0, _signer)
        self._checkForYieldProfits(asset, ad)

    # normal transaction
    else:
        action: ws.ActionType = ws.ActionType.TRANSFER
        if _isCheque:
            action = ws.ActionType.PAY_CHEQUE
        ad = self._performPreActionTasks(_signer, action, False, [asset], [], _recipient)

    return asset, ad


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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.EARN_DEPOSIT, False, [_asset], [_legoId])
    return self._depositForYield(_asset, _vaultAddr, _amount, _extraData, True, True, ad)


@internal
def _depositForYield(
    _asset: address,
    _vaultAddr: address,
    _amount: uint256,
    _extraData: bytes32,
    _shouldPerformPostActionTasks: bool,
    _shouldGenerateEvent: bool,
    _ad: ws.ActionData,
) -> (uint256, address, uint256, uint256):
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, _ad.legoAddr) # doing approval here

    # deposit for yield
    assetAmount: uint256 = 0
    vaultToken: address = empty(address)
    vaultTokenAmountReceived: uint256 = 0
    txUsdValue: uint256 = 0
    assetAmount, vaultToken, vaultTokenAmountReceived, txUsdValue = extcall Lego(_ad.legoAddr).depositForYield(_asset, amount, _vaultAddr, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
    self._resetApproval(_asset, _ad.legoAddr)

    # perform post action tasks
    if _shouldPerformPostActionTasks:
        self._performPostActionTasks([_asset, vaultToken], txUsdValue, _ad)

    if _shouldGenerateEvent:
        log WalletAction(
            op = 10,
            asset1 = _asset,
            asset2 = vaultToken,
            amount1 = assetAmount,
            amount2 = vaultTokenAmountReceived,
            usdValue = txUsdValue,
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
    _extraData: bytes32 = empty(bytes32),
    _isSpecialTx: bool = False,
) -> (uint256, address, uint256, uint256):
    ad: ws.ActionData = empty(ws.ActionData)

    # prepares payment (might be clawback trial funds, or some other payment/transfer/cheque)
    if _isSpecialTx:
        walletConfig: address = self.walletConfig
        assert msg.sender == walletConfig # dev: perms

        ad = staticcall WalletConfig(walletConfig).getActionDataBundle(_legoId, msg.sender)
        self._checkForYieldProfits(_vaultToken, ad)

    # normal transaction
    else:
        ad = self._performPreActionTasks(msg.sender, ws.ActionType.EARN_WITHDRAW, False, [_vaultToken], [_legoId])

    return self._withdrawFromYield(_vaultToken, _amount, _extraData, True, True, _isSpecialTx, ad)


@internal
def _withdrawFromYield(
    _vaultToken: address,
    _amount: uint256,
    _extraData: bytes32,
    _shouldPerformPostActionTasks: bool,
    _shouldGenerateEvent: bool,
    _isSpecialTx: bool,
    _ad: ws.ActionData,
) -> (uint256, address, uint256, uint256):
    amount: uint256 = _amount
    if _vaultToken != empty(address):
        amount = self._getAmountAndApprove(_vaultToken, _amount, empty(address)) # not approving here

        # some vault tokens require max value approval (comp v3)
        assert extcall IERC20(_vaultToken).approve(_ad.legoAddr, max_value(uint256), default_return_value = True) # dev: appr

    # withdraw from yield
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    txUsdValue: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount, txUsdValue = extcall Lego(_ad.legoAddr).withdrawFromYield(_vaultToken, amount, _extraData, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))

    if _vaultToken != empty(address):
        self._resetApproval(_vaultToken, _ad.legoAddr)

    # perform post action tasks
    if _shouldPerformPostActionTasks:
        self._performPostActionTasks([underlyingAsset, _vaultToken], txUsdValue, _ad, _isSpecialTx)

    if _shouldGenerateEvent:
        log WalletAction(
            op = 11,
            asset1 = _vaultToken,
            asset2 = underlyingAsset,
            amount1 = vaultTokenAmountBurned,
            amount2 = underlyingAmount,
            usdValue = txUsdValue,
            legoId = _ad.legoId,
            signer = _ad.signer,
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, address, uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.EARN_REBALANCE, False, [_fromVaultToken, _toVaultAddr], [_fromLegoId, _toLegoId])

    # withdraw
    vaultTokenAmountBurned: uint256 = 0
    underlyingAsset: address = empty(address)
    underlyingAmount: uint256 = 0
    withdrawTxUsdValue: uint256 = 0
    vaultTokenAmountBurned, underlyingAsset, underlyingAmount, withdrawTxUsdValue = self._withdrawFromYield(_fromVaultToken, _fromVaultAmount, _extraData, False, False, False, ad)

    # deposit
    toVaultToken: address = empty(address)
    toVaultTokenAmountReceived: uint256 = 0
    depositTxUsdValue: uint256 = 0
    ad.legoId = _toLegoId
    ad.legoAddr = staticcall Registry(ad.legoBook).getAddr(_toLegoId)
    underlyingAmount, toVaultToken, toVaultTokenAmountReceived, depositTxUsdValue = self._depositForYield(underlyingAsset, _toVaultAddr, underlyingAmount, _extraData, False, False, ad)

    maxUsdValue: uint256 = max(withdrawTxUsdValue, depositTxUsdValue)
    self._performPostActionTasks([underlyingAsset, _fromVaultToken, toVaultToken], maxUsdValue, ad)
    log WalletAction(
        op = 12,
        asset1 = _fromVaultToken,
        asset2 = toVaultToken,
        amount1 = vaultTokenAmountBurned,
        amount2 = toVaultTokenAmountReceived,
        usdValue = maxUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
    )
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
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.SWAP, False, [tokenIn, tokenOut], legoIds)
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

    assert lastTokenOutAmount != 0 # dev: no output amount
    assert lastTokenOut == tokenOut # dev: must swap into token out

    # handle swap fee
    if lastTokenOut != empty(address):
        swapFee: uint256 = staticcall LootDistributor(ad.lootDistributor).getSwapFee(self, tokenIn, lastTokenOut, ad.missionControl)
        if swapFee != 0 and lastTokenOutAmount != 0:
            swapFee = self._payTransactionFee(lastTokenOut, lastTokenOutAmount, min(swapFee, 5_00), ws.ActionType.SWAP, ad.lootDistributor, ad.missionControl)
            lastTokenOutAmount -= swapFee

    self._performPostActionTasks([tokenIn, lastTokenOut], maxTxUsdValue, ad)
    log WalletAction(
        op = 20,
        asset1 = tokenIn,
        asset2 = lastTokenOut,
        amount1 = origAmountIn,
        amount2 = lastTokenOutAmount,
        usdValue = maxTxUsdValue,
        legoId = ad.legoId, # using just the first lego used
        signer = ad.signer,
    )
    return tokenIn, origAmountIn, lastTokenOut, lastTokenOutAmount, maxTxUsdValue


@internal
def _performSwapInstruction(
    _amountIn: uint256,
    _i: wi.SwapInstruction,
    _ad: ws.ActionData,
) -> (address, uint256, uint256):
    legoAddr: address = staticcall Registry(_ad.legoBook).getAddr(_i.legoId)
    assert legoAddr != empty(address) # dev: lego

    # tokens
    tokenIn: address = _i.tokenPath[0]
    tokenOut: address = _i.tokenPath[len(_i.tokenPath) - 1]
    tokenInAmount: uint256 = 0
    tokenOutAmount: uint256 = 0
    txUsdValue: uint256 = 0

    assert extcall IERC20(tokenIn).approve(legoAddr, _amountIn, default_return_value = True) # dev: appr
    tokenInAmount, tokenOutAmount, txUsdValue = extcall Lego(legoAddr).swapTokens(_amountIn, _i.minAmountOut, _i.tokenPath, _i.poolPath, self, self._packMiniAddys(_ad.ledger, _ad.missionControl, _ad.legoBook, _ad.appraiser))
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, bool, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.MINT_REDEEM, False, [_tokenIn, _tokenOut], [_legoId])

    # mint or redeem asset
    tokenInAmount: uint256 = self._getAmountAndApprove(_tokenIn, _amountIn, ad.legoAddr) # doing approval here
    tokenOutAmount: uint256 = 0
    isPending: bool = False
    txUsdValue: uint256 = 0
    tokenInAmount, tokenOutAmount, isPending, txUsdValue = extcall Lego(ad.legoAddr).mintOrRedeemAsset(_tokenIn, _tokenOut, tokenInAmount, _minAmountOut, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))
    self._resetApproval(_tokenIn, ad.legoAddr)

    self._performPostActionTasks([_tokenIn, _tokenOut], txUsdValue, ad)
    log WalletAction(
        op = 21,
        asset1 = _tokenIn,
        asset2 = _tokenOut,
        amount1 = tokenInAmount,
        amount2 = tokenOutAmount,
        usdValue = txUsdValue,
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.CONFIRM_MINT_REDEEM, False, [_tokenIn, _tokenOut], [_legoId])

    # confirm mint or redeem asset (if there is a delay on action)
    tokenOutAmount: uint256 = 0
    txUsdValue: uint256 = 0
    tokenOutAmount, txUsdValue = extcall Lego(ad.legoAddr).confirmMintOrRedeemAsset(_tokenIn, _tokenOut, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

    self._performPostActionTasks([_tokenIn, _tokenOut], txUsdValue, ad)
    log WalletAction(
        op = 22,
        asset1 = _tokenIn,
        asset2 = _tokenOut,
        amount1 = 0,
        amount2 = tokenOutAmount,
        usdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
    )
    return tokenOutAmount, txUsdValue


###################
# Debt Management #
###################


# NOTE: these functions assume there is no vault token involved (i.e. Ripe Protocol)
# You can also use `depositForYield` and `withdrawFromYield` if a vault token is involved


# add collateral


@nonreentrant
@external
def addCollateral(
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.ADD_COLLATERAL, True, [_asset], [_legoId])

    # some vault tokens require max value approval (comp v3)
    assert extcall IERC20(_asset).approve(ad.legoAddr, max_value(uint256), default_return_value = True) # dev: appr

    # add collateral
    amount: uint256 = self._getAmountAndApprove(_asset, _amount, empty(address)) # not approving here
    amountDeposited: uint256 = 0
    txUsdValue: uint256 = 0
    amountDeposited, txUsdValue = extcall Lego(ad.legoAddr).addCollateral(_asset, amount, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))
    self._resetApproval(_asset, ad.legoAddr)

    self._performPostActionTasks([_asset], txUsdValue, ad)
    log WalletAction(
        op = 40,
        asset1 = _asset,
        asset2 = empty(address),
        amount1 = amountDeposited,
        amount2 = 0,
        usdValue = txUsdValue,
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.REMOVE_COLLATERAL, True, [_asset], [_legoId])

    # remove collateral
    amountRemoved: uint256 = 0
    txUsdValue: uint256 = 0   
    amountRemoved, txUsdValue = extcall Lego(ad.legoAddr).removeCollateral(_asset, _amount, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

    self._performPostActionTasks([_asset], txUsdValue, ad)
    log WalletAction(
        op = 41,
        asset1 = _asset,
        asset2 = empty(address),
        amount1 = amountRemoved,
        amount2 = 0,
        usdValue = txUsdValue,
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.BORROW, True, [_borrowAsset], [_legoId])

    # borrow
    borrowAmount: uint256 = 0
    txUsdValue: uint256 = 0
    borrowAmount, txUsdValue = extcall Lego(ad.legoAddr).borrow(_borrowAsset, _amount, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

    self._performPostActionTasks([_borrowAsset], txUsdValue, ad)
    log WalletAction(
        op = 42,
        asset1 = _borrowAsset,
        asset2 = empty(address),
        amount1 = borrowAmount,
        amount2 = 0,
        usdValue = txUsdValue,
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.REPAY_DEBT, True, [_paymentAsset], [_legoId])

    # repay debt
    amount: uint256 = self._getAmountAndApprove(_paymentAsset, _paymentAmount, ad.legoAddr) # doing approval here
    repaidAmount: uint256 = 0
    txUsdValue: uint256 = 0
    repaidAmount, txUsdValue = extcall Lego(ad.legoAddr).repayDebt(_paymentAsset, amount, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))
    self._resetApproval(_paymentAsset, ad.legoAddr)

    self._performPostActionTasks([_paymentAsset], txUsdValue, ad)
    log WalletAction(
        op = 43,
        asset1 = _paymentAsset,
        asset2 = empty(address),
        amount1 = repaidAmount,
        amount2 = 0,
        usdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
    )
    return repaidAmount, txUsdValue


####################
# Claim Incentives #
####################


@nonreentrant
@external
def claimIncentives(
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _proofs: DynArray[bytes32, MAX_PROOFS] = [],
) -> (uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.REWARDS, True, [_rewardToken], [_legoId])

    # pre balance
    preBalance: uint256 = 0
    if _rewardToken != empty(address):
        preBalance = staticcall IERC20(_rewardToken).balanceOf(self)

    # claim rewards
    rewardAmount: uint256 = 0
    txUsdValue: uint256 = 0
    rewardAmount, txUsdValue = extcall Lego(ad.legoAddr).claimIncentives(self, _rewardToken, _rewardAmount, _proofs, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

    # post balance
    postBalance: uint256 = 0
    if _rewardToken != empty(address):
        postBalance = staticcall IERC20(_rewardToken).balanceOf(self)
    actualRewardAmount: uint256 = postBalance - preBalance

    # handle rewards fee
    if _rewardToken != empty(address):
        rewardsFee: uint256 = staticcall LootDistributor(ad.lootDistributor).getRewardsFee(self, _rewardToken, ad.missionControl)
        if rewardsFee != 0 and actualRewardAmount != 0:
            rewardsFee = self._payTransactionFee(_rewardToken, actualRewardAmount, min(rewardsFee, 25_00), ws.ActionType.REWARDS, ad.lootDistributor, ad.missionControl)
            actualRewardAmount -= rewardsFee

    self._performPostActionTasks([_rewardToken], txUsdValue, ad)
    log WalletAction(
        op = 50,
        asset1 = _rewardToken,
        asset2 = ad.legoAddr,
        amount1 = actualRewardAmount,
        amount2 = rewardAmount,
        usdValue = txUsdValue,
        legoId = ad.legoId,
        signer = ad.signer,
    )
    return actualRewardAmount, txUsdValue


###############
# Wrapped ETH #
###############


# weth -> eth


@nonreentrant
@external
def convertWethToEth(_amount: uint256 = max_value(uint256)) -> (uint256, uint256):
    weth: address = WETH
    eth: address = ETH
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.WETH_TO_ETH, False, [weth, eth], [], empty(address))

    # convert weth to eth
    amount: uint256 = self._getAmountAndApprove(weth, _amount, empty(address)) # nothing to approve
    extcall WethContract(weth).withdraw(amount)

    txUsdValue: uint256 = self._updatePriceAndGetUsdValue(weth, amount, ad)
    self._performPostActionTasks([weth, eth], txUsdValue, ad)
    log WalletAction(
        op = 2,
        asset1 = weth,
        asset2 = eth,
        amount1 = amount,
        amount2 = amount,
        usdValue = txUsdValue,
        legoId = 0,
        signer = ad.signer,
    )
    return amount, txUsdValue


# eth -> weth


@nonreentrant
@payable
@external
def convertEthToWeth(_amount: uint256 = max_value(uint256)) -> (uint256, uint256):
    eth: address = ETH
    weth: address = WETH
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.ETH_TO_WETH, False, [eth, weth], [], empty(address))

    # convert eth to weth
    amount: uint256 = min(_amount, self.balance)
    assert amount != 0 # dev: no amt
    extcall WethContract(weth).deposit(value = amount)

    txUsdValue: uint256 = self._updatePriceAndGetUsdValue(weth, amount, ad)
    self._performPostActionTasks([eth, weth], txUsdValue, ad)
    log WalletAction(
        op = 3,
        asset1 = eth,
        asset2 = weth,
        amount1 = msg.value,
        amount2 = amount,
        usdValue = txUsdValue,
        legoId = 0,
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.ADD_LIQ, False, [_tokenA, _tokenB], [_legoId])

    # token approvals
    amountA: uint256 = 0
    if _amountA != 0:
        amountA = self._getAmountAndApprove(_tokenA, _amountA, ad.legoAddr)
    amountB: uint256 = 0
    if _amountB != 0:
        amountB = self._getAmountAndApprove(_tokenB, _amountB, ad.legoAddr)

    # add liquidity via lego partner
    lpToken: address = empty(address)
    lpAmountReceived: uint256 = 0
    addedTokenA: uint256 = 0
    addedTokenB: uint256 = 0
    txUsdValue: uint256 = 0
    lpToken, lpAmountReceived, addedTokenA, addedTokenB, txUsdValue = extcall Lego(ad.legoAddr).addLiquidity(_pool, _tokenA, _tokenB, amountA, amountB, _minAmountA, _minAmountB, _minLpAmount, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

    # remove approvals
    if amountA != 0:
        self._resetApproval(_tokenA, ad.legoAddr)
    if amountB != 0:
        self._resetApproval(_tokenB, ad.legoAddr)

    self._performPostActionTasks([_tokenA, _tokenB, lpToken], txUsdValue, ad)
    log WalletAction(
        op = 30,
        asset1 = _tokenA,
        asset2 = _tokenB,
        amount1 = addedTokenA,
        amount2 = addedTokenB,
        usdValue = txUsdValue,
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.REMOVE_LIQ, False, [_tokenA, _tokenB], [_legoId])

    # remove liquidity via lego partner
    amountAReceived: uint256 = 0
    amountBReceived: uint256 = 0
    lpAmountBurned: uint256 = 0
    txUsdValue: uint256 = 0
    lpAmount: uint256 = self._getAmountAndApprove(_lpToken, _lpAmount, ad.legoAddr)
    amountAReceived, amountBReceived, lpAmountBurned, txUsdValue = extcall Lego(ad.legoAddr).removeLiquidity(_pool, _tokenA, _tokenB, _lpToken, lpAmount, _minAmountA, _minAmountB, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))
    self._resetApproval(_lpToken, ad.legoAddr)

    self._performPostActionTasks([_tokenA, _tokenB, _lpToken], txUsdValue, ad)
    log WalletAction(
        op = 31,
        asset1 = _tokenA,
        asset2 = _tokenB,
        amount1 = amountAReceived,
        amount2 = amountBReceived,
        usdValue = txUsdValue,
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.ADD_LIQ_CONC, False, [_tokenA, _tokenB], [_legoId])

    # token approvals
    amountA: uint256 = 0
    if _amountA != 0:
        amountA = self._getAmountAndApprove(_tokenA, _amountA, ad.legoAddr)
    amountB: uint256 = 0
    if _amountB != 0:
        amountB = self._getAmountAndApprove(_tokenB, _amountB, ad.legoAddr)

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
    liqAdded, addedTokenA, addedTokenB, nftTokenId, txUsdValue = extcall Lego(ad.legoAddr).addLiquidityConcentrated(_nftTokenId, _pool, _tokenA, _tokenB, _tickLower, _tickUpper, amountA, amountB, _minAmountA, _minAmountB, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

    # make sure nft is back
    assert staticcall IERC721(_nftAddr).ownerOf(nftTokenId) == self # dev: nft not returned

    # remove approvals
    if amountA != 0:
        self._resetApproval(_tokenA, ad.legoAddr)
    if amountB != 0:
        self._resetApproval(_tokenB, ad.legoAddr)

    self._performPostActionTasks([_tokenA, _tokenB], txUsdValue, ad)
    log WalletActionExt(
        op = 32,
        asset1 = _tokenA,
        asset2 = _tokenB,
        tokenId = nftTokenId,
        amount1 = addedTokenA,
        amount2 = addedTokenB,
        usdValue = txUsdValue,
        extra = liqAdded,
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
    _extraData: bytes32 = empty(bytes32),
) -> (uint256, uint256, uint256, uint256):
    ad: ws.ActionData = self._performPreActionTasks(msg.sender, ws.ActionType.REMOVE_LIQ_CONC, False, [_tokenA, _tokenB], [_legoId])

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
    amountAReceived, amountBReceived, liqRemoved, isDepleted, txUsdValue = extcall Lego(ad.legoAddr).removeLiquidityConcentrated(_nftTokenId, _pool, _tokenA, _tokenB, _liqToRemove, _minAmountA, _minAmountB, _extraData, self, self._packMiniAddys(ad.ledger, ad.missionControl, ad.legoBook, ad.appraiser))

    # validate the nft came back (if not depleted)
    if not isDepleted:
        assert staticcall IERC721(_nftAddr).ownerOf(_nftTokenId) == self # dev: nft not returned

    self._performPostActionTasks([_tokenA, _tokenB], txUsdValue, ad)
    log WalletActionExt(
        op = 33,
        asset1 = _tokenA,
        asset2 = _tokenB,
        tokenId = _nftTokenId,
        amount1 = amountAReceived,
        amount2 = amountBReceived,
        usdValue = txUsdValue,
        extra = liqRemoved,
    )
    return amountAReceived, amountBReceived, liqRemoved, txUsdValue


#################
# House Keeping #
#################


# pre action tasks


@internal
def _performPreActionTasks(
    _signer: address,
    _action: ws.ActionType,
    _shouldCheckAccess: bool,
    _assets: DynArray[address, MAX_ASSETS],
    _legoIds: DynArray[uint256, MAX_LEGOS] = [],
    _transferRecipient: address = empty(address),
) -> ws.ActionData:
    legoId: uint256 = 0
    if len(_legoIds) != 0:
        legoId = _legoIds[0]
    ad: ws.ActionData = staticcall WalletConfig(self.walletConfig).checkSignerPermissionsAndGetBundle(_signer, _action, _assets, _legoIds, _transferRecipient)

    # cannot perform any actions if wallet is frozen
    assert not ad.isFrozen # dev: frozen wallet

    # eject mode can only do transfer and eth conversions
    if ad.inEjectMode:
        assert _action in (ws.ActionType.TRANSFER | ws.ActionType.ETH_TO_WETH | ws.ActionType.WETH_TO_ETH) # dev: invalid action in eject mode
        assert _signer == ad.walletOwner # dev: only owner can act in eject mode
        return ad

    # make sure lego can perform the action
    if _shouldCheckAccess:
        self._setLegoAccessForAction(ad.legoAddr, _action)

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
    _ad: ws.ActionData,
    _isSpecialTx: bool = False,
):
    # first, check and update manager caps
    if not _isSpecialTx and _ad.signer != _ad.billing:
        assert extcall WalletConfig(_ad.walletConfig).checkManagerUsdLimitsAndUpdateData(_ad.signer, _txUsdValue) # dev: manager limits not allowed

    # can immediately deregister assets on zero balance
    canDeregister: bool = True
    if _isSpecialTx or _ad.signer == _ad.billing:
        canDeregister = False

    # update each asset that was touched
    newTotalUsdValue: uint256 = _ad.lastTotalUsdValue
    for a: address in _assets:
        newTotalUsdValue = self._updateAssetData(a, newTotalUsdValue, canDeregister, _ad)

    if not _ad.inEjectMode:
        extcall LootDistributor(_ad.lootDistributor).updateDepositPointsWithNewValue(self, newTotalUsdValue)


##################
# Yield Handling #
##################


@internal
def _checkForYieldProfits(_asset: address, _ad: ws.ActionData):
    if _asset in [empty(address), _ad.eth, _ad.weth]:
        return

    # skip if already checked
    if self.checkedYield[_asset]:
        return

    # nothing to do here (nothing saved, not a yield asset)
    data: ws.WalletAssetData = self.assetData[_asset]
    if data.assetBalance == 0 or not data.isYieldAsset:
        return

    # no balance, nothing to do here
    currentBalance: uint256 = staticcall IERC20(_asset).balanceOf(self)
    if currentBalance == 0:
        return

    # calculate yield profits
    yieldRealized: uint256 = 0
    feeRatio: uint256 = 0
    data.lastPricePerShare, yieldRealized, feeRatio = extcall Appraiser(_ad.appraiser).calculateYieldProfits(_asset, currentBalance, data.assetBalance, data.lastPricePerShare, _ad.missionControl, _ad.legoBook)

    # only save if appraiser returns a price per share (non-rebasing assets)
    if data.lastPricePerShare != 0:
        self.assetData[_asset] = data

    # pay yield fee
    self._payYieldFee(_asset, yieldRealized, feeRatio, _ad)

    # mark as checked
    self.checkedYield[_asset] = True


##############
# Asset Data #
##############


# from wallet config


@external
def updateAssetData(
    _legoId: uint256,
    _asset: address,
    _shouldCheckYield: bool,
    _prevTotalUsdValue: uint256,
    _ad: ws.ActionData = empty(ws.ActionData),
) -> uint256:
    walletConfig: address = self.walletConfig
    assert msg.sender == walletConfig # dev: perms

    ad: ws.ActionData = _ad
    if ad.signer == empty(address):
        ad = staticcall WalletConfig(walletConfig).getActionDataBundle(_legoId, walletConfig)

    # check for yield
    if _shouldCheckYield and not ad.inEjectMode:
        self._checkForYieldProfits(_asset, ad)

    # update asset data
    return self._updateAssetData(_asset, _prevTotalUsdValue, False, ad)


# update asset data


@internal
def _updateAssetData(
    _asset: address,
    _prevTotalUsdValue: uint256,
    _canDeregister: bool,
    _ad: ws.ActionData,
) -> uint256:
    if _asset == empty(address):
        return _prevTotalUsdValue

    data: ws.WalletAssetData = self.assetData[_asset]
    newTotalUsdValue: uint256 = _prevTotalUsdValue - min(data.usdValue, _prevTotalUsdValue)

    # ETH / ERC20
    currentBalance: uint256 = 0
    if _asset == _ad.eth:
        currentBalance = self.balance
    else:
        currentBalance = staticcall IERC20(_asset).balanceOf(self)

    # no balance, deregister asset
    if currentBalance == 0:
        data.assetBalance = 0
        data.usdValue = 0
        self.assetData[_asset] = data

        # in some cases (wallet migration, trial funds clawback, pulling payment, etc), we are iterating thru assets
        # we cannot deregister here or it'll mess up the indexes/order/iteration
        if _canDeregister:
            self._deregisterAsset(_asset)

        return newTotalUsdValue

    # update usd value
    data.usdValue = 0
    data.isYieldAsset = False
    if not _ad.inEjectMode:
        data.usdValue, data.isYieldAsset = extcall Appraiser(_ad.appraiser).updatePriceAndGetUsdValueAndIsYieldAsset(_asset, currentBalance, _ad.missionControl, _ad.legoBook)
        newTotalUsdValue += data.usdValue

    # when receiving vault token for the first time, need to get price per share
    if data.isYieldAsset and data.lastPricePerShare == 0:
        data.lastPricePerShare = staticcall Appraiser(_ad.appraiser).lastPricePerShare(_asset)

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
    self.assets[aid] = _asset
    self.indexOfAsset[_asset] = aid
    self.numAssets = aid + 1


# deregister asset


@external
def deregisterAsset(_asset: address) -> bool:
    assert msg.sender == self.walletConfig # dev: perms
    return self._deregisterAsset(_asset)


@internal
def _deregisterAsset(_asset: address) -> bool:
    if staticcall IERC20(_asset).balanceOf(self) != 0:
        return False

    numAssets: uint256 = self.numAssets
    if numAssets == 1:
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


#############
# Utilities #
#############


# pay fees


@internal
def _payYieldFee(
    _asset: address,
    _yieldRealized: uint256,
    _feeRatio: uint256,
    _ad: ws.ActionData,
):
    if _ad.lootDistributor == empty(address):
        return

    # do not charge fees in eject mode
    if _ad.inEjectMode:
        return

    feeAmount: uint256 = _yieldRealized * min(_feeRatio, 25_00) // HUNDRED_PERCENT
    if feeAmount != 0:
        assert extcall IERC20(_asset).transfer(_ad.lootDistributor, feeAmount, default_return_value = True) # dev: xfer

    # notify loot distributor
    if feeAmount != 0 or _yieldRealized != 0:
        extcall LootDistributor(_ad.lootDistributor).addLootFromYieldProfit(_asset, feeAmount, _yieldRealized, _ad.missionControl, _ad.appraiser, _ad.legoBook)


# pay transaction fees (swap / rewards)


@internal
def _payTransactionFee(
    _asset: address,
    _transactionValue: uint256,
    _feeRatio: uint256,
    _action: ws.ActionType,
    _lootDistributor: address,
    _missionControl: address,
) -> uint256:
    feeAmount: uint256 = min(_transactionValue * _feeRatio // HUNDRED_PERCENT, staticcall IERC20(_asset).balanceOf(self))
    if feeAmount == 0:
        return 0
    assert extcall IERC20(_asset).approve(_lootDistributor, feeAmount, default_return_value = True) # dev: appr
    extcall LootDistributor(_lootDistributor).addLootFromSwapOrRewards(_asset, feeAmount, _action, _missionControl)
    self._resetApproval(_asset, _lootDistributor)
    return feeAmount


# update price and get usd value


@internal
def _updatePriceAndGetUsdValue(_asset: address, _amount: uint256, _ad: ws.ActionData) -> uint256:
    if _ad.inEjectMode:
        return 0
    return extcall Appraiser(_ad.appraiser).updatePriceAndGetUsdValue(_asset, _amount, _ad.missionControl, _ad.legoBook)


# approve


@internal
def _getAmountAndApprove(_token: address, _amount: uint256, _legoAddr: address) -> uint256:
    amount: uint256 = min(_amount, staticcall IERC20(_token).balanceOf(self))
    assert amount != 0 # dev: no balance for _token
    if _legoAddr != empty(address):
        assert extcall IERC20(_token).approve(_legoAddr, amount, default_return_value = True) # dev: appr
    return amount


# reset approval


@internal
def _resetApproval(_token: address, _legoAddr: address):
    if _legoAddr != empty(address):
        assert extcall IERC20(_token).approve(_legoAddr, 0, default_return_value = True) # dev: appr


# recover nft


@nonreentrant
@external
def recoverNft(_collection: address, _nftTokenId: uint256, _recipient: address):
    assert msg.sender == self.walletConfig # dev: perms
    extcall IERC721(_collection).safeTransferFrom(self, _recipient, _nftTokenId)


# lego access


@external
def setLegoAccessForAction(_legoAddr: address, _action: ws.ActionType) -> bool:
    assert msg.sender == self.walletConfig # dev: perms
    return self._setLegoAccessForAction(_legoAddr, _action)


@internal
def _setLegoAccessForAction(_legoAddr: address, _action: ws.ActionType) -> bool:
    if _legoAddr == empty(address):
        return False

    targetAddr: address = empty(address)
    accessAbi: String[64] = empty(String[64])
    numInputs: uint256 = 0
    targetAddr, accessAbi, numInputs = staticcall Lego(_legoAddr).getAccessForLego(self, _action)

    # nothing to do here
    if targetAddr == empty(address):
        return False

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
            revert_on_failure = False,
            max_outsize = 32,
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
            revert_on_failure = False,
            max_outsize = 32,
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
            revert_on_failure = False,
            max_outsize = 32,
        )

    assert success # dev: failed to set operator
    return True


# mini addys


@view
@internal
def _packMiniAddys(
    _ledger: address,
    _missionControl: address,
    _legoBook: address,
    _appraiser: address,
) -> ws.MiniAddys:
    return ws.MiniAddys(
        ledger = _ledger,
        missionControl = _missionControl,
        legoBook = _legoBook,
        appraiser = _appraiser,
    )