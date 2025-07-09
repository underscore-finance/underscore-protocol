# @version 0.4.3

from ethereum.ercs import IERC20

struct TokenData:
    symbol: String[32]
    tokenAddress: address

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

# NOTE: this does not include ALL required erc20/4626 methods. 
# This only includes what we use/need for our strats

balanceOf: public(HashMap[address, uint256]) # user -> shares
totalSupply: public(uint256)
allowance: public(HashMap[address, HashMap[address, uint256]])


@deploy
def __init__():
    pass


@view
@external
def getReserveTokensAddresses(_asset: address) -> (address, address, address):
    return self, empty(address), empty(address)


@view
@external
def getPoolDataProvider() -> address:
    return self


@view
@external
def getAllATokens() -> DynArray[TokenData, 40]:
    return [TokenData(
        symbol="aUSDC",
        tokenAddress=self,
    )]


@view
@external
def getTotalDebt(_asset: address) -> uint256:
    return 0


@external
def supply(_asset: address, _amount: uint256, _onBehalfOf: address, _referralCode: uint16):
    assert extcall IERC20(_asset).transferFrom(msg.sender, self, _amount, default_return_value=True) # dev: transfer failed
    self.balanceOf[_onBehalfOf] += _amount
    self.totalSupply += _amount


@external
def withdraw(_asset: address, _amount: uint256, _to: address):
    vaultTokenAmount: uint256 = min(_amount, self.balanceOf[msg.sender])
    transferAmount: uint256 = min(vaultTokenAmount, staticcall IERC20(_asset).balanceOf(self))
    assert extcall IERC20(_asset).transfer(_to, transferAmount, default_return_value=True) # dev: transfer failed
    self.balanceOf[msg.sender] -= transferAmount
    self.totalSupply -= transferAmount


# erc20 methods


@external
def transfer(_to: address, _value: uint256) -> bool:
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    log Transfer(sender=msg.sender, receiver=_to, value=_value)
    return True


@external
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowance[_from][msg.sender] -= _value
    log Transfer(sender=_from, receiver=_to, value=_value)
    return True


@external
def approve(_spender: address, _value: uint256) -> bool:
    self.allowance[msg.sender][_spender] = _value
    log Approval(owner=msg.sender, spender=_spender, value=_value)
    return True