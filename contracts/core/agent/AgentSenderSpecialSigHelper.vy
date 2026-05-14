#     ╔════════════════════════════════════════════════════════════════════════════════╗
#     ║  ** Signature Helper - Special Workflows **                                   ║
#     ║  Generates message hashes for AgentSenderSpecial signatures                   ║
#     ╚════════════════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

import contracts.modules.SigHelper as sigHelper
from interfaces import Wallet
from interfaces import WalletStructs as ws

struct CollateralAsset:
    vaultId: uint256
    asset: address
    amount: uint256

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

struct ChequeInstruction:
    recipient: address
    asset: address
    amount: uint256
    unlockNumBlocks: uint256
    expiryNumBlocks: uint256
    canManagerPay: bool
    canBePulled: bool

MAX_COLLATERAL_ASSETS: constant(uint256) = 10
MAX_YIELD_POSITIONS: constant(uint256) = 25
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25
MAX_CHEQUES: constant(uint256) = 25
MAX_WHITELIST_ADDRS: constant(uint256) = 25


################################
# Add Collateral + Borrow     #
################################


@view
@external
def getAddCollateralAndBorrowHash(
    _agentSender: address,
    _agentWrapper: address,
    _userWallet: address,
    _debtLegoId: uint256,
    _addCollateralAssets: DynArray[CollateralAsset, MAX_COLLATERAL_ASSETS] = [],
    _greenBorrowAmount: uint256 = 0,
    _wantsSavingsGreen: bool = True,
    _shouldEnterStabPool: bool = False,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    _yieldPosition: DepositYieldPosition = empty(DepositYieldPosition),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for addCollateralAndBorrow function (action code 100)
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentSender, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentSender, keccak256(abi_encode(
        convert(100, uint8),
        _agentWrapper,
        _userWallet,
        _debtLegoId,
        _addCollateralAssets,
        _greenBorrowAmount,
        _wantsSavingsGreen,
        _shouldEnterStabPool,
        _swapInstructions,
        _yieldPosition,
        nonce,
        expiration
    ))), nonce, expiration)


#############################
# Repay + Withdraw          #
#############################


@view
@external
def getRepayAndWithdrawHash(
    _agentSender: address,
    _agentWrapper: address,
    _userWallet: address,
    _debtLegoId: uint256,
    _deleverageAssets: DynArray[ws.DeleverageAsset, 10] = [],
    _yieldPosition: WithdrawYieldPosition = empty(WithdrawYieldPosition),
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    _repayAsset: address = empty(address),
    _repayAmount: uint256 = max_value(uint256),
    _removeCollateralAssets: DynArray[CollateralAsset, MAX_COLLATERAL_ASSETS] = [],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for repayAndWithdraw function (action code 101)
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentSender, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentSender, keccak256(abi_encode(
        convert(101, uint8),
        _agentWrapper,
        _userWallet,
        _debtLegoId,
        _deleverageAssets,
        _yieldPosition,
        _swapInstructions,
        _repayAsset,
        _repayAmount,
        _removeCollateralAssets,
        nonce,
        expiration
    ))), nonce, expiration)


##########################################
# Rebalance Yield Positions + Swap       #
##########################################


@view
@external
def getRebalanceYieldPositionsWithSwapHash(
    _agentSender: address,
    _agentWrapper: address,
    _userWallet: address,
    _withdrawFrom: DynArray[WithdrawYieldPosition, MAX_YIELD_POSITIONS] = [],
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    _depositTo: DynArray[DepositYieldPosition, MAX_YIELD_POSITIONS] = [],
    _transferTo: DynArray[TransferData, MAX_COLLATERAL_ASSETS] = [],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for rebalanceYieldPositionsWithSwap function (action code 102)
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentSender, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentSender, keccak256(abi_encode(
        convert(102, uint8),
        _agentWrapper,
        _userWallet,
        _withdrawFrom,
        _swapInstructions,
        _depositTo,
        _transferTo,
        nonce,
        expiration
    ))), nonce, expiration)


#####################################
# Claim Incentives + Swap           #
#####################################


@view
@external
def getClaimIncentivesAndSwapHash(
    _agentSender: address,
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
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for claimIncentivesAndSwap function (action code 103)
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentSender, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentSender, keccak256(abi_encode(
        convert(103, uint8),
        _agentWrapper,
        _userWallet,
        _rewardLegoId,
        _rewardToken,
        _rewardAmount,
        _rewardProofs,
        _swapInstructions,
        _depositTo,
        _debtLegoId,
        _addCollateralAssets,
        nonce,
        expiration
    ))), nonce, expiration)


######################
# Issue Pull Cheques #
######################


@view
@external
def getIssuePullChequesHash(
    _agentSender: address,
    _agentWrapper: address,
    _userWallet: address,
    _cheques: DynArray[ChequeInstruction, MAX_CHEQUES],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for issuePullCheques function (action code 104)
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentSender, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentSender, keccak256(abi_encode(
        convert(104, uint8),
        _agentWrapper,
        _userWallet,
        _cheques,
        nonce,
        expiration
    ))), nonce, expiration)


#########################
# Whitelist Maintenance #
#########################


@view
@external
def getWhitelistMaintenanceHash(
    _agentSender: address,
    _agentWrapper: address,
    _userWallet: address,
    _confirmAddrs: DynArray[address, MAX_WHITELIST_ADDRS] = [],
    _cancelPendingAddrs: DynArray[address, MAX_WHITELIST_ADDRS] = [],
    _removeAddrs: DynArray[address, MAX_WHITELIST_ADDRS] = [],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for whitelistMaintenance function (action code 105)
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentSender, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentSender, keccak256(abi_encode(
        convert(105, uint8),
        _agentWrapper,
        _userWallet,
        _confirmAddrs,
        _cancelPendingAddrs,
        _removeAddrs,
        nonce,
        expiration
    ))), nonce, expiration)


############################
# Harvest And Issue Cheque #
############################


@view
@external
def getHarvestAndIssueChequeHash(
    _agentSender: address,
    _agentWrapper: address,
    _userWallet: address,
    _rewardLegoId: uint256 = 0,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _rewardProofs: DynArray[bytes32, MAX_PROOFS] = [],
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS] = [],
    _cheque: ChequeInstruction = empty(ChequeInstruction),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for harvestAndIssueCheque function (action code 106)
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentSender, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentSender, keccak256(abi_encode(
        convert(106, uint8),
        _agentWrapper,
        _userWallet,
        _rewardLegoId,
        _rewardToken,
        _rewardAmount,
        _rewardProofs,
        _swapInstructions,
        _cheque,
        nonce,
        expiration
    ))), nonce, expiration)
