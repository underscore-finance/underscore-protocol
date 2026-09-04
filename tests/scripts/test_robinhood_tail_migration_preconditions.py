import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from eth_utils import keccak

from scripts.utils import ripe_preconditions


pytestmark = pytest.always

MIGRATIONS_DIR = Path("migrations/robinhood-mainnet/v1")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
HQ_ADDRESS = "0x1111111111111111111111111111111111111111"
FACTORY_ADDRESS = "0x2222222222222222222222222222222222222222"
GOVERNANCE_ADDRESS = "0x3333333333333333333333333333333333333333"
WETH_ADDRESS = "0x4444444444444444444444444444444444444444"
WALLET_IMPLEMENTATION = "0x5555555555555555555555555555555555555555"
CONFIG_IMPLEMENTATION = "0x6666666666666666666666666666666666666666"
TEST_RUNTIME = b"\x01"
TEST_RUNTIME_HASH = "0x" + keccak(TEST_RUNTIME).hex()
RIPE_HQ = "0x7777777777777777777777777777777777777777"
RIPE_TOKEN = "0x8888888888888888888888888888888888888888"
PRICE_DESK = "0x9999999999999999999999999999999999999999"
RIPE_TELLER = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

CORE_MANIFEST = {
    "Ledger": "0x0000000000000000000000000000000000000001",
    "MissionControl": "0x0000000000000000000000000000000000000002",
    "LegoBook": "0x0000000000000000000000000000000000000003",
    "Switchboard": "0x0000000000000000000000000000000000000004",
    "Hatchery": "0x0000000000000000000000000000000000000005",
    "LootDistributor": "0x0000000000000000000000000000000000000006",
    "Appraiser": "0x0000000000000000000000000000000000000007",
    "WalletBackpack": "0x0000000000000000000000000000000000000008",
    "Billing": "0x0000000000000000000000000000000000000009",
    "SwitchboardAlpha": "0x0000000000000000000000000000000000000011",
    "SwitchboardBravo": "0x0000000000000000000000000000000000000012",
}


# These migration preflight tests do not need the repo-wide protocol fixtures.
@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


