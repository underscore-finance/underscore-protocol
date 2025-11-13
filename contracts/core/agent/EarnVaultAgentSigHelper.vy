#     ╔════════════════════════════════════════════════════════════════════════════════╗
#     ║  ** Earn Vault Agent Signature Helper **                                       ║
#     ║  Generates message hashes for Earn Vault Agent signatures                      ║
#     ╚════════════════════════════════════════════════════════════════════════════════╝
#
#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

import contracts.modules.SigHelper as sigHelper

from interfaces import Wallet

struct ActionInstruction:
    usePrevAmountOut: bool     # Use output from previous instruction as amount
    action: uint8              # Action type: 10=depositYield, 11=withdrawYield
    legoId: uint16             # Protocol/Lego ID
    asset: address             # Primary asset/token (or vaultToken for withdrawals)
    target: address            # vaultAddr for deposits, unused for withdrawals
    amount: uint256            # Primary amount (or max_value for "all")
    extraData: bytes32         # Protocol-specific extra data


MAX_INSTRUCTIONS: constant(uint256) = 15
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_PROOFS: constant(uint256) = 25


#########
# Yield #
#########

@view
@external
def getDepositForYieldHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _asset: address,
    _vaultAddr: address = empty(address),
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for depositForYield function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(10, uint8), _userWallet, _legoId, _asset, _vaultAddr, _amount, _extraData, nonce, expiration))), nonce, expiration)


@view
@external
def getWithdrawFromYieldHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _vaultToken: address,
    _amount: uint256 = max_value(uint256),
    _extraData: bytes32 = empty(bytes32),
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for withdrawFromYield function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(11, uint8), _userWallet, _legoId, _vaultToken, _amount, _extraData, nonce, expiration))), nonce, expiration)



###################
# Swap / Exchange #
###################


@view
@external
def getSwapTokensHash(
    _agentWrapper: address,
    _userWallet: address,
    _swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for swapTokens function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(20, uint8), _userWallet, _swapInstructions, nonce, expiration))), nonce, expiration)



#################
# Claim Rewards #
#################

@view
@external
def getClaimIncentivesHash(
    _agentWrapper: address,
    _userWallet: address,
    _legoId: uint256,
    _rewardToken: address = empty(address),
    _rewardAmount: uint256 = max_value(uint256),
    _proofs: DynArray[bytes32, MAX_PROOFS] = [],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for claimIncentives function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(convert(50, uint8), _userWallet, _legoId, _rewardToken, _rewardAmount, _proofs, nonce, expiration))), nonce, expiration)



#################
# Batch Actions #
#################


@view
@external
def getBatchActionsHash(
    _agentWrapper: address,
    _userWallet: address,
    _instructions: DynArray[ActionInstruction, MAX_INSTRUCTIONS],
    _nonce: uint256 = 0,
    _expiration: uint256 = 0,
) -> (bytes32, uint256, uint256):
    """
    Get message hash for performBatchActions function
    """
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    nonce, expiration = sigHelper._getNonceAndExpiration(_agentWrapper, _userWallet, _nonce, _expiration)
    return (sigHelper._getFullDigest(_agentWrapper, keccak256(abi_encode(_userWallet, _instructions, nonce, expiration))), nonce, expiration)
