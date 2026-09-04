#!/usr/bin/env python3
"""Preflight and prepare deterministic deployments through the 0x4e59 singleton.

This utility intentionally does not sign or broadcast transactions. It verifies
the canonical singleton on the target chain and emits the transaction payload
for an approved deployment workflow.
"""

import json
import re
from pathlib import Path
from typing import Type

import click
import requests
from eth_utils import keccak, to_canonical_address, to_checksum_address


CANONICAL_CREATE2_SINGLETON = "0x4e59b44847b379578588920cA78FbF26c0B4956C"
CANONICAL_CREATE2_SINGLETON_RUNTIME = bytes.fromhex(
    "7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe0"
    "3601600081602082378035828234f58015156039578182fd5b8082525050506014"
    "600cf3"
)
CANONICAL_CREATE2_SINGLETON_RUNTIME_LENGTH = 69
CANONICAL_CREATE2_SINGLETON_CODEHASH = bytes.fromhex(
    "2fa86add0aed31f33a762c9d88e807c475bd51d0f52bd0955754b2608f7e4989"
)
HATCHERY_REGISTRY_ID = 5
MISSION_CONTROL_REGISTRY_ID = 2
GET_ADDR_SELECTOR = keccak(text="getAddr(uint256)")[:4]
USER_WALLET_CONFIG_SELECTOR = keccak(text="userWalletConfig()")[:4]
CHAIN_MANIFEST_FIELDS = frozenset(
    (
        "name",
        "cutoverStatus",
        "undyHq",
        "hatcheryRegistryId",
        "missionControlRegistryId",
        "approvedHatcheryAddress",
        "approvedHatcheryRuntimeCodehash",
        "approvedLegacyWalletTemplateAddress",
        "approvedLegacyWalletTemplateRuntimeCodehash",
        "approvedLegacyConfigTemplateAddress",
        "approvedLegacyConfigTemplateRuntimeCodehash",
        "missionControlTemplateGeneration",
        "reason",
    )
)
DEFAULT_RELEASE_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "deployment-manifests"
    / "wallet-v1.json"
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WALLET_FACTORY_SOURCE = Path("contracts/core/userWallet/UserWalletFactory.vy")
WALLET_FACTORY_ADMIN_CONSTANT_NAME = "WALLET_FACTORY_ADMIN"
# Release-blocking sentinel: a factory accidentally deployed with this value
# cannot configure any chain, and release tooling refuses to bless or prepare it.
WALLET_FACTORY_ADMIN_PLACEHOLDER = "0x0000000000000000000000000000000000000000"
WALLET_FACTORY_ADMIN_DECLARATION = re.compile(
    rf"^[ \t]*{WALLET_FACTORY_ADMIN_CONSTANT_NAME}[ \t]*:[ \t]*"
    r"(?:public\([ \t]*)?constant\([ \t]*address[ \t]*\)"
    r"(?:[ \t]*\))?[ \t]*=[ \t]*"
    r"(0x[0-9a-fA-F]{40})[ \t]*(?:#.*)?$",
    re.MULTILINE,
)

# Vyper 0.4.3's create_minimal_proxy_to initcode is 54 bytes. Its creation
# prelude differs from the common 55-byte OpenZeppelin clone initcode.
VYPER_MINIMAL_PROXY_CREATION_PREFIX = bytes.fromhex(
    "602d3d8160093d39f3363d3d373d3d3d363d73"
)
VYPER_MINIMAL_PROXY_RUNTIME_PREFIX = bytes.fromhex("363d3d373d3d3d363d73")
MINIMAL_PROXY_RUNTIME_SUFFIX = bytes.fromhex("5af43d82803e903d91602b57fd5bf3")
VYPER_MINIMAL_PROXY_INITCODE_LENGTH = 54
UINT256_MAX = 2**256 - 1
VALID_STARTER_AGENT_TIERS = frozenset((1, 2, 4))

USER_WALLET_IMPL_V1_SALT_LABEL = "UNDERSCORE_USER_WALLET_IMPL_V1"
USER_WALLET_IMPL_V1_SALT = bytes.fromhex(
    "da9e0e08155d5e49d144d1878faacbcf25fec5790c5ca4cfea6c03788d80329d"
)
USER_WALLET_CONFIG_IMPL_V1_SALT_LABEL = "UNDERSCORE_USER_WALLET_CONFIG_IMPL_V1"
USER_WALLET_CONFIG_IMPL_V1_SALT = bytes.fromhex(
    "c54fd3bd79f3df3298ee349c311ac2d48d1dd8bdbc6e4c795ec0b851c7321227"
)
WALLET_FACTORY_V1_SALT_LABEL = "UNDERSCORE_WALLET_FACTORY_V1"
WALLET_FACTORY_V1_SALT = bytes.fromhex(
    "97049e1342f95e7c1a137d37a08a26977defb40ca4763dd6c6d05cef6bce600a"
)