def _load_migration(filename):
    path = MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(
        f"test_{filename.replace('-', '_').replace('.', '_')}",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeRegistry:
    def __init__(self, address, entries):
        self.address = address
        self.entries = entries

    def getAddr(self, reg_id):
        return self.entries.get(reg_id, ZERO_ADDRESS)

    def numAddrs(self):
        return max(self.entries, default=0) + 1


class FakeMigration:
    def __init__(self, *, integrations=None, manifest=None, contracts=None):
        self.blueprint = SimpleNamespace(
            INTEGRATION_ADDYS=integrations or {},
            CONSTANTS=SimpleNamespace(ZERO_ADDRESS=ZERO_ADDRESS),
            TOKENS={},
            PARAMS={},
        )
        self.log = SimpleNamespace(h2=lambda _message: None)
        self.manifest = manifest or {}
        self.contracts = contracts or {}
        self.deploy_calls = []
        self.execute_calls = []
        self.get_contract_calls = []
        self.discard_calls = 0

    def get_address(self, name):
        return self.manifest[name]

    def get_contract(self, name):
        self.get_contract_calls.append(name)
        return self.contracts[name]

    def deploy(self, *args, **kwargs):
        self.deploy_calls.append((args, kwargs))
        return object()

    def execute(self, *args, **kwargs):
        self.execute_calls.append((args, kwargs))
        return True

    def discard_transaction_replay(self):
        self.discard_calls += 1


def _patch_code(monkeypatch, module, code_addresses):
    code_addresses = {address.lower() for address in code_addresses}
    monkeypatch.setattr(
        module.boa.env,
        "get_code",
        lambda address: b"\x01" if str(address).lower() in code_addresses else b"",
    )


def _fake_factory(hq=HQ_ADDRESS, admin=GOVERNANCE_ADDRESS):
    contract = SimpleNamespace(
        undyHq=lambda: hq,
        WALLET_FACTORY_ADMIN=lambda: admin,
        USER_WALLET_IMPLEMENTATION=lambda: WALLET_IMPLEMENTATION,
        USER_WALLET_IMPLEMENTATION_CODEHASH=lambda: keccak(TEST_RUNTIME),
        USER_WALLET_CONFIG_IMPLEMENTATION=lambda: CONFIG_IMPLEMENTATION,
        USER_WALLET_CONFIG_IMPLEMENTATION_CODEHASH=lambda: keccak(TEST_RUNTIME),
    )
    return SimpleNamespace(at=lambda _address: contract)


def _ripe_migration():
    migration = FakeMigration(
        integrations={
            "RIPE_HQ_V1": RIPE_HQ,
            "RIPE_PRICE_DESK": PRICE_DESK,
            "RIPE_HQ_V1_CODEHASH": TEST_RUNTIME_HASH,
            "RIPE_TOKEN_CODEHASH": TEST_RUNTIME_HASH,
            "RIPE_PRICE_DESK_CODEHASH": TEST_RUNTIME_HASH,
            "RIPE_TELLER": RIPE_TELLER,
            "RIPE_TELLER_CODEHASH": TEST_RUNTIME_HASH,
        }
    )
    migration.blueprint.TOKENS = {"RIPE": RIPE_TOKEN}
    return migration


def _patch_ripe_registry(monkeypatch, entries, code_addresses):
    _patch_code(monkeypatch, ripe_preconditions, code_addresses)
    registry = FakeRegistry(RIPE_HQ, entries)
    monkeypatch.setattr(
        ripe_preconditions.boa,
        "load_abi",
        lambda *_args, **_kwargs: SimpleNamespace(at=lambda _address: registry),
    )


def _hatchery_migration(integrations=None):
    prefix = {reg_id: CORE_MANIFEST[name] for reg_id, name in enumerate(
        ("Ledger", "MissionControl", "LegoBook", "Switchboard"),
        start=1,
    )}
    hq = FakeRegistry(HQ_ADDRESS, prefix)
    migration = FakeMigration(
        integrations=integrations,
        manifest=CORE_MANIFEST,
        contracts={"UndyHq": hq},
    )
    migration.blueprint.TOKENS = {
        "WETH": WETH_ADDRESS,
        "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
    }
    return migration


def _approved_factory_integrations():
    return {
        "WALLET_FACTORY": FACTORY_ADDRESS,
        "WALLET_FACTORY_CODEHASH": TEST_RUNTIME_HASH,
        "WETH_CODEHASH": TEST_RUNTIME_HASH,
    }


def test_hatchery_missing_factory_fails_before_any_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration()
    _patch_code(monkeypatch, module, CORE_MANIFEST.values())

    with pytest.raises(
        RuntimeError,
        match="Robinhood WALLET_FACTORY is not approved; refusing to deploy Hatchery",
    ):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_hatchery_factory_without_code_fails_before_any_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration(_approved_factory_integrations())
    _patch_code(monkeypatch, module, CORE_MANIFEST.values())

    with pytest.raises(
        RuntimeError,
        match="Robinhood WALLET_FACTORY has no code; refusing to deploy Hatchery",
    ):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_hatchery_factory_for_wrong_hq_fails_before_any_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration(_approved_factory_integrations())
    _patch_code(
        monkeypatch,
        module,
        [
            *CORE_MANIFEST.values(),
            FACTORY_ADDRESS,
            WALLET_IMPLEMENTATION,
            CONFIG_IMPLEMENTATION,
        ],
    )
    monkeypatch.setattr(
        module.boa,
        "load_abi",
        lambda *_args, **_kwargs: _fake_factory(
            hq="0x4444444444444444444444444444444444444444"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="Robinhood WALLET_FACTORY is initialized for a different UndyHq",
    ):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_hatchery_factory_codehash_mismatch_fails_before_any_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    integrations = _approved_factory_integrations()
    integrations["WALLET_FACTORY_CODEHASH"] = "0x" + "ff" * 32
    migration = _hatchery_migration(integrations)
    _patch_code(
        monkeypatch,
        module,
        [*CORE_MANIFEST.values(), FACTORY_ADDRESS],
    )

    with pytest.raises(
        RuntimeError,
        match="Robinhood WALLET_FACTORY live codehash does not match its approval",
    ):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_hatchery_zero_factory_admin_fails_before_any_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration(_approved_factory_integrations())
    _patch_code(
        monkeypatch,
        module,
        [
            *CORE_MANIFEST.values(),
            FACTORY_ADDRESS,
            WALLET_IMPLEMENTATION,
            CONFIG_IMPLEMENTATION,
        ],
    )
    monkeypatch.setattr(
        module.boa,
        "load_abi",
        lambda *_args, **_kwargs: _fake_factory(admin=ZERO_ADDRESS),
    )

    with pytest.raises(
        RuntimeError,
        match="Robinhood WALLET_FACTORY still has the zero-address admin placeholder",
    ):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_hatchery_missing_implementation_code_fails_before_any_transaction(
    monkeypatch,
):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration(_approved_factory_integrations())
    _patch_code(
        monkeypatch,
        module,
        [*CORE_MANIFEST.values(), FACTORY_ADDRESS, CONFIG_IMPLEMENTATION],
    )
    monkeypatch.setattr(
        module.boa,
        "load_abi",
        lambda *_args, **_kwargs: _fake_factory(),
    )

    with pytest.raises(RuntimeError, match="UserWallet implementation has no code"):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_hatchery_weth_without_code_fails_before_any_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration(_approved_factory_integrations())
    _patch_code(
        monkeypatch,
        module,
        [
            *CORE_MANIFEST.values(),
            FACTORY_ADDRESS,
            WALLET_IMPLEMENTATION,
            CONFIG_IMPLEMENTATION,
        ],
    )
    monkeypatch.setattr(
        module.boa,
        "load_abi",
        lambda *_args, **_kwargs: _fake_factory(),
    )

    with pytest.raises(
        RuntimeError,
        match="Robinhood WETH has no code; refusing to deploy Hatchery",
    ):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


@pytest.mark.parametrize(
    ("registry_id", "wrong_address", "expected_error"),
    [
        (
            3,
            ZERO_ADDRESS,
            f"Robinhood RipeHq ID 3 is {ZERO_ADDRESS}, expected RIPE at {RIPE_TOKEN}",
        ),
        (
            7,
            ZERO_ADDRESS,
            "Robinhood RipeHq ID 7 is "
            f"{ZERO_ADDRESS}, expected PriceDesk at {PRICE_DESK}",
        ),
    ],
)
def test_ripe_registry_immutable_dependency_mismatch_fails_exactly(
    monkeypatch,
    registry_id,
    wrong_address,
    expected_error,
):
    migration = _ripe_migration()
    entries = {3: RIPE_TOKEN, 7: PRICE_DESK, 17: RIPE_TELLER}
    entries[registry_id] = wrong_address
    _patch_ripe_registry(
        monkeypatch,
        entries,
        [RIPE_HQ, RIPE_TOKEN, PRICE_DESK, RIPE_TELLER],
    )

    with pytest.raises(RuntimeError) as exc_info:
        ripe_preconditions.require_robinhood_ripe_dependencies(migration)

    assert str(exc_info.value) == expected_error


def test_ripe_registry_teller_must_have_code(monkeypatch):
    migration = _ripe_migration()
    _patch_ripe_registry(
        monkeypatch,
        {3: RIPE_TOKEN, 7: PRICE_DESK, 17: RIPE_TELLER},
        [RIPE_HQ, RIPE_TOKEN, PRICE_DESK],
    )

    with pytest.raises(
        RuntimeError,
        match="Robinhood RipeHq ID 17 Teller has no code",
    ):
        ripe_preconditions.require_robinhood_ripe_dependencies(migration)


def test_ripe_registry_exact_dependencies_pass(monkeypatch):
    migration = _ripe_migration()
    _patch_ripe_registry(
        monkeypatch,
        {3: RIPE_TOKEN, 7: PRICE_DESK, 17: RIPE_TELLER},
        [RIPE_HQ, RIPE_TOKEN, PRICE_DESK, RIPE_TELLER],
    )

    assert ripe_preconditions.require_robinhood_ripe_dependencies(migration) == (
        RIPE_HQ,
        RIPE_TOKEN,
        PRICE_DESK,
        RIPE_TELLER,
    )


def test_hatchery_wrong_core_prefix_fails_before_factory_or_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration({"WALLET_FACTORY": FACTORY_ADDRESS})
    migration.contracts["UndyHq"].entries[3] = ZERO_ADDRESS
    _patch_code(
        monkeypatch,
        module,
        [*CORE_MANIFEST.values(), FACTORY_ADDRESS],
    )

    with pytest.raises(
        RuntimeError
    ) as exc_info:
        module.migrate(migration)

    assert str(exc_info.value) == (
        "before Robinhood Hatchery deployment: registry ID 3 is "
        f"{ZERO_ADDRESS}, expected LegoBook at {CORE_MANIFEST['LegoBook']}"
    )

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


@pytest.mark.parametrize(
    ("filename", "dependency", "reg_id", "context"),
    [
        (
            "0006-LootDistributor.py",
            "Hatchery",
            5,
            "before Robinhood LootDistributor deployment",
        ),
        (
            "0007-Appraiser.py",
            "LootDistributor",
            6,
            "before Robinhood Appraiser deployment",
        ),
        (
            "0008-WalletBackpack.py",
            "Appraiser",
            7,
            "before Robinhood WalletBackpack deployment",
        ),
        (
            "0009-Billing.py",
            "WalletBackpack",
            8,
            "before Robinhood Billing deployment",
        ),
    ],
)
def test_tail_dependency_mismatch_never_deploys_or_mutates_registry(
    monkeypatch,
    filename,
    dependency,
    reg_id,
    context,
):
    module = _load_migration(filename)
    hq_names = (
        "Ledger",
        "MissionControl",
        "LegoBook",
        "Switchboard",
        "Hatchery",
        "LootDistributor",
        "Appraiser",
        "WalletBackpack",
    )
    entries = {
        index: CORE_MANIFEST[name]
        for index, name in enumerate(hq_names[:reg_id], start=1)
    }
    entries[reg_id] = ZERO_ADDRESS
    hq = FakeRegistry(HQ_ADDRESS, entries)
    migration = FakeMigration(
        manifest=CORE_MANIFEST,
        contracts={"UndyHq": hq},
    )
    _patch_code(monkeypatch, module, CORE_MANIFEST.values())

    with pytest.raises(RuntimeError) as exc_info:
        module.migrate(migration)

    assert str(exc_info.value) == (
        f"{context}: registry ID {reg_id} is {ZERO_ADDRESS}, "
        f"expected {dependency} at {CORE_MANIFEST[dependency]}"
    )

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_robinhood_migrations_never_hide_transactions_inside_python_asserts():
    violations = []
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            for child in ast.walk(node.test):
                if not isinstance(child, ast.Call):
                    continue
                function = child.func
                if (
                    isinstance(function, ast.Attribute)
                    and function.attr in {"execute", "deploy", "deploy_bp"}
                ):
                    violations.append((path.name, node.lineno, function.attr))

    assert violations == []


def test_robinhood_migration_writes_are_all_single_attempt():
    violations = []
    for path in sorted(MIGRATIONS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if not (
                isinstance(function, ast.Attribute)
                and isinstance(function.value, ast.Name)
                and function.value.id == "migration"
                and function.attr in {"execute", "deploy", "deploy_bp"}
            ):
                continue
            no_retry = next(
                (keyword.value for keyword in node.keywords if keyword.arg == "no_retry"),
                None,
            )
            if not (
                isinstance(no_retry, ast.Constant)
                and no_retry.value is True
            ):
                violations.append((path.name, node.lineno, function.attr))

    assert violations == []


@pytest.mark.parametrize(
    ("integrations", "coded", "error"),
    [
        (
            {},
            [],
            "Robinhood GOVERNANCE is not approved; refusing to finish UndyHq setup",
        ),
        (
            {
                "GOVERNANCE": GOVERNANCE_ADDRESS,
                "GOVERNANCE_CODEHASH": TEST_RUNTIME_HASH,
            },
            [],
            "Robinhood GOVERNANCE has no code; refusing to finish UndyHq setup",
        ),
    ],
)
def test_finish_setup_unapproved_governance_fails_before_any_state_read_or_write(
    monkeypatch,
    integrations,
    coded,
    error,
):
    module = _load_migration("1000-FinishSetup.py")
    migration = FakeMigration(integrations=integrations)
    _patch_code(monkeypatch, module, coded)

    with pytest.raises(RuntimeError, match=error):
        module.migrate(migration)

    assert migration.get_contract_calls == []
    assert migration.deploy_calls == []
    assert migration.execute_calls == []
