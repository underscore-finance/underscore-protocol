from types import SimpleNamespace

import boa
import pytest
from eth_utils import keccak

from scripts.utils.registry_preconditions import (
    deploy_and_register,
    register_address,
    require_registry_prefix,
)

pytestmark = pytest.always

TEST_RUNTIME_CODEHASH = "0x" + keccak(b"\x01").hex()
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


class FakeRegistry:
    def __init__(
        self,
        addresses=(),
        *,
        start_result=True,
        confirmed_id=None,
        pending=None,
        descriptions=None,
    ):
        self.addresses = list(addresses)
        self.descriptions = list(descriptions or addresses)
        self.start_result = start_result
        self.confirmed_id = confirmed_id
        self.pending = dict(pending or {})

    def numAddrs(self):
        return len(self.addresses) + 1

    def registryChangeTimeLock(self):
        return 0

    def getAddr(self, registry_id):
        return self.addresses[registry_id - 1]

    def startAddNewAddressToRegistry(self, address, description):
        self.pending[str(address)] = SimpleNamespace(
            description=description,
            confirmBlock=1,
        )
        return self.start_result

    def confirmNewAddressToRegistry(self, address):
        if self.confirmed_id is not None:
            return self.confirmed_id
        self.addresses.append(str(address))
        self.descriptions.append(self.pending[str(address)].description)
        self.pending.pop(str(address), None)
        return len(self.addresses)

    def pendingNewAddr(self, address):
        return self.pending.get(
            str(address),
            SimpleNamespace(description="", confirmBlock=0),
        )

    def getRegId(self, address):
        try:
            return self.addresses.index(str(address)) + 1
        except ValueError:
            return 0

    def getAddrInfo(self, registry_id):
        return SimpleNamespace(
            addr=self.addresses[registry_id - 1],
            version=1,
            lastModified=1,
            description=self.descriptions[registry_id - 1],
        )

    def pendingAddrUpdate(self, registry_id):
        return SimpleNamespace(newAddr=ZERO_ADDRESS, initiatedBlock=0, confirmBlock=0)

    def pendingAddrDisable(self, registry_id):
        return SimpleNamespace(initiatedBlock=0, confirmBlock=0)

    def hasPendingHqConfigChange(self, registry_id):
        return False


class FakeContract:
    def __init__(self, address):
        self.address = address

    def __str__(self):
        return self.address


class FakeMigration:
    def __init__(self, *, manifest=None, deployment_address="0x300"):
        self.calls = []
        self.manifest = dict(manifest or {})
        self.deployment_address = deployment_address
        self.deploy_calls = []
        self.attach_calls = []
        self.discard_calls = 0
        self.preflight_calls = []

    def execute(self, transaction, *args, **kwargs):
        self.calls.append((transaction.__name__, args, kwargs))
        return transaction(*args)

    def get_address(self, name):
        return self.manifest[name]

    def get_manifest_entry(self, name):
        entry = self.manifest.get(name)
        if entry is None:
            return None
        if isinstance(entry, dict):
            return entry
        return {
            "address": entry,
            "runtime_codehash": TEST_RUNTIME_CODEHASH,
        }

    def deploy(self, name, *args, **kwargs):
        self.deploy_calls.append((name, args, kwargs))
        contract = FakeContract(self.deployment_address)
        self.manifest[name] = contract.address
        return contract

    def preflight_contract_manifest(self, name, args):
        self.preflight_calls.append((name, args))

    def register_existing(self, name, address, *args):
        self.attach_calls.append((name, address, args))
        self.manifest[name] = address
        return FakeContract(address)

    def discard_transaction_replay(self):
        self.discard_calls += 1


