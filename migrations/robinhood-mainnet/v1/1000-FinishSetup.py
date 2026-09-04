import boa
from eth_utils import keccak

from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import require_registry_prefix


CORE_REGISTRY = (
    (1, "Ledger"),
    (2, "MissionControl"),
    (3, "LegoBook"),
    (4, "Switchboard"),
    (5, "Hatchery"),
    (6, "LootDistributor"),
    (7, "Appraiser"),
    (8, "WalletBackpack"),
    (9, "Billing"),
)

SWITCHBOARD_REGISTRY = (
    (1, "SwitchboardAlpha"),
    (2, "SwitchboardBravo"),
)


def _execute_true(migration: Migration, transaction, *args, action: str):
    result = migration.execute(transaction, *args, no_retry=True)
    if result is not True:
        raise RuntimeError(f"{action}: got {result!r}")


def _require_governance(migration: Migration) -> str:
    address = migration.blueprint.INTEGRATION_ADDYS.get("GOVERNANCE")
    approved_codehash = migration.blueprint.INTEGRATION_ADDYS.get(
        "GOVERNANCE_CODEHASH"
    )
    zero_address = migration.blueprint.CONSTANTS.ZERO_ADDRESS
    zero_hash = "0x" + "00" * 32
    if not address or address.lower() == zero_address.lower():
        raise RuntimeError(
            "Robinhood GOVERNANCE is not approved; refusing to finish UndyHq setup"
        )
    if not approved_codehash or approved_codehash.lower() == zero_hash:
        raise RuntimeError(
            "Robinhood GOVERNANCE_CODEHASH is not approved; "
            "refusing to finish UndyHq setup"
        )
    runtime = boa.env.get_code(address)
    if not runtime:
        raise RuntimeError(
            "Robinhood GOVERNANCE has no code; refusing to finish UndyHq setup"
        )
    live_codehash = "0x" + keccak(runtime).hex()
    if live_codehash.lower() != approved_codehash.lower():
        raise RuntimeError(
            "Robinhood GOVERNANCE live codehash does not match its approval"
        )
    return address


def _require_registry(migration: Migration, registry, entries, label: str):
    expected_entries = []
    for reg_id, contract_name in entries:
        try:
            expected = migration.get_address(contract_name)
        except (KeyError, TypeError) as exc:
            raise RuntimeError(
                f"{contract_name} is missing from the prior manifest"
            ) from exc

        expected_entries.append((contract_name, expected))
        if not boa.env.get_code(expected):
            raise RuntimeError(
                f"{contract_name} has no code; refusing to finish setup"
            )

    require_registry_prefix(
        registry,
        tuple(expected_entries),
        f"before finishing Robinhood {label} setup",
    )


def _require_wallet_backpack_items(migration: Migration, wallet_backpack):
    items = (
        ("Kernel", wallet_backpack.kernel),
        ("Sentinel", wallet_backpack.sentinel),
        ("HighCommand", wallet_backpack.highCommand),
        ("Paymaster", wallet_backpack.paymaster),
        ("ChequeBook", wallet_backpack.chequeBook),
        ("Migrator", wallet_backpack.migrator),
        ("ActionDataProvider", wallet_backpack.actionDataProvider),
    )
    contracts = {}
    ledger = migration.get_contract("Ledger")
    for name, getter in items:
        try:
            expected = migration.get_address(name)
        except (KeyError, TypeError) as exc:
            raise RuntimeError(f"{name} is missing from the prior manifest") from exc
        actual = getter()
        if str(actual).lower() != str(expected).lower():
            raise RuntimeError(
                f"WalletBackpack {name} is {actual}, expected {expected}"
            )
        if not boa.env.get_code(actual):
            raise RuntimeError(f"WalletBackpack {name} has no code")
        if ledger.isRegisteredBackpackItem(actual) is not True:
            raise RuntimeError(f"Ledger has not registered WalletBackpack {name}")
        contracts[name] = migration.get_contract(name)

    expected_flags = (
        ("HighCommand.canInstantAddManager", contracts["HighCommand"].canInstantAddManager(), True),
        ("Paymaster.canInstantAddPayee", contracts["Paymaster"].canInstantAddPayee(), True),
        (
            "Paymaster.canInstantSetGlobalPayeeSettings",
            contracts["Paymaster"].canInstantSetGlobalPayeeSettings(),
            True,
        ),
        (
            "ChequeBook.canInstantSetChequeSettings",
            contracts["ChequeBook"].canInstantSetChequeSettings(),
            True,
        ),
        ("Migrator.instantMigrationEnabled", contracts["Migrator"].instantMigrationEnabled(), False),
    )
    for label, actual, expected in expected_flags:
        if actual is not expected:
            raise RuntimeError(f"{label} is {actual!r}, expected {expected!r}")

    if wallet_backpack.actionId() != 8:
        raise RuntimeError(
            f"WalletBackpack actionId is {wallet_backpack.actionId()}, expected 8"
        )
    for action_id in range(1, 8):
        if wallet_backpack.pendingActions(action_id).confirmBlock != 0:
            raise RuntimeError(
                f"WalletBackpack action {action_id} is still pending"
            )
    for backpack_type in (1, 2, 4, 8, 16, 32, 64):
        if wallet_backpack.pendingUpdates(backpack_type).actionId != 0:
            raise RuntimeError(
                f"WalletBackpack type {backpack_type} update is still pending"
            )


