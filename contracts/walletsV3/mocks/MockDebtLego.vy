# @version 0.4.3

from contracts.walletsV3.interfaces import IUserWalletV3
from contracts.walletsV3.types import WalletV3Types as w3


interface ERC20:
    def allowance(owner: address, spender: address) -> uint256: view
    def balanceOf(owner: address) -> uint256: view
    def transferFrom(owner: address, to: address, amount: uint256) -> bool: nonpayable
    def approve(spender: address, amount: uint256) -> bool: nonpayable


interface DebtProtocol:
    def debt(owner: address, asset: address) -> uint256: view
    def borrow(owner: address, asset: address, amount: uint256, recipient: address): nonpayable
    def repay(owner: address, asset: address, amount: uint256): nonpayable
    def removeCollateral(owner: address, asset: address, amount: uint256, recipient: address): nonpayable


interface OperatorProtocol:
    def useOperator(owner: address): nonpayable


mode: public(uint8)
consumeCount: public(uint256)


@external
def setMode(mode: uint8):
    self.mode = mode


@internal
def _consume(wallet: address, request: w3.ActionEnvelope):
    if self.mode == 1:
        request.maxAmount = max_value(uint256)
    elif self.mode == 2:
        request.effectClass = 4
    elif self.mode == 3:
        request.resource = request.target
    elif self.mode == 4:
        request.actionId = 30
    elif self.mode == 5:
        request.actionDataHash = keccak256("wrong action data")
    extcall IUserWalletV3(wallet).consumeCapability(request)
    self.consumeCount += 1


@external
def borrow(wallet: address, protocol: address, asset: address, amount: uint256):
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=10,
        effectClass=2,
        consumer=self,
        target=protocol,
        resource=asset,
        maxAmount=amount,
        beneficiary=wallet,
        actionDataHash=keccak256(abi_encode(protocol, asset, amount, wallet)),
    )
    self._consume(wallet, request)
    extcall DebtProtocol(protocol).borrow(wallet, asset, amount, wallet)


@external
def repayClose(wallet: address, protocol: address, asset: address, maxAmount: uint256):
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=11,
        effectClass=1,
        consumer=self,
        target=protocol,
        resource=asset,
        maxAmount=maxAmount,
        beneficiary=wallet,
        actionDataHash=keccak256(abi_encode(protocol, asset, maxAmount, wallet)),
    )
    self._consume(wallet, request)
    debtAmount: uint256 = staticcall DebtProtocol(protocol).debt(wallet, asset)
    payment: uint256 = min(maxAmount, debtAmount)
    assert payment != 0
    assert extcall ERC20(asset).transferFrom(wallet, self, payment)
    assert extcall ERC20(asset).approve(protocol, payment)
    extcall DebtProtocol(protocol).repay(wallet, asset, payment)
    assert extcall ERC20(asset).approve(protocol, 0)
    assert staticcall ERC20(asset).allowance(self, protocol) == 0
    assert staticcall ERC20(asset).balanceOf(self) == 0


@external
def removeCollateral(wallet: address, protocol: address, asset: address, amount: uint256):
    request: w3.ActionEnvelope = w3.ActionEnvelope(
        actionId=12,
        effectClass=3,
        consumer=self,
        target=protocol,
        resource=asset,
        maxAmount=amount,
        beneficiary=wallet,
        actionDataHash=keccak256(abi_encode(protocol, asset, amount, wallet)),
    )
    self._consume(wallet, request)
    extcall DebtProtocol(protocol).removeCollateral(wallet, asset, amount, wallet)


@external
def attemptOperatorUse(
    wallet: address,
    operatorProtocol: address,
    request: w3.ActionEnvelope,
):
    extcall IUserWalletV3(wallet).consumeCapability(request)
    extcall OperatorProtocol(operatorProtocol).useOperator(wallet)