def test_require_registry_prefix_checks_count_and_exact_addresses(monkeypatch):
    monkeypatch.setattr(boa.env, "get_code", lambda _address: b"\x01")
    registry = FakeRegistry(
        ("0xAbC", "0xDef"),
        descriptions=("first", "second"),
    )

    require_registry_prefix(
        registry,
        (("first", "0xabc"), ("second", "0xdEF")),
        "before deployment",
    )

    with pytest.raises(
        RuntimeError,
        match="before deployment: registry next ID is 3, expected 2",
    ):
        require_registry_prefix(registry, (("first", "0xabc"),), "before deployment")

    with pytest.raises(
        RuntimeError,
        match=(
            "before deployment: registry ID 2 is 0xDef, "
            "expected second at 0xBAD"
        ),
    ):
        require_registry_prefix(
            registry,
            (("first", "0xabc"), ("second", "0xBAD")),
            "before deployment",
        )


def test_register_address_executes_both_transactions_and_checks_exact_id():
    migration = FakeMigration()
    registry = FakeRegistry(confirmed_id=3)

    assert register_address(migration, registry, "0x123", "Lego Book", 3) == 3
    assert [name for name, _, _ in migration.calls] == [
        "startAddNewAddressToRegistry",
        "confirmNewAddressToRegistry",
    ]
    assert all(kwargs == {"no_retry": True} for _, _, kwargs in migration.calls)


def test_deploy_and_register_handles_fresh_pending_and_confirmed_states(monkeypatch):
    monkeypatch.setattr(boa.env, "get_code", lambda _address: b"\x01")
    context = "before test deployment"

    fresh_migration = FakeMigration()
    fresh_registry = FakeRegistry()
    fresh = deploy_and_register(
        fresh_migration,
        fresh_registry,
        name="TestContract",
        args=("arg",),
        description="Test Contract",
        expected_id=1,
        expected_prefix=(),
        context=context,
        validate=lambda _contract: None,
        expected_runtime_codehash=TEST_RUNTIME_CODEHASH,
        expected_runtime=b"\x01",
    )
    assert fresh.address == "0x300"
    assert fresh_migration.deploy_calls == [
        ("TestContract", ("arg",), {"no_retry": True})
    ]
    assert fresh_migration.preflight_calls == [("TestContract", ("arg",))]
    assert [name for name, _, _ in fresh_migration.calls] == [
        "startAddNewAddressToRegistry",
        "confirmNewAddressToRegistry",
    ]

    pending_registry = FakeRegistry(
        pending={
            "0x300": SimpleNamespace(
                description="Test Contract",
                confirmBlock=1,
            )
        }
    )
    pending_migration = FakeMigration(manifest={"TestContract": "0x300"})
    deploy_and_register(
        pending_migration,
        pending_registry,
        name="TestContract",
        args=("arg",),
        description="Test Contract",
        expected_id=1,
        expected_prefix=(),
        context=context,
        validate=lambda _contract: None,
        expected_runtime_codehash=TEST_RUNTIME_CODEHASH,
        expected_runtime=b"\x01",
    )
    assert pending_migration.deploy_calls == []
    assert pending_migration.preflight_calls == []
    assert [name for name, _, _ in pending_migration.calls] == [
        "confirmNewAddressToRegistry"
    ]

    confirmed_registry = FakeRegistry(
        ("0x300",),
        descriptions=("Test Contract",),
    )
    confirmed_migration = FakeMigration(manifest={"TestContract": "0x300"})
    deploy_and_register(
        confirmed_migration,
        confirmed_registry,
        name="TestContract",
        args=("arg",),
        description="Test Contract",
        expected_id=1,
        expected_prefix=(),
        context=context,
        validate=lambda _contract: None,
        expected_runtime_codehash=TEST_RUNTIME_CODEHASH,
        expected_runtime=b"\x01",
    )
    assert confirmed_migration.deploy_calls == []
    assert confirmed_migration.preflight_calls == []
    assert confirmed_migration.calls == []
    assert confirmed_migration.attach_calls == [
        ("TestContract", "0x300", ("arg",))
    ]


