# @version 0.4.3

# A typed false-return token. Short, missing, malformed-bool, and oversized
# returndata are expressed with the bounded inline EVM shims documented in the
# wallet-v3 test fixture.

balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])


@external
def mint(to: address, amount: uint256):
    self.balanceOf[to] += amount


@external
def transfer(to: address, amount: uint256) -> bool:
    return False


@external
def approve(spender: address, amount: uint256) -> bool:
    return False


@external
def transferFrom(owner: address, to: address, amount: uint256) -> bool:
    return False
