#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

exports: earnVault.__interface__
initializes: earnVault
from contracts.vaults.modules import EarnVault as earnVault

@deploy
def __init__(
    _asset: address,
    _name: String[64],
    _symbol: String[32],
    _undyHq: address,
    _minHqTimeLock: uint256,
    _maxHqTimeLock: uint256,
    _startingAgent: address,
):
    earnVault.__init__(
        _asset,
        _name,
        _symbol,
        _undyHq,
        _minHqTimeLock,
        _maxHqTimeLock,
        _startingAgent,
    )
