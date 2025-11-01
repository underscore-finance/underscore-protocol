# @version 0.4.3

from ethereum.ercs import IERC20Detailed
from ethereum.ercs import IERC20
from ethereum.ercs import IERC4626

interface MockToken:
    def mint(_to: address, _value: uint256): nonpayable
    def burn(_value: uint256) -> bool: nonpayable

mockPrices: public(HashMap[address, uint256]) # asset -> price in USD (18 decimals)
userCollateral: public(HashMap[address, HashMap[address, uint256]]) # user -> asset -> amount
userDebt: public(HashMap[address, uint256]) # user -> debt amount

GREEN_TOKEN: public(immutable(address))
SAVINGS_GREEN: public(immutable(address))
RIPE_TOKEN: public(immutable(address))


@deploy
def __init__(_greenToken: address, _savingsGreen: address, _ripeToken: address):
    assert empty(address) not in [_greenToken, _savingsGreen, _ripeToken] # dev: invalid tokens
    GREEN_TOKEN = _greenToken
    SAVINGS_GREEN = _savingsGreen
    RIPE_TOKEN = _ripeToken


###########################
# MOCK CONFIG FUNCTIONS #
###########################


@external
def setPrice(_asset: address, _price: uint256):
    self.mockPrices[_asset] = _price


@external
def setUserDebt(_user: address, _debtAmount: uint256):
    self.userDebt[_user] = _debtAmount


@external
def setUserCollateral(_user: address, _asset: address, _amount: uint256):
    self.userCollateral[_user][_asset] = _amount


###########################
# RIPE REGISTRY INTERFACE #
###########################


@view
@external
def getAddr(_regId: uint256) -> address:
    return self


@view
@external
def isValidAddr(_addr: address) -> bool:
    return True


@view
@external
def greenToken() -> address:
    return GREEN_TOKEN


@view
@external
def savingsGreen() -> address:
    return SAVINGS_GREEN


@view
@external
def ripeToken() -> address:
    return RIPE_TOKEN


#########################
# RIPE TELLER INTERFACE #
#########################


@external
def deposit(
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _user: address = msg.sender,
    _vaultAddr: address = empty(address),
    _vaultId: uint256 = 0,
) -> uint256:
    return self._deposit(_asset, _amount, _user, msg.sender, _vaultAddr, _vaultId)


@internal
def _deposit(
    _asset: address,
    _amount: uint256,
    _user: address,
    _sender: address,
    _vaultAddr: address,
    _vaultId: uint256,
) -> uint256:
    amount: uint256 = _amount
    if amount == max_value(uint256):
        amount = staticcall IERC20(_asset).balanceOf(_sender)
    else:
        amount = min(amount, staticcall IERC20(_asset).balanceOf(_sender))
    assert amount != 0 # dev: nothing to deposit

    assert extcall IERC20(_asset).transferFrom(_sender, self, amount, default_return_value=True) # dev: transfer failed
    self.userCollateral[_user][_asset] += amount
    return amount


@external
def withdraw(
    _asset: address,
    _amount: uint256 = max_value(uint256),
    _user: address = msg.sender,
    _vaultAddr: address = empty(address),
    _vaultId: uint256 = 0,
) -> uint256:
    amount: uint256 = 0
    if _amount == max_value(uint256):
        amount = self.userCollateral[_user][_asset]
    else:
        amount = min(_amount, self.userCollateral[_user][_asset])
    assert amount != 0 # dev: nothing to withdraw

    self.userCollateral[_user][_asset] -= amount
    assert extcall IERC20(_asset).transfer(_user, amount, default_return_value=True) # dev: transfer failed
    return amount


@external
def borrow(
    _greenAmount: uint256 = max_value(uint256),
    _user: address = msg.sender,
    _wantsSavingsGreen: bool = True,
    _shouldEnterStabPool: bool = False,
) -> uint256:
    amount: uint256 = _greenAmount
    assert amount != max_value(uint256) # dev: must specify amount
    assert amount != 0 # dev: nothing to borrow

    recipient: address = _user
    if _wantsSavingsGreen:
        recipient = self
    extcall MockToken(GREEN_TOKEN).mint(recipient, amount)

    if _wantsSavingsGreen:
        extcall IERC20(GREEN_TOKEN).approve(SAVINGS_GREEN, amount)
        extcall IERC4626(SAVINGS_GREEN).deposit(amount, _user)

    self.userDebt[_user] += amount
    return amount