FIXED_ARTIFACT_SALTS = {
    USER_WALLET_IMPL_V1_SALT_LABEL: USER_WALLET_IMPL_V1_SALT,
    USER_WALLET_CONFIG_IMPL_V1_SALT_LABEL: USER_WALLET_CONFIG_IMPL_V1_SALT,
    WALLET_FACTORY_V1_SALT_LABEL: WALLET_FACTORY_V1_SALT,
}
FIXED_ARTIFACT_NAMES_BY_SALT = {
    USER_WALLET_IMPL_V1_SALT: "userWalletImplementation",
    USER_WALLET_CONFIG_IMPL_V1_SALT: "userWalletConfigImplementation",
    WALLET_FACTORY_V1_SALT: "walletFactory",
}


class SingletonPreflightError(RuntimeError):
    """The canonical singleton cannot safely be used on the target chain."""


class CutoverPreflightError(RuntimeError):
    """The target chain does not match the approved wallet-system cutover."""


class DeploymentInputError(ValueError):
    """A deployment input is not canonically encoded."""


def _decode_hex(value: str | bytes, label: str, *, allow_empty: bool = False) -> bytes:
    if isinstance(value, bytes):
        decoded = value
    elif isinstance(value, str):
        normalized = value.strip()
        if normalized.startswith(("0x", "0X")):
            normalized = normalized[2:]
        try:
            decoded = bytes.fromhex(normalized)
        except ValueError as exc:
            raise DeploymentInputError(f"{label} must be valid hexadecimal bytes") from exc
    else:
        raise DeploymentInputError(f"{label} must be bytes or a hexadecimal string")

    if not decoded and not allow_empty:
        raise DeploymentInputError(f"{label} must not be empty")
    return decoded


def _decode_address(address: str) -> bytes:
    try:
        return to_canonical_address(address)
    except (TypeError, ValueError) as exc:
        raise DeploymentInputError(f"invalid EVM address: {address!r}") from exc


def normalize_salt(salt: str | bytes) -> bytes:
    decoded = _decode_hex(salt, "salt")
    if len(decoded) != 32:
        raise DeploymentInputError(
            f"salt must be exactly 32 bytes, got {len(decoded)} bytes"
        )
    return decoded


def derive_ascii_label_salt(label: str) -> bytes:
    """Return keccak256 of an exact, non-empty ASCII label."""
    if not isinstance(label, str) or not label:
        raise DeploymentInputError("artifact salt label must be a non-empty string")
    try:
        encoded = label.encode("ascii")
    except UnicodeEncodeError as exc:
        raise DeploymentInputError("artifact salt label must contain only ASCII") from exc
    return keccak(encoded)


