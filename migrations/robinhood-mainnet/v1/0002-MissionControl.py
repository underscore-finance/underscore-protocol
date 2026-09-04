from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import (
    deploy_and_register,
    install_defaults_materialization_dependency,
    materialize_contract_runtime,
)

MISSION_CONTROL_RUNTIME_CODEHASH = (
    "0x315f3a118800f228ed7df13ffe824220a28cae87431dff234dc2ab6a4eeaa096"
)


def _validate_mission_control(mission_control, hq, defaults):
    if str(mission_control.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError("Robinhood MissionControl is bound to the wrong UndyHq")
    for config_name in (
        "userWalletConfig",
        "agentConfig",
        "managerConfig",
        "payeeConfig",
        "chequeConfig",
        "ripeRewardsConfig",
    ):
        actual = getattr(mission_control, config_name)()
        expected = getattr(defaults, config_name)()
        if actual != expected:
            raise RuntimeError(
                f"Robinhood MissionControl has unexpected {config_name}"
            )
    if mission_control.numSecuritySigners() != 1:
        raise RuntimeError(
            "Robinhood MissionControl has unexpected security signers"
        )
    if mission_control.numWhitelistedCreators() != 1:
        raise RuntimeError(
            "Robinhood MissionControl has unexpected whitelisted creators"
        )
    if mission_control.isPaused() or mission_control.canMintUndy():
        raise RuntimeError(
            "Robinhood MissionControl has unexpected department flags"
        )


def migrate(migration: Migration):
    migration.log.h2("Mission Control")
    hq = migration.get_contract("UndyHq")
    defaults = migration.get_contract("DefaultsRobinhood")
    deploy_and_register(
        migration,
        hq,
        name="MissionControl",
        args=(hq, defaults),
        description="Mission Control",
        expected_id=2,
        expected_prefix=(("Ledger", migration.get_address("Ledger")),),
        context="before Robinhood MissionControl deployment",
        validate=lambda mission_control: _validate_mission_control(
            mission_control,
            hq,
            defaults,
        ),
        expected_runtime_codehash=MISSION_CONTROL_RUNTIME_CODEHASH,
        runtime_builder=lambda: materialize_contract_runtime(
            migration,
            "MissionControl",
            (hq, defaults),
            prepare=lambda: install_defaults_materialization_dependency(
                migration,
                defaults,
            ),
        ),
    )
