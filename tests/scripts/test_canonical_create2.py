import json
from pathlib import Path
from unittest.mock import Mock

import boa
import pytest
import vyper
from click.testing import CliRunner
from eth_abi import encode
from eth_utils import keccak

from scripts.canonical_create2 import (
    CANONICAL_CREATE2_SINGLETON,
    CANONICAL_CREATE2_SINGLETON_CODEHASH,
    CANONICAL_CREATE2_SINGLETON_RUNTIME,
    CANONICAL_CREATE2_SINGLETON_RUNTIME_LENGTH,
    CHAIN_MANIFEST_FIELDS,
    CutoverPreflightError,
    DeploymentInputError,
    FIXED_ARTIFACT_SALTS,
    GET_ADDR_SELECTOR,
    HATCHERY_REGISTRY_ID,
    MISSION_CONTROL_REGISTRY_ID,
    SingletonPreflightError,
    USER_WALLET_CONFIG_IMPL_V1_SALT,
    USER_WALLET_CONFIG_IMPL_V1_SALT_LABEL,
    USER_WALLET_IMPL_V1_SALT,
    USER_WALLET_IMPL_V1_SALT_LABEL,
    WALLET_FACTORY_V1_SALT,
    WALLET_FACTORY_V1_SALT_LABEL,
    WALLET_FACTORY_ADMIN_CONSTANT_NAME,
    WALLET_FACTORY_ADMIN_PLACEHOLDER,
    WALLET_FACTORY_SOURCE,
    USER_WALLET_CONFIG_SELECTOR,
    build_singleton_calldata,
    cli,
    derive_ascii_label_salt,
    derive_wallet_salt,
    encode_wallet_salt_preimage,
    predict_create2_address,
    predict_vyper_minimal_proxy_address,
    predict_vyper_wallet_address,
    preflight_canonical_singleton,
    preflight_hatchery_cutover,
    prepare_singleton_deployment,
    validate_canonical_singleton_runtime,
    validate_fixed_artifact_deployment,
    validate_wallet_factory_admin_release_gate,
    vyper_minimal_proxy_initcode,
)


REPO_ROOT = Path(__file__).parents[2]
RELEASE_MANIFEST = REPO_ROOT / "docs/deployment-manifests/wallet-v1.json"
TEST_CHAIN_ID = 31337
TEST_CHAIN_ID_QUANTITY = "0x7a69"
TEST_UNDY_HQ = "0x4444444444444444444444444444444444444444"
TEST_HATCHERY = "0x5555555555555555555555555555555555555555"
TEST_MISSION_CONTROL = "0x2222222222222222222222222222222222222222"
TEST_WALLET_TEMPLATE = "0x6666666666666666666666666666666666666666"
TEST_CONFIG_TEMPLATE = "0x7777777777777777777777777777777777777777"
TEST_WALLET_TEMPLATE_RUNTIME = bytes.fromhex("60016000f3")
TEST_CONFIG_TEMPLATE_RUNTIME = bytes.fromhex("60026000f3")


def test_cutover_abi_selectors_match_exact_public_signatures():
    assert GET_ADDR_SELECTOR == bytes.fromhex("d81f84b7")
    assert USER_WALLET_CONFIG_SELECTOR == bytes.fromhex("c1ae586e")


def test_canonical_singleton_constants_are_self_consistent():
    assert len(CANONICAL_CREATE2_SINGLETON_RUNTIME) == 69
    assert CANONICAL_CREATE2_SINGLETON_RUNTIME_LENGTH == 69
    assert keccak(CANONICAL_CREATE2_SINGLETON_RUNTIME) == CANONICAL_CREATE2_SINGLETON_CODEHASH


def test_fixed_v1_artifact_salts_are_exact_ascii_label_hashes():
    expected = {
        USER_WALLET_IMPL_V1_SALT_LABEL: (
            USER_WALLET_IMPL_V1_SALT,
            "da9e0e08155d5e49d144d1878faacbcf25fec5790c5ca4cfea6c03788d80329d",
        ),
        USER_WALLET_CONFIG_IMPL_V1_SALT_LABEL: (
            USER_WALLET_CONFIG_IMPL_V1_SALT,
            "c54fd3bd79f3df3298ee349c311ac2d48d1dd8bdbc6e4c795ec0b851c7321227",
        ),
        WALLET_FACTORY_V1_SALT_LABEL: (
            WALLET_FACTORY_V1_SALT,
            "97049e1342f95e7c1a137d37a08a26977defb40ca4763dd6c6d05cef6bce600a",
        ),
    }

    assert FIXED_ARTIFACT_SALTS == {
        label: literal for label, (literal, _) in expected.items()
    }
    for label, (literal, expected_hex) in expected.items():
        assert len(literal) == 32
        assert literal.hex() == expected_hex
        assert derive_ascii_label_salt(label) == literal


