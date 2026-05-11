# @version 0.4.3

kernel: public(address)
sentinel: public(address)
highCommand: public(address)
paymaster: public(address)
chequeBook: public(address)
migrator: public(address)


@deploy
def __init__(
    _kernel: address,
    _sentinel: address,
    _highCommand: address,
    _paymaster: address,
    _chequeBook: address,
    _migrator: address,
):
    self.kernel = _kernel
    self.sentinel = _sentinel
    self.highCommand = _highCommand
    self.paymaster = _paymaster
    self.chequeBook = _chequeBook
    self.migrator = _migrator
