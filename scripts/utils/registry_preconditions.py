import boa
from eth_utils import keccak


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
DEFAULT_REGISTRY_DESCRIPTIONS = {
    "MissionControl": "Mission Control",
    "LegoBook": "Lego Book",
    "LootDistributor": "Loot Distributor",
    "WalletBackpack": "Wallet Backpack",
}

def _address(value):
    return str(value.address if hasattr(value, "address") else value)


def require_live_code(address, context: str):
    address = _address(address)
    if not boa.env.get_code(address):
        raise RuntimeError(f"{context}: {address} has no code")


def require_registry_prefix(registry, expected_entries, context: str):
    """Fail closed unless a registry contains exactly the expected prefix."""
    expected_next_id = len(expected_entries) + 1
    actual_next_id = registry.numAddrs()
    if actual_next_id != expected_next_id:
        raise RuntimeError(
            f"{context}: registry next ID is {actual_next_id}, "
            f"expected {expected_next_id}"
        )

    for registry_id, entry in enumerate(
        expected_entries,
        start=1,
    ):
        name, expected_address, description = _registry_entry(entry)
        actual_address = str(registry.getAddr(registry_id))
        if actual_address.lower() != str(expected_address).lower():
            raise RuntimeError(
                f"{context}: registry ID {registry_id} is {actual_address}, "
                f"expected {name} at {expected_address}"
            )
        require_live_code(
            actual_address,
            f"{context}: registry ID {registry_id} ({name})",
        )
        _require_registry_entry_state(
            registry,
            registry_id,
            description,
            context,
        )


def _registry_entry(entry):
    if len(entry) == 3:
        return entry
    name, address = entry
    return name, address, DEFAULT_REGISTRY_DESCRIPTIONS.get(name, name)


def _require_zero_struct(data, fields, context: str):
    for field in fields:
        value = getattr(data, field)
        if value in (0, False, ""):
            continue
        if str(value).lower() == ZERO_ADDRESS.lower():
            continue
        if value not in (0, False, ZERO_ADDRESS, ""):
            raise RuntimeError(f"{context}: latent {field} is {value!r}")


def _require_registry_entry_state(
    registry,
    registry_id: int,
    expected_description: str,
    context: str,
):
    info = registry.getAddrInfo(registry_id)
    if info.version != 1 or info.description != expected_description:
        raise RuntimeError(
            f"{context}: registry ID {registry_id} has version "
            f"{info.version} and description {info.description!r}; expected "
            f"version 1 and {expected_description!r}"
        )
    _require_zero_struct(
        registry.pendingAddrUpdate(registry_id),
        ("newAddr", "initiatedBlock", "confirmBlock"),
        f"{context}: registry ID {registry_id} pending update",
    )
    _require_zero_struct(
        registry.pendingAddrDisable(registry_id),
        ("initiatedBlock", "confirmBlock"),
        f"{context}: registry ID {registry_id} pending disable",
    )
    if hasattr(registry, "hasPendingHqConfigChange") and (
        registry.hasPendingHqConfigChange(registry_id)
    ):
        raise RuntimeError(
            f"{context}: registry ID {registry_id} has a pending HQ config"
        )


def _optional_manifest_entry(migration, name: str):
    return migration.get_manifest_entry(name)


def _require_manifest_runtime(
    migration,
    name: str,
    address,
    expected_runtime_codehash: str,
    expected_runtime: bytes,
    context: str,
):
    entry = _optional_manifest_entry(migration, name)
    if entry is None:
        raise RuntimeError(
            f"{context}: no authenticated manifest entry exists for {name}"
        )
    expected_hash = entry.get("runtime_codehash")
    if not expected_hash:
        raise RuntimeError(
            f"{context}: manifest entry for {name} has no runtime_codehash"
        )
    if str(expected_hash).lower() != expected_runtime_codehash.lower():
        raise RuntimeError(
            f"{context}: manifest runtime codehash for {name} is "
            f"{expected_hash}, expected approved hash "
            f"{expected_runtime_codehash}"
        )
    manifest_address = entry.get("address")
    if str(manifest_address).lower() != _address(address).lower():
        raise RuntimeError(
            f"{context}: {name} address is {_address(address)}, but the live "
            f"manifest records {manifest_address}"
        )
    runtime = boa.env.get_code(_address(address))
    if not runtime:
        raise RuntimeError(f"{context}: {_address(address)} has no code")
    actual_hash = "0x" + keccak(runtime).hex()
    if actual_hash.lower() != expected_runtime_codehash.lower():
        raise RuntimeError(
            f"{context}: {name} runtime codehash is {actual_hash}, expected "
            f"approved hash {expected_runtime_codehash}"
        )
    if runtime != expected_runtime:
        raise RuntimeError(
            f"{context}: {name} runtime does not match materialized source"
        )


def _require_pending_registration(registry, address, description: str, context: str):
    pending = registry.pendingNewAddr(address)
    if pending.confirmBlock == 0:
        return False
    if pending.description != description:
        raise RuntimeError(
            f"{context}: pending description is {pending.description!r}, "
            f"expected {description!r}"
        )
    return True