def _validate_uint256(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DeploymentInputError(f"{label} must be an integer")
    if value < 0 or value > UINT256_MAX:
        raise DeploymentInputError(f"{label} must fit in uint256")
    return value


def _validate_starter_agent_tier(value: int) -> int:
    tier = _validate_uint256(value, "starter agent tier")
    if tier not in VALID_STARTER_AGENT_TIERS:
        raise DeploymentInputError(
            "starter agent tier must be one of PROD=1, STAGING=2, DEV=4"
        )
    return tier


def encode_wallet_salt_preimage(
    owner: str, group_id: int, starter_agent_tier: int
) -> bytes:
    """Encode abi.encode(address,uint256,uint256), never packed encoding."""
    owner_word = b"\x00" * 12 + _decode_address(owner)
    group_word = _validate_uint256(group_id, "group id").to_bytes(32, "big")
    tier_word = _validate_starter_agent_tier(starter_agent_tier).to_bytes(32, "big")
    encoded = owner_word + group_word + tier_word
    assert len(encoded) == 96
    return encoded


def derive_wallet_salt(owner: str, group_id: int, starter_agent_tier: int) -> bytes:
    """Return keccak256(abi.encode(owner, groupId, starterAgentTier))."""
    return keccak(encode_wallet_salt_preimage(owner, group_id, starter_agent_tier))


def validate_canonical_singleton_runtime(code: str | bytes) -> bytes:
    """Validate the exact runtime expected at the canonical singleton address."""
    try:
        runtime = _decode_hex(code, "singleton runtime")
    except DeploymentInputError as exc:
        if isinstance(code, str) and code.strip().lower() in ("", "0x"):
            raise SingletonPreflightError(
                f"canonical CREATE2 singleton is absent at {CANONICAL_CREATE2_SINGLETON}"
            ) from exc
        raise SingletonPreflightError(str(exc)) from exc

    if len(runtime) != CANONICAL_CREATE2_SINGLETON_RUNTIME_LENGTH:
        raise SingletonPreflightError(
            "canonical CREATE2 singleton runtime length mismatch at "
            f"{CANONICAL_CREATE2_SINGLETON}: expected "
            f"{CANONICAL_CREATE2_SINGLETON_RUNTIME_LENGTH} bytes, got {len(runtime)} bytes"
        )

    actual_codehash = keccak(runtime)
    if actual_codehash != CANONICAL_CREATE2_SINGLETON_CODEHASH:
        raise SingletonPreflightError(
            "canonical CREATE2 singleton runtime codehash mismatch at "
            f"{CANONICAL_CREATE2_SINGLETON}: expected "
            f"0x{CANONICAL_CREATE2_SINGLETON_CODEHASH.hex()}, got 0x{actual_codehash.hex()}"
        )

    # Keep an exact-byte assertion in addition to the required hash check. It
    # makes an accidental constant change fail locally rather than relying on
    # collision resistance to explain why the code is canonical.
    if runtime != CANONICAL_CREATE2_SINGLETON_RUNTIME:
        raise SingletonPreflightError(
            f"canonical CREATE2 singleton runtime bytes mismatch at {CANONICAL_CREATE2_SINGLETON}"
        )

    return runtime


def _rpc_call(
    rpc_url: str,
    method: str,
    params: list,
    *,
    timeout: float = 15,
    error_type: Type[RuntimeError] = SingletonPreflightError,
) -> object:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        response = requests.post(rpc_url, json=payload, timeout=timeout)
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise error_type(f"JSON-RPC request failed: {exc}") from exc

    if not isinstance(body, dict):
        raise error_type("JSON-RPC response must be an object")
    if body.get("error") is not None:
        raise error_type(f"JSON-RPC {method} failed: {body['error']}")
    if "result" not in body:
        raise error_type("JSON-RPC response is missing result")
    return body["result"]


def preflight_canonical_singleton(rpc_url: str, *, timeout: float = 15) -> bytes:
    """Fetch and validate the singleton at its one canonical address."""
    code = _rpc_call(
        rpc_url,
        "eth_getCode",
        [CANONICAL_CREATE2_SINGLETON, "latest"],
        timeout=timeout,
    )
    if not isinstance(code, (str, bytes)):
        raise SingletonPreflightError("JSON-RPC eth_getCode result must be hexadecimal bytes")
    return validate_canonical_singleton_runtime(code)


def load_release_manifest(path: Path = DEFAULT_RELEASE_MANIFEST) -> dict:
    try:
        manifest = json.loads(path.read_text())
    except (OSError, UnicodeError, ValueError) as exc:
        raise CutoverPreflightError(f"could not read release manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise CutoverPreflightError("release manifest must be a JSON object")
    return manifest


def validate_wallet_factory_admin_release_gate(
    manifest: dict,
    *,
    repository_root: Path = REPOSITORY_ROOT,
    require_final: bool = False,
) -> str:
    """Match the factory admin literal to the manifest and block placeholders.

    A zero admin is intentionally allowed only in an entirely pending manifest,
    so development can compile and test fail-closed placeholder bytecode without
    allowing any artifact in that address family to be blessed or prepared.
    """
    try:
        artifacts = manifest["artifacts"]
        factory = artifacts["walletFactory"]
        source_value = factory["source"]
        manifest_admin_value = factory["admin"]
    except (KeyError, TypeError) as exc:
        raise CutoverPreflightError(
            "release manifest must declare artifacts.walletFactory source and admin"
        ) from exc

    if not isinstance(artifacts, dict) or not isinstance(factory, dict):
        raise CutoverPreflightError(
            "release manifest artifacts and walletFactory entries must be objects"
        )
    if source_value != WALLET_FACTORY_SOURCE.as_posix():
        raise CutoverPreflightError(
            "wallet factory source must be exactly "
            f"{WALLET_FACTORY_SOURCE.as_posix()}"
        )

    try:
        manifest_admin_bytes = _decode_address(manifest_admin_value)
        manifest_admin = to_checksum_address(manifest_admin_bytes)
    except DeploymentInputError as exc:
        raise CutoverPreflightError(
            f"wallet factory manifest admin is invalid: {exc}"
        ) from exc

    repository_root = repository_root.resolve()
    source_path = (repository_root / WALLET_FACTORY_SOURCE).resolve()
    try:
        source_path.relative_to(repository_root)
        source = source_path.read_text()
    except (OSError, ValueError) as exc:
        raise CutoverPreflightError(
            f"could not read wallet factory source {source_path}: {exc}"
        ) from exc

    declarations = WALLET_FACTORY_ADMIN_DECLARATION.findall(source)
    if len(declarations) != 1:
        raise CutoverPreflightError(
            "wallet factory source must declare exactly one literal "
            f"{WALLET_FACTORY_ADMIN_CONSTANT_NAME}: constant(address)"
        )
    source_admin = to_checksum_address(_decode_address(declarations[0]))
    if source_admin != manifest_admin:
        raise CutoverPreflightError(
            f"wallet factory source admin {source_admin} does not match the "
            f"release manifest admin {manifest_admin}"
        )

    placeholder = to_checksum_address(WALLET_FACTORY_ADMIN_PLACEHOLDER)
    if manifest_admin == placeholder:
        blessed_artifacts = []
        for artifact_name, artifact in artifacts.items():
            if not isinstance(artifact, dict):
                raise CutoverPreflightError(
                    f"release manifest artifact {artifact_name} must be an object"
                )
            if artifact.get("status") != "pending":
                blessed_artifacts.append(artifact_name)
        if blessed_artifacts:
            raise CutoverPreflightError(
                "wallet factory admin placeholder cannot bless ready artifacts: "
                + ", ".join(sorted(blessed_artifacts))
            )
        if require_final:
            raise CutoverPreflightError(
                "wallet factory admin is still the zero-address placeholder; "
                "select and record the final admin before release deployment"
            )

    return manifest_admin


def validate_fixed_artifact_deployment(
    manifest: dict,
    salt: str | bytes,
    initcode: str | bytes,
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> str | None:
    """Require fixed-family initcode to match a ready, final-admin manifest."""
    salt_bytes = normalize_salt(salt)
    artifact_name = FIXED_ARTIFACT_NAMES_BY_SALT.get(salt_bytes)
    if artifact_name is None:
        return None

    validate_wallet_factory_admin_release_gate(
        manifest,
        repository_root=repository_root,
        require_final=True,
    )
    try:
        artifact = manifest["artifacts"][artifact_name]
    except (KeyError, TypeError) as exc:
        raise CutoverPreflightError(
            f"release manifest is missing fixed V1 artifact {artifact_name}"
        ) from exc
    if not isinstance(artifact, dict) or artifact.get("status") != "ready":
        raise CutoverPreflightError(
            f"fixed V1 artifact {artifact_name} is not ready in the release manifest"
        )

    try:
        manifest_salt = normalize_salt(artifact["salt"])
        deployment = artifact["deploymentBytecode"]
        expected_bytes = deployment["bytes"]
        expected_hash = _decode_hex(
            deployment["keccak256"],
            f"{artifact_name} deployment bytecode hash",
        )
        expected_address = artifact["predictedAddress"]
    except (KeyError, TypeError, DeploymentInputError) as exc:
        raise CutoverPreflightError(
            f"ready deployment metadata for {artifact_name} is invalid: {exc}"
        ) from exc
    if manifest_salt != salt_bytes:
        raise CutoverPreflightError(
            f"release manifest salt mismatch for {artifact_name}"
        )
    if (
        isinstance(expected_bytes, bool)
        or not isinstance(expected_bytes, int)
        or expected_bytes <= 0
        or len(expected_hash) != 32
    ):
        raise CutoverPreflightError(
            f"ready deployment metadata for {artifact_name} is invalid"
        )

    initcode_bytes = _decode_hex(initcode, "initcode")
    actual_hash = keccak(initcode_bytes)
    if len(initcode_bytes) != expected_bytes or actual_hash != expected_hash:
        raise CutoverPreflightError(
            f"initcode does not match the ready {artifact_name} deployment metadata"
        )
    predicted_address = predict_create2_address(
        CANONICAL_CREATE2_SINGLETON,
        salt_bytes,
        initcode_bytes,
    )
    try:
        normalized_expected_address = to_checksum_address(
            _decode_address(expected_address)
        )
    except DeploymentInputError as exc:
        raise CutoverPreflightError(
            f"ready deployment metadata for {artifact_name} is invalid: {exc}"
        ) from exc
    if predicted_address != normalized_expected_address:
        raise CutoverPreflightError(
            f"predicted address does not match the ready {artifact_name} manifest"
        )
    return artifact_name


def _decode_rpc_quantity(value: object, label: str) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise CutoverPreflightError(f"{label} must be a hexadecimal JSON-RPC quantity")
    try:
        decoded = int(value[2:], 16)
    except ValueError as exc:
        raise CutoverPreflightError(
            f"{label} must be a hexadecimal JSON-RPC quantity"
        ) from exc
    if not value[2:] or decoded <= 0 or hex(decoded) != value.lower():
        raise CutoverPreflightError(
            f"{label} must be a canonical, positive JSON-RPC quantity"
        )
    return decoded


def _manifest_address_and_codehash(
    chain: dict,
    address_field: str,
    codehash_field: str,
    label: str,
) -> tuple[str, bytes]:
    address_bytes = _decode_address(chain[address_field])
    codehash = _decode_hex(chain[codehash_field], f"{label} runtime codehash")
    if len(codehash) != 32:
        raise DeploymentInputError(
            f"{label} runtime codehash must be exactly 32 bytes"
        )
    if address_bytes == b"\x00" * 20 or codehash == b"\x00" * 32:
        raise DeploymentInputError(
            f"{label} address and runtime codehash must not be placeholders"
        )
    return to_checksum_address(address_bytes), codehash


def _approved_hatchery_cutover(manifest: dict, chain_id: int) -> dict:
    chains = manifest.get("chains")
    if not isinstance(chains, dict):
        raise CutoverPreflightError("release manifest is missing the chains map")

    chain_key = str(chain_id)
    chain = chains.get(chain_key)
    if not isinstance(chain, dict):
        raise CutoverPreflightError(
            f"release manifest has no chain entry for eth_chainId {chain_id}"
        )
    unsupported_fields = set(chain) - CHAIN_MANIFEST_FIELDS
    if unsupported_fields:
        raise CutoverPreflightError(
            f"chain {chain_id} contains unsupported fields: "
            + ", ".join(sorted(unsupported_fields))
        )

    template_generation = chain.get("missionControlTemplateGeneration")
    if template_generation != "legacy-pair":
        raise CutoverPreflightError(
            f"chain {chain_id} MissionControl templates must be legacy-pair; "
            "mixed wallet/config generations are forbidden"
        )

    status = chain.get("cutoverStatus", "missing")
    if status != "ready":
        raise CutoverPreflightError(
            f"Hatchery cutover approval for chain {chain_id} is {status}; expected ready"
        )
    if chain.get("hatcheryRegistryId") != HATCHERY_REGISTRY_ID:
        raise CutoverPreflightError(
            f"Hatchery cutover registry id must be {HATCHERY_REGISTRY_ID}"
        )
    if chain.get("missionControlRegistryId") != MISSION_CONTROL_REGISTRY_ID:
        raise CutoverPreflightError(
            "MissionControl cutover registry id must be "
            f"{MISSION_CONTROL_REGISTRY_ID}"
        )

    try:
        undy_hq_bytes = _decode_address(chain["undyHq"])
        undy_hq_address = to_checksum_address(undy_hq_bytes)
        hatchery_address, hatchery_codehash = _manifest_address_and_codehash(
            chain,
            "approvedHatcheryAddress",
            "approvedHatcheryRuntimeCodehash",
            "approved Hatchery",
        )
        wallet_template_address, wallet_template_codehash = (
            _manifest_address_and_codehash(
                chain,
                "approvedLegacyWalletTemplateAddress",
                "approvedLegacyWalletTemplateRuntimeCodehash",
                "approved legacy wallet template",
            )
        )
        config_template_address, config_template_codehash = (
            _manifest_address_and_codehash(
                chain,
                "approvedLegacyConfigTemplateAddress",
                "approvedLegacyConfigTemplateRuntimeCodehash",
                "approved legacy config template",
            )
        )
    except (KeyError, DeploymentInputError) as exc:
        raise CutoverPreflightError(
            f"invalid Hatchery cutover manifest for chain {chain_id}: {exc}"
        ) from exc
    if undy_hq_bytes == b"\x00" * 20:
        raise CutoverPreflightError(
            "UndyHq must not be a placeholder"
        )
    return {
        "undyHq": undy_hq_address,
        "hatchery": hatchery_address,
        "hatcheryCodehash": hatchery_codehash,
        "walletTemplate": wallet_template_address,
        "walletTemplateCodehash": wallet_template_codehash,
        "configTemplate": config_template_address,
        "configTemplateCodehash": config_template_codehash,
    }


def _decode_abi_address(value: object, label: str) -> str:
    if not isinstance(value, (str, bytes)):
        raise CutoverPreflightError(f"{label} must be hexadecimal bytes")
    try:
        encoded = _decode_hex(value, label)
    except DeploymentInputError as exc:
        raise CutoverPreflightError(str(exc)) from exc
    if len(encoded) != 32 or encoded[:12] != b"\x00" * 12:
        raise CutoverPreflightError(f"{label} must be one ABI-encoded address word")
    return to_checksum_address(encoded[-20:])


def _resolve_registry_address(
    rpc_url: str,
    undy_hq_address: str,
    registry_id: int,
    label: str,
    *,
    timeout: float,
) -> str:
    call_data = "0x" + (
        GET_ADDR_SELECTOR + registry_id.to_bytes(32, "big")
    ).hex()
    resolved = _decode_abi_address(
        _rpc_call(
            rpc_url,
            "eth_call",
            [{"to": undy_hq_address, "data": call_data}, "latest"],
            timeout=timeout,
            error_type=CutoverPreflightError,
        ),
        f"UndyHq getAddr({registry_id}) result",
    )
    if _decode_address(resolved) == b"\x00" * 20:
        raise CutoverPreflightError(
            f"UndyHq registry ID {registry_id} resolves to zero; expected {label}"
        )
    return resolved


def _validate_runtime_codehash(
    rpc_url: str,
    address: str,
    expected_codehash: bytes,
    label: str,
    *,
    timeout: float,
) -> tuple[bytes, bytes]:
    code = _rpc_call(
        rpc_url,
        "eth_getCode",
        [address, "latest"],
        timeout=timeout,
        error_type=CutoverPreflightError,
    )
    if not isinstance(code, (str, bytes)):
        raise CutoverPreflightError(
            f"{label} eth_getCode result must be hexadecimal bytes"
        )
    try:
        runtime = _decode_hex(code, f"{label} runtime")
    except DeploymentInputError as exc:
        if isinstance(code, str) and code.strip().lower() in ("", "0x"):
            raise CutoverPreflightError(
                f"{label} code is absent at {address}"
            ) from exc
        raise CutoverPreflightError(str(exc)) from exc

    actual_codehash = keccak(runtime)
    if actual_codehash != expected_codehash:
        raise CutoverPreflightError(
            f"{label} runtime codehash mismatch at {address}: "
            f"expected 0x{expected_codehash.hex()}, got 0x{actual_codehash.hex()}"
        )
    return runtime, actual_codehash


def _decode_user_wallet_templates(value: object) -> tuple[str, str]:
    if not isinstance(value, (str, bytes)):
        raise CutoverPreflightError(
            "MissionControl userWalletConfig() result must be hexadecimal bytes"
        )
    try:
        encoded = _decode_hex(value, "MissionControl userWalletConfig() result")
    except DeploymentInputError as exc:
        raise CutoverPreflightError(str(exc)) from exc
    if len(encoded) < 64 or len(encoded) % 32 != 0:
        raise CutoverPreflightError(
            "MissionControl userWalletConfig() result must contain at least two "
            "complete ABI words"
        )

    wallet_template = _decode_abi_address(
        encoded[:32], "MissionControl walletTemplate"
    )
    config_template = _decode_abi_address(
        encoded[32:64], "MissionControl configTemplate"
    )
    if (
        _decode_address(wallet_template) == b"\x00" * 20
        or _decode_address(config_template) == b"\x00" * 20
    ):
        raise CutoverPreflightError(
            "MissionControl walletTemplate and configTemplate must both be nonzero"
        )
    return wallet_template, config_template


def preflight_hatchery_cutover(
    rpc_url: str,
    manifest: dict,
    *,
    timeout: float = 15,
) -> dict:
    """Require the live Hatchery and legacy template pair to match approvals."""
    chain_id = _decode_rpc_quantity(
        _rpc_call(
            rpc_url,
            "eth_chainId",
            [],
            timeout=timeout,
            error_type=CutoverPreflightError,
        ),
        "eth_chainId result",
    )
    approved = _approved_hatchery_cutover(manifest, chain_id)
    undy_hq_address = approved["undyHq"]

    hatchery = _resolve_registry_address(
        rpc_url,
        undy_hq_address,
        HATCHERY_REGISTRY_ID,
        "the approved new Hatchery",
        timeout=timeout,
    )
    if hatchery != approved["hatchery"]:
        raise CutoverPreflightError(
            "UndyHq registry ID 5 does not resolve to the approved new Hatchery: "
            f"expected {approved['hatchery']}, got {hatchery}"
        )
    hatchery_runtime, hatchery_codehash = _validate_runtime_codehash(
        rpc_url,
        hatchery,
        approved["hatcheryCodehash"],
        "approved Hatchery",
        timeout=timeout,
    )

    mission_control = _resolve_registry_address(
        rpc_url,
        undy_hq_address,
        MISSION_CONTROL_REGISTRY_ID,
        "MissionControl",
        timeout=timeout,
    )
    wallet_template, config_template = _decode_user_wallet_templates(
        _rpc_call(
            rpc_url,
            "eth_call",
            [
                {
                    "to": mission_control,
                    "data": "0x" + USER_WALLET_CONFIG_SELECTOR.hex(),
                },
                "latest",
            ],
            timeout=timeout,
            error_type=CutoverPreflightError,
        )
    )
    if wallet_template != approved["walletTemplate"]:
        raise CutoverPreflightError(
            "MissionControl walletTemplate does not match the approved legacy "
            f"template: expected {approved['walletTemplate']}, got {wallet_template}"
        )
    if config_template != approved["configTemplate"]:
        raise CutoverPreflightError(
            "MissionControl configTemplate does not match the approved legacy "
            f"template: expected {approved['configTemplate']}, got {config_template}"
        )

    wallet_runtime, wallet_codehash = _validate_runtime_codehash(
        rpc_url,
        wallet_template,
        approved["walletTemplateCodehash"],
        "approved legacy wallet template",
        timeout=timeout,
    )
    config_runtime, config_codehash = _validate_runtime_codehash(
        rpc_url,
        config_template,
        approved["configTemplateCodehash"],
        "approved legacy config template",
        timeout=timeout,
    )
    return {
        "chainId": chain_id,
        "undyHq": undy_hq_address,
        "registryId": HATCHERY_REGISTRY_ID,
        "hatchery": hatchery,
        "runtimeBytes": len(hatchery_runtime),
        "runtimeCodehash": "0x" + hatchery_codehash.hex(),
        "missionControlRegistryId": MISSION_CONTROL_REGISTRY_ID,
        "missionControl": mission_control,
        "legacyTemplates": {
            "walletTemplate": {
                "address": wallet_template,
                "runtimeBytes": len(wallet_runtime),
                "runtimeCodehash": "0x" + wallet_codehash.hex(),
            },
            "configTemplate": {
                "address": config_template,
                "runtimeBytes": len(config_runtime),
                "runtimeCodehash": "0x" + config_codehash.hex(),
            },
        },
        "status": "ok",
    }


def predict_create2_address(deployer: str, salt: str | bytes, initcode: str | bytes) -> str:
    deployer_bytes = _decode_address(deployer)
    salt_bytes = normalize_salt(salt)
    initcode_bytes = _decode_hex(initcode, "initcode")
    digest = keccak(b"\xff" + deployer_bytes + salt_bytes + keccak(initcode_bytes))
    return to_checksum_address(digest[-20:])


def build_singleton_calldata(salt: str | bytes, initcode: str | bytes) -> str:
    """Return 0x4e59 calldata: salt32 followed directly by contract initcode."""
    salt_bytes = normalize_salt(salt)
    initcode_bytes = _decode_hex(initcode, "initcode")
    return "0x" + (salt_bytes + initcode_bytes).hex()


def prepare_singleton_deployment(salt: str | bytes, initcode: str | bytes) -> dict:
    salt_bytes = normalize_salt(salt)
    initcode_bytes = _decode_hex(initcode, "initcode")
    return {
        "singleton": CANONICAL_CREATE2_SINGLETON,
        "singletonRuntimeBytes": CANONICAL_CREATE2_SINGLETON_RUNTIME_LENGTH,
        "singletonRuntimeCodehash": "0x" + CANONICAL_CREATE2_SINGLETON_CODEHASH.hex(),
        "salt": "0x" + salt_bytes.hex(),
        "initcodeBytes": len(initcode_bytes),
        "initcodeHash": "0x" + keccak(initcode_bytes).hex(),
        "predictedAddress": predict_create2_address(
            CANONICAL_CREATE2_SINGLETON, salt_bytes, initcode_bytes
        ),
        "transaction": {
            "to": CANONICAL_CREATE2_SINGLETON,
            "data": build_singleton_calldata(salt_bytes, initcode_bytes),
            "value": "0x0",
        },
    }


def vyper_minimal_proxy_initcode(implementation: str) -> bytes:
    implementation_bytes = _decode_address(implementation)
    initcode = (
        VYPER_MINIMAL_PROXY_CREATION_PREFIX
        + implementation_bytes
        + MINIMAL_PROXY_RUNTIME_SUFFIX
    )
    assert len(initcode) == VYPER_MINIMAL_PROXY_INITCODE_LENGTH
    return initcode


def predict_vyper_minimal_proxy_address(
    factory: str, salt: str | bytes, implementation: str
) -> str:
    return predict_create2_address(factory, salt, vyper_minimal_proxy_initcode(implementation))


def predict_vyper_wallet_address(
    factory: str,
    implementation: str,
    owner: str,
    group_id: int,
    starter_agent_tier: int,
) -> str:
    salt = derive_wallet_salt(owner, group_id, starter_agent_tier)
    return predict_vyper_minimal_proxy_address(factory, salt, implementation)


def _read_initcode(initcode: str | None, initcode_file: Path | None) -> str:
    if (initcode is None) == (initcode_file is None):
        raise click.ClickException("provide exactly one of --initcode or --initcode-file")
    if initcode_file is not None:
        try:
            return initcode_file.read_text().strip()
        except OSError as exc:
            raise click.ClickException(f"could not read initcode file: {exc}") from exc
    assert initcode is not None
    return initcode


@click.group()
def cli():
    """Verify 0x4e59 and prepare deterministic deployment payloads."""


@cli.command("artifact-salts")
def artifact_salts():
    """Print the fixed V1 singleton deployment salts."""
    click.echo(
        json.dumps(
            {
                label: "0x" + salt.hex()
                for label, salt in FIXED_ARTIFACT_SALTS.items()
            },
            indent=2,
        )
    )


@cli.command("cutover-preflight")
@click.option(
    "--rpc-url",
    envvar="UNDERSCORE_RPC_URL",
    required=True,
    help="Target-chain JSON-RPC URL (or set UNDERSCORE_RPC_URL).",
)
@click.option(
    "--manifest",
    type=click.Path(path_type=Path, dir_okay=False),
    default=DEFAULT_RELEASE_MANIFEST,
    show_default=True,
)
@click.option("--timeout", type=float, default=15, show_default=True)
def cutover_preflight(rpc_url: str, manifest: Path, timeout: float):
    """Verify the approved Hatchery and live legacy MissionControl templates."""
    try:
        release_manifest = load_release_manifest(manifest)
        validate_wallet_factory_admin_release_gate(
            release_manifest,
            require_final=True,
        )
        result = preflight_hatchery_cutover(
            rpc_url, release_manifest, timeout=timeout
        )
    except CutoverPreflightError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, indent=2))


@cli.command()
@click.option(
    "--rpc-url",
    envvar="UNDERSCORE_RPC_URL",
    required=True,
    help="Target-chain JSON-RPC URL (or set UNDERSCORE_RPC_URL).",
)
@click.option("--timeout", type=float, default=15, show_default=True)
def preflight(rpc_url: str, timeout: float):
    """Fail unless the exact canonical singleton runtime is present."""
    try:
        runtime = preflight_canonical_singleton(rpc_url, timeout=timeout)
    except SingletonPreflightError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        json.dumps(
            {
                "address": CANONICAL_CREATE2_SINGLETON,
                "runtimeBytes": len(runtime),
                "runtimeCodehash": "0x" + keccak(runtime).hex(),
                "status": "ok",
            },
            indent=2,
        )
    )


