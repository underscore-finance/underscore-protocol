# @version 0.4.3

isOperator: public(HashMap[address, HashMap[address, bool]])
useCount: public(HashMap[address, uint256])


@external
def setOperator(operator: address, enabled: bool):
    assert operator != empty(address)
    self.isOperator[msg.sender][operator] = enabled


@external
def useOperator(owner: address):
    assert self.isOperator[owner][msg.sender], "not operator"
    self.useCount[owner] += 1
