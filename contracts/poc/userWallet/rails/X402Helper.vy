# @version 0.4.3


interface EIP3009Token:
    def DOMAIN_SEPARATOR() -> bytes32: view
    def TRANSFER_WITH_AUTHORIZATION_TYPEHASH() -> bytes32: view
    def authorizationState(authorizer: address, nonce: bytes32) -> bool: view


TOKEN: public(immutable(address))


@deploy
def __init__(token: address):
    assert token.is_contract
    TOKEN = token


@view
@external
def token() -> address:
    return TOKEN


@view
@external
def digest(
    wallet: address,
    destination: address,
    amount: uint256,
    validAfter: uint256,
    validBefore: uint256,
    nonce: bytes32,
) -> bytes32:
    structHash: bytes32 = keccak256(
        abi_encode(
            staticcall EIP3009Token(TOKEN).TRANSFER_WITH_AUTHORIZATION_TYPEHASH(),
            wallet,
            destination,
            amount,
            validAfter,
            validBefore,
            nonce,
        )
    )
    return keccak256(
        concat(
            b"\x19\x01",
            staticcall EIP3009Token(TOKEN).DOMAIN_SEPARATOR(),
            structHash,
        )
    )


@view
@external
def authorizationUsed(wallet: address, nonce: bytes32) -> bool:
    return staticcall EIP3009Token(TOKEN).authorizationState(wallet, nonce)