def test_v1_release_manifest_matches_compiled_implementations(monkeypatch):
    manifest = json.loads(RELEASE_MANIFEST.read_text())
    monkeypatch.chdir(REPO_ROOT)

    assert manifest["compiler"] == {
        "name": "vyper",
        "version": "0.4.3",
        "longVersion": "0.4.3+commit.bff19ea2",
        "entrypoint": "boa.load_partial",
        "sourcePathsRelativeTo": "repository-root",
    }
    assert vyper.__version__ == manifest["compiler"]["version"]
    assert vyper.__long_version__ == manifest["compiler"]["longVersion"]
    assert manifest["deterministicDeployer"] == {
        "address": CANONICAL_CREATE2_SINGLETON,
        "runtimeBytes": CANONICAL_CREATE2_SINGLETON_RUNTIME_LENGTH,
        "runtimeCodehash": "0x" + CANONICAL_CREATE2_SINGLETON_CODEHASH.hex(),
    }
    assert "activation" not in manifest
    assert set(manifest["chains"]) == {"8453"}
    base = manifest["chains"]["8453"]
    assert set(base) <= CHAIN_MANIFEST_FIELDS
    assert base["cutoverStatus"] == "pending"
    assert base["hatcheryRegistryId"] == HATCHERY_REGISTRY_ID
    assert base["missionControlRegistryId"] == MISSION_CONTROL_REGISTRY_ID
    assert base["missionControlTemplateGeneration"] == "legacy-pair"
    assert "approvedHatcheryAddress" not in base
    assert "approvedHatcheryRuntimeCodehash" not in base
    assert "approvedLegacyWalletTemplateAddress" not in base
    assert "approvedLegacyWalletTemplateRuntimeCodehash" not in base
    assert "approvedLegacyConfigTemplateAddress" not in base
    assert "approvedLegacyConfigTemplateRuntimeCodehash" not in base
    assert "artifacts" not in base

    expected_salts = {
        "userWalletImplementation": USER_WALLET_IMPL_V1_SALT,
        "userWalletConfigImplementation": USER_WALLET_CONFIG_IMPL_V1_SALT,
        "walletFactory": WALLET_FACTORY_V1_SALT,
    }
    factory_admin = validate_wallet_factory_admin_release_gate(manifest)
    if factory_admin == WALLET_FACTORY_ADMIN_PLACEHOLDER:
        assert all(
            artifact["status"] == "pending"
            for artifact in manifest["artifacts"].values()
        )
    for artifact_name, expected_salt in expected_salts.items():
        artifact = manifest["artifacts"][artifact_name]
        compiled = boa.load_partial(artifact["source"]).compiler_data
        deployment_bytecode = compiled.bytecode
        runtime_bytecode = compiled.bytecode_runtime

        assert bytes.fromhex(artifact["salt"][2:]) == expected_salt
        assert artifact["status"] in ("pending", "ready")
        if artifact["status"] == "pending":
            assert artifact["reason"]
            assert "deploymentBytecode" not in artifact
            assert "runtimeBytecode" not in artifact
            assert "predictedAddress" not in artifact
            continue

        assert artifact["deploymentBytecode"] == {
            "bytes": len(deployment_bytecode),
            "keccak256": "0x" + keccak(deployment_bytecode).hex(),
        }
        assert artifact["runtimeBytecode"] == {
            "bytes": len(runtime_bytecode),
            "keccak256": "0x" + keccak(runtime_bytecode).hex(),
        }
        assert artifact["predictedAddress"] == predict_create2_address(
            CANONICAL_CREATE2_SINGLETON,
            expected_salt,
            deployment_bytecode,
        )

    factory = manifest["artifacts"]["walletFactory"]
    assert factory["source"] == WALLET_FACTORY_SOURCE.as_posix()
    assert bytes.fromhex(factory["salt"][2:]) == WALLET_FACTORY_V1_SALT
    assert factory_admin == factory["admin"]


def _factory_admin_manifest(source: str, admin: str, *, ready: bool = False) -> dict:
    return {
        "artifacts": {
            "userWalletImplementation": {
                "status": "ready" if ready else "pending",
            },
            "userWalletConfigImplementation": {"status": "pending"},
            "walletFactory": {
                "status": "pending",
                "source": source,
                "admin": admin,
            },
        }
    }


def _write_factory_source(repository_root: Path, admin: str) -> Path:
    source = repository_root / WALLET_FACTORY_SOURCE
    source.parent.mkdir(parents=True)
    source.write_text(
        f"{WALLET_FACTORY_ADMIN_CONSTANT_NAME}: constant(address) = {admin}\n"
    )
    return source


def test_factory_admin_release_gate_accepts_matching_final_literal(tmp_path):
    admin = "0x2222222222222222222222222222222222222222"
    _write_factory_source(tmp_path, admin)
    manifest = _factory_admin_manifest(WALLET_FACTORY_SOURCE.as_posix(), admin)

    assert validate_wallet_factory_admin_release_gate(
        manifest,
        repository_root=tmp_path,
        require_final=True,
    ) == admin


