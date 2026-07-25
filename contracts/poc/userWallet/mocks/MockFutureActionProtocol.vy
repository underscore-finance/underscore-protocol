# @version 0.4.3


interface ERC20:
    def transfer(to: address, amount: uint256) -> bool: nonpayable


bond: public(HashMap[address, HashMap[address, uint256]])


@external
def seedBond(owner: address, asset: address, amount: uint256):
    assert owner != empty(address) and amount != 0
    self.bond[owner][asset] += amount


@external
def releaseBond(owner: address, asset: address, amount: uint256, recipient: address):
    assert owner == recipient and amount != 0
    self.bond[owner][asset] -= amount
    assert extcall ERC20(asset).transfer(recipient, amount)
