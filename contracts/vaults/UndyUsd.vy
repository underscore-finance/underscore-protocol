#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3
# pragma optimize codesize

exports: earnVault.__interface__
initializes: earnVault
from contracts.vaults.modules import EarnVault as earnVault

from interfaces import WalletConfigStructs as wcs


@deploy
def __init__(
    _asset: address,
    _undyHq: address,
    _minHqTimeLock: uint256,
    _maxHqTimeLock: uint256,
    _startingAgent: address,
    # wallet backpack addrs
    _sentinel: address,
    _highCommand: address,
    # price config
    _minSnapshotDelay: uint256,
    _maxNumSnapshots: uint256,
    _maxUpsideDeviation: uint256,
    _staleTime: uint256,
):
    earnVault.__init__(
        _asset,
        "Underscore Blue Chip USD",
        "undyUSD",
        _undyHq,
        _minHqTimeLock,
        _maxHqTimeLock,
        _startingAgent,
        _sentinel,
        _highCommand,
        _minSnapshotDelay,
        _maxNumSnapshots,
        _maxUpsideDeviation,
        _staleTime,
    )
