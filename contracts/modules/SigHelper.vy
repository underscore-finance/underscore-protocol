#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

interface AgentSenderGeneric:
    def currentNonce(_userWallet: address) -> uint256: view

# unified signature validation
SIG_PREFIX: constant(bytes32) = 0x1901000000000000000000000000000000000000000000000000000000000000


@view
@internal
def _domainSeparator(_agentSender: address) -> bytes32:
    return keccak256(abi_encode(
        keccak256('EIP712Domain(string name,uint256 chainId,address verifyingContract)'),
        keccak256('UnderscoreAgent'),
        chain.id,
        _agentSender
    ))


@view
@internal
def _getFullDigest(_agentSender: address, _messageHash: bytes32) -> bytes32:
    """
    Get the full EIP-712 digest that needs to be signed
    """
    domain_separator: bytes32 = self._domainSeparator(_agentSender)
    return keccak256(concat(SIG_PREFIX, domain_separator, _messageHash))


@view
@internal
def _getNonce(_agentSender: address, _userWallet: address) -> uint256:
    return staticcall AgentSenderGeneric(_agentSender).currentNonce(_userWallet)


@view
@internal
def _getNonceAndExpiration(_agentSender: address, _userWallet: address, _nonce: uint256, _expiration: uint256) -> (uint256, uint256):
    nonce: uint256 = _nonce
    expiration: uint256 = _expiration
    if _nonce == 0:
        nonce = self._getNonce(_agentSender, _userWallet)
    if _expiration == 0:
        expiration = block.timestamp + 3600  # 1 hour default

    return (nonce, expiration)

