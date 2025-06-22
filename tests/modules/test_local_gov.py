import pytest
import boa

from config.BluePrint import PARAMS
from constants import MAX_UINT256, ZERO_ADDRESS
from conf_utils import filter_logs


@pytest.fixture(scope="module")
def createMockLocalGov(undy_hq, deploy3r, fork):
    def createMockLocalGov(
        _undyHq = undy_hq,
        _initialGov = deploy3r,
        _minTimeLock = PARAMS[fork]["UNDY_HQ_MIN_GOV_TIMELOCK"],
        _maxTimeLock = PARAMS[fork]["UNDY_HQ_MAX_GOV_TIMELOCK"],
        _initialTimeLock = 0
    ):
        return boa.load(
            "contracts/mock/MockWithGov.vy",
            _undyHq,
            _initialGov,
            _minTimeLock,
            _maxTimeLock,
            _initialTimeLock,
        )
    yield createMockLocalGov


# tests


def test_local_gov_deploy(
    createMockLocalGov,
    mock_rando_contract,
    governance,
):
    with boa.reverts("invalid time lock"):
        local_gov = createMockLocalGov(
            _minTimeLock = 100,
            _maxTimeLock = MAX_UINT256,
        )

    with boa.reverts("invalid time lock"):
        local_gov = createMockLocalGov(
            _minTimeLock = 200,  # min > max
            _maxTimeLock = 100,
        )

    with boa.reverts("invalid time lock"):
        local_gov = createMockLocalGov(
            _initialTimeLock = MAX_UINT256 - 1,  # above max
        )

    # Success case with valid parameters
    local_gov = createMockLocalGov(
        _initialGov = mock_rando_contract,
        _minTimeLock = 100,
        _maxTimeLock = 200,
        _initialTimeLock = 150,
    )

    assert local_gov.governance() == mock_rando_contract.address
    assert local_gov.canGovern(mock_rando_contract)
    assert local_gov.canGovern(governance) # undy hq

    assert not local_gov.hasPendingGovChange()
    assert local_gov.pendingGov() == (ZERO_ADDRESS, 0, 0)

    assert local_gov.govChangeTimeLock() == 150
    assert local_gov.minGovChangeTimeLock() == 100
    assert local_gov.maxGovChangeTimeLock() == 200

    # cannot do "finish setup" on local gov
    with boa.reverts("only undy hq"):
        local_gov.finishUndyHqSetup(mock_rando_contract, sender=governance.address)


def test_undy_hq_gov_deploy(
    createMockLocalGov,
    governance,
    deploy3r,
):
    # initial gov is required
    with boa.reverts("undy hq must have gov"):
        hq_gov = createMockLocalGov(
            _undyHq = ZERO_ADDRESS,
            _initialGov = ZERO_ADDRESS,
            _minTimeLock = 100,
            _maxTimeLock = 200,
            _initialTimeLock = 150,
        )

    # need undy hq if no time locks
    with boa.reverts("need undy hq if no time locks"):
        hq_gov = createMockLocalGov(
            _undyHq = ZERO_ADDRESS,
            _initialGov = deploy3r,
            _minTimeLock = 0,
            _maxTimeLock = 0,
        )

    # Success case with valid parameters
    hq_gov = createMockLocalGov(
        _undyHq = ZERO_ADDRESS,
        _initialGov = deploy3r,
        _minTimeLock = 100,
        _maxTimeLock = 200,
        _initialTimeLock = 150, # will be ignored
    )

    assert hq_gov.governance() == deploy3r
    assert hq_gov.canGovern(deploy3r)
    assert not hq_gov.canGovern(governance)

    assert not hq_gov.hasPendingGovChange()
    assert hq_gov.pendingGov() == (ZERO_ADDRESS, 0, 0)

    assert hq_gov.govChangeTimeLock() == 0 # ignored on hq gov
    assert hq_gov.minGovChangeTimeLock() == 100
    assert hq_gov.maxGovChangeTimeLock() == 200


