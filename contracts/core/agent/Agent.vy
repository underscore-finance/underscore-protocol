# @version 0.4.3

# core
owner: public(address)
timeLock: public(uint256)

UNDY_HQ: public(immutable(address))
MIN_TIMELOCK: public(immutable(uint256))
MAX_TIMELOCK: public(immutable(uint256))


@deploy
def __init__(
    _undyHq: address,
    _owner: address,
    _minTimeLock: uint256,
    _maxTimeLock: uint256,
):
    assert empty(address) not in [_undyHq, _owner] # dev: invalid addrs
    UNDY_HQ = _undyHq
    self.owner = _owner

    # time lock
    assert _minTimeLock < _maxTimeLock # dev: invalid delay
    MIN_TIMELOCK = _minTimeLock
    MAX_TIMELOCK = _maxTimeLock
    self.timeLock = _minTimeLock

    # TODO: implement this contract