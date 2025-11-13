#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

interface AgentWrapper:
    def getNonce(_userWallet: address) -> uint256: view

# unified signature validation
SIG_PREFIX: constant(bytes32) = 0x1901000000000000000000000000000000000000000000000000000000000000


@view
@internal
def _domainSeparator(_agentWrapper: address) -> bytes32:
    return keccak256(abi_encode(
        keccak256('EIP712Domain(string name,uint256 chainId,address verifyingContract)'),
        keccak256('UnderscoreAgent'),
        chain.id,
        _agentWrapper
    ))


@view
@internal
def _getFullDigest(_agentWrapper: address, _messageHash: bytes32) -> bytes32:
    """
    Get the full EIP-712 digest that needs to be signed
    """
    domain_separator: bytes32 = self._domainSeparator(_agentWrapper)
    return keccak256(concat(SIG_PREFIX, domain_separator, _messageHash))


@view
@internal
def _getNonce(_agentWrapper: address, _userWallet: address) -> uint256:
    return staticcall AgentWrapper(_agentWrapper).getNonce(_userWallet)


@view
@internal
def _getNonceAndExpiration(_agentWrapper: address, _userWallet: address, _nonce: uint256, _expiration: uint256) -> (uint256, uint256):
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    if _nonce == 0:
        nonce = self._getNonce(_agentWrapper, _userWallet)
    if _expiration == 0:
        expiration = block.timestamp + 3600  # 1 hour default
    
    return (nonce, expiration)