@external
def repay(
    _paymentAmount: uint256 = max_value(uint256),
    _user: address = msg.sender,
    _isPaymentSavingsGreen: bool = False,
    _shouldRefundSavingsGreen: bool = True,
) -> bool:
    paymentAsset: address = SAVINGS_GREEN if _isPaymentSavingsGreen else GREEN_TOKEN
    availBalance: uint256 = staticcall IERC20(paymentAsset).balanceOf(msg.sender)
    userDebtAmount: uint256 = self.userDebt[_user]

    amount: uint256 = min(availBalance, userDebtAmount)
    if _paymentAmount != max_value(uint256):
        amount = min(amount, _paymentAmount)
    assert amount != 0 # dev: nothing to repay

    assert extcall IERC20(paymentAsset).transferFrom(msg.sender, self, amount, default_return_value=True) # dev: transfer failed

    # If paying with SAVINGS_GREEN, redeem it to GREEN first
    greenAmount: uint256 = amount
    if _isPaymentSavingsGreen:
        greenAmount = extcall IERC4626(SAVINGS_GREEN).redeem(amount, self, self)
    extcall MockToken(GREEN_TOKEN).burn(greenAmount)

    self.userDebt[_user] -= greenAmount
    return True


@external
def depositIntoGovVault(
    _asset: address,
    _amount: uint256,
    _lockDuration: uint256,
    _user: address = msg.sender,
) -> uint256:
    return self._deposit(_asset, _amount, _user, msg.sender, empty(address), 0)


@external
def claimLoot(
    _user: address = msg.sender,
    _shouldStake: bool = True,
) -> uint256:
    # Mock claiming 100 RIPE tokens as rewards
    amount: uint256 = 100 * 10 ** 18
    extcall MockToken(RIPE_TOKEN).mint(_user, amount)
    return amount


##################################
# RIPE MISSION CONTROL INTERFACE #
##################################


@view
@external
def doesUndyLegoHaveAccess(_wallet: address, _legoAddr: address) -> bool:
    return True


@view
@external
def getFirstVaultIdForAsset(_asset: address) -> uint256:
    return 1


@view
@external
def isSupportedAsset(_asset: address) -> bool:
    return True


#############################
# RIPE PRICE DESK INTERFACE #
#############################


@external
def addPriceSnapshot(_asset: address) -> bool:
    return True


@view
@external
def getPrice(_asset: address, _shouldRaise: bool = False) -> uint256:
    return self.mockPrices[_asset]


@view
@external
def getAssetAmount(_asset: address, _usdValue: uint256, _shouldRaise: bool = False) -> uint256:
    price: uint256 = self.mockPrices[_asset]
    if price == 0:
        if _shouldRaise:
            raise "no price set"
        return 0
    decimals: uint256 = convert(staticcall IERC20Detailed(_asset).decimals(), uint256)
    return _usdValue * (10 ** decimals) // price


@view
@external
def getUsdValue(_asset: address, _amount: uint256, _shouldRaise: bool = False) -> uint256:
    price: uint256 = self.mockPrices[_asset]
    if price == 0:
        if _shouldRaise:
            raise "no price set"
        return 0
    decimals: uint256 = convert(staticcall IERC20Detailed(_asset).decimals(), uint256)
    return price * _amount // (10 ** decimals)


###########################
# CREDIT ENGINE INTERFACE #
###########################


@view
@external
def getUserDebtAmount(_user: address) -> uint256:
    return self.userDebt[_user]


################################
# RIPE DEPOSIT VAULT INTERFACE #
################################


@view
@external
def getTotalAmountForUser(_user: address, _asset: address) -> uint256:
    return self.userCollateral[_user][_asset]