@cli.command()
@click.option(
    "--rpc-url",
    envvar="UNDERSCORE_RPC_URL",
    required=True,
    help="Target-chain JSON-RPC URL (or set UNDERSCORE_RPC_URL).",
)
@click.option("--salt", required=True, help="Exactly 32 bytes as hexadecimal.")
@click.option("--initcode", help="Contract creation bytecode as hexadecimal.")
@click.option(
    "--initcode-file",
    type=click.Path(path_type=Path, dir_okay=False),
    help="File containing contract creation bytecode as hexadecimal.",
)
@click.option(
    "--manifest",
    type=click.Path(path_type=Path, dir_okay=False),
    default=DEFAULT_RELEASE_MANIFEST,
    show_default=True,
)
@click.option("--timeout", type=float, default=15, show_default=True)
def prepare(
    rpc_url: str,
    salt: str,
    initcode: str | None,
    initcode_file: Path | None,
    manifest: Path,
    timeout: float,
):
    """Preflight the chain, then print a deployment transaction payload."""
    initcode_value = _read_initcode(initcode, initcode_file)
    try:
        salt_bytes = normalize_salt(salt)
        if salt_bytes in FIXED_ARTIFACT_SALTS.values():
            validate_fixed_artifact_deployment(
                load_release_manifest(manifest),
                salt_bytes,
                initcode_value,
            )
        preflight_canonical_singleton(rpc_url, timeout=timeout)
        plan = prepare_singleton_deployment(salt_bytes, initcode_value)
    except (
        CutoverPreflightError,
        DeploymentInputError,
        SingletonPreflightError,
    ) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(plan, indent=2))


