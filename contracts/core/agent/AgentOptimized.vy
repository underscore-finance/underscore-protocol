# @version 0.4.3
# pragma optimize codesize

from interfaces import Wallet
from interfaces import LegoPartner as Lego

interface MissionControl:
    def canPerformSecurityAction(_addr: address) -> bool: view

interface Registry:
    def getAddr(_regId: uint256) -> address: view

struct PendingOwnerChange:
    newOwner: address
    confirmBlock: uint256

struct Signature:
    signature: Bytes[65]
    signer: address
    expiration: uint256

struct ActionInstruction:
    usePrevAmountOut: bool
    action: uint8
    legoId: uint16
    asset: address
    target: address
    amount: uint256
    asset2: address
    amount2: uint256
    minOut1: uint256
    minOut2: uint256
    tickLower: int24
    tickUpper: int24
    extraAddr: address
    extraVal: uint256
    extraData: bytes32
    auxData: bytes32
    swapInstructions: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS]

event OwnershipChanged:
    prevOwner: indexed(address)
    newOwner: indexed(address)

event TimeLockSet:
    numBlocks: uint256

# core
owner: public(address)
timeLock: public(uint256)
pendingOwner: public(PendingOwnerChange)
usedSigs: public(HashMap[Bytes[65], bool])

MAX_INSTRUCTIONS: constant(uint256) = 15
MAX_SWAP_INSTRUCTIONS: constant(uint256) = 5
MAX_TOKEN_PATH: constant(uint256) = 5
MC_ID: constant(uint256) = 3

# Unified signature validation
SIG_PREFIX: constant(bytes32) = 0x1901000000000000000000000000000000000000000000000000000000000000

UNDY_HQ: public(immutable(address))
MIN_TL: public(immutable(uint256))
MAX_TL: public(immutable(uint256))


@deploy
def __init__(_hq: address, _owner: address, _min: uint256, _max: uint256):
    assert empty(address) not in [_hq, _owner] # dev: invalid addrs
    UNDY_HQ = _hq
    self.owner = _owner
    assert _min < _max # dev: invalid delay
    MIN_TL = _min
    MAX_TL = _max
    self.timeLock = _min


# Ownership
@external
def changeOwnership(_new: address):
    assert msg.sender == self.owner # dev: no perms
    assert _new not in [empty(address), self.owner] # dev: invalid new owner
    self.pendingOwner = PendingOwnerChange(newOwner=_new, confirmBlock=block.number + self.timeLock)
    log OwnershipChanged(prevOwner=self.owner, newOwner=_new)


@external
def confirmOwnershipChange():
    p: PendingOwnerChange = self.pendingOwner
    assert p.newOwner != empty(address) # dev: no pending owner
    assert block.number >= p.confirmBlock # dev: time delay not reached
    assert msg.sender == p.newOwner # dev: only new owner can confirm
    old: address = self.owner
    self.owner = p.newOwner
    self.pendingOwner = empty(PendingOwnerChange)
    log OwnershipChanged(prevOwner=old, newOwner=p.newOwner)


@external
def setTimeLock(_n: uint256):
    assert msg.sender == self.owner # dev: no perms
    assert _n >= MIN_TL and _n <= MAX_TL # dev: invalid delay
    self.timeLock = _n
    log TimeLockSet(numBlocks=_n)


# Unified auth check
@internal
def _auth(_h: bytes32, _sig: Signature):
    if msg.sender != self.owner:
        assert not self.usedSigs[_sig.signature] # dev: signature already used
        assert _sig.expiration >= block.timestamp # dev: signature expired
        assert self._verify(_h, _sig) == self.owner # dev: invalid signer
        self.usedSigs[_sig.signature] = True


