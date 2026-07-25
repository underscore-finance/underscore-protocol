# @version 0.4.3


interface ERC20:
    def transfer(to: address, amount: uint256) -> bool: nonpayable
    def transferFrom(owner: address, to: address, amount: uint256) -> bool: nonpayable


debt: public(HashMap[address, HashMap[address, uint256]])
collateral: public(HashMap[address, HashMap[address, uint256]])
positionOwner: public(HashMap[address, address])


@external
def seedCollateral(owner: address, asset: address, amount: uint256):
    assert owner != empty(address) and amount != 0
    self.positionOwner[owner] = owner
    self.collateral[owner][asset] += amount


@external
def seedDebt(owner: address, asset: address, amount: uint256):
    assert owner != empty(address) and amount != 0
    self.positionOwner[owner] = owner
    self.debt[owner][asset] += amount


@external
def borrow(owner: address, asset: address, amount: uint256, recipient: address):
    assert owner == recipient and amount != 0
    self.positionOwner[owner] = owner
    self.debt[owner][asset] += amount
    assert extcall ERC20(asset).transfer(recipient, amount)


@external
def repay(owner: address, asset: address, amount: uint256):
    assert amount != 0 and amount <= self.debt[owner][asset]
    assert extcall ERC20(asset).transferFrom(msg.sender, self, amount)
    self.debt[owner][asset] -= amount


@external
def removeCollateral(owner: address, asset: address, amount: uint256, recipient: address):
    assert owner == recipient and amount != 0
    self.collateral[owner][asset] -= amount
    assert extcall ERC20(asset).transfer(recipient, amount)
