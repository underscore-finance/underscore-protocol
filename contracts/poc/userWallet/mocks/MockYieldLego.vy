# @version 0.4.3

from contracts.poc.userWallet.interfaces import IUserWalletV3
from contracts.poc.userWallet.types import WalletV3Types as w3


interface ERC20:
    def allowance(owner: address, spender: address) -> uint256: view
    def balanceOf(owner: address) -> uint256: view
    def transferFrom(owner: address, to: address, amount: uint256) -> bool: nonpayable
    def approve(spender: address, amount: uint256) -> bool: nonpayable


interface Vault:
    def deposit(amount: uint256, receiver: address): nonpayable


lastWalletAllowance: public(uint256)
lastProtocolAllowance: public(uint256)
lastActionDataHash: public(bytes32)
consumeCount: public(uint256)
mode: public(uint8)


@external
def setMode(mode: uint8):
    self.mode = mode


@external
def deposit(wallet: address, vault: address, token: address, amount: uint256):
    actionDataHash: bytes32 = keccak256(abi_encode(vault, token, amount, wallet))
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=1,
        effectClass=1,
        consumer=self,
        target=vault,
        resource=token,
        maxAmount=amount,
        beneficiary=wallet,
        actionDataHash=actionDataHash,
    )
    if self.mode == 2:
        request.target = token
    elif self.mode == 3:
        request.maxAmount = amount + 1
    elif self.mode == 4:
        request.actionId = 10
    elif self.mode == 5:
        request.actionDataHash = keccak256("wrong action data")
    extcall IUserWalletV3(wallet).consumeCapability(request)
    if self.mode == 1:
        extcall IUserWalletV3(wallet).consumeCapability(request)
    self.consumeCount += 1
    self.lastActionDataHash = actionDataHash
    self.lastWalletAllowance = staticcall ERC20(token).allowance(wallet, self)
    assert self.lastWalletAllowance == amount, "wrong wallet allowance"
    assert extcall ERC20(token).transferFrom(wallet, self, amount)
    assert extcall ERC20(token).approve(vault, amount)
    self.lastProtocolAllowance = staticcall ERC20(token).allowance(self, vault)
    assert self.lastProtocolAllowance == amount, "wrong protocol allowance"
    extcall Vault(vault).deposit(amount, wallet)
    assert extcall ERC20(token).approve(vault, 0)
    assert staticcall ERC20(token).allowance(self, vault) == 0
    assert staticcall ERC20(token).balanceOf(self) == 0