@view
@internal
def _verify(_h: bytes32, _s: Signature) -> address:
    d: bytes32 = keccak256(concat(SIG_PREFIX, self._dom(), _h))
    r: Bytes[32] = raw_call(
        0x0000000000000000000000000000000000000001,
        abi_encode(d, convert(slice(_s.signature, 64, 1), uint8), slice(_s.signature, 0, 32), slice(_s.signature, 32, 32)),
        max_outsize=32,
        is_static_call=True
    )
    return abi_decode(r, address) if len(r) == 32 else empty(address)


@view
@internal
def _dom() -> bytes32:
    return keccak256(abi_encode(
        keccak256('EIP712Domain(string name,uint256 chainId,address verifyingContract)'),
        keccak256('UnderscoreAgent'),
        chain.id,
        self
    ))


# Individual actions with unified auth
@nonreentrant
@external
def depositForYield(
    _w: address,
    _l: uint256,
    _a: address,
    _v: address = empty(address),
    _amt: uint256 = max_value(uint256),
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> (uint256, address, uint256):
    self._auth(keccak256(abi_encode(convert(0, uint8), _w, _l, _a, _v, _amt, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).depositForYield(_l, _a, _v, _amt, _ea, _ev, _ed)


@nonreentrant
@external
def withdrawFromYield(
    _w: address,
    _l: uint256,
    _v: address,
    _amt: uint256 = max_value(uint256),
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> (uint256, address, uint256):
    self._auth(keccak256(abi_encode(convert(1, uint8), _w, _l, _v, _amt, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).withdrawFromYield(_l, _v, _amt, _ea, _ev, _ed)


@nonreentrant
@external
def rebalanceYieldPosition(
    _w: address,
    _fl: uint256,
    _fv: address,
    _tl: uint256,
    _tv: address = empty(address),
    _amt: uint256 = max_value(uint256),
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> (uint256, address, uint256):
    self._auth(keccak256(abi_encode(convert(2, uint8), _w, _fl, _fv, _tl, _tv, _amt, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).rebalanceYieldPosition(_fl, _fv, _tl, _tv, _amt, _ea, _ev, _ed)


@nonreentrant
@external
def swapTokens(
    _w: address,
    _si: DynArray[Wallet.SwapInstruction, MAX_SWAP_INSTRUCTIONS],
    _s: Signature = empty(Signature),
) -> (address, uint256, address, uint256):
    self._auth(keccak256(abi_encode(convert(3, uint8), _w, _si, _s.expiration)), _s)
    return extcall Wallet(_w).swapTokens(_si)


@nonreentrant
@external
def mintOrRedeemAsset(
    _w: address,
    _l: uint256,
    _ti: address,
    _to: address,
    _ai: uint256 = max_value(uint256),
    _mo: uint256 = 0,
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> (uint256, uint256, bool):
    self._auth(keccak256(abi_encode(convert(4, uint8), _w, _l, _ti, _to, _ai, _mo, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).mintOrRedeemAsset(_l, _ti, _to, _ai, _mo, _ea, _ev, _ed)


@nonreentrant
@external
def confirmMintOrRedeemAsset(
    _w: address,
    _l: uint256,
    _ti: address,
    _to: address,
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> uint256:
    self._auth(keccak256(abi_encode(convert(5, uint8), _w, _l, _ti, _to, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).confirmMintOrRedeemAsset(_l, _ti, _to, _ea, _ev, _ed)


@nonreentrant
@external
def addCollateral(
    _w: address,
    _l: uint256,
    _a: address,
    _amt: uint256 = max_value(uint256),
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> uint256:
    self._auth(keccak256(abi_encode(convert(6, uint8), _w, _l, _a, _amt, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).addCollateral(_l, _a, _amt, _ea, _ev, _ed)


@nonreentrant
@external
def removeCollateral(
    _w: address,
    _l: uint256,
    _a: address,
    _amt: uint256 = max_value(uint256),
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> uint256:
    self._auth(keccak256(abi_encode(convert(7, uint8), _w, _l, _a, _amt, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).removeCollateral(_l, _a, _amt, _ea, _ev, _ed)


@nonreentrant
@external
def borrow(
    _w: address,
    _l: uint256,
    _b: address,
    _amt: uint256 = max_value(uint256),
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> uint256:
    self._auth(keccak256(abi_encode(convert(8, uint8), _w, _l, _b, _amt, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).borrow(_l, _b, _amt, _ea, _ev, _ed)


@nonreentrant
@external
def repayDebt(
    _w: address,
    _l: uint256,
    _p: address,
    _amt: uint256 = max_value(uint256),
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> uint256:
    self._auth(keccak256(abi_encode(convert(9, uint8), _w, _l, _p, _amt, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).repayDebt(_l, _p, _amt, _ea, _ev, _ed)


@nonreentrant
@external
def addLiquidity(
    _w: address,
    _l: uint256,
    _p: address,
    _ta: address,
    _tb: address,
    _aa: uint256 = max_value(uint256),
    _ab: uint256 = max_value(uint256),
    _ma: uint256 = 0,
    _mb: uint256 = 0,
    _ml: uint256 = 0,
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> (uint256, uint256, uint256):
    self._auth(keccak256(abi_encode(convert(10, uint8), _w, _l, _p, _ta, _tb, _aa, _ab, _ma, _mb, _ml, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).addLiquidity(_l, _p, _ta, _tb, _aa, _ab, _ma, _mb, _ml, _ea, _ev, _ed)


@nonreentrant
@external
def addLiquidityConcentrated(
    _w: address,
    _l: uint256,
    _n: address,
    _id: uint256,
    _p: address,
    _ta: address,
    _tb: address,
    _aa: uint256 = max_value(uint256),
    _ab: uint256 = max_value(uint256),
    _tl: int24 = min_value(int24),
    _tu: int24 = max_value(int24),
    _ma: uint256 = 0,
    _mb: uint256 = 0,
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> (uint256, uint256, uint256, uint256):
    self._auth(keccak256(abi_encode(convert(11, uint8), _w, _l, _n, _id, _p, _ta, _tb, _aa, _ab, _tl, _tu, _ma, _mb, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).addLiquidityConcentrated(_l, _n, _id, _p, _ta, _tb, _aa, _ab, _tl, _tu, _ma, _mb, _ea, _ev, _ed)


@nonreentrant
@external
def removeLiquidity(
    _w: address,
    _l: uint256,
    _p: address,
    _ta: address,
    _tb: address,
    _lp: address,
    _amt: uint256 = max_value(uint256),
    _ma: uint256 = 0,
    _mb: uint256 = 0,
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> (uint256, uint256, uint256):
    self._auth(keccak256(abi_encode(convert(12, uint8), _w, _l, _p, _ta, _tb, _lp, _amt, _ma, _mb, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).removeLiquidity(_l, _p, _ta, _tb, _lp, _amt, _ma, _mb, _ea, _ev, _ed)


@nonreentrant
@external
def removeLiquidityConcentrated(
    _w: address,
    _l: uint256,
    _n: address,
    _id: uint256,
    _p: address,
    _ta: address,
    _tb: address,
    _amt: uint256 = max_value(uint256),
    _ma: uint256 = 0,
    _mb: uint256 = 0,
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> (uint256, uint256, uint256):
    self._auth(keccak256(abi_encode(convert(13, uint8), _w, _l, _n, _id, _p, _ta, _tb, _amt, _ma, _mb, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).removeLiquidityConcentrated(_l, _n, _id, _p, _ta, _tb, _amt, _ma, _mb, _ea, _ev, _ed)


@nonreentrant
@external
def transferFunds(
    _w: address,
    _r: address,
    _a: address = empty(address),
    _amt: uint256 = max_value(uint256),
    _s: Signature = empty(Signature),
) -> uint256:
    self._auth(keccak256(abi_encode(convert(14, uint8), _w, _r, _a, _amt, _s.expiration)), _s)
    return extcall Wallet(_w).transferFunds(_r, _a, _amt)


@nonreentrant
@external
def claimRewards(
    _w: address,
    _l: uint256,
    _rt: address = empty(address),
    _ra: uint256 = max_value(uint256),
    _ea: address = empty(address),
    _ev: uint256 = 0,
    _ed: bytes32 = empty(bytes32),
    _s: Signature = empty(Signature),
) -> uint256:
    self._auth(keccak256(abi_encode(convert(15, uint8), _w, _l, _rt, _ra, _ea, _ev, _ed, _s.expiration)), _s)
    return extcall Wallet(_w).claimRewards(_l, _rt, _ra, _ea, _ev, _ed)


@nonreentrant
@external
def convertEthToWeth(_w: address, _amt: uint256 = max_value(uint256), _s: Signature = empty(Signature)) -> uint256:
    self._auth(keccak256(abi_encode(convert(16, uint8), _w, _amt, _s.expiration)), _s)
    return extcall Wallet(_w).convertEthToWeth(_amt)


@nonreentrant
@external
def convertWethToEth(_w: address, _amt: uint256 = max_value(uint256), _s: Signature = empty(Signature)) -> uint256:
    self._auth(keccak256(abi_encode(convert(17, uint8), _w, _amt, _s.expiration)), _s)
    return extcall Wallet(_w).convertWethToEth(_amt)


# Batch actions
@nonreentrant
@external
def performBatchActions(
    _w: address,
    _inst: DynArray[ActionInstruction, MAX_INSTRUCTIONS],
    _s: Signature = empty(Signature),
) -> bool:
    if msg.sender != self.owner:
        h: bytes32 = keccak256(abi_encode(_w, _inst, _s.expiration))
        self._auth(h, _s)
    
    assert len(_inst) > 0 # dev: no instructions
    p: uint256 = 0  # prevAmountReceived
    
    for i: ActionInstruction in _inst:
        p = self._exec(_w, i, p)
    
    return True


@internal
def _exec(_w: address, i: ActionInstruction, p: uint256) -> uint256:
    amt: uint256 = i.amount
    if i.usePrevAmountOut and p != 0:
        amt = p
    
    # Direct action dispatch without enum conversion
    if i.action == 0:  # EARN_DEPOSIT
        a: uint256 = 0
        b: address = empty(address)
        a, b, p = extcall Wallet(_w).depositForYield(convert(i.legoId, uint256), i.asset, i.target, amt, i.extraAddr, i.extraVal, i.extraData)
        return p
    elif i.action == 1:  # EARN_WITHDRAW
        a: uint256 = 0
        b: address = empty(address)
        a, b, p = extcall Wallet(_w).withdrawFromYield(convert(i.legoId, uint256), i.asset, amt, i.extraAddr, i.extraVal, i.extraData)
        return p
    elif i.action == 2:  # EARN_REBALANCE
        a: uint256 = 0
        b: address = empty(address)
        a, b, p = extcall Wallet(_w).rebalanceYieldPosition(convert(i.legoId, uint256), i.asset, i.amount2, i.target, amt, i.extraAddr, i.extraVal, i.extraData)
        return p
    elif i.action == 3:  # SWAP
        if i.usePrevAmountOut and p != 0:
            i.swapInstructions[0].amountIn = p
        a: address = empty(address)
        b: uint256 = 0
        c: address = empty(address)
        a, b, c, p = extcall Wallet(_w).swapTokens(i.swapInstructions)
        return p
    elif i.action == 4:  # MINT_REDEEM
        a: uint256 = 0
        b: bool = False
        a, p, b = extcall Wallet(_w).mintOrRedeemAsset(convert(i.legoId, uint256), i.asset, i.target, amt, i.minOut1, i.extraAddr, i.extraVal, i.extraData)
        return p
    elif i.action == 5:  # CONFIRM_MINT_REDEEM
        p = extcall Wallet(_w).confirmMintOrRedeemAsset(convert(i.legoId, uint256), i.asset, i.target, i.extraAddr, i.extraVal, i.extraData)
        return p
    elif i.action == 6:  # ADD_COLLATERAL
        extcall Wallet(_w).addCollateral(convert(i.legoId, uint256), i.asset, amt, i.extraAddr, i.extraVal, i.extraData)
        return 0
    elif i.action == 7:  # REMOVE_COLLATERAL
        return extcall Wallet(_w).removeCollateral(convert(i.legoId, uint256), i.asset, amt, i.extraAddr, i.extraVal, i.extraData)
    elif i.action == 8:  # BORROW
        p = extcall Wallet(_w).borrow(convert(i.legoId, uint256), i.asset, amt, i.extraAddr, i.extraVal, i.extraData)
        return p
    elif i.action == 9:  # REPAY_DEBT
        extcall Wallet(_w).repayDebt(convert(i.legoId, uint256), i.asset, amt, i.extraAddr, i.extraVal, i.extraData)
        return 0
    elif i.action == 10:  # ADD_LIQ
        if i.usePrevAmountOut and p != 0:
            amt = p
        a: uint256 = 0
        b: uint256 = 0
        p, a, b = extcall Wallet(_w).addLiquidity(convert(i.legoId, uint256), i.target, i.asset, i.asset2, amt, i.amount2, i.minOut1, i.minOut2, convert(i.auxData, uint256), i.extraAddr, i.extraVal, i.extraData)
        return p
    elif i.action == 11:  # ADD_LIQ_CONC
        if i.usePrevAmountOut and p != 0:
            amt = p
        pool: address = convert(convert(i.auxData, uint256) >> 96, address)
        nftId: uint256 = convert(i.auxData, uint256) & convert(max_value(uint96), uint256)
        extcall Wallet(_w).addLiquidityConcentrated(convert(i.legoId, uint256), i.target, nftId, pool, i.asset, i.asset2, amt, i.amount2, i.tickLower, i.tickUpper, i.minOut1, i.minOut2, i.extraAddr, i.extraVal, i.extraData)
        return 0
    elif i.action == 12:  # REMOVE_LIQ
        if i.usePrevAmountOut and p != 0:
            amt = p
        lpToken: address = convert(convert(i.auxData, uint256) & convert(max_value(uint160), uint256), address)
        a: uint256 = 0
        b: uint256 = 0
        p, a, b = extcall Wallet(_w).removeLiquidity(convert(i.legoId, uint256), i.target, i.asset, i.asset2, lpToken, amt, i.minOut1, i.minOut2, i.extraAddr, i.extraVal, i.extraData)
        return p
    elif i.action == 13:  # REMOVE_LIQ_CONC
        if i.usePrevAmountOut and p != 0:
            amt = p
        pool: address = convert(convert(i.auxData, uint256) >> 96, address)
        nftId: uint256 = convert(i.auxData, uint256) & convert(max_value(uint96), uint256)
        a: uint256 = 0
        b: uint256 = 0
        p, a, b = extcall Wallet(_w).removeLiquidityConcentrated(convert(i.legoId, uint256), i.target, nftId, pool, i.asset, i.asset2, amt, i.minOut1, i.minOut2, i.extraAddr, i.extraVal, i.extraData)
        return p
    elif i.action == 14:  # TRANSFER
        extcall Wallet(_w).transferFunds(i.target, i.asset, amt)
        return 0
    elif i.action == 15:  # REWARDS
        return extcall Wallet(_w).claimRewards(convert(i.legoId, uint256), i.asset, i.amount, i.extraAddr, i.extraVal, i.extraData)
    elif i.action == 16:  # ETH_TO_WETH
        return extcall Wallet(_w).convertEthToWeth(amt)
    elif i.action == 17:  # WETH_TO_ETH
        return extcall Wallet(_w).convertWethToEth(amt)
    else:
        raise "Invalid action"