def test_factory_admin_release_gate_allows_placeholder_only_while_all_artifacts_pending(
    tmp_path,
):
    _write_factory_source(tmp_path, WALLET_FACTORY_ADMIN_PLACEHOLDER)
    manifest = _factory_admin_manifest(
        WALLET_FACTORY_SOURCE.as_posix(),
        WALLET_FACTORY_ADMIN_PLACEHOLDER,
    )

    assert validate_wallet_factory_admin_release_gate(
        manifest,
        repository_root=tmp_path,
    ) == WALLET_FACTORY_ADMIN_PLACEHOLDER

    manifest["artifacts"]["userWalletImplementation"]["status"] = "ready"
    with pytest.raises(
        CutoverPreflightError,
        match="placeholder.*cannot bless ready artifacts.*userWalletImplementation",
    ):
        validate_wallet_factory_admin_release_gate(
            manifest,
            repository_root=tmp_path,
        )


def test_factory_admin_release_gate_rejects_placeholder_when_final_admin_required(
    tmp_path,
):
    _write_factory_source(tmp_path, WALLET_FACTORY_ADMIN_PLACEHOLDER)
    manifest = _factory_admin_manifest(
        WALLET_FACTORY_SOURCE.as_posix(),
        WALLET_FACTORY_ADMIN_PLACEHOLDER,
    )

    with pytest.raises(
        CutoverPreflightError,
        match="placeholder.*select and record the final admin",
    ):
        validate_wallet_factory_admin_release_gate(
            manifest,
            repository_root=tmp_path,
            require_final=True,
        )


@pytest.mark.parametrize(
    ("source_body", "manifest_admin", "error"),
    [
        (
            "# WALLET_FACTORY_ADMIN deliberately absent\n",
            "0x2222222222222222222222222222222222222222",
            "must declare exactly one literal",
        ),
        (
            "WALLET_FACTORY_ADMIN: constant(address) = "
            "0x3333333333333333333333333333333333333333\n",
            "0x2222222222222222222222222222222222222222",
            "does not match the release manifest",
        ),
    ],
)
def test_factory_admin_release_gate_rejects_unparseable_or_drifting_source(
    tmp_path, source_body, manifest_admin, error
):
    source = tmp_path / WALLET_FACTORY_SOURCE
    source.parent.mkdir(parents=True)
    source.write_text(source_body)
    manifest = _factory_admin_manifest(
        WALLET_FACTORY_SOURCE.as_posix(),
        manifest_admin,
    )

    with pytest.raises(CutoverPreflightError, match=error):
        validate_wallet_factory_admin_release_gate(
            manifest,
            repository_root=tmp_path,
        )


def test_factory_admin_release_gate_fails_closed_when_source_is_absent(tmp_path):
    manifest = _factory_admin_manifest(
        WALLET_FACTORY_SOURCE.as_posix(),
        "0x2222222222222222222222222222222222222222",
    )

    with pytest.raises(CutoverPreflightError, match="could not read wallet factory source"):
        validate_wallet_factory_admin_release_gate(
            manifest,
            repository_root=tmp_path,
        )


def test_fixed_artifact_deployment_requires_ready_manifest_matched_initcode(tmp_path):
    admin = "0x2222222222222222222222222222222222222222"
    _write_factory_source(tmp_path, admin)
    manifest = _factory_admin_manifest(WALLET_FACTORY_SOURCE.as_posix(), admin)
    initcode = bytes.fromhex("60006000f3")
    artifact = manifest["artifacts"]["userWalletImplementation"]
    artifact.update(
        {
            "status": "ready",
            "salt": "0x" + USER_WALLET_IMPL_V1_SALT.hex(),
            "deploymentBytecode": {
                "bytes": len(initcode),
                "keccak256": "0x" + keccak(initcode).hex(),
            },
            "predictedAddress": predict_create2_address(
                CANONICAL_CREATE2_SINGLETON,
                USER_WALLET_IMPL_V1_SALT,
                initcode,
            ),
        }
    )

    assert validate_fixed_artifact_deployment(
        manifest,
        USER_WALLET_IMPL_V1_SALT,
        initcode,
        repository_root=tmp_path,
    ) == "userWalletImplementation"

    with pytest.raises(
        CutoverPreflightError,
        match="initcode does not match the ready userWalletImplementation",
    ):
        validate_fixed_artifact_deployment(
            manifest,
            USER_WALLET_IMPL_V1_SALT,
            initcode + b"\x00",
            repository_root=tmp_path,
        )