def deploy_and_register(
    migration,
    registry,
    *,
    name: str,
    args,
    description: str,
    expected_id: int,
    expected_prefix,
    context: str,
    validate,
    expected_runtime_codehash: str,
    expected_runtime: bytes,
    maximum_next_id=None,
):
    """Resume a deployment only from its authenticated live registry state."""
    materialized_hash = "0x" + keccak(expected_runtime).hex()
    if materialized_hash.lower() != expected_runtime_codehash.lower():
        raise RuntimeError(
            f"{context}: materialized {name} runtime codehash is "
            f"{materialized_hash}, expected approved hash "
            f"{expected_runtime_codehash}"
        )
    migration.discard_transaction_replay()

    if maximum_next_id is None:
        maximum_next_id = expected_id + 1
    actual_next_id = registry.numAddrs()
    if actual_next_id < expected_id or actual_next_id > maximum_next_id:
        raise RuntimeError(
            f"{context}: registry next ID is {actual_next_id}, expected a "
            f"resumable value from {expected_id} through {maximum_next_id}"
        )

    # Every already-confirmed dependency remains exact and live before any
    # resume action is selected.
    require_registry_prefix_for_resume(
        registry,
        expected_prefix,
        actual_next_id,
        maximum_next_id,
        context,
    )

    manifest_entry = _optional_manifest_entry(migration, name)
    manifest_address = None if manifest_entry is None else manifest_entry.get("address")
    if actual_next_id >= expected_id + 1:
        confirmed_address = str(registry.getAddr(expected_id))
        _require_registry_entry_state(
            registry,
            expected_id,
            description,
            context,
        )
        _require_manifest_runtime(
            migration,
            name,
            confirmed_address,
            expected_runtime_codehash,
            expected_runtime,
            f"{context}: confirmed {name}",
        )
        contract = migration.register_existing(name, confirmed_address, *args)
        validate(contract)
        if registry.pendingNewAddr(confirmed_address).confirmBlock != 0:
            raise RuntimeError(
                f"{context}: confirmed {name} still has a pending registration"
            )
        return contract

    if manifest_address is None:
        migration.preflight_contract_manifest(name, args)
        contract = migration.deploy(name, *args, no_retry=True)
        _require_manifest_runtime(
            migration,
            name,
            contract.address,
            expected_runtime_codehash,
            expected_runtime,
            f"{context}: deployed {name}",
        )
    else:
        _require_manifest_runtime(
            migration,
            name,
            manifest_address,
            expected_runtime_codehash,
            expected_runtime,
            f"{context}: manifest {name}",
        )
        contract = migration.register_existing(name, manifest_address, *args)

    validate(contract)

    address = _address(contract)
    registered_id = registry.getRegId(address)
    if registered_id != 0:
        raise RuntimeError(
            f"{context}: {name} is unexpectedly registered at ID "
            f"{registered_id}, expected 0 before confirmation"
        )

    if registry.registryChangeTimeLock() != 0:
        raise RuntimeError(
            f"{context}: parent registry timelock is active; refusing a "
            "non-idempotent registration"
        )

    if not _require_pending_registration(registry, address, description, context):
        started = migration.execute(
            registry.startAddNewAddressToRegistry,
            contract,
            description,
            no_retry=True,
        )
        if started is not True:
            raise RuntimeError(
                f"failed to start registration for {description}: got {started!r}"
            )
        if not _require_pending_registration(
            registry,
            address,
            description,
            context,
        ):
            raise RuntimeError(
                f"{context}: {name} registration start did not create pending state"
            )

    registry_id = migration.execute(
        registry.confirmNewAddressToRegistry,
        contract,
        no_retry=True,
    )
    if isinstance(registry_id, bool) or registry_id != expected_id:
        raise RuntimeError(
            f"registered {description} at ID {registry_id!r}, "
            f"expected {expected_id}"
        )
    require_registry_prefix(
        registry,
        (*expected_prefix, (name, address)),
        context,
    )
    return contract


def require_registry_prefix_for_resume(
    registry,
    expected_entries,
    actual_next_id: int,
    maximum_next_id: int,
    context: str,
):
    """Validate the confirmed prefix while allowing the current ID on resume."""
    expected_prior_next_id = len(expected_entries) + 1
    if (
        actual_next_id < expected_prior_next_id
        or actual_next_id > maximum_next_id
    ):
        raise RuntimeError(
            f"{context}: registry next ID is {actual_next_id}, expected a "
            f"resumable value from {expected_prior_next_id} through "
            f"{maximum_next_id}"
        )
    for registry_id, entry in enumerate(
        expected_entries,
        start=1,
    ):
        name, expected_address, description = _registry_entry(entry)
        actual_address = str(registry.getAddr(registry_id))
        if actual_address.lower() != str(expected_address).lower():
            raise RuntimeError(
                f"{context}: registry ID {registry_id} is {actual_address}, "
                f"expected {name} at {expected_address}"
            )
        require_live_code(
            actual_address,
            f"{context}: registry ID {registry_id} ({name})",
        )
        _require_registry_entry_state(
            registry,
            registry_id,
            description,
            context,
        )


def register_address(
    migration,
    registry,
    address,
    description: str,
    expected_id: int,
):
    """Register an address without making execution depend on Python asserts."""
    started = migration.execute(
        registry.startAddNewAddressToRegistry,
        address,
        description,
        no_retry=True,
    )
    if started is not True:
        raise RuntimeError(
            f"failed to start registration for {description}: got {started!r}"
        )

    registry_id = migration.execute(
        registry.confirmNewAddressToRegistry,
        address,
        no_retry=True,
    )
    if isinstance(registry_id, bool) or registry_id != expected_id:
        raise RuntimeError(
            f"registered {description} at ID {registry_id!r}, "
            f"expected {expected_id}"
        )

    return registry_id
