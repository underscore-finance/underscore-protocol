# @version 0.4.3


@pure
@internal
def _predictCreate2Proxy(
    _deployer: address,
    _salt: bytes32,
    _implementation: bytes20,
) -> address:
    # Vyper 0.4.3's builtin minimal proxy uses this exact 54-byte initcode,
    # which differs from the common 55-byte OpenZeppelin variant.
    initcode: Bytes[54] = concat(
        x"602d3d8160093d39f3363d3d373d3d3d363d73",
        _implementation,
        x"5af43d82803e903d91602b57fd5bf3",
    )
    create2Hash: uint256 = convert(
        keccak256(
            concat(
                x"ff",
                convert(_deployer, bytes20),
                _salt,
                keccak256(initcode),
            )
        ),
        uint256,
    )
    return convert(
        create2Hash & convert(max_value(uint160), uint256),
        address,
    )


@view
@internal
def _assertCreate2Proxy(_salt: bytes32):
    # `self.code` compiles to CODECOPY and reads the implementation during a
    # delegatecall. Copy through a local address to force EXTCODECOPY against
    # the proxy, whose EIP-1167 runtime stores its implementation at [10:30].
    proxy: address = self
    assert proxy.codesize == 45 # dev: invalid proxy runtime
    implementation: bytes20 = convert(slice(proxy.code, 10, 20), bytes20)
    expectedRuntime: Bytes[45] = concat(
        x"363d3d373d3d3d363d73",
        implementation,
        x"5af43d82803e903d91602b57fd5bf3",
    )
    assert proxy.codehash == keccak256(expectedRuntime) # dev: invalid proxy runtime
    assert self == self._predictCreate2Proxy(
        msg.sender,
        _salt,
        implementation,
    ) # dev: invalid proxy deployer


@view
@internal
def _assertCreate2ProxyPair(
    _counterpart: address,
    _counterpartImplementation: address,
    _salt: bytes32,
):
    self._assertCreate2Proxy(_salt)
    assert _counterpart == self._predictCreate2Proxy(
        msg.sender,
        _salt,
        convert(_counterpartImplementation, bytes20),
    ) # dev: invalid proxy pair
