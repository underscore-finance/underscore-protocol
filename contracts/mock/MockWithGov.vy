# @version 0.4.1

exports: gov.__interface__
initializes: gov
import contracts.modules.LocalGov as gov


@deploy
def __init__(
    _undyHq: address,
    _initialGov: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
    _initialTimeLock: uint256,
):
    gov.__init__(_undyHq, _initialGov, _minTimeLock, _maxTimeLock, _initialTimeLock)

    # NOTE: Mock contract with Local Gov module
