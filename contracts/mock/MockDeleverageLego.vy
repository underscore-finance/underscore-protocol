# @version 0.4.3

from interfaces import WalletStructs as ws


interface UserWallet:
    def deleverage(_legoId: uint256, _deleverageAssets: DynArray[ws.DeleverageAsset, 10], _autoDeleverageAmount: uint256, _extraData: bytes32) -> (uint256, uint256): nonpayable


previewAssets: public(DynArray[address, 10])
touchedAssets: public(DynArray[address, 10])
repaidAmount: public(uint256)
txUsdValue: public(uint256)
debtAsset: public(address)
shouldReenter: public(bool)
reenterLegoId: public(uint256)


@deploy
def __init__(_debtAsset: address):
    self.debtAsset = _debtAsset


@external
def setResponse(
    _previewAssets: DynArray[address, 10],
    _touchedAssets: DynArray[address, 10],
    _repaidAmount: uint256,
    _txUsdValue: uint256,
    _debtAsset: address,
):
    self.previewAssets = _previewAssets
    self.touchedAssets = _touchedAssets
    self.repaidAmount = _repaidAmount
    self.txUsdValue = _txUsdValue
    self.debtAsset = _debtAsset


@external
def setReenter(_shouldReenter: bool, _legoId: uint256):
    self.shouldReenter = _shouldReenter
    self.reenterLegoId = _legoId


@view
@external
def getAccessForLego(_user: address, _action: ws.ActionType) -> (address, String[64], uint256):
    return empty(address), empty(String[64]), 0


@view
@external
def previewAutoDeleverageAssets(
    _user: address,
    _autoDeleverageAmount: uint256,
    _extraData: bytes32,
) -> DynArray[address, 10]:
    return self.previewAssets


@external
def deleverageForUserWallet(
    _user: address,
    _deleverageAssets: DynArray[ws.DeleverageAsset, 10],
    _autoDeleverageAmount: uint256,
    _extraData: bytes32,
    _miniAddys: ws.MiniAddys,
) -> (uint256, uint256, address, DynArray[address, 10]):
    if self.shouldReenter:
        extcall UserWallet(_user).deleverage(self.reenterLegoId, [], 1, empty(bytes32))

    return self.repaidAmount, self.txUsdValue, self.debtAsset, self.touchedAssets
