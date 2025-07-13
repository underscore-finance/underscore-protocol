# @version 0.4.3

initializes: ownership
exports: ownership.__interface__
import contracts.modules.Ownership as ownership


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    ownership.__init__(_undyHq, _owner, _minTimeLock, _maxTimeLock)
