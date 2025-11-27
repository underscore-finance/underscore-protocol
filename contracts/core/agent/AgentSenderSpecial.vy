#            _            _            _             _            _            _      
#           / /\         /\ \         /\ \     _    /\ \         /\ \         /\ \    
#          / /  \       /  \ \       /  \ \   /\_\ /  \ \____   /  \ \       /  \ \   
#         / / /\ \__   / /\ \ \     / /\ \ \_/ / // /\ \_____\ / /\ \ \     / /\ \ \  
#        / / /\ \___\ / / /\ \_\   / / /\ \___/ // / /\/___  // / /\ \_\   / / /\ \_\ 
#        \ \ \ \/___// /_/_ \/_/  / / /  \/____// / /   / / // /_/_ \/_/  / / /_/ / / 
#         \ \ \     / /____/\    / / /    / / // / /   / / // /____/\    / / /__\/ /  
#     _    \ \ \   / /\____\/   / / /    / / // / /   / / // /\____\/   / / /_____/   
#    /_/\__/ / /  / / /______  / / /    / / / \ \ \__/ / // / /______  / / /\ \ \     
#    \ \/___/ /  / / /_______\/ / /    / / /   \ \___\/ // / /_______\/ / /  \ \ \    
#     \_____\/   \/__________/\/_/     \/_/     \/_____/ \/__________/\/_/    \_\/    
#
#     ╔═══════════════════════════════════════════════════════════════════╗
#     ║  ** Agent Sender - Special Workflows **                           ║
#     ║  Special sender with batch actions and signature verification.    ║
#     ╚═══════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

initializes: ownership
exports: ownership.__interface__
import contracts.modules.Ownership as ownership

from interfaces import Wallet
from interfaces import AgentWrapper
from ethereum.ercs import IERC20

interface RipeLego:
    def deleverageWithSpecificAssets(_assets: DynArray[DeleverageAsset, MAX_DELEVERAGE_ASSETS], _user: address) -> uint256: nonpayable

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct CollateralAsset:
    vaultId: uint256
    asset: address
    amount: uint256

struct DeleverageAsset:
    vaultId: uint256
    asset: address
    targetRepayAmount: uint256

struct DepositYieldPosition:
    legoId: uint256
    asset: address
    amount: uint256
    vaultAddr: address

struct WithdrawYieldPosition:
    legoId: uint256
    vaultToken: address
    vaultTokenAmount: uint256

struct TransferData:
    asset: address
    amount: uint256
    recipient: address

struct Signature:
    signature: Bytes[65]
    nonce: uint256
    expiration: uint256

event NonceIncremented:
    userWallet: address
    oldNonce: uint256
    newNonce: uint256

currentNonce: public(HashMap[address, uint256])

MAX_COLLATERAL_ASSETS: constant(uint256) = 10
MAX_DELEVERAGE_ASSETS: constant(uint256) = 25
MAX_YIELD_POSITIONS: constant(uint256) = 25
MAX_INSTRUCTIONS: constant(uint256) = 15
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25
LEGO_BOOK_ID: constant(uint256) = 3

# unified signature validation
ECRECOVER_PRECOMPILE: constant(address) = 0x0000000000000000000000000000000000000001
SIG_PREFIX: constant(bytes32) = 0x1901000000000000000000000000000000000000000000000000000000000000

# core
UNDY_HQ: public(immutable(address))
RIPE_GREEN_TOKEN: public(immutable(address))
RIPE_SAVINGS_GREEN: public(immutable(address))


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
    RIPE_GREEN_TOKEN = _greenToken
    RIPE_SAVINGS_GREEN = _savingsGreen


#########################
# Specialized Workflows #
#########################


# add collateral + borrow + swap (optional) + yield (optional)