@cli.command("predict-vyper-clone")
@click.option("--factory", required=True, help="EIP-1167 CREATE2 factory address.")
@click.option("--implementation", required=True, help="Fixed implementation address.")
@click.option("--salt", required=True, help="Exactly 32 bytes as hexadecimal.")
def predict_vyper_clone(factory: str, implementation: str, salt: str):
    """Predict a Vyper 0.4.3 create_minimal_proxy_to CREATE2 address."""
    try:
        initcode = vyper_minimal_proxy_initcode(implementation)
        predicted = predict_create2_address(factory, salt, initcode)
    except DeploymentInputError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        json.dumps(
            {
                "factory": to_checksum_address(_decode_address(factory)),
                "implementation": to_checksum_address(_decode_address(implementation)),
                "salt": "0x" + normalize_salt(salt).hex(),
                "initcodeBytes": len(initcode),
                "initcodeHash": "0x" + keccak(initcode).hex(),
                "predictedAddress": predicted,
            },
            indent=2,
        )
    )


@cli.command("predict-vyper-wallet")
@click.option("--factory", required=True, help="EIP-1167 CREATE2 factory address.")
@click.option("--implementation", required=True, help="Fixed implementation address.")
@click.option("--owner", required=True, help="Wallet owner address.")
@click.option("--group-id", required=True, type=click.IntRange(min=0))
@click.option(
    "--starter-agent-tier",
    required=True,
    type=click.IntRange(min=0),
    help="Numeric Vyper flag value: PROD=1, STAGING=2, DEV=4.",
)
def predict_vyper_wallet(
    factory: str,
    implementation: str,
    owner: str,
    group_id: int,
    starter_agent_tier: int,
):
    """Derive the protocol wallet salt and predict its proxy address."""
    try:
        preimage = encode_wallet_salt_preimage(owner, group_id, starter_agent_tier)
        salt = keccak(preimage)
        initcode = vyper_minimal_proxy_initcode(implementation)
        predicted = predict_create2_address(factory, salt, initcode)
    except DeploymentInputError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        json.dumps(
            {
                "factory": to_checksum_address(_decode_address(factory)),
                "implementation": to_checksum_address(_decode_address(implementation)),
                "owner": to_checksum_address(_decode_address(owner)),
                "groupId": group_id,
                "starterAgentTier": starter_agent_tier,
                "saltEncoding": "abi.encode(address,uint256,uint256)",
                "saltPreimageBytes": len(preimage),
                "saltPreimage": "0x" + preimage.hex(),
                "salt": "0x" + salt.hex(),
                "cloneInitcodeBytes": len(initcode),
                "cloneInitcodeHash": "0x" + keccak(initcode).hex(),
                "predictedAddress": predicted,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    cli()