def test_undy_hq_gov_finish_setup(
    createMockLocalGov,
    deploy3r,
    mock_rando_contract,
    bob,
):
    hq_gov = createMockLocalGov(
        _undyHq = ZERO_ADDRESS,
        _initialGov = deploy3r,
        _minTimeLock = 100,
        _maxTimeLock = 200,
        _initialTimeLock = 0
    )

    with boa.reverts("no perms"):
        hq_gov.finishUndyHqSetup(mock_rando_contract, sender=bob)

    with boa.reverts("invalid _newGov"):
        hq_gov.finishUndyHqSetup(ZERO_ADDRESS, sender=deploy3r)
    with boa.reverts("invalid _newGov"):
        hq_gov.finishUndyHqSetup(bob, sender=deploy3r)

    # initial state
    assert hq_gov.governance() == deploy3r
    assert hq_gov.numGovChanges() == 0
    assert hq_gov.govChangeTimeLock() == 0

    # success
    assert hq_gov.finishUndyHqSetup(mock_rando_contract, 150, sender=deploy3r)

    log = filter_logs(hq_gov, "UndyHqSetupFinished")[0]
    assert log.prevGov == deploy3r
    assert log.newGov == mock_rando_contract.address
    assert log.timeLock == 150

    # after setup
    assert hq_gov.governance() == mock_rando_contract.address
    assert hq_gov.numGovChanges() == 1
    assert hq_gov.govChangeTimeLock() == 150


def test_undy_hq_gov_fail_finish_setup(
    createMockLocalGov,
    deploy3r,
    mock_rando_contract,
    governance,
):
    hq_gov = createMockLocalGov(
        _undyHq = ZERO_ADDRESS,
        _initialGov = deploy3r,
        _minTimeLock = 100,
        _maxTimeLock = 200,
        _initialTimeLock = 0
    )

    # change gov in standard way
    time_lock = hq_gov.govChangeTimeLock()
    hq_gov.startGovernanceChange(mock_rando_contract, sender=deploy3r)
    boa.env.time_travel(blocks=time_lock)
    hq_gov.confirmGovernanceChange(sender=mock_rando_contract.address)

    with boa.reverts("already changed gov"):
        hq_gov.finishUndyHqSetup(governance, sender=mock_rando_contract.address)


def test_local_gov_change_basic(
    createMockLocalGov,
    mock_rando_contract,
    deploy3r,
    bob,
):
    local_gov = createMockLocalGov()
    time_lock = local_gov.govChangeTimeLock()

    # Start governance change
    # no perms
    with boa.reverts("no perms"):
        local_gov.startGovernanceChange(mock_rando_contract, sender=bob)

    # success
    local_gov.startGovernanceChange(mock_rando_contract, sender=deploy3r)
    
    # Verify pending event
    pending_log = filter_logs(local_gov, "GovChangeStarted")[0]
    assert pending_log.prevGov == deploy3r
    assert pending_log.newGov == mock_rando_contract.address
    assert pending_log.confirmBlock == boa.env.evm.patch.block_number + time_lock
    
    # Verify pending state
    pending = local_gov.pendingGov()
    assert pending.newGov == mock_rando_contract.address
    assert pending.initiatedBlock == boa.env.evm.patch.block_number
    assert pending.confirmBlock == pending_log.confirmBlock

    # time lock not reached
    with boa.reverts("time lock not reached"):
        local_gov.confirmGovernanceChange(sender=mock_rando_contract.address)

    # time travel
    boa.env.time_travel(blocks=time_lock)

    # Confirm governance change
    local_gov.confirmGovernanceChange(sender=mock_rando_contract.address)

    # Verify confirmed event
    confirmed_log = filter_logs(local_gov, "GovChangeConfirmed")[0]
    assert confirmed_log.prevGov == deploy3r
    assert confirmed_log.newGov == mock_rando_contract.address
    assert confirmed_log.initiatedBlock == pending.initiatedBlock
    assert confirmed_log.confirmBlock == pending.confirmBlock

    # Verify governance changed
    assert local_gov.governance() == mock_rando_contract.address
    assert local_gov.canGovern(mock_rando_contract)
    assert not local_gov.canGovern(deploy3r)

    # pending is cleared
    assert local_gov.pendingGov().confirmBlock == 0