@external
def addCollateralAndBorrow(
    _agentWrapper: address,
    _userWallet: address,
    _debtLegoId: uint256,
    _addCollateralAssets: DynArray[CollateralAsset, MAX_COLLATERAL_ASSETS] = [],
    _greenBorrowAmount: uint256 = 0,
    _wantsSavingsGreen: bool = True,
    _shouldEnterStabPool: bool = False,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    _yieldPosition: DepositYieldPosition = empty(DepositYieldPosition),
    _sig: Signature = empty(Signature),
):
    # 1. authenticate access (action code 100)
    messageHash: bytes32 = keccak256(abi_encode(
        convert(100, uint8),
        _userWallet,
        _debtLegoId,
        _addCollateralAssets,
        _greenBorrowAmount,
        _wantsSavingsGreen,
        _shouldEnterStabPool,
        _swapInstructions,
        _yieldPosition,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_userWallet, messageHash, _sig)

    # track outputs for chaining
    borrowAmount: uint256 = 0
    borrowAsset: address = empty(address)
    swapAmountOut: uint256 = 0
    swapTokenOut: address = empty(address)

    # 2. add collateral
    for collateralAsset: CollateralAsset in _addCollateralAssets:
        if collateralAsset.asset != empty(address) and collateralAsset.amount != 0:
            collateralAmount: uint256 = min(collateralAsset.amount, staticcall IERC20(collateralAsset.asset).balanceOf(_userWallet))
            if collateralAmount != 0:
                collateralExtraData: bytes32 = convert(collateralAsset.vaultId, bytes32)
                extcall AgentWrapper(_agentWrapper).addCollateral(
                    _userWallet,
                    _debtLegoId,
                    collateralAsset.asset,
                    collateralAmount,
                    collateralExtraData
                )

    # 3. borrow
    if _greenBorrowAmount != 0:
        borrowAsset = RIPE_SAVINGS_GREEN if _wantsSavingsGreen else RIPE_GREEN_TOKEN
        borrowExtraData: bytes32 = convert(convert(_shouldEnterStabPool, uint256), bytes32) # encode _shouldEnterStabPool in extraData
        usdValue: uint256 = 0
        borrowAmount, usdValue = extcall AgentWrapper(_agentWrapper).borrow(
            _userWallet,
            _debtLegoId,
            borrowAsset,
            _greenBorrowAmount,
            borrowExtraData
        )

    # 4. swap tokens
    if len(_swapInstructions) != 0 and len(_swapInstructions[0].tokenPath) != 0:
        swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = _swapInstructions
        tokenIn: address = swapInstructions[0].tokenPath[0]
        swapBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(_userWallet)

        # if first tokenIn matches borrowAsset, use borrowAmount as input
        if borrowAmount != 0 and tokenIn == borrowAsset:
            swapInstructions[0].amountIn = min(borrowAmount, swapBalance)
        else:
            swapInstructions[0].amountIn = min(swapInstructions[0].amountIn, swapBalance)

        tokenInResult: address = empty(address)
        amountIn: uint256 = 0
        swapUsdValue: uint256 = 0
        tokenInResult, amountIn, swapTokenOut, swapAmountOut, swapUsdValue = extcall AgentWrapper(_agentWrapper).swapTokens(
            _userWallet,
            swapInstructions
        )

    # 5. deposit for yield
    if _yieldPosition.legoId != 0 and _yieldPosition.asset != empty(address):
        yieldAmount: uint256 = staticcall IERC20(_yieldPosition.asset).balanceOf(_userWallet)

        if _yieldPosition.amount != 0 and _yieldPosition.amount != max_value(uint256):
            yieldAmount = min(_yieldPosition.amount, yieldAmount)
        elif swapTokenOut == _yieldPosition.asset and swapAmountOut != 0:
            yieldAmount = min(swapAmountOut, yieldAmount)

        if yieldAmount != 0:
            extcall AgentWrapper(_agentWrapper).depositForYield(
                _userWallet,
                _yieldPosition.legoId,
                _yieldPosition.asset,
                _yieldPosition.vaultAddr,
                yieldAmount,
                empty(bytes32)
            )


# deleverage + withdraw yield + swap + repay + remove collateral assets


@external
def repayAndWithdraw(
    _agentWrapper: address,
    _userWallet: address,
    _debtLegoId: uint256,
    _deleverageAssets: DynArray[DeleverageAsset, MAX_DELEVERAGE_ASSETS] = [],
    _yieldPosition: WithdrawYieldPosition = empty(WithdrawYieldPosition),
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    _repayAsset: address = empty(address),
    _repayAmount: uint256 = max_value(uint256),
    _removeCollateralAssets: DynArray[CollateralAsset, MAX_COLLATERAL_ASSETS] = [],
    _sig: Signature = empty(Signature),
):
    # 1. authenticate access (action code 101)
    messageHash: bytes32 = keccak256(abi_encode(
        convert(101, uint8),
        _userWallet,
        _debtLegoId,
        _deleverageAssets,
        _yieldPosition,
        _swapInstructions,
        _repayAsset,
        _repayAmount,
        _removeCollateralAssets,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_userWallet, messageHash, _sig)

    # track outputs for chaining
    withdrawAmount: uint256 = 0
    withdrawAsset: address = empty(address)
    swapAmountOut: uint256 = 0
    swapTokenOut: address = empty(address)

    # 2. deleverage
    if len(_deleverageAssets) != 0:
        legoBook: address = staticcall Registry(UNDY_HQ).getAddr(LEGO_BOOK_ID)
        debtLego: address = staticcall Registry(legoBook).getAddr(_debtLegoId)
        extcall RipeLego(debtLego).deleverageWithSpecificAssets(_deleverageAssets, _userWallet)

    # 3. withdraw from yield
    if _yieldPosition.legoId != 0 and _yieldPosition.vaultToken != empty(address):
        vaultWithdrawAmount: uint256 = staticcall IERC20(_yieldPosition.vaultToken).balanceOf(_userWallet)

        if _yieldPosition.vaultTokenAmount != 0 and _yieldPosition.vaultTokenAmount != max_value(uint256):
            vaultWithdrawAmount = min(_yieldPosition.vaultTokenAmount, vaultWithdrawAmount)

        if vaultWithdrawAmount != 0:
            vaultTokensUsed: uint256 = 0
            txUsdValue: uint256 = 0
            vaultTokensUsed, withdrawAsset, withdrawAmount, txUsdValue = extcall AgentWrapper(_agentWrapper).withdrawFromYield(
                _userWallet,
                _yieldPosition.legoId,
                _yieldPosition.vaultToken,
                vaultWithdrawAmount,
                empty(bytes32)
            )

    # 4. swap tokens
    if len(_swapInstructions) != 0 and len(_swapInstructions[0].tokenPath) != 0:
        swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = _swapInstructions
        tokenIn: address = swapInstructions[0].tokenPath[0]
        swapBalance: uint256 = staticcall IERC20(tokenIn).balanceOf(_userWallet)

        # if first tokenIn matches withdrawAsset, use withdrawAmount as input
        if withdrawAmount != 0 and tokenIn == withdrawAsset:
            swapInstructions[0].amountIn = min(withdrawAmount, swapBalance)
        else:
            swapInstructions[0].amountIn = min(swapInstructions[0].amountIn, swapBalance)

        tokenInResult: address = empty(address)
        amountIn: uint256 = 0
        swapUsdValue: uint256 = 0
        tokenInResult, amountIn, swapTokenOut, swapAmountOut, swapUsdValue = extcall AgentWrapper(_agentWrapper).swapTokens(
            _userWallet,
            swapInstructions
        )

    # 5. repay debt
    if _repayAsset != empty(address):
        repayAmount: uint256 = min(_repayAmount, staticcall IERC20(_repayAsset).balanceOf(_userWallet))

        # if swapTokenOut matches repayAsset, use min of swapAmountOut and balance
        if swapTokenOut == _repayAsset and swapAmountOut != 0:
            repayAmount = min(swapAmountOut, repayAmount)

        if repayAmount != 0:
            extcall AgentWrapper(_agentWrapper).repayDebt(
                _userWallet,
                _debtLegoId,
                _repayAsset,
                repayAmount,
                empty(bytes32)
            )

    # 6. remove collateral
    for collateralAsset: CollateralAsset in _removeCollateralAssets:
        if collateralAsset.asset != empty(address) and collateralAsset.amount != 0:
            collateralExtraData: bytes32 = convert(collateralAsset.vaultId, bytes32)
            extcall AgentWrapper(_agentWrapper).removeCollateral(
                _userWallet,
                _debtLegoId,
                collateralAsset.asset,
                collateralAsset.amount,
                collateralExtraData
            )


# rebalance yield positions + swap (optional) + deposit (optional) or transfer (optional)


@external
def rebalanceYieldPositionsWithSwap(
    _agentWrapper: address,
    _userWallet: address,
    _withdrawFrom: DynArray[WithdrawYieldPosition, MAX_YIELD_POSITIONS] = [],
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    _depositTo: DynArray[DepositYieldPosition, MAX_YIELD_POSITIONS] = [],
    _transferTo: DynArray[TransferData, MAX_COLLATERAL_ASSETS] = [],
    _sig: Signature = empty(Signature),
):
    # 1. authenticate access (action code 102)
    messageHash: bytes32 = keccak256(abi_encode(
        convert(102, uint8),
        _userWallet,
        _withdrawFrom,
        _swapInstructions,
        _depositTo,
        _transferTo,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_userWallet, messageHash, _sig)

    # 2. withdraw from yield positions
    for position: WithdrawYieldPosition in _withdrawFrom:
        if position.legoId != 0 and position.vaultToken != empty(address):
            vaultWithdrawAmount: uint256 = staticcall IERC20(position.vaultToken).balanceOf(_userWallet)

            if position.vaultTokenAmount != 0 and position.vaultTokenAmount != max_value(uint256):
                vaultWithdrawAmount = min(position.vaultTokenAmount, vaultWithdrawAmount)

            if vaultWithdrawAmount != 0:
                extcall AgentWrapper(_agentWrapper).withdrawFromYield(
                    _userWallet,
                    position.legoId,
                    position.vaultToken,
                    vaultWithdrawAmount,
                    empty(bytes32)
                )

    # 3. swap tokens
    if len(_swapInstructions) != 0 and len(_swapInstructions[0].tokenPath) != 0:
        swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = _swapInstructions
        tokenIn: address = swapInstructions[0].tokenPath[0]
        swapInstructions[0].amountIn = min(swapInstructions[0].amountIn, staticcall IERC20(tokenIn).balanceOf(_userWallet))

        extcall AgentWrapper(_agentWrapper).swapTokens(_userWallet, swapInstructions)

    # 4. either deposit to yield OR transfer
    if len(_depositTo) != 0:
        for position: DepositYieldPosition in _depositTo:
            if position.legoId != 0 and position.asset != empty(address):
                yieldAmount: uint256 = staticcall IERC20(position.asset).balanceOf(_userWallet)

                if position.amount != 0 and position.amount != max_value(uint256):
                    yieldAmount = min(position.amount, yieldAmount)

                if yieldAmount != 0:
                    extcall AgentWrapper(_agentWrapper).depositForYield(
                        _userWallet,
                        position.legoId,
                        position.asset,
                        position.vaultAddr,
                        yieldAmount,
                        empty(bytes32)
                    )

    elif len(_transferTo) != 0:
        for transfer: TransferData in _transferTo:
            if transfer.asset != empty(address) and transfer.recipient != empty(address):
                transferAmount: uint256 = staticcall IERC20(transfer.asset).balanceOf(_userWallet)

                if transfer.amount != 0 and transfer.amount != max_value(uint256):
                    transferAmount = min(transfer.amount, transferAmount)

                if transferAmount != 0:
                    extcall AgentWrapper(_agentWrapper).transferFunds(
                        _userWallet,
                        transfer.recipient,
                        transfer.asset,
                        transferAmount,
                        False
                    )


# claim rewards + swap (optional) + deposit into yield (optional) + add collateral (optional)


@external
def claimIncentivesAndSwap(
    _agentWrapper: address,
    _userWallet: address,
    _rewardLegoId: uint256 = 0,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _rewardProofs: DynArray[bytes32, MAX_PROOFS] = [],
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    _depositTo: DynArray[DepositYieldPosition, MAX_YIELD_POSITIONS] = [],
    _debtLegoId: uint256 = 0,
    _addCollateralAssets: DynArray[CollateralAsset, MAX_COLLATERAL_ASSETS] = [],
    _sig: Signature = empty(Signature),
):
    # 1. authenticate access (action code 103)
    messageHash: bytes32 = keccak256(abi_encode(
        convert(103, uint8),
        _userWallet,
        _rewardLegoId,
        _rewardToken,
        _rewardAmount,
        _rewardProofs,
        _swapInstructions,
        _depositTo,
        _debtLegoId,
        _addCollateralAssets,
        _sig.nonce,
        _sig.expiration
    ))
    self._authenticateAccess(_userWallet, messageHash, _sig)

    # 2. claim incentives
    if _rewardLegoId != 0 and _rewardToken != empty(address):
        extcall AgentWrapper(_agentWrapper).claimIncentives(
            _userWallet,
            _rewardLegoId,
            _rewardToken,
            _rewardAmount,
            _rewardProofs
        )

    # 3. swap tokens
    if len(_swapInstructions) != 0 and len(_swapInstructions[0].tokenPath) != 0:
        swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = _swapInstructions
        tokenIn: address = swapInstructions[0].tokenPath[0]
        swapInstructions[0].amountIn = min(swapInstructions[0].amountIn, staticcall IERC20(tokenIn).balanceOf(_userWallet))
        extcall AgentWrapper(_agentWrapper).swapTokens(_userWallet, swapInstructions)

    # 4. deposit to yield
    for position: DepositYieldPosition in _depositTo:
        if position.legoId != 0 and position.asset != empty(address):
            yieldAmount: uint256 = staticcall IERC20(position.asset).balanceOf(_userWallet)

            if position.amount != 0 and position.amount != max_value(uint256):
                yieldAmount = min(position.amount, yieldAmount)

            if yieldAmount != 0:
                extcall AgentWrapper(_agentWrapper).depositForYield(
                    _userWallet,
                    position.legoId,
                    position.asset,
                    position.vaultAddr,
                    yieldAmount,
                    empty(bytes32)
                )

    # 5. add collateral
    if _debtLegoId != 0:
        for collateralAsset: CollateralAsset in _addCollateralAssets:
            if collateralAsset.asset != empty(address) and collateralAsset.amount != 0:
                collateralAmount: uint256 = min(collateralAsset.amount, staticcall IERC20(collateralAsset.asset).balanceOf(_userWallet))
                if collateralAmount != 0:
                    collateralExtraData: bytes32 = convert(collateralAsset.vaultId, bytes32)
                    extcall AgentWrapper(_agentWrapper).addCollateral(
                        _userWallet,
                        _debtLegoId,
                        collateralAsset.asset,
                        collateralAmount,
                        collateralExtraData
                    )


##################
# Authentication #
##################


@internal
def _authenticateAccess(_userWallet: address, _messageHash: bytes32, _sig: Signature):
    owner: address = ownership.owner
    if msg.sender != owner:
        # check expiration first to prevent DoS
        assert _sig.expiration >= block.timestamp # dev: signature expired

        # check nonce is valid
        assert _sig.nonce == self.currentNonce[_userWallet] # dev: invalid nonce

        # verify signature and check it's from owner
        signer: address = self._verify(_messageHash, _sig)
        assert signer == owner # dev: invalid signer

        # increment nonce for next use
        self._incrementNonce(_userWallet)
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

    # create digest with EIP-712
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
        keccak256('UnderscoreAgent'),
        chain.id,
        self
    ))


@external
def incrementNonce(_userWallet: address):
    assert msg.sender == ownership.owner # dev: no perms
    self._incrementNonce(_userWallet)


@internal
def _incrementNonce(_userWallet: address):
    oldNonce: uint256 = self.currentNonce[_userWallet]
    self.currentNonce[_userWallet] = oldNonce + 1
    log NonceIncremented(userWallet=_userWallet, oldNonce=oldNonce, newNonce=oldNonce + 1)


@view
@external
def getNonce(_userWallet: address) -> uint256:
    return self.currentNonce[_userWallet]
