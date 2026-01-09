#     ╔════════════════════════════════════════════════════════════════════════════════╗
#     ║  ** Leverage Vault Agent Signature Helper **                                   ║
#     ║  Generates message hashes for LevgVaultAgent signatures                        ║
#     ╚════════════════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

import contracts.modules.SigHelper as sigHelper
from interfaces import Wallet

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

# max on lists
MAX_DELEVERAGE_ASSETS: constant(uint256) = 25
MAX_POSITIONS: constant(uint256) = 10
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5

# workflow action codes
WORKFLOW_BORROW_AND_EARN: constant(uint8) = 100
WORKFLOW_DELEVERAGE: constant(uint8) = 101
WORKFLOW_COMPOUND_YIELD: constant(uint8) = 102

# domain name hash for LevgVaultAgent
DOMAIN_NAME_HASH: constant(bytes32) = keccak256('LevgVaultAgent')


#####################
# Borrow & Earn     #
#####################


@view
@external
def getBorrowAndEarnYieldHash(
    _levgVaultAgent: address,
    _levgWallet: address,
    _removeCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _withdrawPositions: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _depositPositions: DynArray[DepositYieldPosition, MAX_POSITIONS] = [],
    _addCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _borrowAmount: uint256 = 0,
    _wantsSavingsGreen: bool = True,
    _shouldEnterStabPool: bool = True,
    _swapInstruction: Wallet.SwapInstruction = empty(Wallet.SwapInstruction),
    _postSwapDeposits: DynArray[DepositYieldPosition, MAX_POSITIONS] = [],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for borrowAndEarnYield function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_levgVaultAgent, _levgWallet, _nonce, _expiration)

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
        _swapInstruction,
        _postSwapDeposits,
        nonce,
        expiration
    ))

    return (sigHelper._getFullDigest(_levgVaultAgent, messageHash, DOMAIN_NAME_HASH), nonce, expiration)


##############
# Deleverage #
##############


@view
@external
def getDeleverageHash(
    _levgVaultAgent: address,
    _levgWallet: address,
    _mode: uint8 = 0,
    _autoDeleverageAmount: uint256 = 0,
    _deleverageAssets: DynArray[DeleverageAsset, MAX_DELEVERAGE_ASSETS] = [],
    _removeCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _withdrawPositions: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _swapInstruction: Wallet.SwapInstruction = empty(Wallet.SwapInstruction),
    _repayAsset: address = empty(address),
    _repayAmount: uint256 = 0,
    _shouldSweepAllForRepay: bool = False,
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for deleverage function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_levgVaultAgent, _levgWallet, _nonce, _expiration)

    messageHash: bytes32 = keccak256(abi_encode(
        WORKFLOW_DELEVERAGE,
        _levgWallet,
        _mode,
        _autoDeleverageAmount,
        _deleverageAssets,
        _removeCollateral,
        _withdrawPositions,
        _swapInstruction,
        _repayAsset,
        _repayAmount,
        _shouldSweepAllForRepay,
        nonce,
        expiration
    ))

    return (sigHelper._getFullDigest(_levgVaultAgent, messageHash, DOMAIN_NAME_HASH), nonce, expiration)


#######################
# Compound Yield Gains #
#######################


@view
@external
def getCompoundYieldGainsHash(
    _levgVaultAgent: address,
    _levgWallet: address,
    _removeCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _withdrawPositions: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _swapInstruction: Wallet.SwapInstruction = empty(Wallet.SwapInstruction),
    _postSwapDeposits: DynArray[DepositYieldPosition, MAX_POSITIONS] = [],
    _addCollateral: DynArray[PositionAsset, MAX_POSITIONS] = [],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for compoundYieldGains function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_levgVaultAgent, _levgWallet, _nonce, _expiration)

    messageHash: bytes32 = keccak256(abi_encode(
        WORKFLOW_COMPOUND_YIELD,
        _levgWallet,
        _removeCollateral,
        _withdrawPositions,
        _swapInstruction,
        _postSwapDeposits,
        _addCollateral,
        nonce,
        expiration
    ))

    return (sigHelper._getFullDigest(_levgVaultAgent, messageHash, DOMAIN_NAME_HASH), nonce, expiration)
