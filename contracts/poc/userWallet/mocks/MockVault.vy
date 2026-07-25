# @version 0.4.3


interface ERC20:
    def transferFrom(owner: address, to: address, amount: uint256) -> bool: nonpayable


TOKEN: public(immutable(address))
balanceOf: public(HashMap[address, uint256])
totalSupply: public(uint256)
depositCount: public(uint256)


@deploy
def __init__(token: address):
    assert token.is_contract
    TOKEN = token


@external
def deposit(amount: uint256, receiver: address):
    assert amount != 0
    assert extcall ERC20(TOKEN).transferFrom(msg.sender, self, amount)
    self.balanceOf[receiver] += amount
    self.totalSupply += amount
    self.depositCount += 1