def _ready_cutover_manifest(hatchery: str, runtime: bytes) -> dict:
    return {
        "chains": {
            str(TEST_CHAIN_ID): {
                "name": "test-chain",
                "cutoverStatus": "ready",
                "undyHq": TEST_UNDY_HQ,
                "hatcheryRegistryId": HATCHERY_REGISTRY_ID,
                "missionControlRegistryId": MISSION_CONTROL_REGISTRY_ID,
                "approvedHatcheryAddress": hatchery,
                "approvedHatcheryRuntimeCodehash": "0x" + keccak(runtime).hex(),
                "approvedLegacyWalletTemplateAddress": TEST_WALLET_TEMPLATE,
                "approvedLegacyWalletTemplateRuntimeCodehash": (
                    "0x" + keccak(TEST_WALLET_TEMPLATE_RUNTIME).hex()
                ),
                "approvedLegacyConfigTemplateAddress": TEST_CONFIG_TEMPLATE,
                "approvedLegacyConfigTemplateRuntimeCodehash": (
                    "0x" + keccak(TEST_CONFIG_TEMPLATE_RUNTIME).hex()
                ),
                "missionControlTemplateGeneration": "legacy-pair",
            }
        }
    }


def _abi_address(address: str) -> str:
    return "0x" + (b"\x00" * 12 + bytes.fromhex(address[2:])).hex()


def _wallet_config_result(
    wallet_template: str = TEST_WALLET_TEMPLATE,
    config_template: str = TEST_CONFIG_TEMPLATE,
) -> str:
    return "0x" + (
        bytes.fromhex(_abi_address(wallet_template)[2:])
        + bytes.fromhex(_abi_address(config_template)[2:])
    ).hex()


def _successful_cutover_rpc(
    hatchery_runtime: bytes,
    *,
    wallet_template: str = TEST_WALLET_TEMPLATE,
    config_template: str = TEST_CONFIG_TEMPLATE,
    wallet_runtime: bytes | str = TEST_WALLET_TEMPLATE_RUNTIME,
    config_runtime: bytes | str = TEST_CONFIG_TEMPLATE_RUNTIME,
):
    def rpc_call(_rpc_url, method, params, **_kwargs):
        if method == "eth_chainId":
            return TEST_CHAIN_ID_QUANTITY
        if method == "eth_call":
            call = params[0]
            registry_prefix = "0x" + GET_ADDR_SELECTOR.hex()
            if call["data"].startswith(registry_prefix):
                registry_id = int(call["data"][-64:], 16)
                if registry_id == HATCHERY_REGISTRY_ID:
                    return _abi_address(TEST_HATCHERY)
                if registry_id == MISSION_CONTROL_REGISTRY_ID:
                    return _abi_address(TEST_MISSION_CONTROL)
            if call == {
                "to": TEST_MISSION_CONTROL,
                "data": "0x" + USER_WALLET_CONFIG_SELECTOR.hex(),
            }:
                return _wallet_config_result(wallet_template, config_template)
            raise AssertionError(f"unexpected eth_call: {call}")
        if method == "eth_getCode":
            address = params[0]
            code = {
                TEST_HATCHERY: hatchery_runtime,
                wallet_template: wallet_runtime,
                config_template: config_runtime,
            }[address]
            return code if isinstance(code, str) else "0x" + code.hex()
        raise AssertionError(f"unexpected JSON-RPC method: {method}")

    return rpc_call


def test_hatchery_cutover_preflight_rejects_missing_live_chain(monkeypatch):
    rpc_call = Mock(return_value=TEST_CHAIN_ID_QUANTITY)
    monkeypatch.setattr("scripts.canonical_create2._rpc_call", rpc_call)

    with pytest.raises(CutoverPreflightError, match="no chain entry.*31337"):
        preflight_hatchery_cutover("https://rpc.invalid", {"chains": {}})

    rpc_call.assert_called_once_with(
        "https://rpc.invalid",
        "eth_chainId",
        [],
        timeout=15,
        error_type=CutoverPreflightError,
    )


def test_hatchery_cutover_preflight_rejects_pending_live_chain(monkeypatch):
    rpc_call = Mock(return_value=TEST_CHAIN_ID_QUANTITY)
    monkeypatch.setattr("scripts.canonical_create2._rpc_call", rpc_call)
    manifest = {
        "chains": {
            str(TEST_CHAIN_ID): {
                "cutoverStatus": "pending",
                "undyHq": TEST_UNDY_HQ,
                "hatcheryRegistryId": 5,
                "missionControlTemplateGeneration": "legacy-pair",
            }
        }
    }

    with pytest.raises(CutoverPreflightError, match="chain 31337 is pending"):
        preflight_hatchery_cutover("https://rpc.invalid", manifest)

    assert rpc_call.call_count == 1


def test_hatchery_cutover_preflight_rejects_per_chain_artifact_drift(monkeypatch):
    rpc_call = Mock(return_value=TEST_CHAIN_ID_QUANTITY)
    monkeypatch.setattr("scripts.canonical_create2._rpc_call", rpc_call)
    manifest = _ready_cutover_manifest(TEST_HATCHERY, b"\x60\x00")
    manifest["chains"][str(TEST_CHAIN_ID)]["artifacts"] = {
        "userWalletImplementation": {"runtimeCodehash": "0x" + "99" * 32}
    }

    with pytest.raises(CutoverPreflightError, match="unsupported fields: artifacts"):
        preflight_hatchery_cutover("https://rpc.invalid", manifest)

    assert rpc_call.call_count == 1