def test_local_gov_change_cancel(
    createMockLocalGov,
    governance,
    mock_rando_contract,
    bob,
):
    local_gov = createMockLocalGov()
    time_lock = local_gov.govChangeTimeLock()

    # Start governance change
    local_gov.startGovernanceChange(mock_rando_contract, sender=governance.address)
    
    # no perms
    with boa.reverts("no perms"):
        local_gov.cancelGovernanceChange(sender=bob)

    # success
    local_gov.cancelGovernanceChange(sender=governance.address)
    
    # Verify cancel event
    cancel_log = filter_logs(local_gov, "GovChangeCancelled")[0]
    assert cancel_log.cancelledGov == mock_rando_contract.address
    assert cancel_log.initiatedBlock == boa.env.evm.patch.block_number
    assert cancel_log.confirmBlock == boa.env.evm.patch.block_number + time_lock
    
    # Verify pending state is cleared
    assert local_gov.pendingGov().confirmBlock == 0


def test_local_gov_change_validation(
    createMockLocalGov,
    governance,
    mock_rando_contract,
    bob,
):
    local_gov = createMockLocalGov()

    # Test non-contract address
    with boa.reverts("_newGov must be a contract"):
        local_gov.startGovernanceChange(bob, sender=governance.address)

    # Test same governance
    with boa.reverts("invalid _newGov"):
        local_gov.startGovernanceChange(governance.address, sender=governance.address)

    # Test unauthorized confirmation
    local_gov.startGovernanceChange(mock_rando_contract, sender=governance.address)
    boa.env.time_travel(blocks=local_gov.govChangeTimeLock())
    with boa.reverts("only new gov can confirm"):
        local_gov.confirmGovernanceChange(sender=governance.address)


def test_local_gov_time_lock_management(
    createMockLocalGov,
    mock_rando_contract,
    governance,
    bob,
):
    local_gov = createMockLocalGov()

    # Test setting time lock
    prev_time_lock = local_gov.govChangeTimeLock()
    new_time_lock = prev_time_lock + 10

    # no perms
    with boa.reverts("no perms"):
        local_gov.setGovTimeLock(new_time_lock, sender=bob)

    # no change
    with boa.reverts("invalid time lock"):
        local_gov.setGovTimeLock(prev_time_lock, sender=governance.address)

    # success
    assert local_gov.setGovTimeLock(new_time_lock, sender=governance.address)
    
    # Verify time lock modified event
    time_lock_log = filter_logs(local_gov, "GovChangeTimeLockModified")[0]
    assert time_lock_log.prevTimeLock == prev_time_lock
    assert time_lock_log.newTimeLock == new_time_lock
    
    assert local_gov.govChangeTimeLock() == new_time_lock

    # Test invalid time locks
    with boa.reverts("invalid time lock"):
        local_gov.setGovTimeLock(local_gov.minGovChangeTimeLock() - 1, sender=governance.address)
    with boa.reverts("invalid time lock"):
        local_gov.setGovTimeLock(local_gov.maxGovChangeTimeLock() + 1, sender=governance.address)

    # Test cannot change time lock during pending governance change
    local_gov.startGovernanceChange(mock_rando_contract, sender=governance.address)
    with boa.reverts("invalid time lock"):
        local_gov.setGovTimeLock(new_time_lock + 10, sender=governance.address)


