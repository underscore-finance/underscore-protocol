#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

#     ╔════════════════════════════════════════════════════════════════════════════════╗
#     ║  ** Leverage Vault Agent **                                                    ║
#     ║  Manages leverage operations for leverage vaults: yield, swap, debt, workflows ║
#     ╚════════════════════════════════════════════════════════════════════════════════╝

initializes: ownership
exports: ownership.__interface__
import contracts.modules.Ownership as ownership

from interfaces import Wallet
from ethereum.ercs import IERC20
from ethereum.ercs import IERC4626

interface LevgVaultWallet:
    def vaultToLegoId(_vaultToken: address) -> uint256: view
    def indexOfManager(_manager: address) -> uint256: view
    def collateralAsset() -> RipeAsset: view
    def leverageAsset() -> RipeAsset: view

interface RipeLego:
    def deleverageWithSpecificAssets(_assets: DynArray[DeleverageAsset, MAX_DELEVERAGE_ASSETS], _user: address) -> uint256: nonpayable
    def deleverageUser(_user: address, _targetRepayAmount: uint256) -> uint256: nonpayable

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct Signature:
    signature: Bytes[65]
    nonce: uint256
    expiration: uint256

struct ActionInstruction:
    usePrevAmountOut: bool     # Use output from previous instruction as amount
    action: uint8              # Action type: 10-50 for standard ops
    legoId: uint16             # Protocol/Lego ID
    asset: address             # Primary asset/token
    target: address            # vaultAddr for deposits, etc.
    amount: uint256            # Primary amount (or max_value for "all")
    extraData: bytes32         # Protocol-specific extra data

struct PositionAsset:
    positionType: uint8  # 0=collateral, 1=leverage, 2=stabPool(sGREEN)
    amount: uint256      # Amount (max_value for all)

struct DeleverageAsset:
    vaultId: uint256
    asset: address
    targetRepayAmount: uint256

struct DepositYieldPosition:
    positionType: uint8              # 0=collateral, 1=leverage, 2=stabPool(GREEN→sGREEN)
    amount: uint256                  # amount to deposit (ignored if shouldSweepAll is true)
    shouldAddToRipeCollateral: bool  # after deposit, add vault token to ripe
    shouldSweepAll: bool             # deposit full wallet balance regardless of chaining

struct RipeAsset:
    vaultToken: address
    ripeVaultId: uint256

event NonceIncremented:
    levgVault: address
    oldNonce: uint256
    newNonce: uint256

# important ids
RIPE_LEGO_ID: constant(uint256) = 1
RIPE_STAB_POOL_ID: constant(uint256) = 1
LEGO_BOOK_ID: constant(uint256) = 3

# max on lists
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_DELEVERAGE_ASSETS: constant(uint256) = 25
MAX_PROOFS: constant(uint256) = 25
MAX_BATCH_INSTRUCTIONS: constant(uint256) = 15
MAX_POSITIONS: constant(uint256) = 25

# unified signature validation
ECRECOVER_PRECOMPILE: constant(address) = 0x0000000000000000000000000000000000000001
SIG_PREFIX: constant(bytes32) = 0x1901000000000000000000000000000000000000000000000000000000000000

# position types for simplified structs
POSITION_COLLATERAL: constant(uint8) = 0
POSITION_LEVERAGE: constant(uint8) = 1
POSITION_STAB_POOL: constant(uint8) = 2

# action codes for 1:1 mappings
ACTION_DEPOSIT_YIELD: constant(uint8) = 10
ACTION_WITHDRAW_YIELD: constant(uint8) = 11
ACTION_SWAP: constant(uint8) = 20
ACTION_ADD_COLLATERAL: constant(uint8) = 40
ACTION_REMOVE_COLLATERAL: constant(uint8) = 41
ACTION_BORROW: constant(uint8) = 42
ACTION_REPAY_DEBT: constant(uint8) = 43
ACTION_CLAIM_INCENTIVES: constant(uint8) = 50

# workflow action codes
WORKFLOW_BORROW_AND_EARN: constant(uint8) = 100
WORKFLOW_DELEVERAGE: constant(uint8) = 101
WORKFLOW_COMPOUND_YIELD: constant(uint8) = 102

UNDY_HQ: public(immutable(address))
GREEN: public(immutable(address))
SAVINGS_GREEN: public(immutable(address))

currentNonce: public(HashMap[address, uint256])


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
    _greenToken: address,
    _savingsGreen: address,
):
    ownership.__init__(_undyHq, _owner, _minTimeLock, _maxTimeLock)
    UNDY_HQ = _undyHq
    GREEN = _greenToken
    SAVINGS_GREEN = _savingsGreen


