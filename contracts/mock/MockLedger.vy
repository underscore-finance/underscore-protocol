# @version 0.4.3

# Mock Ledger for testing backpack and user wallet permissions

# Track who is a user wallet
isUserWallet: public(HashMap[address, bool])

# Track who is a registered backpack item
isRegisteredBackpackItem: public(HashMap[address, bool])

@external
def setUserWallet(_user: address, _isWallet: bool):
    """Set whether an address is a user wallet for testing"""
    self.isUserWallet[_user] = _isWallet

@external
def setBackpackItem(_item: address, _isRegistered: bool):
    """Set whether an address is a registered backpack item for testing"""
    self.isRegisteredBackpackItem[_item] = _isRegistered