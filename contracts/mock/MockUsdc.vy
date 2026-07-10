# @version 0.4.3
# Mock USDC for the payments tests: ERC20 + EIP-3009 `authorizationState` so the PayProcessor's
# refund guard can tell whether a merchant already pulled. `setAuthUsed` simulates a
# transferWithAuthorization consuming a nonce.

name: public(String[32])
symbol: public(String[32])
decimals: public(uint8)
totalSupply: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])
authorizationState: public(HashMap[address, HashMap[bytes32, bool]])   # authorizer -> nonce -> used
domainSeparatorOverride: public(bytes32)   # tests only: non-zero forces a domain mismatch for the deploy guard

@deploy
def __init__(_name: String[32], _symbol: String[32], _decimals: uint8):
    self.name = _name
    self.symbol = _symbol
    self.decimals = _decimals

@external
def mint(_to: address, _amount: uint256):
    self.balanceOf[_to] += _amount
    self.totalSupply += _amount

@external
def transfer(_to: address, _amount: uint256) -> bool:
    self.balanceOf[msg.sender] -= _amount
    self.balanceOf[_to] += _amount
    return True

@external
def transferFrom(_from: address, _to: address, _amount: uint256) -> bool:
    self.allowance[_from][msg.sender] -= _amount
    self.balanceOf[_from] -= _amount
    self.balanceOf[_to] += _amount
    return True

@external
def approve(_spender: address, _amount: uint256) -> bool:
    self.allowance[msg.sender][_spender] = _amount
    return True

@external
def setAuthUsed(_authorizer: address, _nonce: bytes32, _used: bool):
    # simulate transferWithAuthorization consuming (or freeing) an EIP-3009 nonce
    self.authorizationState[_authorizer][_nonce] = _used

@external
def setDomainSeparator(_d: bytes32):
    # tests: force DOMAIN_SEPARATOR() to a mismatching value to exercise the PayProcessor deploy guard
    self.domainSeparatorOverride = _d

@view
@external
def DOMAIN_SEPARATOR() -> bytes32:
    # mirrors the EIP-712 domain the PayProcessor hardcodes for native USDC ("USD Coin" / "2")
    if self.domainSeparatorOverride != empty(bytes32):
        return self.domainSeparatorOverride
    return keccak256(abi_encode(
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
        keccak256("USD Coin"),
        keccak256("2"),
        chain.id,
        self,
    ))
