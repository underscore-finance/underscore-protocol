#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

exports: levgVault.__interface__
initializes: levgVault
from contracts.vaults.modules import LeverageVault as levgVault


@deploy
def __init__(
    _asset: address,
    _yieldVaultAsset: address,
    _borrowLegoId: uint256,
    _undyHq: address,
    _minHqTimeLock: uint256,
    _maxHqTimeLock: uint256,
    _startingAgent: address,
):
    levgVault.__init__(
        _asset,
        _yieldVaultAsset,
        _borrowLegoId,
        "Underscore Blue Chip USD Leverage",
        "undyUSD-L",
        _undyHq,
        _minHqTimeLock,
        _maxHqTimeLock,
        _startingAgent,
    )
