# @version 0.4.3

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256


interface ERC1271:
    def isValidSignature(digest: bytes32, signature: Bytes[256]) -> bytes4: view

name: public(String[32])
symbol: public(String[16])
decimals: public(uint8)
totalSupply: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])

callbackTarget: public(address)
callbackData: Bytes[1024]
callbackOnTransfer: public(bool)
callbackOnApprove: public(bool)
callbackEntered: bool
failZeroApprove: public(bool)
authorizationState: public(HashMap[address, HashMap[bytes32, bool]])

CACHED_DOMAIN_SEPARATOR: immutable(bytes32)
TRANSFER_AUTH_TYPEHASH: constant(bytes32) = keccak256(
    "TransferWithAuthorization(address from,address to,uint256 value,uint256 validAfter,uint256 validBefore,bytes32 nonce)"
)
EIP712_DOMAIN_TYPEHASH: constant(bytes32) = keccak256(
    "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
)
ERC1271_MAGIC: constant(bytes4) = 0x1626ba7e


@deploy
def __init__(name: String[32], symbol: String[16], decimals: uint8):
    self.name = name
    self.symbol = symbol
    self.decimals = decimals
    CACHED_DOMAIN_SEPARATOR = keccak256(
        abi_encode(
            EIP712_DOMAIN_TYPEHASH,
            keccak256(name),
            keccak256("2"),
            chain.id,
            self,
        )
    )


@view
@external
def DOMAIN_SEPARATOR() -> bytes32:
    return CACHED_DOMAIN_SEPARATOR


@pure
@external
def TRANSFER_WITH_AUTHORIZATION_TYPEHASH() -> bytes32:
    return TRANSFER_AUTH_TYPEHASH


@external
def mint(to: address, amount: uint256):
    assert to != empty(address)
    self.balanceOf[to] += amount
    self.totalSupply += amount
    log Transfer(sender=empty(address), receiver=to, value=amount)


@external
def configureCallback(
    target: address,
    data: Bytes[1024],
    onTransfer: bool,
    onApprove: bool,
):
    self.callbackTarget = target
    self.callbackData = data
    self.callbackOnTransfer = onTransfer
    self.callbackOnApprove = onApprove


@external
def clearCallback():
    self.callbackTarget = empty(address)
    self.callbackData = b""
    self.callbackOnTransfer = False
    self.callbackOnApprove = False


@external
def setFailZeroApprove(enabled: bool):
    self.failZeroApprove = enabled


@internal
def _callback(enabled: bool):
    if enabled and self.callbackTarget != empty(address) and not self.callbackEntered:
        self.callbackEntered = True
        raw_call(self.callbackTarget, self.callbackData, max_outsize=0)
        self.callbackEntered = False


@external
def transfer(to: address, amount: uint256) -> bool:
    self.balanceOf[msg.sender] -= amount
    self.balanceOf[to] += amount
    log Transfer(sender=msg.sender, receiver=to, value=amount)
    self._callback(self.callbackOnTransfer)
    return True


@external
def approve(spender: address, amount: uint256) -> bool:
    if self.failZeroApprove and amount == 0:
        return False
    self.allowance[msg.sender][spender] = amount
    log Approval(owner=msg.sender, spender=spender, value=amount)
    self._callback(self.callbackOnApprove)
    return True


@external
def transferFrom(owner: address, to: address, amount: uint256) -> bool:
    self.allowance[owner][msg.sender] -= amount
    self.balanceOf[owner] -= amount
    self.balanceOf[to] += amount
    log Transfer(sender=owner, receiver=to, value=amount)
    self._callback(self.callbackOnTransfer)
    return True


@external
def transferWithAuthorization(
    owner: address,
    to: address,
    amount: uint256,
    validAfter: uint256,
    validBefore: uint256,
    nonce: bytes32,
    signature: Bytes[256],
):
    assert block.timestamp > validAfter and block.timestamp < validBefore
    assert not self.authorizationState[owner][nonce]
    structHash: bytes32 = keccak256(
        abi_encode(
            TRANSFER_AUTH_TYPEHASH,
            owner,
            to,
            amount,
            validAfter,
            validBefore,
            nonce,
        )
    )
    digest: bytes32 = keccak256(concat(b"\x19\x01", CACHED_DOMAIN_SEPARATOR, structHash))
    assert staticcall ERC1271(owner).isValidSignature(digest, signature) == ERC1271_MAGIC
    self.authorizationState[owner][nonce] = True
    self.balanceOf[owner] -= amount
    self.balanceOf[to] += amount
    log Transfer(sender=owner, receiver=to, value=amount)


@view
@external
def probeSignature(wallet: address, digest: bytes32) -> bytes4:
    return staticcall ERC1271(wallet).isValidSignature(digest, b"")