def test_hatchery_cutover_preflight_rejects_mixed_template_generations(monkeypatch):
    rpc_call = Mock(return_value=TEST_CHAIN_ID_QUANTITY)
    monkeypatch.setattr("scripts.canonical_create2._rpc_call", rpc_call)
    manifest = _ready_cutover_manifest(TEST_HATCHERY, b"\x60\x00")
    manifest["chains"][str(TEST_CHAIN_ID)][
        "missionControlTemplateGeneration"
    ] = "new-wallet-legacy-config"

    with pytest.raises(CutoverPreflightError, match="mixed.*generations are forbidden"):
        preflight_hatchery_cutover("https://rpc.invalid", manifest)

    assert rpc_call.call_count == 1


@pytest.mark.parametrize(
    ("approved_address", "runtime_codehash"),
    [
        ("0x" + "00" * 20, "0x" + "11" * 32),
        ("0x" + "55" * 20, "0x" + "00" * 32),
    ],
)
def test_hatchery_cutover_preflight_rejects_manifest_placeholders(
    monkeypatch, approved_address, runtime_codehash
):
    rpc_call = Mock()
    monkeypatch.setattr("scripts.canonical_create2._rpc_call", rpc_call)
    manifest = _ready_cutover_manifest(TEST_HATCHERY, b"\x60\x00")
    chain = manifest["chains"][str(TEST_CHAIN_ID)]
    chain["approvedHatcheryAddress"] = approved_address
    chain["approvedHatcheryRuntimeCodehash"] = runtime_codehash

    rpc_call.return_value = TEST_CHAIN_ID_QUANTITY
    with pytest.raises(
        CutoverPreflightError,
        match="approved Hatchery address and runtime codehash must not be placeholders",
    ):
        preflight_hatchery_cutover("https://rpc.invalid", manifest)

    assert rpc_call.call_count == 1


@pytest.mark.parametrize(
    "field",
    [
        "approvedLegacyWalletTemplateAddress",
        "approvedLegacyWalletTemplateRuntimeCodehash",
        "approvedLegacyConfigTemplateAddress",
        "approvedLegacyConfigTemplateRuntimeCodehash",
    ],
)
def test_hatchery_cutover_preflight_rejects_missing_template_approval(
    monkeypatch, field
):
    rpc_call = Mock(return_value=TEST_CHAIN_ID_QUANTITY)
    monkeypatch.setattr("scripts.canonical_create2._rpc_call", rpc_call)
    manifest = _ready_cutover_manifest(TEST_HATCHERY, b"\x60\x00")
    del manifest["chains"][str(TEST_CHAIN_ID)][field]

    with pytest.raises(
        CutoverPreflightError,
        match="invalid Hatchery cutover manifest",
    ):
        preflight_hatchery_cutover("https://rpc.invalid", manifest)

    assert rpc_call.call_count == 1


def test_hatchery_cutover_preflight_auto_selects_chain_and_checks_exact_code(monkeypatch):
    runtime = bytes.fromhex("60006000f3")
    calls = []
    successful_rpc = _successful_cutover_rpc(runtime)

    def rpc_call(rpc_url, method, params, **kwargs):
        calls.append((rpc_url, method, params, kwargs))
        return successful_rpc(rpc_url, method, params, **kwargs)

    monkeypatch.setattr("scripts.canonical_create2._rpc_call", rpc_call)
    manifest = _ready_cutover_manifest(TEST_HATCHERY, runtime)
    manifest["chains"]["1"] = {
        "name": "unrelated-pending-chain",
        "cutoverStatus": "pending",
        "undyHq": "0x7777777777777777777777777777777777777777",
        "hatcheryRegistryId": 5,
        "missionControlRegistryId": 2,
        "missionControlTemplateGeneration": "legacy-pair",
    }
    result = preflight_hatchery_cutover(
        "https://rpc.invalid",
        manifest,
    )

    assert result == {
        "chainId": TEST_CHAIN_ID,
        "undyHq": TEST_UNDY_HQ,
        "registryId": 5,
        "hatchery": TEST_HATCHERY,
        "runtimeBytes": 5,
        "runtimeCodehash": "0x" + keccak(runtime).hex(),
        "missionControlRegistryId": 2,
        "missionControl": TEST_MISSION_CONTROL,
        "legacyTemplates": {
            "walletTemplate": {
                "address": TEST_WALLET_TEMPLATE,
                "runtimeBytes": len(TEST_WALLET_TEMPLATE_RUNTIME),
                "runtimeCodehash": "0x"
                + keccak(TEST_WALLET_TEMPLATE_RUNTIME).hex(),
            },
            "configTemplate": {
                "address": TEST_CONFIG_TEMPLATE,
                "runtimeBytes": len(TEST_CONFIG_TEMPLATE_RUNTIME),
                "runtimeCodehash": "0x"
                + keccak(TEST_CONFIG_TEMPLATE_RUNTIME).hex(),
            },
        },
        "status": "ok",
    }
    assert calls[0][0:3] == (
        "https://rpc.invalid",
        "eth_chainId",
        [],
    )
    assert calls[1][0:3] == (
        "https://rpc.invalid",
        "eth_call",
        [
            {
                "to": TEST_UNDY_HQ,
                "data": "0x"
                + (GET_ADDR_SELECTOR + HATCHERY_REGISTRY_ID.to_bytes(32, "big")).hex(),
            },
            "latest",
        ],
    )
    assert calls[2][0:3] == (
        "https://rpc.invalid",
        "eth_getCode",
        [TEST_HATCHERY, "latest"],
    )
    assert calls[3][0:3] == (
        "https://rpc.invalid",
        "eth_call",
        [
            {
                "to": TEST_UNDY_HQ,
                "data": "0x"
                + (
                    GET_ADDR_SELECTOR
                    + MISSION_CONTROL_REGISTRY_ID.to_bytes(32, "big")
                ).hex(),
            },
            "latest",
        ],
    )
    assert calls[4][0:3] == (
        "https://rpc.invalid",
        "eth_call",
        [
            {
                "to": TEST_MISSION_CONTROL,
                "data": "0x" + USER_WALLET_CONFIG_SELECTOR.hex(),
            },
            "latest",
        ],
    )
    assert calls[5][0:3] == (
        "https://rpc.invalid",
        "eth_getCode",
        [TEST_WALLET_TEMPLATE, "latest"],
    )
    assert calls[6][0:3] == (
        "https://rpc.invalid",
        "eth_getCode",
        [TEST_CONFIG_TEMPLATE, "latest"],
    )


