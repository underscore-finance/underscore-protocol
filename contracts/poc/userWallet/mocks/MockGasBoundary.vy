# @version 0.4.3

value: public(uint256)


@external
def setValue(newValue: uint256):
    self.value = newValue


@external
def clearValue():
    self.value = 0