def test_local_gov_undy_hq_integration(
    createMockLocalGov,
    governance,
    undy_hq,
):
    # Create local gov with UndyHq
    local_gov = createMockLocalGov(_undyHq=undy_hq)

    # Test UndyHq governance can govern
    assert local_gov.canGovern(governance.address)  # Local governance
    assert local_gov.canGovern(undy_hq.governance())  # UndyHq governance

    # Test UndyHq governance can change time lock
    new_time_lock = local_gov.govChangeTimeLock() + 10
    assert local_gov.setGovTimeLock(new_time_lock, sender=undy_hq.governance())
    assert local_gov.govChangeTimeLock() == new_time_lock


def test_local_gov_zero_address_handling(
    createMockLocalGov,
    deploy3r,
):
    hq_gov = createMockLocalGov(_undyHq=ZERO_ADDRESS)

    # Test zero address in governance change
    with boa.reverts("undy hq cannot set 0x0"):
        hq_gov.startGovernanceChange(ZERO_ADDRESS, sender=deploy3r)


def test_local_gov_set_back_to_zero_address(
    createMockLocalGov,
    mock_rando_contract,
    governance,
):
    local_gov = createMockLocalGov(_initialGov = mock_rando_contract)

    assert local_gov.governance() == mock_rando_contract.address
    assert local_gov.canGovern(mock_rando_contract)
    assert local_gov.canGovern(governance) # undy hq

    # success
    local_gov.startGovernanceChange(ZERO_ADDRESS, sender=mock_rando_contract.address)
    boa.env.time_travel(blocks=local_gov.govChangeTimeLock())
    local_gov.confirmGovernanceChange(sender=mock_rando_contract.address)

    assert local_gov.governance() == ZERO_ADDRESS
    assert not local_gov.canGovern(mock_rando_contract)
    assert local_gov.canGovern(governance) # undy hq


