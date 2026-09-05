import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import boa
import pytest
from eth_utils import keccak

from scripts.utils import ripe_preconditions
from scripts.utils.registry_preconditions import require_registry_prefix
from scripts.utils.robinhood_empty_registry import (
    validate_empty_robinhood_registry,
)


pytestmark = pytest.always

MIGRATIONS_DIR = Path("migrations/robinhood-mainnet/v1")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
HQ_ADDRESS = "0x1111111111111111111111111111111111111111"
GOVERNANCE_ADDRESS = "0x3333333333333333333333333333333333333333"
DEPLOYER_ADDRESS = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"
WETH_ADDRESS = "0x4444444444444444444444444444444444444444"
TEST_RUNTIME = b"\x01"
TEST_RUNTIME_HASH = "0x" + keccak(TEST_RUNTIME).hex()
RIPE_HQ = "0x7777777777777777777777777777777777777777"
RIPE_TOKEN = "0x8888888888888888888888888888888888888888"
PRICE_DESK = "0x9999999999999999999999999999999999999999"
RIPE_TELLER = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

CORE_MANIFEST = {
    "UndyHq": HQ_ADDRESS,
    "Ledger": "0x0000000000000000000000000000000000000001",
    "MissionControl": "0x0000000000000000000000000000000000000002",
    "LegoBook": "0x0000000000000000000000000000000000000003",
    "Switchboard": "0x0000000000000000000000000000000000000004",
    "Hatchery": "0x0000000000000000000000000000000000000005",
    "LootDistributor": "0x0000000000000000000000000000000000000006",
    "Appraiser": "0x0000000000000000000000000000000000000007",
    "WalletBackpack": "0x0000000000000000000000000000000000000008",
    "Billing": "0x0000000000000000000000000000000000000009",
    "VaultRegistry": "0x000000000000000000000000000000000000000a",
    "Helpers": "0x000000000000000000000000000000000000000b",
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

    def getAddrInfo(self, reg_id):
        descriptions = {
            1: "Ledger",
            2: "Mission Control",
            3: "Lego Book",
            4: "Switchboard",
            5: "Hatchery",
            6: "Loot Distributor",
            7: "Appraiser",
            8: "Wallet Backpack",
            9: "Billing",
            10: "Vault Registry",
            11: "Helpers",
        }
        return SimpleNamespace(
            version=1,
            description=descriptions.get(reg_id, ""),
        )

    def pendingAddrUpdate(self, _reg_id):
        return SimpleNamespace(
            newAddr=ZERO_ADDRESS,
            initiatedBlock=0,
            confirmBlock=0,
        )

    def pendingAddrDisable(self, _reg_id):
        return SimpleNamespace(initiatedBlock=0, confirmBlock=0)

    def hasPendingHqConfigChange(self, _reg_id):
        return False

    def registryChangeTimeLock(self):
        return 0

    def governance(self):
        return DEPLOYER_ADDRESS


class FakeMigration:
    def __init__(self, *, integrations=None, manifest=None, contracts=None):
        self.blueprint = SimpleNamespace(
            INTEGRATION_ADDYS=integrations or {},
            CONSTANTS=SimpleNamespace(ZERO_ADDRESS=ZERO_ADDRESS),
            TOKENS={},
            PARAMS={},
        )
        self.account = SimpleNamespace(address=DEPLOYER_ADDRESS)
        self.log = SimpleNamespace(h2=lambda _message: None)
        self.manifest = manifest or {}
        self.contracts = contracts or {}
        self.deploy_calls = []
        self.execute_calls = []
        self.preflight_calls = []
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

    def preflight_contract_manifest(self, name, args):
        self.preflight_calls.append((name, args))

    def discard_transaction_replay(self):
        self.discard_calls += 1


class FakeEmptyRegistry:
    def __init__(
        self,
        name,
        address,
        *,
        governance=ZERO_ADDRESS,
        governors=None,
        num_addrs=1,
        registered_count=None,
        semantic_probe=False,
    ):
        self.name = name
        self.address = address
        self._governance = governance
        self._governors = [DEPLOYER_ADDRESS] if governors is None else governors
        self._num_addrs = num_addrs
        self._registered_count = (
            num_addrs - 1 if registered_count is None else registered_count
        )
        self._semantic_probe = semantic_probe

    def getUndyHq(self):
        return HQ_ADDRESS

    def getUndyHqFromGov(self):
        return HQ_ADDRESS

    def governance(self):
        return self._governance

    def getGovernors(self):
        return self._governors

    def numGovChanges(self):
        return 0

    def hasPendingGovChange(self):
        return False

    def pendingGov(self):
        return SimpleNamespace(
            newGov=ZERO_ADDRESS,
            initiatedBlock=0,
            confirmBlock=0,
        )

    def govChangeTimeLock(self):
        return 7_200

    def minGovChangeTimeLock(self):
        return 7_200

    def maxGovChangeTimeLock(self):
        return 216_000

    def registryChangeTimeLock(self):
        return 0

    def minRegistryTimeLock(self):
        return 600

    def maxRegistryTimeLock(self):
        return 216_000

    def numAddrs(self):
        return self._num_addrs

    def getNumAddrs(self):
        return self._registered_count

    def getRegistryDescription(self):
        return f"{self.name}.vy"

    def isPaused(self):
        return False

    def canMintUndy(self):
        return False

    def isBasicEarnVault(self, _probe):
        return self._semantic_probe

    def isHelpersAddr(self, _probe):
        return self._semantic_probe


def _patch_code(monkeypatch, module, code_addresses):
    code_addresses = {address.lower() for address in code_addresses}
    monkeypatch.setattr(
        boa.env,
        "get_code",
        lambda address: b"\x01" if str(address).lower() in code_addresses else b"",
    )


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


def _approved_hatchery_integrations():
    return {
        "WETH_CODEHASH": TEST_RUNTIME_HASH,
    }


def _patch_hatchery_runtime(monkeypatch, module, migration):
    monkeypatch.setattr(
        module,
        "require_authenticated_robinhood_hq",
        lambda _migration: migration.contracts["UndyHq"],
    )
    monkeypatch.setattr(
        module,
        "require_approved_robinhood_runtime",
        lambda *_args, **_kwargs: TEST_RUNTIME,
    )


def test_hatchery_missing_weth_codehash_fails_before_any_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration()
    _patch_hatchery_runtime(monkeypatch, module, migration)
    _patch_code(monkeypatch, module, [WETH_ADDRESS])

    with pytest.raises(
        RuntimeError,
        match="Robinhood WETH_CODEHASH is not approved; refusing to deploy Hatchery",
    ):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_hatchery_weth_without_code_fails_before_any_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration(_approved_hatchery_integrations())
    _patch_hatchery_runtime(monkeypatch, module, migration)
    _patch_code(monkeypatch, module, [])

    with pytest.raises(
        RuntimeError,
        match="Robinhood WETH has no code; refusing to deploy Hatchery",
    ):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_hatchery_weth_codehash_mismatch_fails_before_any_transaction(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration(
        {"WETH_CODEHASH": "0x" + "ff" * 32}
    )
    _patch_hatchery_runtime(monkeypatch, module, migration)
    _patch_code(monkeypatch, module, [WETH_ADDRESS])

    with pytest.raises(
        RuntimeError,
        match="Robinhood WETH live codehash does not match its approval",
    ):
        module.migrate(migration)

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


def test_hatchery_uses_original_seven_argument_constructor(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration(_approved_hatchery_integrations())
    _patch_hatchery_runtime(monkeypatch, module, migration)
    _patch_code(monkeypatch, module, [WETH_ADDRESS])
    captured = {}

    def capture_deployment(_migration, registry, **kwargs):
        captured.update(kwargs)
        captured["registry"] = registry
        return SimpleNamespace(address=CORE_MANIFEST["Hatchery"])

    monkeypatch.setattr(module, "deploy_and_register", capture_deployment)
    monkeypatch.setattr(
        migration,
        "preflight_contract_manifest",
        lambda name, args: captured.update(preflight=(name, args)),
        raising=False,
    )

    module.migrate(migration)

    args = captured["args"]
    assert len(args) == 7
    assert args[0] is migration.contracts["UndyHq"]
    assert args[1:3] == (
        WETH_ADDRESS,
        migration.blueprint.TOKENS["ETH"],
    )
    assert args[3:] == (
        [True, True, True, True],
        [ZERO_ADDRESS, 0],
        [ZERO_ADDRESS, 0],
        ZERO_ADDRESS,
    )
    assert captured["preflight"] == ("Hatchery", args)
    assert captured["expected_runtime"] == TEST_RUNTIME
    assert "wallet_factory" not in captured

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
        match="Robinhood Teller has no code",
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


def test_hatchery_wrong_core_prefix_fails_before_deployment(monkeypatch):
    module = _load_migration("0005-Hatchery.py")
    migration = _hatchery_migration(_approved_hatchery_integrations())
    migration.contracts["UndyHq"].entries[3] = ZERO_ADDRESS
    _patch_hatchery_runtime(monkeypatch, module, migration)
    _patch_code(monkeypatch, module, [*CORE_MANIFEST.values(), WETH_ADDRESS])
    monkeypatch.setattr(
        migration,
        "preflight_contract_manifest",
        lambda *_args: None,
        raising=False,
    )

    def check_prefix(_migration, registry, **kwargs):
        require_registry_prefix(
            registry,
            kwargs["expected_prefix"],
            kwargs["context"],
        )

    monkeypatch.setattr(module, "deploy_and_register", check_prefix)

    with pytest.raises(RuntimeError) as exc_info:
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
        (
            "0010-VaultRegistry.py",
            "Billing",
            9,
            "before Robinhood VaultRegistry deployment",
        ),
        (
            "0011-Helpers.py",
            "VaultRegistry",
            10,
            "before Robinhood Helpers deployment",
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
        "Billing",
        "VaultRegistry",
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
    migration.blueprint.PARAMS = {
        "UNDY_HQ_MIN_GOV_TIMELOCK": 7_200,
        "UNDY_HQ_MAX_GOV_TIMELOCK": 216_000,
        "UNDY_HQ_MIN_REG_TIMELOCK": 600,
        "UNDY_HQ_MAX_REG_TIMELOCK": 216_000,
    }
    _patch_code(monkeypatch, module, CORE_MANIFEST.values())
    if hasattr(module, "require_authenticated_robinhood_hq"):
        monkeypatch.setattr(
            module,
            "require_authenticated_robinhood_hq",
            lambda _migration: hq,
        )
    if hasattr(module, "require_robinhood_ripe_dependencies"):
        monkeypatch.setattr(
            module,
            "require_robinhood_ripe_dependencies",
            lambda _migration: (RIPE_HQ, RIPE_TOKEN, PRICE_DESK, RIPE_TELLER),
        )
    if hasattr(module, "require_approved_robinhood_runtime"):
        monkeypatch.setattr(
            module,
            "require_approved_robinhood_runtime",
            lambda *_args, **_kwargs: TEST_RUNTIME,
        )
        monkeypatch.setattr(
            migration,
            "preflight_contract_manifest",
            lambda *_args: None,
            raising=False,
        )

        def check_prefix(_migration, registry, **kwargs):
            require_registry_prefix(
                registry,
                kwargs["expected_prefix"],
                kwargs["context"],
            )

        monkeypatch.setattr(module, "deploy_and_register", check_prefix)

    with pytest.raises(RuntimeError) as exc_info:
        module.migrate(migration)

    assert str(exc_info.value) == (
        f"{context}: registry ID {reg_id} is {ZERO_ADDRESS}, "
        f"expected {dependency} at {CORE_MANIFEST[dependency]}"
    )

    assert migration.deploy_calls == []
    assert migration.execute_calls == []


@pytest.mark.parametrize(
    ("filename", "name", "expected_id", "expected_hash"),
    [
        (
            "0010-VaultRegistry.py",
            "VaultRegistry",
            10,
            "0x2fb78e063e05e53ac6472539c6b5a7df532eab4e57308cdb8bdb4abf16598408",
        ),
        (
            "0011-Helpers.py",
            "Helpers",
            11,
            "0xa3b2eab0b95464e263a78b8977a8bbbf97342136406d9c87e454673c84db46ca",
        ),
    ],
)
def test_empty_registry_migrations_use_zero_local_governance_and_exact_state(
    monkeypatch,
    filename,
    name,
    expected_id,
    expected_hash,
):
    module = _load_migration(filename)
    prior_names = (
        "Ledger",
        "MissionControl",
        "LegoBook",
        "Switchboard",
        "Hatchery",
        "LootDistributor",
        "Appraiser",
        "WalletBackpack",
        "Billing",
        "VaultRegistry",
    )[: expected_id - 1]
    hq = FakeRegistry(
        HQ_ADDRESS,
        {
            reg_id: CORE_MANIFEST[prior_name]
            for reg_id, prior_name in enumerate(prior_names, start=1)
        },
    )
    migration = FakeMigration(
        manifest=CORE_MANIFEST,
        contracts={"UndyHq": hq},
    )
    migration.blueprint.PARAMS = {
        "UNDY_HQ_MIN_GOV_TIMELOCK": 7_200,
        "UNDY_HQ_MAX_GOV_TIMELOCK": 216_000,
        "UNDY_HQ_MIN_REG_TIMELOCK": 600,
        "UNDY_HQ_MAX_REG_TIMELOCK": 216_000,
    }
    monkeypatch.setattr(
        module,
        "require_authenticated_robinhood_hq",
        lambda _migration: hq,
    )
    monkeypatch.setattr(
        module,
        "require_approved_robinhood_runtime",
        lambda *_args, **_kwargs: TEST_RUNTIME,
    )
    captured = {}

    def capture_deployment(_migration, registry, **kwargs):
        captured.update(kwargs)
        captured["registry"] = registry
        contract = FakeEmptyRegistry(name, CORE_MANIFEST[name])
        kwargs["validate"](contract)
        return contract

    monkeypatch.setattr(module, "deploy_and_register", capture_deployment)

    module.migrate(migration)

    assert captured["registry"] is hq
    assert captured["name"] == name
    assert captured["expected_id"] == expected_id
    assert captured["expected_runtime_codehash"] == expected_hash
    assert captured["expected_runtime"] == TEST_RUNTIME
    assert captured["args"] == (
        hq,
        ZERO_ADDRESS,
        600,
        216_000,
    )
    assert captured["expected_prefix"] == tuple(
        (prior_name, CORE_MANIFEST[prior_name]) for prior_name in prior_names
    )
    assert migration.preflight_calls == [(name, captured["args"])]
    assert migration.deploy_calls == []
    assert migration.execute_calls == []


@pytest.mark.parametrize(
    ("registry", "error"),
    [
        (
            FakeEmptyRegistry(
                "Helpers",
                CORE_MANIFEST["Helpers"],
                governance=DEPLOYER_ADDRESS,
            ),
            "Robinhood Helpers local governance is not zero",
        ),
        (
            FakeEmptyRegistry(
                "Helpers",
                CORE_MANIFEST["Helpers"],
                governors=[DEPLOYER_ADDRESS, GOVERNANCE_ADDRESS],
            ),
            "Robinhood Helpers effective governors are",
        ),
        (
            FakeEmptyRegistry(
                "Helpers",
                CORE_MANIFEST["Helpers"],
                num_addrs=2,
            ),
            "Robinhood Helpers registry is not empty",
        ),
        (
            FakeEmptyRegistry(
                "Helpers",
                CORE_MANIFEST["Helpers"],
                registered_count=1,
            ),
            "Robinhood Helpers registry is not empty",
        ),
    ],
)
def test_empty_registry_validator_rejects_noncanonical_state(registry, error):
    hq = FakeRegistry(HQ_ADDRESS, {})
    migration = FakeMigration()
    migration.blueprint.PARAMS = {
        "UNDY_HQ_MIN_GOV_TIMELOCK": 7_200,
        "UNDY_HQ_MAX_GOV_TIMELOCK": 216_000,
        "UNDY_HQ_MIN_REG_TIMELOCK": 600,
        "UNDY_HQ_MAX_REG_TIMELOCK": 216_000,
    }

    with pytest.raises(RuntimeError, match=error):
        validate_empty_robinhood_registry(
            registry,
            hq,
            migration,
            name="Helpers",
            registry_description="Helpers.vy",
        )


@pytest.mark.parametrize(
    ("filename", "validator_name", "name", "error"),
    [
        (
            "0010-VaultRegistry.py",
            "_validate_vault_registry",
            "VaultRegistry",
            "Robinhood empty VaultRegistry classifies the probe as an earn vault",
        ),
        (
            "0011-Helpers.py",
            "_validate_helpers",
            "Helpers",
            "Robinhood empty Helpers registry classifies the probe as registered",
        ),
    ],
)
def test_empty_registry_semantic_probe_must_remain_false(
    filename,
    validator_name,
    name,
    error,
):
    module = _load_migration(filename)
    hq = FakeRegistry(HQ_ADDRESS, {})
    migration = FakeMigration()
    migration.blueprint.PARAMS = {
        "UNDY_HQ_MIN_GOV_TIMELOCK": 7_200,
        "UNDY_HQ_MAX_GOV_TIMELOCK": 216_000,
        "UNDY_HQ_MIN_REG_TIMELOCK": 600,
        "UNDY_HQ_MAX_REG_TIMELOCK": 216_000,
    }
    registry = FakeEmptyRegistry(
        name,
        CORE_MANIFEST[name],
        semantic_probe=True,
    )

    with pytest.raises(RuntimeError, match=error):
        getattr(module, validator_name)(registry, hq, migration)


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


def test_finish_setup_requires_and_locks_empty_core_registries(monkeypatch):
    module = _load_migration("1000-FinishSetup.py")
    contracts = {
        name: SimpleNamespace(address=address)
        for name, address in CORE_MANIFEST.items()
    }
    migration = FakeMigration(manifest=CORE_MANIFEST, contracts=contracts)
    calls = SimpleNamespace(registries=[], children=None, locks=[])

    monkeypatch.setattr(
        module,
        "_require_governance",
        lambda _migration: GOVERNANCE_ADDRESS,
    )
    monkeypatch.setattr(
        module,
        "_require_registry",
        lambda _migration, registry, entries, label: calls.registries.append(
            (registry, entries, label)
        ),
    )
    monkeypatch.setattr(
        module,
        "_require_wallet_backpack_items",
        lambda *_args: None,
    )

    def capture_children(_zero_address, children):
        calls.children = tuple(children)

    monkeypatch.setattr(module, "_require_child_governance", capture_children)
    monkeypatch.setattr(
        module,
        "_require_switchboard_actions_pristine",
        lambda *_args: None,
    )

    def final_lock_state(contract, kind, label):
        calls.locks.append((contract, kind, label))
        return contract, kind, label, 1, 1, None

    monkeypatch.setattr(module, "_lock_state", final_lock_state)
    monkeypatch.setattr(
        module,
        "_classify_hq_config",
        lambda _hq: ("final", ("Switchboard", False, True)),
    )
    monkeypatch.setattr(
        module,
        "_classify_hq_governance",
        lambda *_args: ("final", 1),
    )

    module.migrate(migration)

    assert module.CORE_REGISTRY[-2:] == (
        (10, "VaultRegistry"),
        (11, "Helpers"),
    )
    assert module.SWITCHBOARD_REGISTRY == (
        (1, "SwitchboardAlpha"),
        (2, "SwitchboardBravo"),
    )
    assert calls.registries[0][1] == module.CORE_REGISTRY
    assert [label for label, _contract in calls.children][-2:] == [
        "VaultRegistry",
        "Helpers",
    ]
    empty_registry_locks = [
        (kind, label)
        for _contract, kind, label in calls.locks
        if label in {"VaultRegistry registry", "Helpers registry"}
    ]
    assert empty_registry_locks == [
        ("registry", "VaultRegistry registry"),
        ("registry", "Helpers registry"),
    ]
    assert migration.execute_calls == []


def test_finish_setup_never_relinquishes_already_zero_local_governance():
    path = MIGRATIONS_DIR / "1000-FinishSetup.py"
    tree = ast.parse(path.read_text(), filename=str(path))
    relinquish_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr == "relinquishGov":
            relinquish_calls.append(node.lineno)

    assert relinquish_calls == []