def test_hatchery_cutover_preflight_rejects_old_registry_pointer(monkeypatch):
    responses = iter(
        [
            TEST_CHAIN_ID_QUANTITY,
            "0x" + "00" * 12 + "66" * 20,
        ]
    )
    monkeypatch.setattr(
        "scripts.canonical_create2._rpc_call",
        lambda *_args, **_kwargs: next(responses),
    )

    with pytest.raises(
        CutoverPreflightError,
        match="registry ID 5 does not resolve to the approved new Hatchery",
    ):
        preflight_hatchery_cutover(
            "https://rpc.invalid",
            _ready_cutover_manifest(TEST_HATCHERY, b"\x60\x00"),
        )


@pytest.mark.parametrize(
    ("returned_code", "error"),
    [
        ("0x", "approved Hatchery code is absent"),
        ("0x6001", "approved Hatchery runtime codehash mismatch"),
    ],
)
def test_hatchery_cutover_preflight_rejects_absent_or_mismatched_code(
    monkeypatch, returned_code, error
):
    responses = iter(
        [
            TEST_CHAIN_ID_QUANTITY,
            "0x" + "00" * 12 + "55" * 20,
            returned_code,
        ]
    )
    monkeypatch.setattr(
        "scripts.canonical_create2._rpc_call",
        lambda *_args, **_kwargs: next(responses),
    )

    with pytest.raises(CutoverPreflightError, match=error):
        preflight_hatchery_cutover(
            "https://rpc.invalid",
            _ready_cutover_manifest(TEST_HATCHERY, b"\x60\x00"),
        )


@pytest.mark.parametrize(
    ("wallet_template", "config_template", "error"),
    [
        (
            "0x8888888888888888888888888888888888888888",
            TEST_CONFIG_TEMPLATE,
            "walletTemplate does not match the approved legacy template",
        ),
        (
            TEST_WALLET_TEMPLATE,
            "0x8888888888888888888888888888888888888888",
            "configTemplate does not match the approved legacy template",
        ),
    ],
)
def test_hatchery_cutover_preflight_rejects_live_mixed_generation_pair(
    monkeypatch, wallet_template, config_template, error
):
    runtime = b"\x60\x00"
    manifest = _ready_cutover_manifest(TEST_HATCHERY, runtime)
    assert (
        manifest["chains"][str(TEST_CHAIN_ID)][
            "missionControlTemplateGeneration"
        ]
        == "legacy-pair"
    )
    monkeypatch.setattr(
        "scripts.canonical_create2._rpc_call",
        _successful_cutover_rpc(
            runtime,
            wallet_template=wallet_template,
            config_template=config_template,
        ),
    )

    with pytest.raises(CutoverPreflightError, match=error):
        preflight_hatchery_cutover("https://rpc.invalid", manifest)


def test_hatchery_cutover_preflight_rejects_template_getter_decode_failure(
    monkeypatch,
):
    runtime = b"\x60\x00"
    responses = iter(
        [
            TEST_CHAIN_ID_QUANTITY,
            _abi_address(TEST_HATCHERY),
            "0x" + runtime.hex(),
            _abi_address(TEST_MISSION_CONTROL),
            "0x1234",
        ]
    )
    monkeypatch.setattr(
        "scripts.canonical_create2._rpc_call",
        lambda *_args, **_kwargs: next(responses),
    )

    with pytest.raises(
        CutoverPreflightError,
        match="userWalletConfig.*at least two complete ABI words",
    ):
        preflight_hatchery_cutover(
            "https://rpc.invalid",
            _ready_cutover_manifest(TEST_HATCHERY, runtime),
        )


