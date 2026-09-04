#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: walletFactory

import contracts.modules.Create2ProxyGuard as create2ProxyGuard

from interfaces import WalletConfigStructs as wcs
from interfaces import WalletFactory as walletFactory


interface Registry:
    def getAddr(_regId: uint256) -> address: view


interface UserWallet:
    def initialize(_wethAddr: address, _walletConfig: address): nonpayable


interface UserWalletConfig:
    def initialize(
        _wallet: address,
        _undyHq: address,
        _owner: address,
        _groupId: uint256,
        _starterAgentTier: uint256,
        _globalManagerSettings: wcs.GlobalManagerSettings,
        _globalPayeeSettings: wcs.GlobalPayeeSettings,
        _chequeSettings: wcs.ChequeSettings,
        _startingAgent: address,
        _starterAgentSettings: wcs.ManagerSettings,
        _kernel: address,
        _sentinel: address,
        _highCommand: address,
        _paymaster: address,
        _chequeBook: address,
        _migrator: address,
        _actionDataProvider: address,
        _wethAddr: address,
        _ethAddr: address,
        _minTimeLock: uint256,
        _maxTimeLock: uint256,
        _instantActionSettings: wcs.InstantActionSettings,
    ): nonpayable


event UndyHqSet:
    undyHq: indexed(address)


event UserWalletPairCreated:
    wallet: indexed(address)
    walletConfig: indexed(address)
    owner: indexed(address)
    groupId: uint256
    starterAgentTier: uint256
    walletSalt: bytes32


HATCHERY_ID: constant(uint256) = 5

# RELEASE BLOCKER: replace this deliberately unusable placeholder before the
# V1 factory artifact is frozen. Deployment tooling rejects this exact value.
WALLET_FACTORY_ADMIN: public(constant(address)) = 0x0000000000000000000000000000000000000000

# These constants are derived from the fixed V1 singleton salts and the current
# implementation creation bytecode. Any pre-freeze implementation change must
# update the affected address/hash constants before the factory is frozen.
USER_WALLET_IMPLEMENTATION: public(constant(address)) = 0x9dF73483F644C30cF53E3687A63C3b313416E39B
USER_WALLET_IMPLEMENTATION_CODEHASH: public(constant(bytes32)) = 0x00139a906091f956e314d5e00d6aa7d50e94c84ecffeec1b6db42e6afb9ad119
USER_WALLET_CONFIG_IMPLEMENTATION: public(constant(address)) = 0xA9ad47191De9c6e9dc8Af855b705A69d0e8C73f4
USER_WALLET_CONFIG_IMPLEMENTATION_CODEHASH: public(constant(bytes32)) = 0x8457f51866b1bbf292a93ad01582c925c9d2099e36948ea3188e7a06c2685f30


undyHq: public(address)


@external
def setUndyHq(_undyHq: address):
    assert msg.sender == WALLET_FACTORY_ADMIN  # dev: no perms
    assert self.undyHq == empty(address)  # dev: already initialized
    assert _undyHq != empty(address) and _undyHq.is_contract  # dev: invalid undy hq

    self.undyHq = _undyHq
    log UndyHqSet(undyHq=_undyHq)


@view
@external
def isUserWalletConfig(_config: address, _salt: bytes32) -> bool:
    return _config == create2ProxyGuard._predictCreate2Proxy(
        self,
        _salt,
        convert(USER_WALLET_CONFIG_IMPLEMENTATION, bytes20),
    )


@nonreentrant
@external
def createUserWallet(_params: walletFactory.WalletCreationParams) -> (address, address):
    hq: address = self.undyHq
    assert hq != empty(address)  # dev: invalid setup
    hatchery: address = staticcall Registry(hq).getAddr(HATCHERY_ID)
    assert hatchery != empty(address) and hatchery.is_contract  # dev: invalid hatchery
    assert msg.sender == hatchery  # dev: no perms

    # Validate the immutable trust roots before creating either proxy. A clone
    # must never occupy a counterfactual address while pointing at absent or
    # unexpected implementation code.
    assert USER_WALLET_IMPLEMENTATION.is_contract  # dev: invalid wallet implementation
    assert USER_WALLET_IMPLEMENTATION.codehash == USER_WALLET_IMPLEMENTATION_CODEHASH  # dev: invalid wallet implementation
    assert USER_WALLET_CONFIG_IMPLEMENTATION.is_contract  # dev: invalid config implementation
    assert USER_WALLET_CONFIG_IMPLEMENTATION.codehash == USER_WALLET_CONFIG_IMPLEMENTATION_CODEHASH  # dev: invalid config implementation

    assert _params.owner != empty(address)  # dev: invalid owner
    assert _params.starterAgentTier in [1, 2, 4]  # dev: invalid starter agent tier
    walletSalt: bytes32 = keccak256(
        abi_encode(
            _params.owner,
            _params.groupId,
            _params.starterAgentTier,
        )
    )

    expectedWallet: address = create2ProxyGuard._predictCreate2Proxy(
        self,
        walletSalt,
        convert(USER_WALLET_IMPLEMENTATION, bytes20),
    )
    expectedWalletConfig: address = create2ProxyGuard._predictCreate2Proxy(
        self,
        walletSalt,
        convert(USER_WALLET_CONFIG_IMPLEMENTATION, bytes20),
    )
    assert not expectedWallet.is_contract and not expectedWalletConfig.is_contract  # dev: wallet already exists

    # This is deliberately one indivisible sequence: there is no create-only
    # entry point and no external callback between deployment and initialization.
    # Any failure, including a duplicate CREATE2 tuple, reverts both creations.
    walletConfig: address = create_minimal_proxy_to(
        USER_WALLET_CONFIG_IMPLEMENTATION,
        salt=walletSalt,
    )
    wallet: address = create_minimal_proxy_to(
        USER_WALLET_IMPLEMENTATION,
        salt=walletSalt,
    )
    assert wallet == expectedWallet and walletConfig == expectedWalletConfig  # dev: invalid proxy address
    extcall UserWalletConfig(walletConfig).initialize(
        wallet,
        hq,
        _params.owner,
        _params.groupId,
        _params.starterAgentTier,
        _params.globalManagerSettings,
        _params.globalPayeeSettings,
        _params.chequeSettings,
        _params.startingAgent,
        _params.starterAgentSettings,
        _params.kernel,
        _params.sentinel,
        _params.highCommand,
        _params.paymaster,
        _params.chequeBook,
        _params.migrator,
        _params.actionDataProvider,
        _params.weth,
        _params.eth,
        _params.minTimeLock,
        _params.maxTimeLock,
        _params.instantActionSettings,
    )
    extcall UserWallet(wallet).initialize(_params.weth, walletConfig)

    log UserWalletPairCreated(
        wallet=wallet,
        walletConfig=walletConfig,
        owner=_params.owner,
        groupId=_params.groupId,
        starterAgentTier=_params.starterAgentTier,
        walletSalt=walletSalt,
    )
    return wallet, walletConfig