#########
# Yield #
#########


@external
def depositForYield(
    _levgWallet: address,
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
    self._authenticateAccess(_levgWallet, keccak256(abi_encode(ACTION_DEPOSIT_YIELD, _levgWallet, _legoId, _asset, _vaultAddr, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_levgWallet).depositForYield(_legoId, _asset, _vaultAddr, _amount, _extraData)


@external
def withdrawFromYield(
    _levgWallet: address,
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, address, uint256, uint256):
    self._authenticateAccess(_levgWallet, keccak256(abi_encode(ACTION_WITHDRAW_YIELD, _levgWallet, _legoId, _vaultToken, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_levgWallet).withdrawFromYield(_legoId, _vaultToken, _amount, _extraData, False)


###################
# Swap / Exchange #
###################


@external
def swapTokens(
    _levgWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> (address, uint256, address, uint256, uint256):
    self._authenticateAccess(_levgWallet, keccak256(abi_encode(ACTION_SWAP, _levgWallet, _swapInstructions, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_levgWallet).swapTokens(_swapInstructions)


###################
# Debt Management #
###################


@external
def addCollateral(
    _levgWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_levgWallet, keccak256(abi_encode(ACTION_ADD_COLLATERAL, _levgWallet, _legoId, _asset, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_levgWallet).addCollateral(_legoId, _asset, _amount, _extraData)


@external
def removeCollateral(
    _levgWallet: address,
    _legoId: uint256,
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_levgWallet, keccak256(abi_encode(ACTION_REMOVE_COLLATERAL, _levgWallet, _legoId, _asset, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_levgWallet).removeCollateral(_legoId, _asset, _amount, _extraData)


@external
def borrow(
    _levgWallet: address,
    _legoId: uint256,
    _borrowAsset: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_levgWallet, keccak256(abi_encode(ACTION_BORROW, _levgWallet, _legoId, _borrowAsset, _amount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_levgWallet).borrow(_legoId, _borrowAsset, _amount, _extraData)


@external
def repayDebt(
    _levgWallet: address,
    _legoId: uint256,
    _paymentAsset: address,
    _paymentAmount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_levgWallet, keccak256(abi_encode(ACTION_REPAY_DEBT, _levgWallet, _legoId, _paymentAsset, _paymentAmount, _extraData, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_levgWallet).repayDebt(_legoId, _paymentAsset, _paymentAmount, _extraData)


#################
# Claim Rewards #
#################


@external
def claimIncentives(
    _levgWallet: address,
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _proofs: DynArray[bytes32, MAX_PROOFS] = [],
    _sig: Signature = empty(Signature),
) -> (uint256, uint256):
    self._authenticateAccess(_levgWallet, keccak256(abi_encode(ACTION_CLAIM_INCENTIVES, _levgWallet, _legoId, _rewardToken, _rewardAmount, _proofs, _sig.nonce, _sig.expiration)), _sig)
    return extcall Wallet(_levgWallet).claimIncentives(_legoId, _rewardToken, _rewardAmount, _proofs)


#################
# Batch Actions #
#################


@external
def performBatchActions(
    _levgWallet: address,
    _instructions: DynArray[ActionInstruction, MAX_BATCH_INSTRUCTIONS],
    _sig: Signature = empty(Signature),
) -> bool:
    assert len(_instructions) > 0 # dev: no instructions
    messageHash: bytes32 = keccak256(abi_encode(_levgWallet, _instructions, _sig.nonce, _sig.expiration))
    self._authenticateAccess(_levgWallet, messageHash, _sig)

    prevAmountReceived: uint256 = 0
    for instruction: ActionInstruction in _instructions:
        prevAmountReceived = self._executeAction(_levgWallet, instruction, prevAmountReceived)

    return True


@internal
def _executeAction(_levgWallet: address, instruction: ActionInstruction, _prevAmount: uint256) -> uint256:
    nextAmount: uint256 = instruction.amount
    if instruction.usePrevAmountOut and _prevAmount != 0:
        nextAmount = _prevAmount

    txUsdValue: uint256 = 0

    # deposit for yield
    if instruction.action == ACTION_DEPOSIT_YIELD:
        assetAmount: uint256 = 0
        vaultToken: address = empty(address)
        vaultTokenAmount: uint256 = 0
        assetAmount, vaultToken, vaultTokenAmount, txUsdValue = extcall Wallet(_levgWallet).depositForYield(convert(instruction.legoId, uint256), instruction.asset, instruction.target, nextAmount, instruction.extraData)
        return vaultTokenAmount

    # withdraw from yield
    elif instruction.action == ACTION_WITHDRAW_YIELD:
        vaultTokensBurned: uint256 = 0
        underlyingAsset: address = empty(address)
        underlyingAmount: uint256 = 0
        vaultTokensBurned, underlyingAsset, underlyingAmount, txUsdValue = extcall Wallet(_levgWallet).withdrawFromYield(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData, False)
        return underlyingAmount

    # add collateral
    elif instruction.action == ACTION_ADD_COLLATERAL:
        amountDeposited: uint256 = 0
        amountDeposited, txUsdValue = extcall Wallet(_levgWallet).addCollateral(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return amountDeposited

    # remove collateral
    elif instruction.action == ACTION_REMOVE_COLLATERAL:
        amountRemoved: uint256 = 0
        amountRemoved, txUsdValue = extcall Wallet(_levgWallet).removeCollateral(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return amountRemoved

    # borrow
    elif instruction.action == ACTION_BORROW:
        borrowAmount: uint256 = 0
        borrowAmount, txUsdValue = extcall Wallet(_levgWallet).borrow(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return borrowAmount

    # repay debt
    elif instruction.action == ACTION_REPAY_DEBT:
        repaidAmount: uint256 = 0
        repaidAmount, txUsdValue = extcall Wallet(_levgWallet).repayDebt(convert(instruction.legoId, uint256), instruction.asset, nextAmount, instruction.extraData)
        return repaidAmount

    else:
        raise "Invalid action"


#########################
# Specialized Workflows #
#########################


# borrow -> earn yield


@external
def borrowAndEarnYield(
    _levgWallet: address,
    # step 1: remove collateral from ripe (any position type)
    _removeCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    # step 2: withdraw from yield vaults (any position type)
    _withdrawPositions: DynArray[PositionAsset, MAX_POSITIONS] = [],
    # step 3: deposit into yield vaults (any position type, with optional add-to-ripe)
    _depositPositions: DynArray[DepositYieldPosition, MAX_POSITIONS] = [],
    # step 4: add collateral to ripe (vault tokens already in wallet, any position type)
    _addCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    # step 5: borrow
    _borrowAmount: uint256 = 0,
    _wantsSavingsGreen: bool = True,
    _shouldEnterStabPool: bool = True,
    # step 6: swap
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    # step 7: post-swap deposits (any position type, with optional add-to-ripe)
    _postSwapDeposits: DynArray[DepositYieldPosition, MAX_POSITIONS] = [],
    _sig: Signature = empty(Signature),
):
    # 1. authenticate access (action code 100)
    messageHash: bytes32 = keccak256(abi_encode(
        WORKFLOW_BORROW_AND_EARN,
        _levgWallet,
        _removeCollateral,
        _withdrawPositions,
        _depositPositions,
        _addCollateral,
        _borrowAmount,
        _wantsSavingsGreen,
        _shouldEnterStabPool,
        _swapInstructions,
        _postSwapDeposits,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_levgWallet, messageHash, _sig)

    # 2. fetch position data
    collData: RipeAsset = empty(RipeAsset)
    levgData: RipeAsset = empty(RipeAsset)
    collUnderlyingAsset: address = empty(address)
    levgUnderlyingAsset: address = empty(address)
    collLegoId: uint256 = 0
    levgLegoId: uint256 = 0
    collData, levgData, collUnderlyingAsset, levgUnderlyingAsset, collLegoId, levgLegoId = self._fetchPositionData(_levgWallet)

    # track outputs for chaining
    borrowAmountReceived: uint256 = 0
    borrowAsset: address = empty(address)
    swapAmountOut: uint256 = 0
    swapTokenOut: address = empty(address)
    ripeLegoId: uint256 = RIPE_LEGO_ID

    # step 1: remove collateral from ripe
    for op: PositionAsset in _removeCollateral:
        vaultToken: address = empty(address)
        ripeVaultId: uint256 = 0
        vaultToken, ripeVaultId = self._getCollateralData(op.positionType, collData, levgData)
        if vaultToken != empty(address):
            extcall Wallet(_levgWallet).removeCollateral(
                ripeLegoId,
                vaultToken,
                op.amount if op.amount != 0 else max_value(uint256),
                convert(ripeVaultId, bytes32)
            )

    # step 2: withdraw from yield vaults
    for op: PositionAsset in _withdrawPositions:
        vaultToken: address = empty(address)
        legoId: uint256 = 0
        vaultToken, legoId = self._getWithdrawData(op.positionType, collData, levgData, collLegoId, levgLegoId)
        if vaultToken != empty(address):
            extcall Wallet(_levgWallet).withdrawFromYield(
                legoId,
                vaultToken,
                op.amount if op.amount != 0 else max_value(uint256),
                empty(bytes32),
                False
            )

    # step 3: deposit into yield vaults
    for op: DepositYieldPosition in _depositPositions:
        self._processDeposit(
            _levgWallet,
            op,
            collData,
            levgData,
            collLegoId,
            levgLegoId,
            collUnderlyingAsset,
            levgUnderlyingAsset
        )

    # step 4: add collateral to ripe
    for op: PositionAsset in _addCollateral:
        vaultToken: address = empty(address)
        ripeVaultId: uint256 = 0
        vaultToken, ripeVaultId = self._getCollateralData(op.positionType, collData, levgData)
        if vaultToken != empty(address):
            extcall Wallet(_levgWallet).addCollateral(
                ripeLegoId,
                vaultToken,
                op.amount if op.amount != 0 else max_value(uint256),
                convert(ripeVaultId, bytes32)
            )

    # step 5: borrow green/savings_green
    if _borrowAmount != 0:
        borrowAsset = SAVINGS_GREEN if _wantsSavingsGreen else GREEN
        borrowExtraData: bytes32 = convert(convert(_shouldEnterStabPool, uint256), bytes32)
        usdValue: uint256 = 0
        borrowAmountReceived, usdValue = extcall Wallet(_levgWallet).borrow(
            ripeLegoId,
            borrowAsset,
            _borrowAmount,
            borrowExtraData
        )

    # step 6: swap tokens
    if len(_swapInstructions) != 0 and len(_swapInstructions[0].tokenPath) != 0:
        swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = _swapInstructions
        tokenIn: address = swapInstructions[0].tokenPath[0]
        swapBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(_levgWallet)

        # if first token_in matches borrow_asset, use borrow_amount_received as input
        if borrowAmountReceived != 0 and tokenIn == borrowAsset:
            swapInstructions[0].amountIn = min(borrowAmountReceived, swapBalance)
        else:
            swapInstructions[0].amountIn = min(swapInstructions[0].amountIn, swapBalance)

        tokenInResult: address = empty(address)
        amountIn: uint256 = 0
        swapUsdValue: uint256 = 0
        tokenInResult, amountIn, swapTokenOut, swapAmountOut, swapUsdValue = extcall Wallet(_levgWallet).swapTokens(swapInstructions)

    # step 7: post-swap deposits
    for op: DepositYieldPosition in _postSwapDeposits:
        depositAmount: uint256 = op.amount

        if op.shouldSweepAll:
            depositAmount = max_value(uint256)
        elif swapAmountOut != 0:
            depositUnderlying: address = empty(address)
            if op.positionType == POSITION_COLLATERAL:
                depositUnderlying = collUnderlyingAsset
            elif op.positionType == POSITION_LEVERAGE:
                depositUnderlying = levgUnderlyingAsset
            elif op.positionType == POSITION_STAB_POOL:
                depositUnderlying = GREEN

            # if swap output matches deposit's underlying asset, use swapAmountOut
            if swapTokenOut == depositUnderlying:
                depositAmount = swapAmountOut

        modifiedOp: DepositYieldPosition = DepositYieldPosition(
            positionType=op.positionType,
            amount=depositAmount,
            shouldAddToRipeCollateral=op.shouldAddToRipeCollateral,
            shouldSweepAll=False
        )
        self._processDeposit(
            _levgWallet,
            modifiedOp,
            collData,
            levgData,
            collLegoId,
            levgLegoId,
            collUnderlyingAsset,
            levgUnderlyingAsset
        )


# deleverage


@external
def deleverage(
    _levgWallet: address,
    # mode selection: 0=auto_deleverage_user, 1=deleverage_with_specific_assets, 2=manual
    _mode: uint8 = 0,
    # option a: auto-deleverage user (mode 0)
    _autoDeleverageAmount: uint256 = 0,
    # option b: deleverage with specific assets (mode 1)
    _deleverageAssets: DynArray[DeleverageAsset, MAX_DELEVERAGE_ASSETS] = [],
    # option c: manual deleverage (mode 2)
    _removeCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _withdrawPositions: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    # common: repay debt
    _repayAsset: address = empty(address),
    _repayAmount: uint256 = 0,
    _shouldSweepAllForRepay: bool = False,
    _sig: Signature = empty(Signature),
):
    # 1. authenticate access (action code 101)
    messageHash: bytes32 = keccak256(abi_encode(
        WORKFLOW_DELEVERAGE,
        _levgWallet,
        _mode,
        _autoDeleverageAmount,
        _deleverageAssets,
        _removeCollateral,
        _withdrawPositions,
        _swapInstructions,
        _repayAsset,
        _repayAmount,
        _shouldSweepAllForRepay,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_levgWallet, messageHash, _sig)

    # track outputs for chaining
    withdrawAmount: uint256 = 0
    withdrawAsset: address = empty(address)
    swapAmountOut: uint256 = 0
    swapTokenOut: address = empty(address)
    ripeLegoId: uint256 = RIPE_LEGO_ID

    # mode 0: auto deleverage user (via ripe lego)
    if _mode == 0:
        legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
        ripeLego: address = staticcall Registry(legoBook).getAddr(ripeLegoId)
        targetAmount: uint256 = _autoDeleverageAmount if _autoDeleverageAmount != 0 else max_value(uint256)
        extcall RipeLego(ripeLego).deleverageUser(_levgWallet, targetAmount)

    # mode 1: deleverage with specific assets (via ripe lego)
    elif _mode == 1:
        if len(_deleverageAssets) != 0:
            legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
            ripeLego: address = staticcall Registry(legoBook).getAddr(ripeLegoId)
            extcall RipeLego(ripeLego).deleverageWithSpecificAssets(_deleverageAssets, _levgWallet)

    # mode 2: manual deleverage
    elif _mode == 2:

        # 2. fetch position data
        collData: RipeAsset = empty(RipeAsset)
        levgData: RipeAsset = empty(RipeAsset)
        collUnderlyingAsset: address = empty(address)
        levgUnderlyingAsset: address = empty(address)
        collLegoId: uint256 = 0
        levgLegoId: uint256 = 0
        collData, levgData, collUnderlyingAsset, levgUnderlyingAsset, collLegoId, levgLegoId = self._fetchPositionData(_levgWallet)

        # step 2a: remove collateral from ripe
        for op: PositionAsset in _removeCollateral:
            vaultToken: address = empty(address)
            ripeVaultId: uint256 = 0
            vaultToken, ripeVaultId = self._getCollateralData(op.positionType, collData, levgData)
            if vaultToken != empty(address):
                extcall Wallet(_levgWallet).removeCollateral(
                    ripeLegoId,
                    vaultToken,
                    op.amount if op.amount != 0 else max_value(uint256),
                    convert(ripeVaultId, bytes32)
                )

        # step 2b: withdraw from yield
        for op: PositionAsset in _withdrawPositions:
            vaultToken: address = empty(address)
            legoId: uint256 = 0
            vaultToken, legoId = self._getWithdrawData(op.positionType, collData, levgData, collLegoId, levgLegoId)
            if vaultToken != empty(address):
                vaultTokensBurned: uint256 = 0
                txUsdValue: uint256 = 0
                vaultTokensBurned, withdrawAsset, withdrawAmount, txUsdValue = extcall Wallet(_levgWallet).withdrawFromYield(
                    legoId,
                    vaultToken,
                    op.amount if op.amount != 0 else max_value(uint256),
                    empty(bytes32),
                    False
                )

        # step 2c: swap tokens (usdc -> green)
        if len(_swapInstructions) != 0 and len(_swapInstructions[0].tokenPath) != 0:
            swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = _swapInstructions
            tokenIn: address = swapInstructions[0].tokenPath[0]
            tokenInBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(_levgWallet)

            # if first tokenIn matches withdrawAsset, use withdrawAmount as input
            if withdrawAmount != 0 and tokenIn == withdrawAsset:
                swapInstructions[0].amountIn = min(withdrawAmount, tokenInBalance)
            else:
                swapInstructions[0].amountIn = min(swapInstructions[0].amountIn, tokenInBalance)

            tokenInResult: address = empty(address)
            amountIn: uint256 = 0
            swapUsdValue: uint256 = 0
            tokenInResult, amountIn, swapTokenOut, swapAmountOut, swapUsdValue = extcall Wallet(_levgWallet).swapTokens(swapInstructions)

    # step 3: repay debt (works for all modes)
    if _repayAsset != empty(address):
        repayAmount: uint256 = _repayAmount

        if _shouldSweepAllForRepay:
            repayAmount = max_value(uint256)
        elif swapAmountOut != 0 and swapTokenOut == _repayAsset:
            repayAmount = swapAmountOut

        extcall Wallet(_levgWallet).repayDebt(
            ripeLegoId,
            _repayAsset,
            repayAmount if repayAmount != 0 else max_value(uint256),
            empty(bytes32)
        )


# compound yield gains


@external
def compoundYieldGains(
    _levgWallet: address,
    # step 1: remove from ripe
    _removeCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    # step 2: withdraw from yield
    _withdrawPositions: DynArray[PositionAsset, MAX_POSITIONS] = [],
    # step 3: swap to collateral token
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    # step 4: post-swap deposits (any position type, with optional add-to-ripe)
    _postSwapDeposits: DynArray[DepositYieldPosition, MAX_POSITIONS] = [],
    # step 5: add as collateral
    _addCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _sig: Signature = empty(Signature),
):
    # 1. authenticate access (action code 102)
    messageHash: bytes32 = keccak256(abi_encode(
        WORKFLOW_COMPOUND_YIELD,
        _levgWallet,
        _removeCollateral,
        _withdrawPositions,
        _swapInstructions,
        _postSwapDeposits,
        _addCollateral,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_levgWallet, messageHash, _sig)

    # 2. fetch position data
    collData: RipeAsset = empty(RipeAsset)
    levgData: RipeAsset = empty(RipeAsset)
    collUnderlyingAsset: address = empty(address)
    levgUnderlyingAsset: address = empty(address)
    collLegoId: uint256 = 0
    levgLegoId: uint256 = 0
    collData, levgData, collUnderlyingAsset, levgUnderlyingAsset, collLegoId, levgLegoId = self._fetchPositionData(_levgWallet)

    # track outputs for chaining
    withdrawAmount: uint256 = 0
    withdrawAsset: address = empty(address)
    swapAmountOut: uint256 = 0
    swapTokenOut: address = empty(address)
    ripeLegoId: uint256 = RIPE_LEGO_ID

    # step 1: remove collateral from ripe
    for op: PositionAsset in _removeCollateral:
        vaultToken: address = empty(address)
        ripeVaultId: uint256 = 0
        vaultToken, ripeVaultId = self._getCollateralData(op.positionType, collData, levgData)
        if vaultToken != empty(address):
            extcall Wallet(_levgWallet).removeCollateral(
                ripeLegoId,
                vaultToken,
                op.amount if op.amount != 0 else max_value(uint256),
                convert(ripeVaultId, bytes32)
            )

    # step 2: withdraw from yield
    for op: PositionAsset in _withdrawPositions:
        vaultToken: address = empty(address)
        legoId: uint256 = 0
        vaultToken, legoId = self._getWithdrawData(op.positionType, collData, levgData, collLegoId, levgLegoId)
        if vaultToken != empty(address):
            vaultTokensBurned: uint256 = 0
            txUsdValue: uint256 = 0
            vaultTokensBurned, withdrawAsset, withdrawAmount, txUsdValue = extcall Wallet(_levgWallet).withdrawFromYield(
                legoId,
                vaultToken,
                op.amount if op.amount != 0 else max_value(uint256),
                empty(bytes32),
                False
            )

    # step 3: swap to collateral token
    if len(_swapInstructions) != 0 and len(_swapInstructions[0].tokenPath) != 0:
        swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = _swapInstructions
        tokenIn: address = swapInstructions[0].tokenPath[0]
        tokenInBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(_levgWallet)

        # if first tokenIn matches withdrawAsset, use withdrawAmount as input
        if withdrawAmount != 0 and tokenIn == withdrawAsset:
            swapInstructions[0].amountIn = min(withdrawAmount, tokenInBalance)
        else:
            swapInstructions[0].amountIn = min(swapInstructions[0].amountIn, tokenInBalance)

        tokenInResult: address = empty(address)
        amountIn: uint256 = 0
        swapUsdValue: uint256 = 0
        tokenInResult, amountIn, swapTokenOut, swapAmountOut, swapUsdValue = extcall Wallet(_levgWallet).swapTokens(swapInstructions)

    # step 4: post-swap deposits
    for op: DepositYieldPosition in _postSwapDeposits:
        depositAmount: uint256 = op.amount

        if op.shouldSweepAll:
            depositAmount = max_value(uint256)
        elif swapAmountOut != 0:
            depositUnderlying: address = empty(address)
            if op.positionType == POSITION_COLLATERAL:
                depositUnderlying = collUnderlyingAsset
            elif op.positionType == POSITION_LEVERAGE:
                depositUnderlying = levgUnderlyingAsset
            elif op.positionType == POSITION_STAB_POOL:
                depositUnderlying = GREEN

            # if swap output matches deposit's underlying asset, use swapAmountOut
            if swapTokenOut == depositUnderlying:
                depositAmount = swapAmountOut

        modifiedOp: DepositYieldPosition = DepositYieldPosition(
            positionType=op.positionType,
            amount=depositAmount,
            shouldAddToRipeCollateral=op.shouldAddToRipeCollateral,
            shouldSweepAll=False
        )
        self._processDeposit(
            _levgWallet,
            modifiedOp,
            collData,
            levgData,
            collLegoId,
            levgLegoId,
            collUnderlyingAsset,
            levgUnderlyingAsset
        )

    # step 5: add as collateral
    for op: PositionAsset in _addCollateral:
        vaultToken: address = empty(address)
        ripeVaultId: uint256 = 0
        vaultToken, ripeVaultId = self._getCollateralData(op.positionType, collData, levgData)
        if vaultToken != empty(address):
            extcall Wallet(_levgWallet).addCollateral(
                ripeLegoId,
                vaultToken,
                op.amount if op.amount != 0 else max_value(uint256),
                convert(ripeVaultId, bytes32)
            )


####################
# Position Helpers #
####################


@view
@internal
def _fetchPositionData(_levgWallet: address) -> (RipeAsset, RipeAsset, address, address, uint256, uint256):
    collData: RipeAsset = staticcall LevgVaultWallet(_levgWallet).collateralAsset()
    levgData: RipeAsset = staticcall LevgVaultWallet(_levgWallet).leverageAsset()

    collUnderlyingAsset: address = empty(address)
    if collData.vaultToken != empty(address):
        collUnderlyingAsset = staticcall IERC4626(collData.vaultToken).asset()

    levgUnderlyingAsset: address = empty(address)
    if levgData.vaultToken != empty(address):
        levgUnderlyingAsset = staticcall IERC4626(levgData.vaultToken).asset()

    collLegoId: uint256 = staticcall LevgVaultWallet(_levgWallet).vaultToLegoId(collData.vaultToken)
    levgLegoId: uint256 = staticcall LevgVaultWallet(_levgWallet).vaultToLegoId(levgData.vaultToken)

    return collData, levgData, collUnderlyingAsset, levgUnderlyingAsset, collLegoId, levgLegoId


@view
@internal
def _getCollateralData(
    _positionType: uint8,
    _collData: RipeAsset,
    _levgData: RipeAsset,
) -> (address, uint256):
    if _positionType == POSITION_COLLATERAL:
        return _collData.vaultToken, _collData.ripeVaultId
    elif _positionType == POSITION_LEVERAGE:
        return _levgData.vaultToken, _levgData.ripeVaultId
    elif _positionType == POSITION_STAB_POOL:
        return SAVINGS_GREEN, RIPE_STAB_POOL_ID
    else:
        return empty(address), 0


@view
@internal
def _getWithdrawData(
    _positionType: uint8,
    _collData: RipeAsset,
    _levgData: RipeAsset,
    _collLegoId: uint256,
    _levgLegoId: uint256,
) -> (address, uint256):
    if _positionType == POSITION_COLLATERAL:
        return _collData.vaultToken, _collLegoId
    elif _positionType == POSITION_LEVERAGE:
        return _levgData.vaultToken, _levgLegoId
    elif _positionType == POSITION_STAB_POOL:
        return SAVINGS_GREEN, RIPE_LEGO_ID
    else:
        return empty(address), 0


@view
@internal
def _getDepositData(
    _positionType: uint8,
    _collData: RipeAsset,
    _levgData: RipeAsset,
    _collLegoId: uint256,
    _levgLegoId: uint256,
    _collUnderlyingAsset: address,
    _levgUnderlyingAsset: address,
) -> (address, address, uint256, uint256):
    if _positionType == POSITION_COLLATERAL:
        return _collData.vaultToken, _collUnderlyingAsset, _collLegoId, _collData.ripeVaultId
    elif _positionType == POSITION_LEVERAGE:
        return _levgData.vaultToken, _levgUnderlyingAsset, _levgLegoId, _levgData.ripeVaultId
    elif _positionType == POSITION_STAB_POOL:
        return SAVINGS_GREEN, GREEN, RIPE_LEGO_ID, RIPE_STAB_POOL_ID
    else:
        return empty(address), empty(address), 0, 0


@internal
def _processDeposit(
    _levgWallet: address,
    _deposit: DepositYieldPosition,
    _collData: RipeAsset,
    _levgData: RipeAsset,
    _collLegoId: uint256,
    _levgLegoId: uint256,
    _collUnderlyingAsset: address,
    _levgUnderlyingAsset: address,
):
    vaultToken: address = empty(address)
    underlyingAsset: address = empty(address)
    legoId: uint256 = 0
    ripeVaultId: uint256 = 0
    vaultToken, underlyingAsset, legoId, ripeVaultId = self._getDepositData(
        _deposit.positionType,
        _collData,
        _levgData,
        _collLegoId,
        _levgLegoId,
        _collUnderlyingAsset,
        _levgUnderlyingAsset
    )

    if vaultToken == empty(address) or underlyingAsset == empty(address):
        return

    # determine deposit amount
    depositAmount: uint256 = 0
    if _deposit.shouldSweepAll:
        depositAmount = max_value(uint256)
    elif _deposit.amount != 0:
        depositAmount = _deposit.amount
    else:
        depositAmount = max_value(uint256)

    vaultTokenReceived: uint256 = 0
    receivedVaultToken: address = empty(address)
    na: uint256 = 0
    na, receivedVaultToken, vaultTokenReceived, na = extcall Wallet(_levgWallet).depositForYield(
        legoId,
        underlyingAsset,
        vaultToken,
        depositAmount,
        empty(bytes32)
    )

    # optionally add to ripe collateral
    if _deposit.shouldAddToRipeCollateral and vaultTokenReceived != 0:
        extcall Wallet(_levgWallet).addCollateral(
            RIPE_LEGO_ID,
            receivedVaultToken,
            vaultTokenReceived,
            convert(ripeVaultId, bytes32)
        )


##################
# Authentication #
##################


@internal
def _authenticateAccess(_levgWallet: address, _messageHash: bytes32, _sig: Signature):
    owner: address = ownership.owner
    if msg.sender != owner:
        # check expiration first to prevent dos
        assert _sig.expiration >= block.timestamp # dev: signature expired

        # check nonce is valid
        assert _sig.nonce == self.currentNonce[_levgWallet] # dev: invalid nonce

        # verify this agent is a manager of the levg vault wallet
        assert staticcall LevgVaultWallet(_levgWallet).indexOfManager(self) != 0 # dev: not a manager

        # verify signature and check it's from owner
        signer: address = self._verify(_messageHash, _sig)
        assert signer == owner # dev: invalid signer

        # increment nonce for next use
        self._incrementNonce(_levgWallet)
    else:
        assert _sig.signature == empty(Bytes[65]) # dev: must be empty
        assert _sig.nonce == 0 # dev: must be 0
        assert _sig.expiration == 0 # dev: must be 0


@view
@internal
def _verify(_messageHash: bytes32, _sig: Signature) -> address:
    # extract signature components
    r: bytes32 = convert(slice(_sig.signature, 0, 32), bytes32)
    s: bytes32 = convert(slice(_sig.signature, 32, 32), bytes32)
    v: uint8 = convert(slice(_sig.signature, 64, 1), uint8)

    # validate v parameter (27 or 28)
    if v < 27:
        v = v + 27
    assert v == 27 or v == 28 # dev: invalid v parameter

    # prevent signature malleability by ensuring s is in lower half of curve order
    s_uint: uint256 = convert(s, uint256)
    assert s_uint != 0 # dev: invalid s value (zero)
    assert s_uint <= convert(0x7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF5D576E7357A4501DDFE92F46681B20A0, uint256) # dev: invalid s value

    # create digest with eip-712
    digest: bytes32 = keccak256(concat(SIG_PREFIX, self._domainSeparator(), _messageHash))

    # call ecrecover precompile
    result: Bytes[32] = raw_call(
        ECRECOVER_PRECOMPILE,
        abi_encode(digest, v, r, s),
        max_outsize=32,
        is_static_call=True
    )

    # return recovered address or empty if failed
    if len(result) != 32:
        return empty(address)

    recovered: address = abi_decode(result, address)
    assert recovered != empty(address) # dev: signature recovery failed
    return recovered


@view
@internal
def _domainSeparator() -> bytes32:
    return keccak256(abi_encode(
        keccak256('EIP712Domain(string name,uint256 chainId,address verifyingContract)'),
        keccak256('LevgVaultAgent'),
        chain.id,
        self
    ))


@external
def incrementNonce(_levgWallet: address):
    assert msg.sender == ownership.owner # dev: no perms
    self._incrementNonce(_levgWallet)


@internal
def _incrementNonce(_levgWallet: address):
    oldNonce: uint256 = self.currentNonce[_levgWallet]
    self.currentNonce[_levgWallet] = oldNonce + 1
    log NonceIncremented(levgVault=_levgWallet, oldNonce=oldNonce, newNonce=oldNonce + 1)


@view
@external
def getNonce(_levgWallet: address) -> uint256:
    return self.currentNonce[_levgWallet]