@pytest.mark.parametrize(
    ("wallet_runtime", "config_runtime", "error"),
    [
        ("0x", TEST_CONFIG_TEMPLATE_RUNTIME, "wallet template code is absent"),
        (
            b"\x60\xff",
            TEST_CONFIG_TEMPLATE_RUNTIME,
            "wallet template runtime codehash mismatch",
        ),
        (TEST_WALLET_TEMPLATE_RUNTIME, "0x", "config template code is absent"),
        (
            TEST_WALLET_TEMPLATE_RUNTIME,
            b"\x60\xff",
            "config template runtime codehash mismatch",
        ),
    ],
)
def test_hatchery_cutover_preflight_rejects_absent_or_mismatched_template_code(
    monkeypatch, wallet_runtime, config_runtime, error
):
    runtime = b"\x60\x00"
    monkeypatch.setattr(
        "scripts.canonical_create2._rpc_call",
        _successful_cutover_rpc(
            runtime,
            wallet_runtime=wallet_runtime,
            config_runtime=config_runtime,
        ),
    )

    with pytest.raises(CutoverPreflightError, match=error):
        preflight_hatchery_cutover(
            "https://rpc.invalid",
            _ready_cutover_manifest(TEST_HATCHERY, runtime),
        )


def test_validate_canonical_singleton_runtime_accepts_exact_code():
    runtime = validate_canonical_singleton_runtime(
        "0x" + CANONICAL_CREATE2_SINGLETON_RUNTIME.hex()
    )

    assert runtime == CANONICAL_CREATE2_SINGLETON_RUNTIME


def test_validate_canonical_singleton_runtime_rejects_absent_code():
    with pytest.raises(SingletonPreflightError, match="singleton is absent"):
        validate_canonical_singleton_runtime("0x")


def test_validate_canonical_singleton_runtime_rejects_wrong_length():
    with pytest.raises(SingletonPreflightError, match="expected 69 bytes, got 68 bytes"):
        validate_canonical_singleton_runtime(CANONICAL_CREATE2_SINGLETON_RUNTIME[:-1])


def test_validate_canonical_singleton_runtime_rejects_wrong_codehash():
    wrong_runtime = bytearray(CANONICAL_CREATE2_SINGLETON_RUNTIME)
    wrong_runtime[-1] ^= 1

    with pytest.raises(
        SingletonPreflightError,
        match="singleton runtime codehash mismatch",
    ):
        validate_canonical_singleton_runtime(bytes(wrong_runtime))


def test_preflight_queries_only_the_canonical_address(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": "0x" + CANONICAL_CREATE2_SINGLETON_RUNTIME.hex(),
    }
    post = Mock(return_value=response)
    monkeypatch.setattr("scripts.canonical_create2.requests.post", post)

    assert preflight_canonical_singleton("https://rpc.invalid") == (
        CANONICAL_CREATE2_SINGLETON_RUNTIME
    )
    post.assert_called_once_with(
        "https://rpc.invalid",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getCode",
            "params": [CANONICAL_CREATE2_SINGLETON, "latest"],
        },
        timeout=15,
    )


def test_prepare_cli_emits_nothing_for_fixed_salt_while_admin_is_placeholder(
    monkeypatch,
):
    singleton_preflight = Mock()
    monkeypatch.setattr(
        "scripts.canonical_create2.preflight_canonical_singleton",
        singleton_preflight,
    )
    result = CliRunner().invoke(
        cli,
        [
            "prepare",
            "--rpc-url",
            "https://rpc.invalid",
            "--manifest",
            str(RELEASE_MANIFEST),
            "--salt",
            "0x" + USER_WALLET_IMPL_V1_SALT.hex(),
            "--initcode",
            "0x60006000f3",
        ],
    )

    assert result.exit_code == 1
    assert "admin is still the zero-address placeholder" in result.output
    assert "predictedAddress" not in result.output
    assert "transaction" not in result.output
    singleton_preflight.assert_not_called()


def test_cutover_cli_stops_before_live_checks_while_admin_is_placeholder(
    monkeypatch,
):
    hatchery_preflight = Mock()
    monkeypatch.setattr(
        "scripts.canonical_create2.preflight_hatchery_cutover",
        hatchery_preflight,
    )
    result = CliRunner().invoke(
        cli,
        [
            "cutover-preflight",
            "--rpc-url",
            "https://rpc.invalid",
            "--manifest",
            str(RELEASE_MANIFEST),
        ],
    )

    assert result.exit_code == 1
    assert "admin is still the zero-address placeholder" in result.output
    assert '"status": "ok"' not in result.output
    hatchery_preflight.assert_not_called()


