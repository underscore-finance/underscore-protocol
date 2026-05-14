# @version 0.4.3

numAdjustCalls: public(uint256)
lastAdjustUser: public(address)
lastAdjustAsset: public(address)
lastAdjustClaimable: public(uint256)

numEjectionCalls: public(uint256)
lastEjectionUser: public(address)


@external
def adjustLoot(_user: address, _asset: address, _newClaimable: uint256) -> bool:
    self.numAdjustCalls += 1
    self.lastAdjustUser = _user
    self.lastAdjustAsset = _asset
    self.lastAdjustClaimable = _newClaimable
    return True


@external
def updateDepositPointsOnEjection(_user: address):
    self.numEjectionCalls += 1
    self.lastEjectionUser = _user