def test_local_gov_multiple_governors(
    createMockLocalGov,
    governance,
    mock_rando_contract,
    undy_hq,
    deploy3r,
):
    local_gov = createMockLocalGov(_undyHq=undy_hq)
    
    # Test initial governance access
    assert local_gov.canGovern(deploy3r)  # Local governance
    assert local_gov.canGovern(governance.address)  # UndyHq governance
    
    # Change local governance
    time_lock = local_gov.govChangeTimeLock()
    local_gov.startGovernanceChange(mock_rando_contract, sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    local_gov.confirmGovernanceChange(sender=mock_rando_contract.address)
    
    # Verify governance access after change
    assert local_gov.canGovern(mock_rando_contract)  # New local governance
    assert local_gov.canGovern(governance.address)  # UndyHq governance still works
    assert not local_gov.canGovern(deploy3r)  # Old governance no longer works


def test_local_gov_sequential_changes(
    createMockLocalGov,
    mock_rando_contract,
    deploy3r,
    another_rando_contract,
):
    local_gov = createMockLocalGov()
    time_lock = local_gov.govChangeTimeLock()
    
    # First governance change
    local_gov.startGovernanceChange(mock_rando_contract, sender=deploy3r)
    boa.env.time_travel(blocks=time_lock)
    local_gov.confirmGovernanceChange(sender=mock_rando_contract.address)
    
    # Verify first change
    assert local_gov.governance() == mock_rando_contract.address
    assert local_gov.numGovChanges() == 1
    assert not local_gov.canGovern(deploy3r)

    # Second governance change
    local_gov.startGovernanceChange(another_rando_contract, sender=mock_rando_contract.address)
    boa.env.time_travel(blocks=time_lock)
    local_gov.confirmGovernanceChange(sender=another_rando_contract.address)
    
    # Verify second change
    assert local_gov.governance() == another_rando_contract.address
    assert local_gov.numGovChanges() == 2
    assert not local_gov.canGovern(mock_rando_contract)


def test_local_gov_time_lock_edge_cases(
    createMockLocalGov,
    governance,
    mock_rando_contract,
):
    local_gov = createMockLocalGov(
        _minTimeLock = 100,
        _maxTimeLock = 200,
        _initialTimeLock = 150,
    )
    
    # Test time lock at minimum
    assert local_gov.setGovTimeLock(local_gov.minGovChangeTimeLock(), sender=governance.address)
    assert local_gov.govChangeTimeLock() == local_gov.minGovChangeTimeLock()
    
    # Test time lock at maximum
    assert local_gov.setGovTimeLock(local_gov.maxGovChangeTimeLock(), sender=governance.address)
    assert local_gov.govChangeTimeLock() == local_gov.maxGovChangeTimeLock()
    
    # Start governance change
    local_gov.startGovernanceChange(mock_rando_contract, sender=governance.address)
    
    # Try to change time lock during pending change
    with boa.reverts("invalid time lock"):
        local_gov.setGovTimeLock(local_gov.minGovChangeTimeLock(), sender=governance.address)
    
    # Complete governance change
    boa.env.time_travel(blocks=local_gov.govChangeTimeLock())
    local_gov.confirmGovernanceChange(sender=mock_rando_contract.address)
    
    # Verify time lock can be changed after governance change
    new_time_lock = local_gov.minGovChangeTimeLock() + 10
    assert local_gov.setGovTimeLock(new_time_lock, sender=mock_rando_contract.address)
    assert local_gov.govChangeTimeLock() == new_time_lock


def test_local_gov_undy_hq_governance_changes(
    createMockLocalGov,
    deploy3r,
    mock_rando_contract,
    undy_hq,
    governance,
):
    local_gov = createMockLocalGov()
    
    # undy hq
    assert undy_hq.governance() == governance.address
    assert undy_hq.canGovern(governance)
    assert not undy_hq.canGovern(deploy3r)
    assert len(undy_hq.getGovernors()) == 1

    # local gov
    assert local_gov.governance() == deploy3r
    assert local_gov.canGovern(deploy3r)
    assert local_gov.canGovern(governance)
    assert len(local_gov.getGovernors()) == 2
 
    # Change UndyHq governance
    time_lock = local_gov.govChangeTimeLock()
    undy_hq.startGovernanceChange(mock_rando_contract, sender=governance.address)
    boa.env.time_travel(blocks=time_lock)
    undy_hq.confirmGovernanceChange(sender=mock_rando_contract.address)
    
    # Verify local governance access after UndyHq change
    assert local_gov.canGovern(deploy3r)  # Local governance still works
    assert local_gov.canGovern(mock_rando_contract)  # New UndyHq governance works
    assert not local_gov.canGovern(governance.address)  # Old UndyHq governance no longer works


def test_local_gov_governance_change_validation(
    createMockLocalGov,
    deploy3r,
    mock_rando_contract,
    bob,
):
    local_gov = createMockLocalGov()
    
    # Test starting governance change with invalid parameters
    with boa.reverts("no perms"):
        local_gov.startGovernanceChange(mock_rando_contract, sender=bob)
    
    with boa.reverts("_newGov must be a contract"):
        local_gov.startGovernanceChange(bob, sender=deploy3r)
    
    with boa.reverts("invalid _newGov"):
        local_gov.startGovernanceChange(deploy3r, sender=deploy3r)
    
    # Start valid governance change
    local_gov.startGovernanceChange(mock_rando_contract, sender=deploy3r)
    
    # Test confirming governance change with invalid parameters
    with boa.reverts("time lock not reached"):
        local_gov.confirmGovernanceChange(sender=mock_rando_contract.address)

    boa.env.time_travel(blocks=local_gov.govChangeTimeLock())

    with boa.reverts("only new gov can confirm"):
        local_gov.confirmGovernanceChange(sender=deploy3r)
    
    # Complete governance change
    local_gov.confirmGovernanceChange(sender=mock_rando_contract.address)
    
    # Verify governance changed
    assert local_gov.governance() == mock_rando_contract.address
    assert local_gov.canGovern(mock_rando_contract)
    assert not local_gov.canGovern(deploy3r)
