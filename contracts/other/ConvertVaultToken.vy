# @version 0.4.3

from ethereum.ercs import IERC4626
from ethereum.ercs import IERC20


@internal
def _verifyAndReturnAmount(_token: address) -> bool:
    amount: uint256 = staticcall IERC20(_token).balanceOf(self)
    if amount != 0:
        return extcall IERC20(_token).transfer(msg.sender, amount, default_return_value=True)
    return True


@external
def convertVaultToken(_fromVaultToken: address, _toVaultToken: address, _fromAmount: uint256 = max_value(uint256)) -> bool:
    # valdate and get from vault token data
    amount: uint256 = min(_fromAmount, staticcall IERC20(_fromVaultToken).balanceOf(msg.sender))
    assert amount != 0 # dev: amount is 0

    underlyingAsset: address = staticcall IERC4626(_fromVaultToken).asset()  # from vault token asset
    assert underlyingAsset == staticcall IERC4626(_toVaultToken).asset() # dev: asset mismatch
    
    # transfer from vault token to this contract and redeem
    assert extcall IERC20(_fromVaultToken).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed
    extcall IERC4626(_fromVaultToken).redeem(amount, self, self)
    
    # deposit underlying asset to to vault token
    underlyingAmount: uint256 = staticcall IERC20(underlyingAsset).balanceOf(self)
    assert underlyingAmount != 0 # dev: no token amount
    
    depositedAmount: uint256 = extcall IERC4626(_toVaultToken).deposit(underlyingAmount, msg.sender)

    assert depositedAmount != 0 # dev: no vault tokens received

    assert self._verifyAndReturnAmount(_fromVaultToken) 
    assert self._verifyAndReturnAmount(_toVaultToken)
    assert self._verifyAndReturnAmount(underlyingAsset)

    return True