def test_deploy_and_register_resumes_earlier_child_with_later_prefix(monkeypatch):
    monkeypatch.setattr(boa.env, "get_code", lambda _address: b"\x01")
    registry = FakeRegistry(
        ("0x300", "0x400"),
        descriptions=("SwitchboardAlpha", "SwitchboardBravo"),
    )
    migration = FakeMigration(
        manifest={"SwitchboardAlpha": "0x300"},
    )

    contract = deploy_and_register(
        migration,
        registry,
        name="SwitchboardAlpha",
        args=(),
        description="SwitchboardAlpha",
        expected_id=1,
        expected_prefix=(),
        context="before alpha",
        validate=lambda _contract: None,
        expected_runtime_codehash=TEST_RUNTIME_CODEHASH,
        expected_runtime=b"\x01",
        maximum_next_id=3,
    )

    assert contract.address == "0x300"
    assert migration.deploy_calls == []
    assert migration.calls == []


def test_deploy_and_register_rejects_manifest_confirmed_mismatch(monkeypatch):
    monkeypatch.setattr(boa.env, "get_code", lambda _address: b"\x01")
    registry = FakeRegistry(
        ("0x300",),
        descriptions=("Test Contract",),
    )
    migration = FakeMigration(manifest={"TestContract": "0xBAD"})

    with pytest.raises(
        RuntimeError,
        match=(
            "confirmed TestContract: TestContract address is 0x300, but the "
            "live manifest records 0xBAD"
        ),
    ):
        deploy_and_register(
            migration,
            registry,
            name="TestContract",
            args=(),
            description="Test Contract",
            expected_id=1,
            expected_prefix=(),
            context="before test deployment",
            validate=lambda _contract: None,
            expected_runtime_codehash=TEST_RUNTIME_CODEHASH,
            expected_runtime=b"\x01",
        )

    assert migration.deploy_calls == []
    assert migration.calls == []


def test_deploy_and_register_rejects_manifestless_or_unapproved_runtime(monkeypatch):
    registry = FakeRegistry(
        ("0x300",),
        descriptions=("Test Contract",),
    )

    monkeypatch.setattr(boa.env, "get_code", lambda _address: b"\x01")
    with pytest.raises(
        RuntimeError,
        match="no authenticated manifest entry exists for TestContract",
    ):
        deploy_and_register(
            FakeMigration(),
            registry,
            name="TestContract",
            args=(),
            description="Test Contract",
            expected_id=1,
            expected_prefix=(),
            context="before test deployment",
            validate=lambda _contract: None,
            expected_runtime_codehash=TEST_RUNTIME_CODEHASH,
            expected_runtime=b"\x01",
        )

    monkeypatch.setattr(boa.env, "get_code", lambda _address: b"\x02")
    with pytest.raises(
        RuntimeError,
        match="runtime codehash .* expected approved hash",
    ):
        deploy_and_register(
            FakeMigration(manifest={"TestContract": "0x300"}),
            registry,
            name="TestContract",
            args=(),
            description="Test Contract",
            expected_id=1,
            expected_prefix=(),
            context="before test deployment",
            validate=lambda _contract: None,
            expected_runtime_codehash=TEST_RUNTIME_CODEHASH,
            expected_runtime=b"\x01",
        )


@pytest.mark.parametrize(
    ("start_result", "confirmed_id", "message", "expected_calls"),
    (
        (False, 3, "failed to start registration for Lego Book", 1),
        (True, 2, "registered Lego Book at ID 2, expected 3", 2),
        (True, True, "registered Lego Book at ID True, expected 3", 2),
    ),
)
def test_register_address_fails_closed_on_unexpected_results(
    start_result,
    confirmed_id,
    message,
    expected_calls,
):
    migration = FakeMigration()
    registry = FakeRegistry(
        start_result=start_result,
        confirmed_id=confirmed_id,
    )

    with pytest.raises(RuntimeError, match=message):
        register_address(migration, registry, "0x123", "Lego Book", 3)

    assert len(migration.calls) == expected_calls
