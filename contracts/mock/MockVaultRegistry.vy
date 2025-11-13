# @version 0.4.3

# Mock VaultRegistry for testing earn vault snapshot functionality

# Track which vaults are marked as earn vaults
isEarnVault: public(HashMap[address, bool])

# Track snapshot calls for testing
snapshotsCalled: public(HashMap[address, uint256])

@external
def setEarnVault(_vault: address, _isEarn: bool):
    """Set whether a vault is an earn vault for testing"""
    self.isEarnVault[_vault] = _isEarn

@external
def getSnapshotCount(_asset: address) -> uint256:
    """Get the number of times a snapshot was called for an asset"""
    return self.snapshotsCalled[_asset]

@external
def trackSnapshot(_asset: address):
    """Track that a snapshot was requested (called by mock Ripe)"""
    self.snapshotsCalled[_asset] += 1