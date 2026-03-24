# @version 0.4.3

activeAssets: public(uint256)


@external
def setActiveAssets(_activeAssets: uint256):
    self.activeAssets = _activeAssets