def _require_child_governance(zero_address: str, children):
    for label, child in children:
        if str(child.governance()).lower() != zero_address.lower():
            raise RuntimeError(f"{label} local governance is not relinquished")
        if child.numGovChanges() != 0:
            raise RuntimeError(f"{label} has unexpected governance changes")
        if child.hasPendingGovChange():
            raise RuntimeError(f"{label} has a pending governance change")


def _require_switchboard_actions_pristine(switchboard_alpha, switchboard_bravo):
    for label, child in (
        ("SwitchboardAlpha", switchboard_alpha),
        ("SwitchboardBravo", switchboard_bravo),
    ):
        if child.actionId() != 1:
            raise RuntimeError(f"{label} actionId is {child.actionId()}, expected 1")


def _lock_state(contract, kind: str, label: str):
    if kind == "action":
        current = contract.actionTimeLock()
        expected = contract.minActionTimeLock()
        transaction = contract.setActionTimeLockAfterSetup
    else:
        current = contract.registryChangeTimeLock()
        expected = contract.minRegistryTimeLock()
        transaction = contract.setRegistryTimeLockAfterSetup

    if current not in (0, expected):
        raise RuntimeError(
            f"{label} has conflicting lock {current}; expected 0 or {expected}"
        )
    return contract, kind, label, current, expected, transaction


def _apply_lock(migration: Migration, state):
    contract, kind, label, current, expected, transaction = state
    if current == expected:
        return
    _execute_true(migration, transaction, action=f"failed to lock {label}")
    if kind == "action":
        actual = contract.actionTimeLock()
    else:
        actual = contract.registryChangeTimeLock()
    if actual != expected:
        raise RuntimeError(
            f"{label} post-lock value is {actual}, expected {expected}"
        )


def _config_values(config):
    return (
        config.description,
        config.canMintUndy,
        config.canSetTokenBlacklist,
    )


def _classify_hq_config(hq):
    description = hq.getAddrDescription(4)
    current = _config_values(hq.hqConfig(4))
    pending = hq.pendingHqConfig(4)
    has_pending = pending.confirmBlock != 0
    pending_values = _config_values(pending.newHqConfig)
    initial = ("", False, False)
    final = (description, False, True)

    if current == final and not has_pending:
        return "final", final
    if current == initial and not has_pending:
        return "initial", final
    if current == initial and has_pending and pending_values == final:
        return "pending", final
    raise RuntimeError(
        "UndyHq ID 4 permissions conflict with both the initial and exact final state"
    )


def _classify_hq_governance(migration: Migration, hq, governance: str):
    if hq.hasPendingGovChange():
        raise RuntimeError("UndyHq has a pending governance change")
    current = str(hq.governance())
    changes = hq.numGovChanges()
    current_timelock = hq.govChangeTimeLock()
    expected_timelock = hq.minGovChangeTimeLock()
    deployer = str(migration.account.address)

    if (
        current.lower() == governance.lower()
        and changes == 1
        and current_timelock == expected_timelock
    ):
        return "final", expected_timelock
    if current.lower() == deployer.lower() and changes == 0 and current_timelock == 0:
        return "initial", expected_timelock
    raise RuntimeError(
        "UndyHq governance conflicts with both the deployment and exact final state"
    )