def test_prepare_cli_emits_nothing_when_singleton_preflight_fails(monkeypatch):
    def fail_preflight(*_args, **_kwargs):
        raise SingletonPreflightError("canonical singleton is absent")

    monkeypatch.setattr(
        "scripts.canonical_create2.preflight_canonical_singleton", fail_preflight
    )
    result = CliRunner().invoke(
        cli,
        [
            "prepare",
            "--rpc-url",
            "https://rpc.invalid",
            "--salt",
            "0x" + "00" * 32,
            "--initcode",
            "0x60006000f3",
        ],
    )

    assert result.exit_code == 1
    assert "Error: canonical singleton is absent" in result.output
    assert "predictedAddress" not in result.output
    assert "transaction" not in result.output


def test_singleton_calldata_and_prediction_match_known_vector():
    salt = "0x" + "00" * 32
    initcode = "0x60006000f3"

    assert build_singleton_calldata(salt, initcode) == (
        "0x" + "00" * 32 + "60006000f3"
    )
    assert predict_create2_address(CANONICAL_CREATE2_SINGLETON, salt, initcode) == (
        "0x5415Ff926E55733bA02095045BD818a5100325C9"
    )

    plan = prepare_singleton_deployment(salt, initcode)
    assert plan["predictedAddress"] == "0x5415Ff926E55733bA02095045BD818a5100325C9"
    assert plan["transaction"] == {
        "to": CANONICAL_CREATE2_SINGLETON,
        "data": "0x" + "00" * 32 + "60006000f3",
        "value": "0x0",
    }


def test_salt_must_be_exactly_32_bytes():
    with pytest.raises(DeploymentInputError, match="exactly 32 bytes"):
        build_singleton_calldata("0x1234", "0x6000")


def test_wallet_salt_is_exact_96_byte_abi_encoding_not_packed():
    owner = "0x1111111111111111111111111111111111111111"
    preimage = encode_wallet_salt_preimage(owner, 42, 2)

    assert len(preimage) == 96
    assert preimage == encode(["address", "uint256", "uint256"], [owner, 42, 2])
    assert preimage.hex() == (
        "00" * 12
        + "11" * 20
        + "00" * 31
        + "2a"
        + "00" * 31
        + "02"
    )
    assert derive_wallet_salt(owner, 42, 2).hex() == (
        "d92aad855c2b3fdf53ba506346acb6ea8ed549eed105509441ab9c742ba9148b"
    )

    packed_preimage = (
        bytes.fromhex("11" * 20)
        + (42).to_bytes(32, "big")
        + (2).to_bytes(32, "big")
    )
    assert len(packed_preimage) == 84
    assert keccak(packed_preimage) != derive_wallet_salt(owner, 42, 2)


def test_wallet_prediction_uses_derived_protocol_salt():
    factory = "0x2222222222222222222222222222222222222222"
    implementation = "0x3333333333333333333333333333333333333333"
    owner = "0x1111111111111111111111111111111111111111"
    salt = derive_wallet_salt(owner, 42, 2)

    assert predict_vyper_wallet_address(factory, implementation, owner, 42, 2) == (
        predict_vyper_minimal_proxy_address(factory, salt, implementation)
    )


@pytest.mark.parametrize("bad_value", [-1, 2**256])
def test_wallet_salt_rejects_values_outside_uint256(bad_value):
    with pytest.raises(DeploymentInputError, match="must fit in uint256"):
        derive_wallet_salt(
            "0x1111111111111111111111111111111111111111", bad_value, 1
        )


@pytest.mark.parametrize("bad_tier", [0, 3, 5])
def test_wallet_salt_rejects_unreachable_starter_agent_tiers(bad_tier):
    with pytest.raises(
        DeploymentInputError,
        match="starter agent tier must be one of PROD=1, STAGING=2, DEV=4",
    ):
        derive_wallet_salt(
            "0x1111111111111111111111111111111111111111", 42, bad_tier
        )


def test_vyper_043_clone_initcode_and_prediction_differ_from_openzeppelin():
    factory = "0x2222222222222222222222222222222222222222"
    implementation = "0x1111111111111111111111111111111111111111"
    salt = (123).to_bytes(32, "big")

    vyper_initcode = vyper_minimal_proxy_initcode(implementation)
    openzeppelin_initcode = (
        bytes.fromhex("3d602d80600a3d3981f3")
        + bytes.fromhex("363d3d373d3d3d363d73")
        + bytes.fromhex("11" * 20)
        + bytes.fromhex("5af43d82803e903d91602b57fd5bf3")
    )

    assert len(vyper_initcode) == 54
    assert len(openzeppelin_initcode) == 55
    assert vyper_initcode.hex() == (
        "602d3d8160093d39f3363d3d373d3d3d363d73"
        + "11" * 20
        + "5af43d82803e903d91602b57fd5bf3"
    )
    assert predict_vyper_minimal_proxy_address(factory, salt, implementation) == (
        "0x63228b3A092fd9Afa6f98b5ee5263fF2d66a0085"
    )
    assert predict_create2_address(factory, salt, openzeppelin_initcode) == (
        "0xd401527dCe68afDef993134702d34DeE0770C84d"
    )