def migrate(migration: Migration):
    migration.log.h2("Finish Setup")

    # This is intentionally the first chain-state precondition. The Robinhood
    # profile omits governance until a contract address is approved, so a
    # partial profile cannot lock or mutate any protocol contract.
    governance = _require_governance(migration)

    hq = migration.get_contract("UndyHq")
    switchboard = migration.get_contract("Switchboard")
    _require_registry(migration, hq, CORE_REGISTRY, "UndyHq")
    _require_registry(
        migration,
        switchboard,
        SWITCHBOARD_REGISTRY,
        "Switchboard",
    )

    switchboard_alpha = migration.get_contract("SwitchboardAlpha")
    switchboard_bravo = migration.get_contract("SwitchboardBravo")
    wallet_backpack = migration.get_contract("WalletBackpack")
    lego_book = migration.get_contract("LegoBook")
    _require_wallet_backpack_items(migration, wallet_backpack)
    _require_child_governance(
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        (
            ("Switchboard", switchboard),
            ("LegoBook", lego_book),
            ("WalletBackpack", wallet_backpack),
            ("SwitchboardAlpha", switchboard_alpha),
            ("SwitchboardBravo", switchboard_bravo),
        ),
    )
    _require_switchboard_actions_pristine(
        switchboard_alpha,
        switchboard_bravo,
    )

    # Positional transaction logs are not evidence of on-chain completion.
    # Every step below reconciles independently authenticated on-chain state.
    migration.discard_transaction_replay()
    lock_states = (
        _lock_state(switchboard_alpha, "action", "SwitchboardAlpha"),
        _lock_state(switchboard_bravo, "action", "SwitchboardBravo"),
        _lock_state(wallet_backpack, "action", "WalletBackpack"),
        _lock_state(switchboard, "registry", "Switchboard registry"),
        _lock_state(lego_book, "registry", "LegoBook registry"),
    )
    hq_lock_state = _lock_state(hq, "registry", "UndyHq registry")
    config_state, final_hq_config = _classify_hq_config(hq)
    governance_state, expected_gov_timelock = _classify_hq_governance(
        migration,
        hq,
        governance,
    )

    all_locks_final = all(state[3] == state[4] for state in lock_states)
    all_final = (
        all_locks_final
        and hq_lock_state[3] == hq_lock_state[4]
        and config_state == "final"
    )
    if governance_state == "final":
        if not all_final:
            raise RuntimeError(
                "UndyHq governance is final but setup state is incomplete; "
                "manual reconciliation is required"
            )
        return

    if hq_lock_state[3] == hq_lock_state[4] and config_state == "initial":
        raise RuntimeError(
            "UndyHq registry is already locked while ID 4 permissions are unset; "
            "manual reconciliation is required"
        )

    # DefaultsRobinhood deliberately leaves the production starter agent at
    # zero and the creator whitelist empty. Do not create or install a starter
    # agent implicitly: public wallet creation remains fail closed until a
    # separate governance-approved configuration action.
    for state in lock_states:
        _apply_lock(migration, state)

    # Switchboard may configure token blacklists.
    if config_state == "initial":
        initiate_result = migration.execute(
            hq.initiateHqConfigChange,
            4,
            False,
            True,
            no_retry=True,
        )
        if initiate_result is not None:
            raise RuntimeError(
                "staging Switchboard HQ permissions returned an unexpected value: "
                f"{initiate_result!r}"
            )
        pending = hq.pendingHqConfig(4)
        if (
            pending.confirmBlock == 0
            or _config_values(pending.newHqConfig) != final_hq_config
        ):
            raise RuntimeError(
                "Switchboard HQ permission staging did not produce the exact pending config"
            )
        config_state = "pending"
    if config_state == "pending":
        _execute_true(
            migration,
            hq.confirmHqConfigChange,
            4,
            action="failed to confirm Switchboard HQ permissions",
        )
    if _config_values(hq.hqConfig(4)) != final_hq_config:
        raise RuntimeError("Switchboard HQ permissions failed their final postcheck")
    if hq.hasPendingHqConfigChange(4):
        raise RuntimeError("Switchboard HQ permissions remain pending after confirmation")

    _apply_lock(migration, hq_lock_state)
    _execute_true(
        migration,
        hq.finishUndyHqSetup,
        governance,
        action="failed to transfer UndyHq governance",
    )
    if (
        str(hq.governance()).lower() != governance.lower()
        or hq.numGovChanges() != 1
        or hq.govChangeTimeLock() != expected_gov_timelock
    ):
        raise RuntimeError("UndyHq governance handoff failed its final postcheck")
